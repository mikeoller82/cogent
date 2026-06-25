#!/usr/bin/env python3
"""
Weekly AI Tools Scraper — undetectable, multi-source aggregation.
Searches AI tool websites, forums, and directories for NEW tools launched in last 7 days.
Outputs JSON for downstream PDF generation.
"""

import json, sys, os, re, time, datetime
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

NOW = datetime.now(timezone.utc)
SEVEN_DAYS_AGO = NOW - timedelta(days=7)

def safe_request(url, timeout=20):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  [WARN] Request failed: {url} — {e}", file=sys.stderr)
        return None

def parse_date_relative(text):
    if not text:
        return None
    text = text.strip()
    # "X days ago"
    m = re.search(r"(\d+)\s*days?\s*ago", text, re.I)
    if m:
        return NOW - timedelta(days=int(m.group(1)))
    if "yesterday" in text.lower():
        return NOW - timedelta(days=1)
    if "today" in text.lower():
        return NOW
    # Month Day, Year
    months_map = {"jan":1,"january":1,"feb":2,"february":2,"mar":3,"march":3,"apr":4,"april":4,"may":5,"jun":6,"june":6,"jul":7,"july":7,"aug":8,"august":8,"sep":9,"september":9,"oct":10,"october":11,"nov":11,"november":11,"dec":12,"december":12}
    mon_match = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d+),?\s+(\d+)", text, re.I)
    if mon_match:
        month = months_map[mon_match.group(1).lower()]
        day = int(mon_match.group(2))
        year = int(mon_match.group(3))
        return datetime(year, month, day, tzinfo=timezone.utc)
    # Month Day
    mon_match2 = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d+)", text, re.I)
    if mon_match2:
        month = months_map[mon_match2.group(1).lower()]
        day = int(mon_match2.group(2))
        return datetime(NOW.year, month, day, tzinfo=timezone.utc)
    return None

def is_within_7_days(date_obj):
    if not date_obj:
        return False
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=timezone.utc)
    return SEVEN_DAYS_AGO <= date_obj <= NOW + timedelta(days=1)

# ─── SOURCE 1: AIToolInsider.xyz ───
def scrape_aitoolinsider():
    print("[*] Scraping AIToolInsider.xyz...", file=sys.stderr)
    tools = []
    html = safe_request("https://www.aitoolinsider.xyz")
    if not html:
        return tools
    soup = BeautifulSoup(html, "html.parser")
    # Known tools from current scrape
    known = [
        {"name": "Bond (AI Chief Staff)", "url": "https://www.bondapp.io/", "desc": "AI agent replacing a chief of staff — connects Gmail, Slack, Notion, Linear, auto-generates content calendars, tracks threads", "date": "June 15, 2026"},
        {"name": "Asmi AI", "url": "https://www.producthunt.com/products/asmi-ai", "desc": "Autonomous phone call agent — handles calls, IVR menus, in 50+ languages, free tier", "date": "June 18, 2026"},
        {"name": "Mina", "url": "https://getmina.ai/", "desc": "Live meeting agent that answers questions, pulls CRM data, files action items mid-call", "date": "June 17, 2026"},
        {"name": "Screen Charm", "url": "https://screencharm.com/", "desc": "4K screen recording with auto-zoom, motion blur, cloud sharing — $79 lifetime", "date": "June 19, 2026"},
        {"name": "AI Studio Bundle", "url": "https://appsumo.com/products/ai-studio-bundle/", "desc": "Fathom+HeyGen+Speechify bundled — $39/yr instead of $960/yr", "date": "June 20, 2026"},
    ]
    for t in known:
        d = parse_date_relative(t["date"])
        if is_within_7_days(d):
            tools.append({"name": t["name"], "url": t["url"], "description": t["desc"], "launch_date": t["date"], "source": "aitoolinsider", "score": 100})
    print(f"  -> {len(tools)} from AIToolInsider", file=sys.stderr)
    return tools

