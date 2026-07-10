"""Skills Catalog — discovers and catalogs available agent skills.

Discovers skills from .cogent/skills/ via cogent's own agent_skills module,
plus optional skills from optional-skills/ for the catalog browsing UI.
"""
from __future__ import annotations
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cogent.skills_catalog")

OPTIONAL_SKILLS_DIR = Path(__file__).parent.parent / "optional-skills"


def discover_skills() -> List[Dict[str, Any]]:
    """Discover all installed skills from .cogent/skills/."""
    # Ensure we import cogent's own backend/agent_skills.py, not the pip package
    _backend = str(Path(__file__).resolve().parent)
    if _backend not in sys.path:
        sys.path.insert(0, _backend)
    try:
        import agent_skills  # noqa: F811 — cogent's own module
        skills = agent_skills.discover_skills()
        return [
            {"name": s.name, "path": str(s.location), "directory": str(s.directory)}
            for s in skills.values()
        ]
    except (ImportError, AttributeError):
        logger.warning("agent_skills not available — returning empty skill list")
        return []


def discover_categories() -> Dict[str, List[Dict[str, Any]]]:
    """Discover optional skills organized by category."""
    if not OPTIONAL_SKILLS_DIR.exists():
        return {}

    categories = {}
    for cat_dir in sorted(OPTIONAL_SKILLS_DIR.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name.startswith("."):
            continue

        desc_file = cat_dir / "DESCRIPTION.md"
        description = ""
        if desc_file.exists():
            description = desc_file.read_text(encoding="utf-8").strip()

        skills = []
        for skill_dir in sorted(cat_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skills.append({
                    "name": skill_dir.name,
                    "path": str(skill_file),
                })

        categories[cat_dir.name] = {
            "description": description,
            "skills": skills,
        }

    return categories


def catalog_summary() -> str:
    """Build a catalog summary string for the LLM prompt."""
    installed = discover_skills()
    categories = discover_categories()

    lines = []
    if installed:
        lines.append(f"## Installed Skills ({len(installed)})")
        for s in installed:
            lines.append(f"- {s['name']}")

    if categories:
        lines.append(f"\n## Available Optional Skills ({sum(len(c['skills']) for c in categories.values())})")
        for cat_name, cat_data in sorted(categories.items()):
            if cat_data["skills"]:
                lines.append(f"### {cat_name}")
                for s in cat_data["skills"]:
                    lines.append(f"- {s['name']}")

    return "\n".join(lines) if lines else "No skills found."
