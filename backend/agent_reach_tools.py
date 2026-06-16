"""Agent-Reach upstream tool wrappers for Cogent.

Provides async functions that wrap agent-reach's upstream CLI tools
and channel APIs, returning structured results for the LLM.

Agent-Reach design: it installs and configures upstream tools (yt-dlp,
gh CLI, bili-cli, feedparser, etc.) and the agent calls them directly.
These wrappers let Cogent LLM use them via the tool-calling protocol.

Usage:
    from agent_reach_tools import (
        agent_reach_doctor,
        youtube_transcript,
        github_repo_info,
        github_search_code,
        v2ex_hot_topics,
        v2ex_topic_detail,
        rss_read,
        bilibili_search,
    )

Each returns {"result": str, "artifact": None}
"""

import asyncio
import json
import shutil
import subprocess
import urllib.request
import urllib.parse
from typing import Optional

# ── Helpers ──────────────────────────────────────────────────────

_UA = "cogent/1.0"


async def _run(cmd: list[str], timeout: int = 30) -> tuple[str, str]:
    """Run a subprocess command, return (stdout, stderr).

    Raises RuntimeError on non-zero exit or timeout.
    """
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}")
    if proc.returncode != 0:
        err = stderr.decode().strip()
        raise RuntimeError(err or f"Exit code {proc.returncode}")
    return stdout.decode().strip(), stderr.decode().strip()


def _fetch_json(url: str, timeout: int = 15) -> dict | list:
    """Fetch a JSON endpoint with a simple GET."""
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _format_table(header: list[str], rows: list[list]) -> str:
    """Simple markdown table from header + rows."""
    lines = [" | ".join(header), " | ".join("---" for _ in header)]
    for r in rows:
        lines.append(" | ".join(str(c) for c in r))
    return "\n".join(lines)


# ── Doctor / Health Check ────────────────────────────────────────


async def agent_reach_doctor() -> dict:
    """Check health of all agent-reach channels."""
    try:
        from agent_reach.doctor import check_all, format_report
        from agent_reach.config import Config

        config = Config()
        results = check_all(config)
        report = format_report(results)
        return {"result": f"## Agent Reach Health\n\n{report}"}
    except ImportError:
        return {"result": "Agent Reach not installed. Run: pip install agent-reach"}
    except Exception as e:
        return {"result": f"Agent Reach doctor failed: {e}"}


# ── YouTube ──────────────────────────────────────────────────────


async def youtube_transcript(url: str) -> dict:
    """Extract YouTube video subtitles or metadata via yt-dlp.

    Args:
        url: Full YouTube URL (e.g. https://www.youtube.com/watch?v=...)
    """
    if not shutil.which("yt-dlp"):
        return {"result": "yt-dlp not available — needed for YouTube.\nInstall: pip install yt-dlp"}

    # Try subtitles in priority order: auto-en, manual en, raw subs
    for sub_lang in ("en", "en-orig", "a.en"):
        try:
            out, _ = await _run([
                "yt-dlp", "--skip-download",
                "--write-auto-sub", "--sub-langs", sub_lang,
                "--print", "sub",
                "-o", "/dev/null", url,
            ], timeout=60)
            if out:
                truncated = out[:25000]
                if len(out) > 25000:
                    truncated += "\n\n… (truncated, full transcript too long)"
                return {"result": f"## YouTube Transcript\n\n{truncated}"}
        except (RuntimeError, FileNotFoundError):
            pass

    # Fallback: manual subs only
    try:
        out, _ = await _run([
            "yt-dlp", "--skip-download",
            "--write-sub", "--sub-langs", "en",
            "--print", "sub",
            "-o", "/dev/null", url,
        ], timeout=60)
        if out:
            return {"result": f"## YouTube Transcript\n\n{out[:25000]}"}
    except (RuntimeError, FileNotFoundError):
        pass

    # Last resort: video metadata
    try:
        out, _ = await _run([
            "yt-dlp", "--print", "title",
            "--print", "channel",
            "--print", "duration_string",
            "--print", "description",
            url,
        ], timeout=30)
        parts = out.split("\n", 3)
        return {"result": (
            f"## YouTube Video\n\n"
            f"**Title:** {parts[0] if len(parts) > 0 else 'Unknown'}\n"
            f"**Channel:** {parts[1] if len(parts) > 1 else 'Unknown'}\n"
            f"**Duration:** {parts[2] if len(parts) > 2 else 'Unknown'}\n\n"
            f"**Description:**\n{parts[3][:5000] if len(parts) > 3 else 'N/A'}"
        )}
    except Exception as e:
        return {"result": f"Cannot fetch YouTube video: {e}"}


