"""Skill Forge — import and forge agent skills from GitHub repos into Cogent's skill directory.

Two modes:
  1. IMPORT  — repo already has SKILL.md files; copy them into Cogent's skill tree.
  2. FORGE   — repo has code/docs but no ready-made skills; analyze via LLM and
               generate a Cogent-compatible skill.

The bmad-module-skill-forge (SKF) methodology is the reference for the forge mode:
  - Skills are structured as SKILL.md with YAML frontmatter (name, description).
  - Supporting resources live in scripts/, references/, assets/ (one level deep).
  - Provenance is tracked via metadata.json when available.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("cogent.skill_forge")

# ── Paths ────────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
COGENT_SKILLS_DIR = PROJECT_ROOT / ".cogent" / "skills"

# ── Data ─────────────────────────────────────────────────────────────────

@dataclass
class DiscoveredSkill:
    """A skill found inside a cloned repo."""
    name: str
    description: str
    source_dir: Path               # directory containing SKILL.md
    skill_md_path: Path            # the SKILL.md file itself
    metadata: Dict[str, Any] = field(default_factory=dict)
    resources: List[str] = field(default_factory=list)  # relative paths

    @property
    def valid(self) -> bool:
        return bool(self.name) and bool(self.description)


# ── URL parsing ──────────────────────────────────────────────────────────

def parse_github_url(url: str) -> Tuple[str, str, Optional[str], Optional[str]]:
    """Parse a GitHub URL into (owner, repo, subpath, ref).

    Supports:
      https://github.com/owner/repo
      https://github.com/owner/repo/tree/branch/path
      https://github.com/owner/repo.git
      git@github.com:owner/repo.git
      owner/repo  (shorthand)
    """
    # Strip trailing .git
    url = url.rstrip("/")

    # ssh: git@github.com:owner/repo.git
    m = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2).replace(".git", ""), None, None

    # shorthand: owner/repo
    m = re.match(r"^([\w.-]+)/([\w.-]+)$", url)
    if m:
        return m.group(1), m.group(2), None, None

    # https:  github.com/owner/repo[/tree/branch/...path]
    m = re.match(
        r"https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?"
        r"(?:/tree/([^/]+)(/.*)?)?$",
        url,
    )
    if m:
        owner, repo = m.group(1), m.group(2)
        ref = m.group(3)  # branch / tag
        subpath = m.group(4).lstrip("/") if m.group(4) else None
        return owner, repo, subpath, ref

    raise ValueError(f"Unrecognised GitHub URL: {url}")


def build_clone_url(owner: str, repo: str) -> str:
    return f"https://github.com/{owner}/{repo}.git"


# ── Git helpers ──────────────────────────────────────────────────────────

async def _run_git(*args: str, cwd: Optional[Path] = None,
                   timeout: int = 120) -> Tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"git command timed out after {timeout}s: git {' '.join(args)}")

    out = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()
    return proc.returncode or 0, out, err


async def clone_repo(url: str, dest: Path, ref: Optional[str] = None,
                     depth: int = 1) -> None:
    """Clone a GitHub repo into *dest*."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    logger.info("Cloning %s -> %s (depth=%d)", url, dest, depth)
    rc, out, err = await _run_git("clone", "--depth", str(depth), url, str(dest))
    if rc != 0:
        raise RuntimeError(f"git clone failed:\n{err}")

    if ref:
        logger.info("Checking out ref=%s", ref)
        rc, out, err = await _run_git("checkout", ref, cwd=dest)
        if rc != 0:
            raise RuntimeError(f"git checkout {ref} failed:\n{err}")

    logger.info("Clone complete: %s", dest)


# ── Frontmatter parsing ──────────────────────────────────────────────────

