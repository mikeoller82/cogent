# Cogent Agent Skills

Cogent discovers Agent Skills from:

- `.agents/skills/`
- `.cogent/skills/`
- Any extra directories listed in `COGENT_SKILLS_PATHS`, separated by `:`

Each skill is a directory with a required `SKILL.md` file:

```text
my-skill/
  SKILL.md
  references/
  scripts/
  assets/
```

`SKILL.md` must start with YAML frontmatter:

```markdown
---
name: my-skill
description: What this skill does and when Cogent should use it.
---

Skill instructions go here.
```

Cogent exposes skill names and descriptions in the system prompt. When a task matches a skill, the model can call `activate_skill`, then `read_skill_resource` for bundled references, scripts, or assets.
