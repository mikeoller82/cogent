"""Skills Catalog — discovers and catalogs available agent skills.

Mirrors Hermes' skills/ directory structure with a registry-based
approach compatible with Cogent's agent_skills.py.
"""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cogent.skills_catalog")

SKILLS_DIR = Path(__file__).parent.parent / ".cogent" / "skills"
OPTIONAL_SKILLS_DIR = Path(__file__).parent.parent / "optional-skills"


def discover_skills(skills_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Discover all installed skills. Mirrors Hermes' skills discovery."""
    base = skills_dir or SKILLS_DIR
    if not base.exists():
        return []

    skills = []
    for item in base.iterdir():
        skill_file = item / "SKILL.md"
        if skill_file.exists():
            skills.append({
                "name": item.name,
                "path": str(skill_file),
                "directory": str(item),
            })
    return skills


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
