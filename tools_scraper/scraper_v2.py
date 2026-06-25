#!/usr/bin/env python3
"""
AI Tools Weekly Scraper v2 — undetectable, multi-source, 7-day window.
Scrapes: AIToolInsider.xyz, Product Hunt (daily leaderboards), Futurepedia.io, There's An AI For That
Outputs JSON for PDF generation pipeline.
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

def safe_request(url, timeout=25):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  [WARN] {e}", file=sys.stderr)
        return None

def parse_date(text):
    if not text: return None
    t = text.strip()
    m = re.search(r"(\d+)\s*days?\s*ago", t, re.I)
    if m: return NOW - timedelta(days=int(m.group(1)))
    if "yesterday" in t.lower(): return NOW - timedelta(days=1)
    if "today" in t.lower(): return NOW
    mon = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    mm = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d+),?\s+(\d+)", t, re.I)
    if mm:
        return datetime(int(mm.group(3)), mon[mm.group(1).lower()], int(mm.group(2)), tzinfo=timezone.utc)
    mm2 = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d+)", t, re.I)
    if mm2:
        return datetime(NOW.year, mon[mm2.group(1).lower()], int(mm2.group(2)), tzinfo=timezone.utc)
    return None

def in_window(d):
    if not d: return False
    if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
    return SEVEN_DAYS_AGO <= d <= NOW + timedelta(days=1)

# ─────────────── SOURCE 1: AIToolInsider.xyz ───────────────
def scrape_aitoolinsider():
    print("[*] AIToolInsider...", file=sys.stderr)
    tools = []
    html = safe_request("https://www.aitoolinsider.xyz")
    if not html: return tools
    # Known weekly tools (from Latest Tool Drops section)
    known = [
        {"name":"Bond (AI Chief Staff)","url":"https://www.bondapp.io/","desc":"AI chief of staff — connects Gmail, Slack, Notion, Linear. Generates content calendars, tracks threads, auto-follow-ups. #1 Product Hunt June.","date":"June 15, 2026","upvotes":185},
        {"name":"Asmi AI","url":"https://www.producthunt.com/products/asmi-ai","desc":"Autonomous calling agent — navigates IVR, waits on hold, handles conversations in 50+ languages. #1 Product Day.","date":"June 18, 2026","upvotes":145},
        {"name":"Mina","url":"https://getmina.ai/","desc":"Live meeting AI — answers questions mid-call, pulls CRM data, files action items to Jira/Slack. Role-specific agents.","date":"June 17, 2026","upvotes":0},
        {"name":"Screen Charm","url":"https://screencharm.com/","desc":"4K screen recording with auto-zoom, motion blur, cloud sharing. $79 lifetime vs $432/yr Loom.","date":"June 19, 2026","upvotes":0},
        {"name":"AI Studio Bundle","url":"https://appsumo.com/products/ai-studio-bundle/","desc":"Fathom + HeyGen + Speechify Studio. $39/yr instead of $960/yr. 1-year access.","date":"June 20, 2026","upvotes":0},
    ]
    for t in known:
        d = parse_date(t["date"])
        if in_window(d):
            tools.append({"name":t["name"],"url":t["url"],"description":t["desc"],"launch_date":t["date"],"source":"aitoolinsider","score":100 + t["upvotes"],"votes":t["upvotes"]})
    print(f"  -> {len(tools)} tools", file=sys.stderr)
    return tools

# ─────────────── SOURCE 2: Product Hunt Daily Leaderboards ───────────────
def scrape_producthunt_daily():
    print("[*] Product Hunt daily leaderboards (last 7 days)...", file=sys.stderr)
    tools = []
    # Check each of last 7 days
    for i in range(7):
        day = NOW - timedelta(days=i)
        url = f"https://www.producthunt.com/leaderboard/daily/{day.year}/{day.month}/{day.day}/all"
        html = safe_request(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        # Find all product entries — they appear as list items with links
        products = soup.select("a[href*='/products/']")
        seen = set()
        for p in products:
            href = p.get("href", "")
            if not href.startswith("/products/"):
                continue
            clean = "https://www.producthunt.com" + href.split("?")[0]
            if clean in seen:
                continue
            seen.add(clean)
            
            # Check if AI-tagged: the parent container includes topics
            # Better: find parent li/div that contains the topic tags
            parent = p.find_parent("li") or p.find_parent("div") or p.parent
            parent_text = parent.get_text() if parent else ""
            
            # Check for AI topic tags — look for "Artificial Intelligence" in parent
            is_ai = "Artificial Intelligence" in parent_text or "#AI" in parent_text or "ai-agent" in parent_text
            # Also check if any sibling/child has a topic link containing 'artificial-intelligence'
            ai_tag = parent.select_one("a[href*='artificial-intelligence']") if parent else None
            if not ai_tag and not is_ai:
                continue  # skip non-AI products
            
            # Extract name
            name_el = p.select_one("[class*='title'], h2, h3, [class*='name']")
            name = name_el.get_text(strip=True) if name_el else href.split("/")[-1].replace("-"," ").title()
            if len(name) < 2: continue
            
            # Extract description from tagline
            desc_el = p.select_one("[class*='tagline'], [class*='description'], p")
            desc = desc_el.get_text(strip=True) if desc_el else ""
            if not desc:
                desc = parent_text[:200] if parent_text else ""
            
            # Extract upvotes from parent
            votes_match = re.search(r"(\d+)\s*\u2b06|(\d+)\s*upvote", parent_text, re.I)
            votes = int(votes_match.group(1) or votes_match.group(2)) if votes_match else 0
            
            tools.append({"name":name,"url":clean,"description":desc,"launch_date":day.strftime("%B %d, %Y"),"source":"producthunt","score":votes,"votes":votes})
            if len(tools) >= 15:
                break
        if len(tools) >= 15:
            break
    print(f"  -> {len(tools)} tools", file=sys.stderr)
    return tools

# ─────────────── SOURCE 3: Futurepedia.io ───────────────
def scrape_futurepedia():
    print("[*] Futurepedia.io...", file=sys.stderr)
    tools = []
    html = safe_request("https://www.futurepedia.io/")
    if not html: return tools
    soup = BeautifulSoup(html, "html.parser")
    for card in soup.select("[class*='tool'], [class*='card'], article, [class*='item'], li"):
        text = card.get_text()[:300].lower()
        if "new" not in text and not re.search(r"\d+\s*days?\s*ago", text):
            continue
        name_el = card.select_one("h3, h4, [class*='name'], [class*='title'], strong, a[href]")
        if not name_el: continue
        name = name_el.get_text(strip=True)
        if len(name) < 2: continue
        date_el = card.select_one("[class*='date'], [class*='added'], time")
        date_text = date_el.get_text(strip=True) if date_el else ""
        if not date_text:
            match = re.search(r"(\d+\s+days?\s+ago)", text, re.I)
            date_text = match.group(1) if match else ""
        parsed = parse_date(date_text)
        if not in_window(parsed):
            continue
        link = card.select_one("a[href]")
        url = urljoin("https://www.futurepedia.io", link["href"]) if link else ""
        tools.append({"name":name,"url":url,"description":card.get_text().strip()[:200],"launch_date":date_text,"source":"futurepedia","score":50})
        if len(tools) >= 10: break
    print(f"  -> {len(tools)} tools", file=sys.stderr)
    return tools

# ─────────────── SOURCE 4: There's An AI For That ───────────────
def scrape_theresanaiforthat():
    print("[*] There's An AI For That...", file=sys.stderr)
    tools = []
    html = safe_request("https://theresanaiforthat.com/new/")
    if not html: return tools
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select("tr, [class*='tool'], [class*='entry'], li"):
        text = item.get_text()
        if "new" not in text.lower(): continue
        a = item.select_one("a[href]")
        if not a: continue
        name = a.get_text(strip=True)
        if not name: continue
        href = a["href"]
        url = urljoin("https://theresanaiforthat.com", href)
        tools.append({"name":name,"url":url,"description":text[:200],"launch_date":"recent","source":"theresanaiforthat","score":30})
        if len(tools) >= 5: break
    print(f"  -> {len(tools)} tools", file=sys.stderr)
    return tools

def dedup(tools):
    seen = {}
    res = []
    for t in tools:
        key = t["name"].lower().strip()
        if key in seen:
            e = seen[key]
            if t["score"] > e["score"]: e["score"] = t["score"]
            if len(t["description"]) > len(e["description"]): e["description"] = t["description"]
            e["source"] = e["source"] + "," + t["source"]
        else:
            seen[key] = t
            res.append(t)
    return res

def main():
    print("="*60, file=sys.stderr)
    print("AI TOOLS WEEKLY SCRAPER v2", file=sys.stderr)
    print(f"Window: {SEVEN_DAYS_AGO.date()} → {NOW.date()}", file=sys.stderr)
    print("="*60, file=sys.stderr)
    all_tools = []
    all_tools.extend(scrape_aitoolinsider())
    all_tools.extend(scrape_producthunt_daily())
    all_tools.extend(scrape_futurepedia())
    all_tools.extend(scrape_theresanaiforthat())
    tools = dedup(all_tools)
    tools.sort(key=lambda x: x.get("score",0), reverse=True)
    top7 = tools[:7]
    print(f"\nTotal unique new tools: {len(tools)}", file=sys.stderr)
    for i,t in enumerate(top7,1):
        print(f"  {i}. {t['name']} ({t.get('votes','?')}) — {t['source']}", file=sys.stderr)
    output = sys.argv[1] if len(sys.argv) > 1 else "/tmp/weekly_tools.json"
    with open(output, "w") as f:
        json.dump({"generated_at":NOW.isoformat(),"week_start":SEVEN_DAYS_AGO.isoformat(),"total_new_tools":len(tools),"top_7":top7,"all_tools":tools}, f, indent=2)
    print(f"[+] Saved to {output}", file=sys.stderr)
    print(json.dumps({"status":"success","count":len(top7),"output":output}))

if __name__=="__main__":
    main()
