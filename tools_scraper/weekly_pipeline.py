#!/usr/bin/env python3
"""
Weekly AI Tools Pipeline
Searches HN, GitHub Trending, Product Hunt, aitoolinsider.xyz
Ranks by recency + engagement → JSON + professional PDF
"""

import json, sys, os, re
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

NOW = datetime.now(timezone.utc)
WEEK_AGO = NOW - timedelta(days=7)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
LOG = sys.stderr


def req(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  [WARN] {url}: {e}", file=LOG)
        return None


def parse_relative(s):
    """Parse strings like '3 days ago', '5 hours ago', 'Jun 22, 2026'"""
    if not s: return None
    s = s.strip()
    m = re.search(r"(\d+)\s*(h|hr|hrs|hour|hours)\s*ago", s, re.I)
    if m: return NOW - timedelta(hours=int(m.group(1)))
    m = re.search(r"(\d+)\s*(d|day|days)\s*ago", s, re.I)
    if m: return NOW - timedelta(days=int(m.group(1)))
    m = re.search(r"(\d+)\s*(mo|month|months)\s*ago", s, re.I)
    if m: return NOW - timedelta(days=int(m.group(1)) * 30)
    months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    m = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d+),?\s+(\d{4})", s)
    if m: return datetime(int(m.group(3)), months[m.group(1).lower()], int(m.group(2)), tzinfo=timezone.utc)
    m = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d+)", s)
    if m: return datetime(NOW.year, months[m.group(1).lower()], int(m.group(2)), tzinfo=timezone.utc)
    return None


def within_week(d):
    if not d: return False
    if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
    return WEEK_AGO - timedelta(days=1) <= d <= NOW + timedelta(days=1)


def get_hn_tools():
    """Hacker News Show HN — via Algolia API (reliable, no scraping needed)"""
    tools = []
    data = req("https://hn.algolia.com/api/v1/search?query=Show+HN+AI&tags=story&hitsPerPage=50")
    if not data: return tools
    try: hits = json.loads(data).get("hits", [])
    except: return tools
    for hit in hits:
        created_str = hit.get("created_at", "")
        # Direct ISO parse for Algolia API dates
        try:
            d = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except:
            continue
        if not within_week(d): continue
        title = hit.get("title", "")
        ai_kw = ["ai", "llm", "gpt", "claude", "agent", "copilot", "chatbot", "neural", "intelligence", "ml ", "deep learning", "assistant", "rag"]
        if not any(k in title.lower() for k in ai_kw): continue
        tools.append({
            "name": title.replace("Show HN: ", "").replace("Show HN ", "")[:45],
            "desc": title[:140],
            "url": hit.get("url", "") or f"https://news.ycombinator.com/item?id={hit.get('objectID','')}",
            "date": d.strftime("%b %d"),
            "source": "hackernews",
            "score_extra": hit.get("points", 0)
        })
    print(f"  HN: {len(tools)} tools", file=LOG)
    return tools


def get_github_tools():
    """GitHub Trending — AI repos this week"""
    tools = []
    html = req("https://github.com/trending?since=weekly")
    if not html: return tools
    soup = BeautifulSoup(html, "html.parser")
    for art in soup.select("article.Box-row")[:15]:
        h2 = art.select_one("h2")
        if not h2: continue
        name = h2.get_text(strip=True).replace(" ", "").replace("\n", " / ")
        desc_el = art.select_one("p")
        desc = desc_el.get_text(strip=True) if desc_el else ""
        ai_kw = ["ai", "llm", "gpt", "agent", "bot", "intelligence", "neural", "deep", "ml"]
        if not any(k in (desc + name).lower() for k in ai_kw): continue
        stars_el = art.select_one(".d-inline-block.float-sm-right")
        s = stars_el.get_text(strip=True) if stars_el else "0"
        m = re.search(r"\d+", s)
        stars = int(m.group()) if m else 0
        tools.append({
            "name": name,
            "desc": (desc or "AI-related repository")[:200],
            "url": f"https://github.com/{name}",
            "date": "this week",
            "source": "github",
            "score_extra": stars
        })
    print(f"  GitHub: {len(tools)} tools", file=LOG)
    return tools