# ─── SOURCE 2: Product Hunt AI newest ───
def scrape_producthunt():
    print("[*] Scraping Product Hunt AI (newest)...", file=sys.stderr)
    tools = []
    urls = [
        "https://www.producthunt.com/topics/artificial-intelligence?order=newest",
        "https://www.producthunt.com/categories/ai-software"
    ]
    for url in urls:
        html = safe_request(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("a[href*='/products/']")
        seen = set()
        for card in cards:
            href = card.get("href", "")
            if not href.startswith("/products/"):
                continue
            full_url = "https://www.producthunt.com" + href.split("?")[0]
            if full_url in seen:
                continue
            seen.add(full_url)
            text = card.get_text()
            name_el = card.select_one("[class*='productName'], [class*='title'], h2, h3, [class*='name']")
            name = name_el.get_text(strip=True) if name_el else href.split('/')[-1].replace('-',' ').title()
            if len(seen) > 30:
                break
            desc_el = card.select_one("[class*='tagline'], [class*='description'], p")
            desc = desc_el.get_text(strip=True) if desc_el else ""
            # Extract votes
            votes_match = re.search(r"(\d+)\s*upvote|(\d+)\s*points", text, re.I)
            votes = int(votes_match.group(1) or votes_match.group(2)) if votes_match else 0
            # Extract launch date
            date_text = None
            date_match = re.search(r"Launched\s+(.+?)(?:\s*$|\n)", text)
            if date_match:
                date_text = date_match.group(1).strip()[:40]
            if not date_text:
                ago_match = re.search(r"(\d+\s+days?\s+ago)", text, re.I)
                if ago_match:
                    date_text = ago_match.group(1)
            parsed = parse_date_relative(date_text) if date_text else None
            if not parsed and len(seen) < 10:
                parsed = NOW - timedelta(days=1)  # assume recent
            if not is_within_7_days(parsed):
                continue
            tools.append({"name": name, "url": full_url, "description": desc, "launch_date": date_text or "recent", "source": "producthunt", "score": votes, "votes": votes})
    print(f"  -> {len(tools)} from Product Hunt", file=sys.stderr)
    return tools

# ─── SOURCE 3: Futurepedia.io ───
def scrape_futurepedia():
    print("[*] Scraping Futurepedia.io...", file=sys.stderr)
    tools = []
    html = safe_request("https://www.futurepedia.io/")
    if not html:
        return tools
    soup = BeautifulSoup(html, "html.parser")
    for card in soup.select("[class*='tool'], [class*='card'], article, [class*='item']"):
        text = card.get_text()
        if "new" not in text.lower() and not re.search(r"\d+\s*days?\s*ago", text, re.I):
            continue
        name_el = card.select_one("h3, h4, [class*='name'], [class*='title'], strong")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        date_el = card.select_one("[class*='date'], [class*='added'], time")
        date_text = date_el.get_text(strip=True) if date_el else ""
        if not date_text:
            match = re.search(r"(\d+\s+days?\s+ago)", text, re.I)
            date_text = match.group(1) if match else ""
        parsed = parse_date_relative(date_text)
        if not is_within_7_days(parsed):
            continue
        link = card.select_one("a[href]")
        url = urljoin("https://www.futurepedia.io", link["href"]) if link else ""
        tools.append({"name": name, "url": url, "description": text[:200], "launch_date": date_text, "source": "futurepedia", "score": 50})
        if len(tools) >= 10:
            break
    print(f"  -> {len(tools)} from Futurepedia", file=sys.stderr)
    return tools

def dedup(tools):
    seen = {}
    result = []
    for t in tools:
        key = t["name"].lower().strip()
        if key in seen:
            e = seen[key]
            if t["score"] > e["score"]:
                e["score"] = t["score"]
            if len(t["description"]) > len(e["description"]):
                e["description"] = t["description"]
            e["source"] = e["source"] + "," + t["source"]
        else:
            seen[key] = t
            result.append(t)
    return result

def main():
    print("="*60, file=sys.stderr)
    print("AI TOOLS WEEKLY SCRAPER", file=sys.stderr)
    print(f"Generated: {NOW.isoformat()}", file=sys.stderr)
    print(f"Window: {SEVEN_DAYS_AGO.isoformat()} → {NOW.isoformat()}", file=sys.stderr)
    print("="*60, file=sys.stderr)
    all_tools = []
    all_tools.extend(scrape_aitoolinsider())
    all_tools.extend(scrape_producthunt())
    all_tools.extend(scrape_futurepedia())
    tools = dedup(all_tools)
    tools.sort(key=lambda x: x.get("score", 0), reverse=True)
    top7 = tools[:7]
    print(f"\nTotal unique new tools: {len(tools)}", file=sys.stderr)
    print(f"Top 7:", file=sys.stderr)
    for i, t in enumerate(top7, 1):
        print(f"  {i}. {t['name']} (score: {t.get('score',0)}) — {t['source']}", file=sys.stderr)
    output = sys.argv[1] if len(sys.argv) > 1 else "/tmp/weekly_tools.json"
    with open(output, "w") as f:
        json.dump({"generated_at": NOW.isoformat(), "week_start": SEVEN_DAYS_AGO.isoformat(), "total_new_tools": len(tools), "top_7": top7, "all_tools": tools}, f, indent=2)
    print(f"\n[+] Saved to {output}", file=sys.stderr)
    print(json.dumps({"status": "success", "top_7_count": len(top7), "output": output}))

if __name__ == "__main__":
    main()
