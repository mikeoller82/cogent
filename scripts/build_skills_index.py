#!/usr/bin/env python3
"""Build a skills index for Cogent. Mirrors Hermes' build_skills_index.py."""
import json
import sys
from pathlib import Path

def build_index(skills_dir: Path) -> dict:
    """Scan a directory for SKILL.md files and build an index."""
    index = {"skills": [], "categories": {}}

    if not skills_dir.exists():
        return index

    for item in sorted(skills_dir.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue

        skill_file = item / "SKILL.md"
        if skill_file.exists():
            index["skills"].append({
                "name": item.name,
                "path": str(skill_file),
            })

    return index


if __name__ == "__main__":
    base_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".cogent/skills")
    index = build_index(base_dir)
    print(json.dumps(index, indent=2))