# ── GitHub ───────────────────────────────────────────────────────


def _fmt_gh_repo(r: dict) -> str:
    lang = r.get("primaryLanguage", {}).get("name", "") if isinstance(r.get("primaryLanguage"), dict) else (r.get("primaryLanguage") or "")
    topics = ", ".join(
        t.get("name", "") if isinstance(t, dict) else str(t)
        for t in (r.get("repositoryTopics") or [])
    )[:200]
    desc = r.get("description") or ""
    return (
        f"**{r.get('name', '')}** — {desc}\n"
        f"  ⭐ {r.get('stargazerCount', r.get('stargazers_count', 0))}  "
        f"⑂ {r.get('forkCount', r.get('forks_count', 0))}  "
        f"{'🔠 ' + lang if lang else ''}\n"
        f"  📍 {r.get('url', r.get('html_url', ''))}\n"
        + (f"  🏷️ {topics}\n" if topics else "")
    )


async def github_repo_info(repo: str) -> dict:
    """Get detailed info about a GitHub repository.

    Args:
        repo: Repository in "owner/repo" format.
    """
    if shutil.which("gh"):
        try:
            out, _ = await _run([
                "gh", "repo", "view", repo, "--json",
                "name,owner,description,url,stargazerCount,forkCount,openIssueCount,"
                "primaryLanguage,repositoryTopics,createdAt,pushedAt,licenseInfo,readme",
            ], timeout=15)
            d = json.loads(out)
            owner = d.get("owner", {})
            if isinstance(owner, dict):
                owner_name = owner.get("login", repo.split("/")[0])
            else:
                owner_name = str(owner)
            readme = d.get("readme", "")

            topics = ", ".join(
                t.get("name", "") if isinstance(t, dict) else str(t)
                for t in (d.get("repositoryTopics") or [])
            )
            result = (
                f"## {d['name']}\n\n"
                f"**Owner:** {owner_name}  \n"
                f"**Description:** {d.get('description', 'No description')}\n\n"
                f"⭐ {d['stargazerCount']} stars  |  "
                f"⑂ {d['forkCount']} forks  |  "
                f"🔧 {d.get('openIssueCount', 0)} open issues\n"
                f"**Language:** {d.get('primaryLanguage', {}).get('name', 'N/A') if isinstance(d.get('primaryLanguage'), dict) else (d.get('primaryLanguage') or 'N/A')}\n"
                f"**License:** {d.get('licenseInfo', {}).get('spdxId', 'N/A') if isinstance(d.get('licenseInfo'), dict) else (d.get('licenseInfo') or 'N/A')}\n"
                f"**Created:** {d.get('createdAt', '')[:10]}  |  "
                f"**Last push:** {d.get('pushedAt', '')[:10]}\n"
                + (f"**Topics:** {topics}\n" if topics else "")
                + f"\n**URL:** {d['url']}\n"
                + (f"\n---\n{readme[:3000]}" if readme else "")
            )
            return {"result": result}
        except (RuntimeError, json.JSONDecodeError):
            pass

    # Fallback: GitHub public API
    try:
        d = _fetch_json(f"https://api.github.com/repos/{repo}")
        owner = d.get("owner", {}) or {}
        desc = d.get("description") or "No description"
        result = (
            f"## {d.get('name', repo)}\n\n"
            f"**Owner:** {owner.get('login', '')}  \n"
            f"**Description:** {desc}\n\n"
            f"⭐ {d.get('stargazers_count', 0)} stars  |  "
            f"⑂ {d.get('forks_count', 0)} forks  |  "
            f"🔧 {d.get('open_issues_count', 0)} open issues\n"
            f"**Language:** {d.get('language') or 'N/A'}\n"
            f"**License:** {d.get('license', {}).get('spdx_id', 'N/A') if isinstance(d.get('license'), dict) else 'N/A'}\n"
            f"**Created:** {d.get('created_at', '')[:10]}  |  "
            f"**Last push:** {d.get('pushed_at', '')[:10]}\n\n"
            f"**URL:** {d.get('html_url', '')}\n"
        )
        return {"result": result}
    except Exception as e:
        return {"result": f"Cannot fetch GitHub repo: {e}"}


