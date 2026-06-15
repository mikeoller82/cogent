"""Agent Skills discovery and activation helpers.

Implements the portable SKILL.md layout from https://agentskills.io.
"""
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
MAX_RESOURCE_BYTES = 200_000
MAX_LISTED_RESOURCES = 200


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    location: Path
    directory: Path
    body: str
    metadata: Dict[str, Any]


def _skill_roots() -> List[Path]:
    roots = [
        PROJECT_ROOT / ".agents" / "skills",
        PROJECT_ROOT / ".cogent" / "skills",
    ]
    extra = os.environ.get("COGENT_SKILLS_PATHS", "")
    for raw in extra.split(os.pathsep):
        raw = raw.strip()
        if raw:
            roots.append(Path(raw).expanduser())
    return roots


def _parse_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _parse_frontmatter(markdown: str) -> Optional[tuple[Dict[str, Any], str]]:
    if not markdown.startswith("---"):
        return None

    match = re.search(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", markdown, re.DOTALL)
    if not match:
        return None

    frontmatter = match.group(1)
    body = markdown[match.end():].strip()
    data: Dict[str, Any] = {}
    current_map: Optional[str] = None

    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if line.startswith((" ", "\t")) and current_map:
            key, sep, value = stripped.partition(":")
            if sep:
                data.setdefault(current_map, {})[key.strip()] = _parse_scalar(value)
            continue

        current_map = None
        key, sep, value = stripped.partition(":")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = _parse_scalar(value)
        else:
            data[key] = {}
            current_map = key

    return data, body


def _load_skill(skill_file: Path) -> Optional[Skill]:
    try:
        markdown = skill_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        markdown = skill_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    parsed = _parse_frontmatter(markdown)
    if not parsed:
        return None
    metadata, body = parsed

    name = str(metadata.get("name") or skill_file.parent.name).strip()
    description = str(metadata.get("description") or "").strip()
    if not name or not description:
        return None

    return Skill(
        name=name,
        description=description,
        location=skill_file.resolve(),
        directory=skill_file.parent.resolve(),
        body=body,
        metadata=metadata,
    )


def discover_skills() -> Dict[str, Skill]:
    """Discover skills by name. Earlier roots take precedence."""
    skills: Dict[str, Skill] = {}
    for root in _skill_roots():
        if not root.exists() or not root.is_dir():
            continue
        for skill_file in sorted(root.glob("*/SKILL.md")):
            skill = _load_skill(skill_file)
            if skill and skill.name not in skills:
                skills[skill.name] = skill
    return skills


def skill_catalog_for_prompt() -> str:
    skills = discover_skills()
    if not skills:
        return ""

    lines = [
        "## Agent Skills",
        "The following skills provide specialized instructions for specific tasks.",
        "When a task matches a skill's description, call activate_skill with the skill name before proceeding.",
        "After activating a skill, follow its instructions. If it references bundled files, call read_skill_resource.",
        "",
        "<available_skills>",
    ]
    for skill in skills.values():
        lines.extend([
            "  <skill>",
            f"    <name>{skill.name}</name>",
            f"    <description>{skill.description}</description>",
            "  </skill>",
        ])
    lines.append("</available_skills>")
    return "\n".join(lines)


def has_skills() -> bool:
    return bool(discover_skills())


def _relative_resource_paths(skill: Skill) -> List[str]:
    files: List[str] = []
    for dirname in ("scripts", "references", "assets"):
        root = skill.directory / dirname
        if not root.exists() or not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                files.append(path.relative_to(skill.directory).as_posix())
                if len(files) >= MAX_LISTED_RESOURCES:
                    return files
    return files


def activate_skill(name: str) -> Dict[str, Any]:
    skills = discover_skills()
    skill = skills.get(name)
    if not skill:
        available = ", ".join(sorted(skills)) or "none"
        return {"result": f"Skill not found: {name}. Available skills: {available}"}

    resources = _relative_resource_paths(skill)
    resource_block = ""
    if resources:
        resource_lines = "\n".join(f"  <file>{path}</file>" for path in resources)
        resource_block = f"\n<skill_resources>\n{resource_lines}\n</skill_resources>"

    return {
        "result": (
            f'<skill_content name="{skill.name}">\n'
            f"{skill.body}\n\n"
            f"Skill directory: {skill.directory}\n"
            "Relative paths in this skill are relative to the skill directory."
            f"{resource_block}\n"
            "</skill_content>"
        )
    }


def read_skill_resource(skill_name: str, path: str) -> Dict[str, Any]:
    skills = discover_skills()
    skill = skills.get(skill_name)
    if not skill:
        available = ", ".join(sorted(skills)) or "none"
        return {"result": f"Skill not found: {skill_name}. Available skills: {available}"}

    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts:
        return {"result": "Invalid skill resource path. Use a relative path inside the skill directory."}

    target = (skill.directory / relative).resolve()
    try:
        target.relative_to(skill.directory)
    except ValueError:
        return {"result": "Invalid skill resource path. Use a relative path inside the skill directory."}

    if not target.exists() or not target.is_file():
        return {"result": f"Skill resource not found: {path}"}
    if target.stat().st_size > MAX_RESOURCE_BYTES:
        return {"result": f"Skill resource is too large to read: {path}"}

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"result": f"Could not read skill resource: {e}"}

    return {
        "result": (
            f'<skill_resource skill="{skill.name}" path="{relative.as_posix()}">\n'
            f"{content}\n"
            "</skill_resource>"
        )
    }