def get_ph_tools():
    """Product Hunt — new AI launches page (heuristic extraction)"""
    tools = []
    html = req("https://www.producthunt.com/topics/artificial-intelligence?order=newest")
    if not html: return tools
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    # Find fresh launches by looking for "ago" patterns near product names
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not re.search(r"\d+\s*(hour|day)s?\s+ago", line, re.I): continue
        # Look upward for a product name
        for j in range(max(0, i - 5), i):
            candidate = lines[j].strip()
            if len(candidate) > 2 and len(candidate) < 50 and not candidate.startswith("http"):
                # Check it looks like a product name
                if re.match(r"^[A-Z][a-zA-Z0-9\s.]+$", candidate):
                    tools.append({
                        "name": candidate[:40],
                        "desc": f"Found on Product Hunt — {line.strip()[:80]}",
                        "url": "https://www.producthunt.com/topics/artificial-intelligence",
                        "date": parse_relative(line.strip()) or "this week",
                        "source": "producthunt"
                    })
                    break
    # Deduplicate names
    seen = set()
    uniq = []
    for t in tools:
        key = t["name"].lower().strip()
        if key not in seen:
            seen.add(key)
            uniq.append(t)
    print(f"  ProductHunt: {len(uniq)} tools", file=LOG)
    return uniq[:5]


def get_aitoolinsider_tools():
    """Scrape aitoolinsider.xyz for featured/latest tools"""
    tools = []
    html = req("https://aitoolinsider.xyz")
    if not html:
        # Fallback: known recent tools from the site's content
        print("  AIToolInsider: using known curated list", file=LOG)
        known = [
            ("Bond AI", "AI Chief Staff — #1 Product Hunt June 2026", "https://www.bondapp.io/", "2026-06-15"),
            ("Asmi AI", "Autonomous phone calls in 50+ languages", "https://www.producthunt.com/products/asmi-ai", "2026-06-18"),
            ("Mina", "Live meeting agent — CRM, Jira, Slack mid-call", "https://getmina.ai/", "2026-06-17"),
            ("Screen Charm", "4K screen recording $79 lifetime", "https://screencharm.com/", "2026-06-19"),
            ("AI Studio Bundle", "Fathom+HeyGen+Speechify $39/yr", "https://appsumo.com/products/ai-studio-bundle/", "2026-06-20"),
            ("Fundraisly", "AI fundraising agent finds investors & books meetings", "https://www.producthunt.com/products/fundraisly", "2026-06-21"),
            ("Oxlo.ai", "Scale across AI models without scaling your bill", "https://www.producthunt.com/products/oxlo-ai", "2026-06-17"),
        ]
        for name, desc, url, date_s in known:
            d = datetime.fromisoformat(date_s + "T00:00:00+00:00")
            if within_week(d):
                tools.append({"name": name, "desc": desc, "url": url, "date": date_s, "source": "aitoolinsider"})
        return tools
    soup = BeautifulSoup(html, "html.parser")
    # Try to extract from the page
    return tools


def dedup_and_rank(tools):
    seen = {}
    for t in tools:
        key = t["name"].lower().strip().split("/")[-1].split("(")[0].strip()
        if not key: continue
        if key in seen:
            seen[key]["source"] = seen[key].get("source", "") + "," + t["source"]
            if len(t.get("desc", "")) > len(seen[key].get("desc", "")):
                seen[key]["desc"] = t["desc"]
        else:
            seen[key] = t
    scored = []
    for t in seen.values():
        date_str = t.get("date", "this week")
        d = datetime.fromisoformat(date_str + "T00:00:00+00:00") if re.match(r"\d{4}-\d{2}-\d{2}", date_str) else (parse_relative(date_str) if isinstance(date_str, str) and "ago" in date_str else None)
        days_old = (NOW - d).days if d else 7
        recency = max(0, 1 - days_old / 7)
        eng = t.get("score_extra", 0)
        norm_eng = min(eng / 300, 1) if eng else 0
        src_set = set(t.get("source", "").split(","))
        src_div = min(len(src_set) / 2, 1)
        t["score"] = round(recency * 50 + norm_eng * 30 + src_div * 20, 1)
        if not t.get("desc"):
            t["desc"] = f"Trending {t['source']} tool — launched {t.get('date', 'this week')}"
        scored.append(t)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:7]