async def github_search(query: str, limit: int = 5) -> dict:
    """Search GitHub repositories by keyword.

    Args:
        query: Search query (e.g. "llm agent framework").
        limit: Max results (default 5, max 20).
    """
    limit = min(limit, 20)
    if shutil.which("gh"):
        try:
            out, _ = await _run([
                "gh", "search", "repos", query,
                "--sort", "stars", "--limit", str(limit),
                "--json", "name,owner,description,url,stargazerCount,forkCount,primaryLanguage",
            ], timeout=15)
            items = json.loads(out)
            if not items:
                return {"result": f"No GitHub repos found for '{query}'"}
            lines = [f"## GitHub Search: {query}\n"]
            for r in items:
                lines.append(_fmt_gh_repo(r))
            return {"result": "\n".join(lines)}
        except (RuntimeError, json.JSONDecodeError):
            pass

    try:
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&per_page={limit}"
        d = _fetch_json(url, timeout=15)
        items = d.get("items", [])
        if not items:
            return {"result": f"No GitHub repos found for '{query}'"}
        lines = [f"## GitHub Search: {query}\n"]
        for r in items:
            lines.append(_fmt_gh_repo(r))
        return {"result": "\n".join(lines)}
    except Exception as e:
        return {"result": f"Cannot search GitHub: {e}"}


async def github_search_code(query: str, limit: int = 5) -> dict:
    """Search GitHub code by keyword.

    Args:
        query: Code search query (e.g. "FastAPI user auth").
        limit: Max results (default 5, max 20).
    """
    limit = min(limit, 20)
    if shutil.which("gh"):
        try:
            out, _ = await _run([
                "gh", "search", "code", query,
                "--limit", str(limit),
                "--json", "repository,name,path,url",
            ], timeout=15)
            items = json.loads(out)
            lines = [f"## GitHub Code Search: {query}\n"]
            for r in items[:limit]:
                repo = r.get("repository", {})
                repo_name = repo.get("nameWithOwner", "") if isinstance(repo, dict) else str(repo)
                lines.append(
                    f"- **{r.get('name', '')}** in `{repo_name}`\n"
                    f"  Path: `{r.get('path', '')}`\n"
                    f"  {r.get('url', '')}"
                )
            return {"result": "\n".join(lines)}
        except (RuntimeError, json.JSONDecodeError):
            pass

    return {"result": "GitHub code search requires the `gh` CLI. Install: https://cli.github.com"}


# ── V2EX ─────────────────────────────────────────────────────────


async def v2ex_hot_topics(limit: int = 20) -> dict:
    """Get hot topics from V2EX.

    Args:
        limit: Max topics to return (default 20, max 50).
    """
    try:
        from agent_reach.channels.v2ex import V2EXChannel
        ch = V2EXChannel()
        topics = ch.get_hot_topics(min(limit, 50))
        if not topics:
            return {"result": "No hot topics available from V2EX."}
        lines = ["## V2EX Hot Topics\n"]
        for t in topics:
            lines.append(
                f"- **{t['title']}** — 💬 {t['replies']} replies\n"
                f"  [{t['node_title']}] {t['url']}"
            )
        return {"result": "\n".join(lines)}
    except ImportError:
        return {"result": "Agent Reach not installed (required for V2EX)."}
    except Exception as e:
        return {"result": f"V2EX error: {e}"}


