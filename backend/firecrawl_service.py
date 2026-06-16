"""Firecrawl web search and content extraction service.

Wraps the Firecrawl Python SDK with async support for Cogent's tool system.
Supports both Firecrawl Cloud (api.firecrawl.dev) and self-hosted instances.
"""

import os
import asyncio
from typing import Optional

from firecrawl import FirecrawlApp

# Env var names
API_KEY_ENV = "FIRECRAWL_API_KEY"
BASE_URL_ENV = "FIRECRAWL_BASE_URL"  # optional, for self-hosted

# Defaults
CLOUD_URL = "https://api.firecrawl.dev"
DEFAULT_SEARCH_LIMIT = 5


def _get_api_key() -> str:
    key = os.environ.get(API_KEY_ENV)
    if key:
        return key
    # Fallback: derive from Firecrawl cloud free tier or let SDK raise
    raise ValueError(
        f"{API_KEY_ENV} not set. "
        "Get a key at https://www.firecrawl.dev/app/api-keys "
        "or set FIRECRAWL_BASE_URL for self-hosted (no key needed)."
    )


def _build_app() -> FirecrawlApp:
    """Build a FirecrawlApp instance configured from env vars."""
    api_key = _get_api_key()
    base_url = os.environ.get(BASE_URL_ENV)
    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["api_url"] = base_url.rstrip("/")
    return FirecrawlApp(**kwargs)


# ---------------------------------------------------------------------------
# Synchronous core (called via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _search(query: str, max_results: int = DEFAULT_SEARCH_LIMIT) -> list[dict]:
    """Run a Firecrawl search and return structured results."""
    app = _build_app()
    resp = app.search(
        query,
        limit=max_results,
        # Request full markdown content in results so the LLM gets actual page text
        scrape_options={"formats": ["markdown"]},
    )
    # resp is SearchData: { web: list[SearchResultWeb | Document], news: ..., images: ... }
    results: list[dict] = []

    # Collect from web results (primary)
    web = resp.web if hasattr(resp, "web") else getattr(resp, "web", None)
    if web:
        for item in web:
            url = item.url if hasattr(item, "url") else ""
            title = getattr(item, "title", None) or ""
            description = getattr(item, "description", None) or ""
            # If the result also carries markdown content (from scrape_options)
            content = ""
            if hasattr(item, "markdown") and item.markdown:
                content = item.markdown
            elif hasattr(item, "content") and item.content:
                content = item.content
            results.append({
                "url": url,
                "title": title,
                "description": description,
                "content": content,
            })

    # Also collect news results if web was empty
    if not results:
        news = resp.news if hasattr(resp, "news") else getattr(resp, "news", None)
        if news:
            for item in news:
                url = getattr(item, "url", None) or ""
                title = getattr(item, "title", None) or ""
                snippet = getattr(item, "snippet", None) or ""
                content = ""
                if hasattr(item, "markdown") and item.markdown:
                    content = item.markdown
                results.append({
                    "url": url,
                    "title": title,
                    "description": snippet,
                    "content": content,
                })

    return results


def _scrape(url: str) -> dict:
    """Scrape a single URL and return markdown + metadata."""
    app = _build_app()
    doc = app.scrape(url, formats=["markdown"])
    # doc is a Document
    metadata = doc.metadata if hasattr(doc, "metadata") else None
    md = doc.markdown if hasattr(doc, "markdown") else ""
    html_content = doc.html if hasattr(doc, "html") else ""

    title = ""
    description = ""
    if metadata:
        title = getattr(metadata, "title", None) or ""
        description = getattr(metadata, "description", None) or ""

    return {
        "url": url,
        "title": title,
        "description": description,
        "markdown": md or html_content or "",
        "content_type": getattr(metadata, "content_type", None) if metadata else None,
    }


# ---------------------------------------------------------------------------
# Async public API (used by tools.py)
# ---------------------------------------------------------------------------

async def web_search(query: str, max_results: int = DEFAULT_SEARCH_LIMIT) -> list[dict]:
    """Search the web via Firecrawl. Returns list of {url, title, description, content}."""
    return await asyncio.to_thread(_search, query, max_results)


async def web_scrape(url: str) -> dict:
    """Extract content from a URL via Firecrawl. Returns {url, title, description, markdown, content_type}."""
    return await asyncio.to_thread(_scrape, url)
