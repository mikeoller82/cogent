import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import agent_skills


def write_skill(root: Path):
    skill_dir = root / "data-analysis"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "scripts").mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: data-analysis
description: Analyze CSV files and summarize datasets. Use when users ask about spreadsheets or data.
metadata:
  version: "1.0"
---
# Data Analysis

Use pandas for tabular data when available.
""",
        encoding="utf-8",
    )
    (skill_dir / "references" / "REFERENCE.md").write_text("Prefer concise summaries.", encoding="utf-8")
    (skill_dir / "scripts" / "analyze.py").write_text("print('ok')\n", encoding="utf-8")
    return skill_dir


def test_discover_skills_parses_frontmatter_and_body(tmp_path, monkeypatch):
    write_skill(tmp_path)
    monkeypatch.setattr(agent_skills, "_skill_roots", lambda: [tmp_path])

    skills = agent_skills.discover_skills()

    assert list(skills) == ["data-analysis"]
    skill = skills["data-analysis"]
    assert skill.description.startswith("Analyze CSV files")
    assert "Use pandas" in skill.body
    assert skill.metadata["metadata"]["version"] == "1.0"


def test_catalog_and_activation_use_progressive_disclosure(tmp_path, monkeypatch):
    write_skill(tmp_path)
    monkeypatch.setattr(agent_skills, "_skill_roots", lambda: [tmp_path])

    catalog = agent_skills.skill_catalog_for_prompt()
    activation = agent_skills.activate_skill("data-analysis")["result"]

    assert "1 specialized skills" in catalog
    assert "search_skills" in catalog
    assert "Use pandas" not in catalog
    assert '<skill_content name="data-analysis">' in activation
    assert "Use pandas" in activation
    assert "<file>references/REFERENCE.md</file>" in activation
    assert "<file>scripts/analyze.py</file>" in activation


def test_read_skill_resource_stays_inside_skill_directory(tmp_path, monkeypatch):
    write_skill(tmp_path)
    monkeypatch.setattr(agent_skills, "_skill_roots", lambda: [tmp_path])

    resource = agent_skills.read_skill_resource("data-analysis", "references/REFERENCE.md")["result"]
    escaped = agent_skills.read_skill_resource("data-analysis", "../secret.txt")["result"]

    assert '<skill_resource skill="data-analysis" path="references/REFERENCE.md">' in resource
    assert "Prefer concise summaries." in resource
    assert "Invalid skill resource path" in escaped
