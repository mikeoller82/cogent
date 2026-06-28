---
name: ponytail-review
description: Review the current code diff or implementation for over-engineering. Returns a prioritized delete-list of unnecessary code.
---

# /ponytail-review — Over-Engineering Audit

Reads the current working tree diff and reviews it against the ponytail rung ladder, returning a prioritized list of unnecessary code.

## Process

1. Reads `git diff` (or the current implementation context)
2. Evaluates each changed file against the 7 rungs:
   - Does this change need to exist at all? (YAGNI)
   - Is there existing codebase code to reuse?
   - Does stdlib already cover this?
   - Is there a native platform feature?
   - Does an installed dependency already handle it?
   - Can it be one line instead of many?
   - Is this the minimum viable version?
3. Returns categorized findings: DELETE / SHRINK / REUSE / KEEP

## Output format

```
### /ponytail-review findings

**DELETE (2)**
- `path/to/file.py:42-60` — unnecessary abstraction, inline it
- `path/to/helper.py` — entire file, use stdlib `pathlib` instead

**SHRINK (1)**
- `path/to/module.py:15-30` — 15 lines for a 2-line cache lookup

**REUSE (1)**
- `path/to/new.py:5` — duplicated `parse_date()` — use `src/utils.py:100`

**KEEP (4)**
— no changes recommended
```
