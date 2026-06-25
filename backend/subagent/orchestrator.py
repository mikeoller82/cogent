"""Orchestrator — receives tasks, plans, spawns subagents, aggregates results.

Lifecycle:
1. PLANNING — LLM call to decompose task into subtasks + agent roles
2. FACTORY — create Subagent instances from the plan
3. EXECUTION — wave-based concurrent subagent runs (via asyncio.gather + Semaphore)
4. AGGREGATION — collect results, decide if more agents needed (loop)
5. ASSEMBLY — final output from all results

All events are yielded as SSE-compatible dicts for streaming to the frontend.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from .types import (
    SubagentRole, SubagentStatus, SubtaskSpec,
    SubagentResult, DecompositionPlan,
    sse_orchestrator_plan, sse_subagent_start,
    sse_subagent_complete, sse_subagent_fail,
)
from .task_graph import TaskGraph
from .agent_factory import AgentFactory

logger = logging.getLogger("cogent.subagent.orchestrator")

PLAN_RE = re.compile(r"<plan>\s*(\{.*?\})\s*</plan>", re.DOTALL)

DEFAULT_MAX_CONCURRENT = 3

PLANNING_SYSTEM_PROMPT = """You are a task decomposition planner. Break a complex task into
specialized subtasks that run on different agent roles. You think in steps before you write —
reason about the decomposition, then output a plan.

## Reasoning process (think through these before writing)

### 1. Understand the task
What kind of work is this? Research-heavy? Code-heavy? Mixed? How many distinct concern areas
exist that could reasonably be split?

### 2. Choose the right agents
- **researcher** — needs web information, data gathering, source analysis
- **explorer** — needs codebase navigation, file mapping, pattern discovery
- **coder** — needs code writing, modification, debugging, shell execution
- **validator** — needs adversarial review of outputs before they ship
- **synthesizer** — needs to merge multiple agent outputs into a final deliverable

### 3. Decide dependencies
- Independent tasks → no dependencies (they run in parallel)
- Sequential tasks → depends on the task that produces its input
- A researcher finding specs → a coder implementing → a validator reviewing is the classic chain

### 4. Minimize, then verify
Break into the FEWEST subtasks that still cover the work. One well-scoped agent beats three
vague ones. After you draft the plan, ask: is every subtask necessary? Could any merge?

## Agent selection rules
- Use researcher for any task that starts with "find", "research", "investigate", "compare",
  "search", "analyze", "what is", "how does"
- Use explorer when the task requires understanding unfamiliar code
- Use coder when the task requires writing, modifying, or debugging code
- Use validator when outputs need review before delivery (always pair with coder or synthesizer)
- Use synthesizer ONLY when 2+ agents produce distinct outputs that need merging. If the task
  is sequential (A → B → C), no synthesizer needed — the last agent produces the answer.

## Output schema

<plan>
{
  "reasoning": "Your decomposition strategy: what the task needs, why you chose these roles, how dependencies flow",
  "subtasks": [
    {
      "role": "researcher",
      "prompt": "Detailed, specific instructions for this subtask. Include what to find and how to present it.",
      "dependencies": []
    }
  ]
}
</plan>

Each subtask must have: "role" (one of the five above), "prompt" (detailed instructions),
and "dependencies" (list of 0-based indices or strings referencing prior subtask outputs)."""

REPLANNING_SYSTEM_PROMPT = """You are a task replanning coordinator. You receive the
original task and results from a completed wave of subagents. Decide if the job is done
or if more work is needed.

## Evaluation checklist (run through each)

1. **Completeness** — Does every part of the original task appear to be addressed? Are there
   explicit "I couldn't find" or "not implemented" notes from agents?
2. **Contradictions** — Do any agent outputs disagree with each other? If so, is one clearly
   more reliable (cited sources, specific evidence)?
3. **Confidence** — Do the results feel definitive, or are they exploratory? An agent that only
   found 1 source when 3+ were expected suggests more research is needed.
4. **Quality** — Are outputs thorough and specific, or vague and generic? Vague outputs mean
   the subtask prompt was too broad — narrow it in the re-plan.

## Decision rules
- Set `complete: true` only when ALL parts of the task are convincingly addressed with no
  critical gaps. "Good enough for a first pass" is still `complete: false` if the task
  requires thoroughness.
- If the task IS complete, include a brief explanation of what was accomplished.
- If the task is NOT complete, provide new_subtasks that fill the gaps. Each subtask should
  reference what was already done: "The first agent found X but couldn't find Y — investigate Y."

## Output schema

<decision>
{
  "complete": false,
  "explanation": "Clear assessment of what's done and what's missing",
  "new_subtasks": [
    {
      "role": "researcher",
      "prompt": "Specific gap to address, referencing prior results",
      "dependencies": []
    }
  ]
}
</decision>

Each new_subtask must have: "role", "prompt" (addresses a specific gap), and "dependencies"."""

SYNTHESIS_SYSTEM_PROMPT = """You are a SYNTHESIZER — combining outputs from multiple
specialized agents (researcher, coder, validator, explorer) into a single coherent
deliverable. You are the last quality gate before output ships. Be discriminating.