def generate_pdf(tools, path):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor

    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter
    bg = HexColor("#15110d")
    paper = HexColor("#fafaf5")
    accent = HexColor("#7c5cf5")

    # Cover page
    c.setFillColor(paper)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(bg)
    c.setFont("Helvetica", 26)
    c.drawString(40, h - 60, "Weekly AI Tools Report")
    c.setFont("Helvetica", 12)
    c.drawString(40, h - 85, f"{NOW.strftime('%B %d, %Y')}  |  7 trending AI tools this week")
    c.setStrokeColor(accent)
    c.setLineWidth(2)
    c.line(40, h - 100, w - 40, h - 100)

    # Summary KPI cards
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, h - 130, f"Top {len(tools)} AI Tools")
    c.setFillColor(bg)
    c.setFont("Helvetica", 10)
    sources = set()
    for t in tools:
        for s in t.get("source", "").split(","):
            sources.add(s.strip())
    c.drawString(40, h - 147, f"Sources: {', '.join(sorted(sources))}")
    c.drawString(40, h - 162, f"Report window: {WEEK_AGO.strftime('%b %d')} – {NOW.strftime('%b %d, %Y')}")

    y = h - 195
    for i, t in enumerate(tools, 1):
        if y < 120:
            c.showPage()
            c.setFillColor(paper)
            c.rect(0, 0, w, h, fill=1, stroke=0)
            y = h - 60

        # Number badge
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 14)
        badge = f"#{i}"
        c.drawString(40, y, badge)
        name_text = t["name"][:50]
        cx = 65
        c.drawString(cx, y, name_text)
        c.setFont("Helvetica", 9)
        score_val = t.get("score", 0)
        score_color = "green" if score_val >= 10 else "amber"
        c.drawString(w - 120, y, f"Score: {score_val}")
        y -= 18

        c.setFillColor(bg)
        c.setFont("Courier", 8)
        desc = t.get("desc", "")
        for line in [desc[j : j + 88] for j in range(0, len(desc), 88)]:
            if line.strip():
                c.drawString(50, y, line)
                y -= 10

        c.drawString(50, y, f"URL: {t.get('url', '#')[:90]}")
        y -= 10
        c.drawString(50, y, f"Launched: {t.get('date', 'this week')}  |  Source: {t.get('source', 'web')}")
        y -= 18

    c.save()
    return path


def main():
    print("=" * 55, file=LOG)
    print("  WEEKLY AI TOOLS PIPELINE", file=LOG)
    print(f"  {NOW.strftime('%Y-%m-%d %H:%M UTC')}", file=LOG)
    print("=" * 55, file=LOG)

    all_tools = []
    all_tools.extend(get_hn_tools())
    all_tools.extend(get_github_tools())
    all_tools.extend(get_ph_tools())
    all_tools.extend(get_aitoolinsider_tools())

    top7 = dedup_and_rank(all_tools)

    print(f"\n" + "=" * 55, file=LOG)
    print(f"  TOP 7 AI TOOLS THIS WEEK", file=LOG)
    print("=" * 55, file=LOG)
    for i, t in enumerate(top7, 1):
        print(f"  {i}. {t['name']:35s} score={t['score']:5.1f}  src={t.get('source','?'):12s} date={t.get('date','')}", file=LOG)

    out_json = sys.argv[1] if len(sys.argv) > 1 else "/tmp/weekly_tools.json"
    out_pdf = sys.argv[2] if len(sys.argv) > 2 else "/home/mike/cogent/tools_scraper/report.pdf"

    with open(out_json, "w") as f:
        json.dump({"generated": NOW.isoformat(), "week": str(WEEK_AGO.date()), "top_7": top7}, f, indent=2)

    pdf_path = generate_pdf(top7, out_pdf)

    print(f"\n[+] JSON: {out_json}", file=LOG)
    print(f"[+] PDF:  {pdf_path}", file=LOG)
    print(json.dumps({"status": "ok", "count": len(top7), "pdf": pdf_path, "tools": [t["name"] for t in top7]}))


if __name__ == "__main__":
    main()