async def v2ex_topic_detail(topic_id: int) -> dict:
    """Get full details of a V2EX topic including replies.

    Args:
        topic_id: V2EX topic ID from the URL (e.g. 12345 from v2ex.com/t/12345).
    """
    try:
        from agent_reach.channels.v2ex import V2EXChannel
        ch = V2EXChannel()
        t = ch.get_topic(topic_id)
        lines = [
            f"## {t['title']}\n",
            f"**Author:** {t.get('author', 'unknown')}  |  "
            f"**Node:** {t.get('node_title', '')}  |  "
            f"**Replies:** {t.get('replies_count', 0)}\n",
            f"---\n{t.get('content', '')}\n---\n",
            "### Replies\n",
        ]
        for r in (t.get("replies") or [])[:50]:
            lines.append(f"**{r.get('author', '')}:** {r.get('content', '')}")
        return {"result": "\n".join(lines)}
    except ImportError:
        return {"result": "Agent Reach not installed (required for V2EX)."}
    except Exception as e:
        return {"result": f"V2EX topic error: {e}"}


# ── RSS ──────────────────────────────────────────────────────────


async def rss_read(url: str, limit: int = 10) -> dict:
    """Parse an RSS/Atom feed and return recent entries.

    Args:
        url: RSS/Atom feed URL.
        limit: Max entries to return (default 10, max 50).
    """
    try:
        import feedparser

        f = feedparser.parse(url)
        if f.bozo and not f.entries:
            return {"result": f"Cannot parse RSS feed: {f.bozo_exception}"}

        title = f.feed.get("title", url)
        lines = [f"## RSS Feed: {title}\n"]
        for entry in f.entries[:min(limit, 50)]:
            pub = entry.get("published", entry.get("updated", ""))[:16]
            link = entry.get("link", "")
            lines.append(
                f"- **{entry.get('title', 'Untitled')}**\n"
                + (f"  {pub}\n" if pub else "")
                + (f"  {link}\n" if link else "")
                + (f"  {entry.get('summary', '')[:200]}\n" if entry.get("summary") else "")
            )
        return {"result": "\n".join(lines)}
    except ImportError:
        return {"result": "feedparser not available. Install: pip install feedparser"}
    except Exception as e:
        return {"result": f"RSS error: {e}"}


# ── Bilibili ─────────────────────────────────────────────────────


async def bilibili_search(query: str, limit: int = 5) -> dict:
    """Search Bilibili videos.

    Args:
        query: Search keyword.
        limit: Max results (default 5, max 20).
    """
    ttl = min(limit, 20)

    # Try bili-cli first
    if shutil.which("bili"):
        try:
            out, _ = await _run(["bili", "search", query, "--type", "video", "-n", str(ttl)], timeout=15)
            return {"result": f"## Bilibili Search: {query}\n\n{out[:10000]}"}
        except (RuntimeError, FileNotFoundError):
            pass

    # Fallback: Bilibili search API
    try:
        encoded = urllib.parse.quote(query)
        d = _fetch_json(
            f"https://api.bilibili.com/x/web-interface/search/all/v2?keyword={encoded}&page=1",
            timeout=10,
        )
        if d.get("code") != 0:
            return {"result": f"Bilibili search unavailable (API error: {d.get('code', 'unknown')})"}

        video_results = []
        for section in (d.get("data") or {}).get("result", []):
            if section.get("result_type") == "video":
                video_results = section.get("data", [])
                break

        if not video_results:
            return {"result": f"No Bilibili results for '{query}'."}

        lines = [f"## Bilibili Search: {query}\n"]
        for v in video_results[:ttl]:
            aid = v.get("aid", "")
            lines.append(
                f"- **{v.get('title', '').replace('<em class=\"keyword\">', '**').replace('</em>', '**')}**\n"
                f"  👤 {v.get('author', '')}  |  "
                f"▶️ {v.get('play', 0)} plays  |  "
                f"💬 {v.get('video_review', 0)} comments\n"
                f"  https://www.bilibili.com/video/av{aid}\n"
                f"  {v.get('description', '')[:200]}"
            )
        return {"result": "\n".join(lines)}
    except Exception as e:
        return {"result": f"Bilibili search error: {e}"}
