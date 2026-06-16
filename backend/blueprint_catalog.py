"""Blueprint catalog for scheduled tasks.

Analogous to Hermes' ``cron/blueprint_catalog.py`` — provides
templated task definitions the LLM can offer to users when they
ask "what can I schedule?"

Each blueprint has a name, description, cadence suggestion, and
a prompt template with ``{placeholders}`` the LLM fills in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Blueprint:
    """A scheduled-task blueprint."""
    name: str
    description: str
    category: str = "general"
    default_cadence: str = "daily"
    default_time: str = "09:00"
    prompt_template: str = ""
    placeholders: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


# ── Catalog ───────────────────────────────────────────────────────────────

CATALOG: List[Blueprint] = [
    Blueprint(
        name="daily-news-briefing",
        description="Fetch and summarise the day's top news in a specific domain",
        category="research",
        default_cadence="daily",
        default_time="08:00",
        prompt_template=(
            "Search the web for today's top news about {topic}. "
            "Summarise the 5 most important stories with sources. "
            "Focus on developments that affect {audience}."
        ),
        placeholders=["topic", "audience"],
        tags=["news", "research"],
    ),
    Blueprint(
        name="weekly-market-report",
        description="Research and compile a weekly market or industry round-up",
        category="business",
        default_cadence="weekly",
        default_time="09:00",
        prompt_template=(
            "Research this week's developments in {industry}. "
            "Cover: major announcements, funding rounds, regulatory changes, "
            "and competitive moves. Format as a structured brief with sections."
        ),
        placeholders=["industry"],
        tags=["business", "research", "weekly"],
    ),
    Blueprint(
        name="content-idea-generator",
        description="Generate content ideas and outlines for a specific audience",
        category="content",
        default_cadence="daily",
        default_time="07:00",
        prompt_template=(
            "Generate {count} content ideas for {audience} about {topic}. "
            "For each idea provide: title, angle, format suggestion, "
            "and a one-paragraph outline."
        ),
        placeholders=["topic", "audience", "count"],
        tags=["content", "writing"],
    ),
    Blueprint(
        name="competitor-monitor",
        description="Track a competitor's recent activity and public changes",
        category="business",
        default_cadence="weekly",
        default_time="10:00",
        prompt_template=(
            "Research recent activity from {competitor_name}. "
            "Check: product changes, pricing updates, blog posts, "
            "social media activity, hiring signals, and press coverage. "
            "Flag anything noteworthy."
        ),
        placeholders=["competitor_name"],
        tags=["business", "research", "competitive"],
    ),
    Blueprint(
        name="tech-radar-scan",
        description="Scan for new tools, libraries, or trends in a tech domain",
        category="research",
        default_cadence="weekly",
        default_time="06:00",
        prompt_template=(
            "Scan for new and notable developments in {domain}. "
            "Check: GitHub trending, new releases, Hacker News, "
            "product launches, and community discussions. "
            "Rank by relevance to {use_case}."
        ),
        placeholders=["domain", "use_case"],
        tags=["tech", "research"],
    ),
    Blueprint(
        name="health-check",
        description="Check system health metrics and report anomalies",
        category="operations",
        default_cadence="daily",
        default_time="06:00",
        prompt_template=(
            "Check the health of {system_name}. "
            "Verify: service status, recent errors, response times, "
            "and resource utilisation. Report any anomalies or degradation."
        ),
        placeholders=["system_name"],
        tags=["ops", "monitoring"],
    ),
    Blueprint(
        name="learning-reminder",
        description="Send a daily or weekly learning prompt to build a skill",
        category="personal",
        default_cadence="daily",
        default_time="12:00",
        prompt_template=(
            "Provide a {topic} learning exercise for today. "
            "Include: a concept to study, a practical exercise, "
            "and 2-3 resources for deeper exploration."
        ),
        placeholders=["topic"],
        tags=["learning", "personal"],
    ),
    Blueprint(
        name="memory-retention",
        description="Review and reinforce saved memory facts",
        category="personal",
        default_cadence="weekly",
        default_time="18:00",
        prompt_template=(
            "Review the current memory store. "
            "Identify: outdated facts to update, contradictions to resolve, "
            "and gaps worth recording. Suggest any new facts learned this week."
        ),
        placeholders=[],
        tags=["memory", "maintenance"],
    ),
]


# ── Lookup ────────────────────────────────────────────────────────────────

def get_blueprint(name: str) -> Optional[Blueprint]:
    """Look up a blueprint by name."""
    for bp in CATALOG:
        if bp.name == name:
            return bp
    return None


def list_blueprints(category: Optional[str] = None) -> List[Blueprint]:
    """List all blueprints, optionally filtered by category."""
    if not category:
        return list(CATALOG)
    return [bp for bp in CATALOG if bp.category == category]


def catalog_for_prompt() -> str:
    """Return a formatted list of blueprints for the LLM prompt."""
    lines = ["## Available task blueprints",
             "",
             "You can suggest any of these blueprints when the user asks",
             "about scheduling recurring tasks.",
             ""]
    for bp in CATALOG:
        ph = f" — placeholders: {', '.join(bp.placeholders)}" if bp.placeholders else ""
        lines.append(f"- **{bp.name}** ({bp.category}): "
                     f"{bp.description}{ph}")
    return "\n".join(lines)
