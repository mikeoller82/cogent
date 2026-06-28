"""Ponytail review hook — scans every LLM response for over-engineering.

Registers on ``after_message`` to catch violations of the ponytail
lazy-senior-dev principles (YAGNI, reuse, stdlib-first, one-liners)
that the system prompt nudges the LLM toward.

The presence of this hook itself reinforces the ponytail signal.
"""

from __future__ import annotations

import logging
import re

import cogent_hooks

logger = logging.getLogger("cogent.hooks.ponytail")

# ── Over-engineering signals ───────────────────────────────────────────

NEW_DEP_PATTERN = re.compile(
    r"(?:pip\s+install|npm\s+install|yarn\s+add|cargo\s+add|go\s+get|"
    r"apt-get\s+install|brew\s+install|nuget\s+install|gem\s+install|"
    r"ADD\s+dependency|install\s+package)",
    re.IGNORECASE,
)

BOILERPLATE_PATTERNS = [
    re.compile(r"class\s+\w+Factory", re.IGNORECASE),
    re.compile(r"class\s+\w+Builder", re.IGNORECASE),
    re.compile(r"class\s+\w+Abstract\b", re.IGNORECASE),
    re.compile(r"class\s+\w+Provider", re.IGNORECASE),
    re.compile(r"class\s+\w+Manager", re.IGNORECASE),
    re.compile(r"class\s+\w+Strategy", re.IGNORECASE),
]

REUSE_SIGNALS = [
    re.compile(r"let.+(?:copy|clone|duplicate)\s+(?:the\s+)?(?:existing\s+)?(?:function|class|util)"),
    re.compile(r"reimplement", re.IGNORECASE),
    re.compile(r"rewrite\s+(?:the\s+)?(?:entire|whole|from\s+scratch)"),
    re.compile(r"duplicate\s+(?:the\s+)?(?:existing\s+)?(?:logic|code|function)"),
]

STDLIB_MISS_PATTERNS = [
    (re.compile(r"datetime\.strptime|dateutil"), "datetime.strptime" if "dateutil" not in "" else "dateutil"),
    (re.compile(r"os\.path|pathlib"), "os.path/pathlib" if "pathlib" not in "" else "pathlib"),
    (re.compile(r"json\.load|json\.dump"), "json module"),
    (re.compile(r"csv\.\w+"), "csv module"),
    (re.compile(r"collections\.\w+"), "collections"),
    (re.compile(r"functools\.\w+"), "functools"),
    (re.compile(r"itertools\.\w+"), "itertools"),
]

LINES_OF_CODE_PATTERN = re.compile(r"(?:this\s+(?:is|will\s+be)\s+)(\d+)\s*(?:line|loc)", re.IGNORECASE)


def _check_over_engineering(text: str) -> list[str]:
    findings: list[str] = []

    # Check for new deps being added
    for match in NEW_DEP_PATTERN.finditer(text):
        findings.append(f"new-dependency: \"{match.group()}\" — could it use stdlib / existing code instead?")

    # Check for boilerplate class patterns
    for pat in BOILERPLATE_PATTERNS:
        for match in pat.finditer(text):
            findings.append(f"boilerplate: \"{match.group()}\" — is this abstraction really needed?")

    # Check for missed reuse
    for pat in REUSE_SIGNALS:
        for match in pat.finditer(text):
            findings.append(f"missed-reuse: \"{match.group()}\" — check if this already exists in the codebase")

    return findings


async def after_message(session_id: str, assistant_text: str, user_text: str) -> None:
    if not assistant_text:
        return

    findings = _check_over_engineering(assistant_text)
    if findings:
        for f in findings:
            logger.info("[ponytail] session=%s %s", session_id[:12], f)


cogent_hooks.register("after_message", after_message)