def _parse_frontmatter(text: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Parse YAML frontmatter from skill markdown.
    Returns (frontmatter_dict, body).  frontmatter_dict is None on failure.
    """
    text = text.strip()
    if not text.startswith("---"):
        return None, text

    # Find closing ---
    end = text.find("---", 3)
    if end == -1:
        return None, text

    raw = text[3:end].strip()
    body = text[end + 3:].strip()

    try:
        import yaml
        data = yaml.safe_load(raw)
    except Exception:
        # Fallback: minimal manual parse for name + description
        data = _manual_frontmatter(raw)

    if not isinstance(data, dict):
        return None, body

    return data, body


def _manual_frontmatter(raw: str) -> Dict[str, Any]:
    """Minimal frontmatter parser when PyYAML is unavailable."""
    data: Dict[str, Any] = {}
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("name:"):
            data["name"] = line[len("name:"):].strip().strip("\"'")
        elif line.startswith("description:"):
            desc = line[len("description:"):].strip().strip("\"'")
            # Multi-line description continuation
            data["description"] = desc
    return data


# ── Skill scanning ───────────────────────────────────────────────────────

def _relative_resources(skill_dir: Path) -> List[str]:
    """List relative paths of files in scripts/, references/, assets/."""
    files: List[str] = []
    for sub in ("scripts", "references", "assets"):
        d = skill_dir / sub
        if d.is_dir():
            for p in sorted(d.rglob("*")):
                if p.is_file():
                    rel = p.relative_to(skill_dir).as_posix()
                    files.append(rel)
    return files


def scan_for_skills(repo_dir: Path) -> List[DiscoveredSkill]:
    """Recursively scan a repo directory for SKILL.md files and parse them."""
    found: List[DiscoveredSkill] = []
    seen_names: set = set()

    for skill_md in sorted(repo_dir.rglob("SKILL.md")):
        try:
            text = skill_md.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("Cannot read %s: %s", skill_md, exc)
            continue

        fm, body = _parse_frontmatter(text)
        if fm is None:
            logger.debug("No frontmatter in %s — skipping", skill_md)
            continue

        name = (fm.get("name") or "").strip()
        desc = (fm.get("description") or "").strip()

        if not name:
            # Fallback: use parent directory name
            name = skill_md.parent.name

        if not name or name in seen_names:
            continue
        seen_names.add(name)

        resources = _relative_resources(skill_md.parent)
        metadata = {k: v for k, v in fm.items() if k not in ("name", "description")}

        found.append(DiscoveredSkill(
            name=name,
            description=desc or f"Skill imported from {repo_dir.name}",
            source_dir=skill_md.parent,
            skill_md_path=skill_md,
            metadata=metadata,
            resources=resources,
        ))

    return found


# ── Installation ─────────────────────────────────────────────────────────

def install_skill(skill: DiscoveredSkill, target_dir: Optional[Path] = None,
                  force: bool = False) -> Dict[str, Any]:
    """Copy a discovered skill into Cogent's skills directory.

    Returns a result dict with keys: name, installed_path, action (created/updated/skipped)
    """
    if target_dir is None:
        target_dir = COGENT_SKILLS_DIR

    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / skill.name

    action = "created"
    if dest.exists():
        if not force:
            logger.info("Skill '%s' already exists at %s — skipping (use force=True to overwrite)", skill.name, dest)
            return {"name": skill.name, "installed_path": str(dest), "action": "skipped"}
        action = "updated"
        shutil.rmtree(dest)

    shutil.copytree(skill.source_dir, dest, symlinks=False,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))

    # Write a small metadata.json beside it for provenance
    meta = {
        "name": skill.name,
        "description": skill.description,
        "imported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metadata": skill.metadata,
        "resources": skill.resources,
    }
    meta_path = dest / "forge-meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    logger.info("Skill '%s' installed -> %s (%s)", skill.name, dest, action)
    return {"name": skill.name, "installed_path": str(dest), "action": action}


# ── High-level import pipeline ───────────────────────────────────────────

async def import_from_url(url: str, force: bool = False) -> Dict[str, Any]:
    """Full import pipeline: parse URL → clone → scan → install.

    Returns a report dict with keys:
      repo, skills (list of install results), errors (list of strings)
    """
    owner, repo_name, subpath, ref = parse_github_url(url)
    clone_url = build_clone_url(owner, repo_name)

    with tempfile.TemporaryDirectory(prefix="cogent-skf-") as tmp:
        tmp_path = Path(tmp)
        repo_path = tmp_path / "repo"

        await clone_repo(clone_url, repo_path, ref=ref)

        # If subpath specified, scope scanning to that subdirectory
        scan_root = repo_path
        if subpath:
            scan_root = repo_path / subpath
            if not scan_root.is_dir():
                raise ValueError(f"Subpath '{subpath}' does not exist in repo")

        skills = scan_for_skills(scan_root)

        if not skills:
            return {
                "repo": f"{owner}/{repo_name}",
                "skills": [],
                "errors": ["No SKILL.md files found in repo. Use the forge endpoint to generate a skill from code analysis."],
            }

        results = []
        for sk in skills:
            try:
                result = install_skill(sk, force=force)
                results.append(result)
            except Exception as exc:
                logger.exception("Failed to install skill '%s'", sk.name)
                results.append({"name": sk.name, "action": "error", "error": str(exc)})

        return {
            "repo": f"{owner}/{repo_name}",
            "skills": results,
            "errors": [],
        }


# ── Forge mode (LLM-assisted skill generation from code analysis) ────────

FORGE_PROMPT = """You are an expert at analyzing code repositories and creating agent skills.

A skill is a markdown file (SKILL.md) with YAML frontmatter that teaches an AI agent
how to work with a library, tool, or codebase. The frontmatter has:
  name: short-kebab-name
  description: >-
    Trigger-optimised description: what the skill does, when to use it, and
    what NOT to use it for. 1-2 sentences.

The body of SKILL.md is procedural markdown instructions for an AI agent.
Be specific: mention real function names, real file paths, real CLI commands.
Explain how the pieces fit together from an agent's perspective — not a human
reading the docs, but an LLM that needs to *execute* against this code.

The skill directory may also contain:
  references/    — detailed reference material loaded on demand
  scripts/       — executable helpers
  assets/        — templates, schemas, configs

Below is the tree of files in a repository. Analyse it and produce a
Cogent-compatible skill that teaches an agent how to use or contribute to
this codebase. Output only the SKILL.md content (with frontmatter) and
any supporting reference files you recommend.

Repository analysis:
{repo_analysis}
"""


async def analyze_repo_structure(repo_dir: Path) -> str:
    """Build a compact tree + file-summary of a repo for the forge prompt."""
    lines: List[str] = []

    # Directory tree (max depth 4)
    def _walk(d: Path, prefix: str = "", depth: int = 0) -> List[str]:
        if depth > 4:
            return []
        entries = sorted(d.iterdir(), key=lambda p: (p.is_file(), p.name))
        out: List[str] = []
        for i, p in enumerate(entries):
            if p.name.startswith(".") or p.name.startswith("__pycache__"):
                continue
            if p.is_dir():
                out.append(f"{prefix}{'└── ' if i == len(entries)-1 else '├── '}{p.name}/")
                ext = "    " if i == len(entries)-1 else "│   "
                out.extend(_walk(p, prefix + ext, depth + 1))
            else:
                size = p.stat().st_size
                label = f"{p.name}  ({size:,} bytes)"
                out.append(f"{prefix}{'└── ' if i == len(entries)-1 else '├── '}{label}")
        return out

    tree = _walk(repo_dir)
    lines.append("```")
    lines.extend(tree)
    lines.append("```")

    # Key files: README, package.json, pyproject.toml, etc.
    key_files = []
    for pattern in ("README*", "package.json", "pyproject.toml",
                    "Cargo.toml", "setup.py", "setup.cfg", "Makefile",
                    "requirements.txt", "*.md", "*.py", "*.ts", "*.tsx",
                    "*.js", "*.rs", "*.go"):
        for f in repo_dir.rglob(pattern):
            if f.is_file() and f.stat().st_size < 50_000:
                key_files.append(f)
                if len(key_files) >= 15:
                    break
        if len(key_files) >= 15:
            break

    if key_files:
        lines.append("\n### Key files content:\n")
        for f in sorted(key_files, key=lambda p: p.name)[:10]:
            rel = f.relative_to(repo_dir).as_posix()
            try:
                content = f.read_text(encoding="utf-8", errors="replace")[:2000]
                lines.append(f"\n--- {rel} ---\n{content[:1500]}")
            except Exception:
                pass

    return "\n".join(lines)


async def forge_skill(repo_url: str, llm_complete_fn, force: bool = False) -> Dict[str, Any]:
    """Forge a skill from a repo that has no SKILL.md by analysing it via LLM.

    *llm_complete_fn* is an async callable:  llm_complete_fn(prompt: str) -> str
    """
    owner, repo_name, subpath, ref = parse_github_url(url=repo_url)
    clone_url = build_clone_url(owner, repo_name)

    with tempfile.TemporaryDirectory(prefix="cogent-skf-") as tmp:
        tmp_path = Path(tmp)
        repo_path = tmp_path / "repo"

        await clone_repo(clone_url, repo_path, ref=ref)

        scan_root = repo_path
        if subpath:
            scan_root = repo_path / subpath

        repo_analysis = await analyze_repo_structure(scan_root)
        prompt = FORGE_PROMPT.format(repo_analysis=repo_analysis)

        logger.info("Forge: sending analysis to LLM for %s/%s", owner, repo_name)

        llm_output = await llm_complete_fn(prompt)

        # Parse the LLM output — it should contain SKILL.md content
        skill_data = _parse_forge_output(llm_output, repo_name)

        if not skill_data:
            return {
                "repo": f"{owner}/{repo_name}",
                "forge_status": "failed",
                "error": "LLM did not produce a valid skill. Output was empty or unparseable.",
            }

        # Write the generated skill into Cogent's skills dir
        target_dir = COGENT_SKILLS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / skill_data["name"]

        action = "created"
        if dest.exists():
            if not force:
                return {
                    "repo": f"{owner}/{repo_name}",
                    "forge_status": "skipped",
                    "error": f"Skill '{skill_data['name']}' already exists (use force=True to overwrite)",
                }
            action = "updated"
            shutil.rmtree(dest)

        dest.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        (dest / "SKILL.md").write_text(skill_data["content"], encoding="utf-8")

        # Write any reference files
        ref_dir = dest / "references"
        for ref_name, ref_content in skill_data.get("references", {}).items():
            ref_dir.mkdir(parents=True, exist_ok=True)
            (ref_dir / ref_name).write_text(ref_content, encoding="utf-8")

        # Forge metadata
        meta = {
            "name": skill_data["name"],
            "description": skill_data.get("description", ""),
            "forged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_repo": f"{owner}/{repo_name}",
            "source_ref": ref,
        }
        (dest / "forge-meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

        logger.info("Skill '%s' forged -> %s (%s)", skill_data["name"], dest, action)
        return {
            "repo": f"{owner}/{repo_name}",
            "forge_status": action,
            "name": skill_data["name"],
            "installed_path": str(dest),
            "description": skill_data.get("description", ""),
        }


def _parse_forge_output(text: str, fallback_name: str) -> Optional[Dict[str, Any]]:
    """Extract skill name, content, description, and optional references from LLM output.

    Expects a SKILL.md block with frontmatter embedded in the response.
    """
    if not text or not text.strip():
        return None

    # Try to find a SKILL.md block (between ``` markers or just the raw content)
    content = text.strip()

    # If response has ```markdown or ``` fences, extract inside them
    m = re.search(r"```(?:markdown|md)?\s*\n(.*?)```", content, re.DOTALL)
    if m:
        content = m.group(1).strip()

    # Parse frontmatter from the extracted content
    fm, body = _parse_frontmatter(content)
    if fm and fm.get("name"):
        name = fm["name"]
        desc = fm.get("description", "")
    else:
        # No valid frontmatter — try to make one from the content
        name = fallback_name.lower().replace("_", "-").replace(" ", "-")
        desc = f"Skill generated from {fallback_name}"

        # Prepend a basic frontmatter
        content = f"---\nname: {name}\ndescription: >-\n  {desc}\n---\n\n{content}"
        fm = {"name": name, "description": desc}
        body = content

    return {
        "name": fm["name"],
        "description": fm.get("description", ""),
        "content": content,
        "references": {},  # Could be enhanced to extract additional files
    }


# ── Listing & Management ─────────────────────────────────────────────────

def list_installed_skills() -> List[Dict[str, Any]]:
    """List all skills currently installed in Cogent's skills directory."""
    skills_dir = COGENT_SKILLS_DIR
    if not skills_dir.is_dir():
        return []

    results: List[Dict[str, Any]] = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            continue

        try:
            text = skill_md.read_text(encoding="utf-8")
        except Exception:
            continue

        fm, _ = _parse_frontmatter(text)
        name = (fm.get("name") if fm else entry.name) or entry.name
        desc = (fm.get("description") if fm else "") or ""

        # Load forge-meta if present
        meta = {}
        meta_path = entry / "forge-meta.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Count resources
        resource_count = len(_relative_resources(entry))

        results.append({
            "name": name,
            "description": desc,
            "path": str(entry),
            "resource_count": resource_count,
            "imported_at": meta.get("imported_at") or meta.get("forged_at", ""),
            "source_repo": meta.get("source_repo", ""),
        })

    return results


def get_skill_detail(name: str) -> Optional[Dict[str, Any]]:
    """Get full detail for a single installed skill."""
    skills_dir = COGENT_SKILLS_DIR
    skill_dir = skills_dir / name
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        return None

    try:
        text = skill_md.read_text(encoding="utf-8")
    except Exception:
        return None

    fm, body = _parse_frontmatter(text)
    resources = _relative_resources(skill_dir)

    # Load forge-meta
    meta = {}
    meta_path = skill_dir / "forge-meta.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "name": (fm.get("name") if fm else name) or name,
        "description": (fm.get("description") if fm else "") or "",
        "metadata": fm if fm else {},
        "body": body[:5000],  # truncate for API
        "body_length": len(body),
        "path": str(skill_dir),
        "resources": resources,
        "resource_count": len(resources),
        "forge_meta": meta,
    }


def delete_skill(name: str) -> bool:
    """Remove an installed skill directory. Returns True if deleted."""
    skill_dir = COGENT_SKILLS_DIR / name
    if not skill_dir.is_dir():
        return False
    shutil.rmtree(skill_dir)
    logger.info("Skill '%s' deleted", name)
    return True
