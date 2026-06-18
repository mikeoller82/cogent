"""Cinematic terminal display for Cogent CLI.

Epic-design visual system: full-width banners, bordered panels,
box-drawing characters, glass-depth aesthetic. Zero external dependencies.
"""

from __future__ import annotations

import json
import sys
from shutil import get_terminal_size
from typing import Any

# ── ANSI ──────────────────────────────────────────────────────────────
RS = "\033[0m"   # reset
BD = "\033[1m"   # bold
DM = "\033[2m"   # dim
IT = "\033[3m"   # italic
UL = "\033[4m"   # underline
RV = "\033[7m"   # reverse

def fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"

def bg(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m"

def _strip(s: str) -> str:
    import re
    return re.sub(r'\033\[[0-9;]*m', '', s)

# ── Palette ───────────────────────────────────────────────────────────
PURPLE  = fg(181, 168, 245)
PURPLE2 = fg(160, 140, 240)
PURPLE3 = fg(120, 100, 220)
WARM    = fg(245, 237, 224)
DIM     = fg(168, 160, 146)
GREEN   = fg(34, 197, 94)
AMBER   = fg(245, 158, 11)
RED     = fg(239, 68, 68)
CYAN    = fg(6, 182, 212)
WHITE   = "\033[97m"

# Backgrounds
BG_DARK  = bg(22, 17, 12)
BG_PURP  = bg(60, 50, 100)
BG_GREEN = bg(20, 80, 40)
BG_AMBER = bg(70, 50, 10)
BG_RED   = bg(70, 30, 30)
BG_CYAN  = bg(10, 60, 70)
BG_WARM  = bg(45, 38, 32)

# ── Terminal ──────────────────────────────────────────────────────────

def _tw() -> int:
    return get_terminal_size(fallback=(80, 24)).columns

def _len(text: str) -> int:
    return len(_strip(text))

# ══════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════

# ── Full-width banners ────────────────────────────────────────────────

def banner(text: str, sub: str = "") -> None:
    """Large cinematic banner — full-width colored bar with text."""
    w = _tw()
    line = f" {BD}{PURPLE}◆{RS} {WHITE}{BD}{text}{RS}"
    if sub:
        line += f" {PURPLE2}│{RS} {DIM}{sub}{RS}"
    spacer = max(0, w - _len(line) - 2)
    print(f"{BG_PURP}{PURPLE3}{'▀' * w}{RS}")
    print(f"{BG_PURP} {line}{' ' * spacer}{RS}")
    print(f"{BG_PURP}{PURPLE3}{'▄' * w}{RS}")

def header(title: str, accent: str = PURPLE, symbol: str = "◆") -> None:
    """Section header with accent line."""
    w = _tw()
    print()
    print(f"  {accent}{symbol} {BD}{title}{RS}")
    print(f"  {DM}{accent}{'─' * min(w - 4, 60)}{RS}")

def subheader(title: str) -> None:
    """Minor section with right-angle bracket."""
    print(f"\n  {PURPLE}└─{RS} {WHITE}{BD}{title}{RS}")

# ── Bordered panels ───────────────────────────────────────────────────

def panel(title: str, content: str, accent: str = PURPLE) -> None:
    """Draw a bordered console panel around content."""
    w = min(_tw() - 2, 76)
    tl, tr, bl, br = "╔", "╗", "╚", "╝"
    hbar, vbar = "═", "║"

    # Title
    title_text = f" {title} " if title else ""
    title_len = _strip(title_text).len()
    top_len = w - title_len

    print(f"  {accent}{tl}{hbar * (title_len + 2) if title else hbar * w}{tr}{RS}")
    if title:
        print(f"  {accent}{vbar}{RS} {BD}{accent}{title}{RS} {' ' * (w - title_len - 2)}{accent}{vbar}{RS}")
        print(f"  {accent}{vbar}{RS}{DM}{hbar * w}{RS}{accent}{vbar}{RS}")

    for line in content.split("\n"):
        clean = _strip(line)
        if len(clean) > w:
            # Overflow: split
            print(f"  {accent}{vbar}{RS} {line[:w]}")
            print(f"  {accent}{vbar}{RS} {line[w:]}{' ' * (w - _strip(line[w:]).len())}{accent}{vbar}{RS}")
        else:
            print(f"  {accent}{vbar}{RS} {line}{' ' * (w - len(clean))}{accent}{vbar}{RS}")

    print(f"  {accent}{bl}{hbar * w}{br}{RS}")

# ── Content blocks ────────────────────────────────────────────────────

def section(title: str, items: list[tuple[str, str]], accent: str = PURPLE) -> None:
    """Named section with key-value pairs in a bordered box."""
    lines = []
    for k, v in items:
        lines.append(f"{DM}{k}{RS}  {WARM}{v}{RS}")
    panel(title, "\n".join(lines), accent)

def table(rows: list[list[str]], headers: list[str] | None = None) -> None:
    """Bordered table with grid lines."""
    if not rows:
        return

    # Calculate widths
    col_count = max(len(r) for r in rows)
    if headers:
        col_count = max(col_count, len(headers))

    widths = [0] * col_count
    if headers:
        for i, h in enumerate(headers):
            widths[i] = max(widths[i], len(h))
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(_strip(str(cell))))

    # Clamp to terminal
    max_w = _tw() - 4 - (col_count - 1) * 3 - 2  # border + padding
    total = sum(widths)
    if total > max_w:
        ratio = max_w / total
        widths = [max(1, int(w * ratio)) for w in widths]
        # Distribute remainder
        remainder = max_w - sum(widths)
        for i in range(remainder):
            widths[i % col_count] += 1

    sep = f"  {PURPLE}├{RS}{DM}{'─' * (sum(widths) + (col_count - 1) * 2)}{RS}{PURPLE}┤{RS}"

    # Top
    print(f"  {PURPLE}┌{RS}{DM}{'─' * (sum(widths) + (col_count - 1) * 2)}{RS}{PURPLE}┐{RS}")

    if headers:
        parts = []
        for i, h in enumerate(headers):
            parts.append(f"{BD}{PURPLE}{h}{RS}")
        header_line = "  " + "  ".join(
            f"{PURPLE}│{RS} {h.ljust(widths[idx])} " for idx, h in enumerate(headers)
        ) + f"{PURPLE}│{RS}"
        print(header_line)
        print(sep)

    for row_idx, row in enumerate(rows):
        parts = []
        for i, cell in enumerate(row[:col_count]):
            text = str(cell)
            display = text if len(text) <= widths[i] else text[:widths[i]]
            if i == 0:
                parts.append(f"{WARM}{display.ljust(widths[i])}{RS}")
            else:
                parts.append(f"{display.ljust(widths[i])}")
        line = "  " + "  ".join(
            f"{PURPLE}│{RS} {parts[idx]} " for idx in range(len(parts))
        ) + f"{PURPLE}│{RS}"
        print(line)

        # Row separator (except last)
        if row_idx < len(rows) - 1:
            print(sep)

    # Bottom
    print(f"  {PURPLE}└{RS}{DM}{'─' * (sum(widths) + (col_count - 1) * 2)}{RS}{PURPLE}┘{RS}")