## Methodology

1. **Read everything first** — before writing a sentence, absorb all agent outputs.
2. **Resolve contradictions** — if agents disagree, prefer the output with cited sources
   or explicit evidence. If neither has evidence, flag the contradiction explicitly.
3. **Tag confidence** — annotate claims with confidence:
   - [HIGH] — corroborated by multiple agents or sources
   - [MED] — single source, reasonable confidence
   - [LOW] — inference, assumption, or weak evidence
   - [CONFLICT] — agents disagreed, no clear resolution
4. **Preserve specifics** — keep exact numbers, code snippets, file paths, and quotes.
   Do not paraphrase data points into vagueness.
5. **Do not add new information** — your job is to combine, not extend. If something
   critical is missing, say so in an "Open questions" section.

## Output structure

Organize the answer for its intended audience. If no format is specified, use:
1. **Summary** — what was accomplished (2-4 sentences)
2. **Key findings** — the important results, organized by topic
3. **Details** — supporting evidence, code, sources
4. **Open questions** — what remains uncertain or unresolved

Use bullet points and tables over paragraphs. Lead with the conclusion."""


class Orchestrator:
    """Coordinates the full subagent lifecycle for a single task.

    Usage::

        orch = Orchestrator(llm_call_fn=some_async_fn)
        async for event in orch.run("Research and build X"):
            pass  # event is a dict with "type" and "data" keys
    """

    def __init__(
        self,
        llm_call_fn,
        agent_factory: Optional[AgentFactory] = None,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    ) -> None:
        self._llm_call = llm_call_fn
        self._factory = agent_factory or AgentFactory(llm_call_fn=llm_call_fn)
        self._max_concurrent = max_concurrent
        self._graph: Optional[TaskGraph] = None
        self._plan: Optional[DecompositionPlan] = None

    # ── Public API ─────────────────────────────────────────────────────

    async def run(
        self,
        task: str,
        context: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        """Run the full orchestration lifecycle for a task.

        Yields SSE-style event dicts for streaming.  Final event is
        ``orchestrator_result`` with the assembled output.
        """
        # Phase 1: Planning
        async for event in self._planning_phase(task, context):
            yield event

        if not self._plan or not self._plan.subtasks:
            yield {
                "type": "orchestrator_error",
                "data": {"error": "Planning produced no subtasks"},
            }
            return

        # Phase 2-4: Execute waves + aggregate + decide loop
        accumulated_results: List[SubagentResult] = []
        loop_count = 0
        max_loops = 2

        while loop_count < max_loops:
            loop_count += 1
            yield {
                "type": "orchestrator_status",
                "data": {"message": f"Execution wave {loop_count}", "loop": loop_count},
            }

            self._graph = TaskGraph()
            for spec in self._plan.subtasks:
                self._graph.add_node(spec)

            async for event in self._execute_waves():
                yield event

            wave_results = [
                n.result for n in self._graph.succeeded if n.result is not None
            ]
            accumulated_results.extend(wave_results)

            yield {
                "type": "orchestrator_status",
                "data": {
                    "message": (
                        f"Wave {loop_count} complete: "
                        f"{len(self._graph.succeeded)} succeeded, "
                        f"{len(self._graph.failures)} failed"
                    ),
                    "loop": loop_count,
                },
            }

            if loop_count >= max_loops:
                break

            decision = await self._replanning_pass(task, accumulated_results, context)
            if decision.get("complete"):
                break

            new_subtasks = decision.get("new_subtasks", [])
            if not new_subtasks:
                break

            self._plan = DecompositionPlan(
                subtasks=[
                    SubtaskSpec(**s) if isinstance(s, dict)
                    else SubtaskSpec(prompt=str(s))
                    for s in new_subtasks
                ],
                reasoning=decision.get("explanation", ""),
            )
            yield {
                "type": "orchestrator_status",
                "data": {
                    "message": f"Re-planning: {len(new_subtasks)} additional subtasks",
                    "loop": loop_count,
                },
            }

        # Phase 5: Final assembly
        final_output = await self._assemble(task, accumulated_results, context)
        yield {"type": "orchestrator_result", "data": {"output": final_output}}

    # ── Phase 1: Planning ──────────────────────────────────────────────

    async def _planning_phase(
        self, task: str, context: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        """Decompose the task into subtasks via LLM."""
        yield {
            "type": "orchestrator_status",
            "data": {"message": "Planning task decomposition"},
        }

        messages = [
            {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Decompose this task into subtasks:\n\n{task}"
                           + (f"\n\nContext:\n{context}" if context else ""),
            },
        ]

        try:
            response = await self._llm_call(messages)
        except Exception as exc:
            logger.error("Planning LLM call failed: %s", exc)
            self._plan = DecompositionPlan(
                subtasks=[SubtaskSpec(role=SubagentRole.SYNTHESIZER, prompt=task)],
                reasoning=f"Planning failed ({exc}), running as single agent",
            )
            yield sse_orchestrator_plan(self._plan)
            return

        plan = self._parse_plan(response)
        if not plan or not plan.subtasks:
            self._plan = DecompositionPlan(
                subtasks=[SubtaskSpec(role=SubagentRole.SYNTHESIZER, prompt=task)],
                reasoning="Could not parse structured plan, running as single agent",
            )
        else:
            self._plan = plan

        yield sse_orchestrator_plan(self._plan)

    @staticmethod
    def _parse_plan(response: str) -> Optional[DecompositionPlan]:
        """Parse the <plan> JSON block from the LLM response."""
        m = PLAN_RE.search(response)
        if m:
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError:
                return None
        else:
            try:
                data = json.loads(response)
            except json.JSONDecodeError:
                return None

        subtasks_data = data.get("subtasks", [])
        if not subtasks_data:
            return None

        subtasks = []
        for sd in subtasks_data:
            role_str = sd.get("role", "researcher")
            try:
                role = SubagentRole(role_str)
            except ValueError:
                role = SubagentRole.RESEARCHER
            subtasks.append(SubtaskSpec(
                role=role,
                prompt=sd.get("prompt", ""),
                dependencies=sd.get("dependencies", []),
            ))

        return DecompositionPlan(
            subtasks=subtasks,
            reasoning=data.get("reasoning", ""),
        )

    # ── Phase 3: Wave execution ────────────────────────────────────────

    async def _execute_waves(self) -> AsyncGenerator[dict, None]:
        """Execute subagents in dependency-respecting waves.

        Each wave runs ready agents concurrently (bounded by semaphore).
        Yields start/complete events per agent.
        """
        semaphore = asyncio.Semaphore(self._max_concurrent)

        while not self._graph.all_done:
            ready = self._graph.get_ready_nodes()
            if not ready:
                if self._graph.running_count == 0:
                    logger.warning("Task graph stalled — unresolvable dependencies")
                    break
                await asyncio.sleep(0.1)
                continue

            pending = [asyncio.ensure_future(
                self._run_agent_and_collect(n, semaphore)) for n in ready
            ]
            for fut in asyncio.as_completed(pending):
                events, _ = await fut
                for ev in events:
                    yield ev

    async def _run_agent_and_collect(
        self, node, semaphore: asyncio.Semaphore,
    ):
        """Run one agent, collect its SSE events and result."""
        events: list = []
        self._graph.update_status(node.id, SubagentStatus.RUNNING)
        agent = self._factory.create_agent(node.spec)
        events.append(sse_subagent_start(agent.to_spec()))

        async with semaphore:
            logger.info("Starting subagent %s (%s)", agent.agent_id, agent.role.value)
            result = await agent.execute()

        if result.status == SubagentStatus.COMPLETED:
            self._graph.update_status(node.id, SubagentStatus.COMPLETED, result=result)
            events.append(sse_subagent_complete(result))
        else:
            self._graph.update_status(node.id, SubagentStatus.FAILED, result=result)
            events.append(sse_subagent_fail(result))

        logger.info(
            "Subagent %s done: %s (tools=%d, elapsed=%.1fs)",
            agent.agent_id, result.status.value,
            result.tool_calls_made, result.elapsed_seconds,
        )
        return events, result

    # ── Phase 4b: Re-planning ──────────────────────────────────────────

    async def _replanning_pass(
        self,
        task: str,
        results: List[SubagentResult],
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ask the LLM if more subagents are needed."""
        results_block = "\n\n".join(
            f"=== {r.role.value} ({r.status.value}) ===\n{r.output[:800]}"
            for r in results if r.status == SubagentStatus.COMPLETED
        )

        messages = [
            {"role": "system", "content": REPLANNING_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Original task: {task}\n\n"
                    f"Results so far:\n{results_block}\n\n"
                    f"Context: {context or 'none'}\n\n"
                    "Is the task complete? If not, what additional subtasks are needed?"
                ),
            },
        ]

        try:
            response = await self._llm_call(messages)
        except Exception:
            return {"complete": True, "explanation": "Re-planning call failed"}

        m = re.search(r"<decision>\s*(\{.*?\})\s*</decision>", response, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        return {"complete": True, "explanation": "Could not parse re-planning decision"}

    # ── Phase 5: Final assembly ────────────────────────────────────────

    async def _assemble(
        self,
        task: str,
        results: List[SubagentResult],
        context: Optional[str] = None,
    ) -> str:
        """Synthesize all subagent results into the final output."""
        successful = [r for r in results if r.status == SubagentStatus.COMPLETED]
        if not successful:
            return "(all subagents failed — no output produced)"

        if len(successful) == 1:
            return successful[0].output

        results_block = "\n\n".join(
            f"=== {r.role.value.upper()} ===\n{r.output}" for r in successful
        )

        messages = [
            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Task: {task}\n\n"
                    f"Subagent Results:\n{results_block}\n\n"
                    f"Context: {context or 'none'}\n\n"
                    "Synthesize these results into a single comprehensive answer."
                ),
            },
        ]

        try:
            return await self._llm_call(messages)
        except Exception as exc:
            logger.error("Synthesis LLM call failed: %s", exc)
            return "\n\n".join(
                f"## {r.role.value.title()}\n{r.output}" for r in successful
            )