# ── Status indicators ─────────────────────────────────────────────────

def ok(text: str) -> None:
    """Green check — success."""
    print(f"  {GREEN}●{RS} {GREEN}{BD}{text}{RS}")

def fail(text: str) -> None:
    """Red x — error."""
    print(f"  {RED}●{RS} {RED}{BD}{text}{RS}", file=sys.stderr)

def warn(text: str) -> None:
    """Amber triangle — warning."""
    print(f"  {AMBER}●{RS} {AMBER}{BD}{text}{RS}", file=sys.stderr)

def hint(text: str) -> None:
    """Cyan dot — info."""
    print(f"  {CYAN}●{RS} {WARM}{text}{RS}")

# Short aliases
success = ok
error = fail
warning = warn
info = hint

def item(text: str, bullet: str = "•") -> None:
    """Bullet item."""
    print(f"  {DM}{bullet}{RS} {WARM}{text}{RS}")

def badge(label: str, color: str = PURPLE) -> str:
    """Return a colored badge string."""
    return f"{DM}[{RS}{color}{BD}{label}{RS}{DM}]{RS}"

def status_badge(status: str) -> str:
    """Colored status pill."""
    s = status.lower()
    if s in ("running", "active", "ok", "true", "yes"):
        return f"{GREEN}{RV} {s.upper()} {RS}"
    elif s in ("stopped", "inactive", "error", "false", "no"):
        return f"{RED}{RV} {s.upper()} {RS}"
    elif s in ("warning", "degraded", "stale"):
        return f"{AMBER}{RV} {s.upper()} {RS}"
    else:
        return f"{DM}{s.upper()}{RS}"

def keyval(key: str, value: str, key_w: int = 16) -> None:
    """Key-value with alignment."""
    print(f"  {DM}{key.ljust(key_w)}{RS} {WARM}{value}{RS}")

def divider(char: str = "─", color: str = DM + PURPLE) -> None:
    """Full-width divider."""
    w = _tw() - 2
    print(f"  {color}{char * min(w, 60)}{RS}")

# ── Raw / JSON ────────────────────────────────────────────────────────

def raw(text: str) -> None:
    """Passthrough — no formatting."""
    print(text)

def json_out(data: Any) -> None:
    """Pretty JSON (for --json flag paths — no ANSI)."""
    print(json.dumps(data, indent=2, default=str))

def _len(text: str) -> int:
    return len(_strip(text))
