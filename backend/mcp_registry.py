"""MCP Registry — GitHub MCP registry integration for Cogent.

Fetches and caches the GitHub MCP server catalog (https://github.com/mcp),
manages installation via manifest.yaml files in optional-mcps/, and
provides a clean API for the frontend.

Data flow:
  GitHub MCP Registry (scraped)  →  local cache (memory/cache/mcp_registry.json)
                                        ↓
  User clicks Install             →  manifest.yaml generated in optional-mcps/<server>/
                                        ↓
  Docker MCP server manages the   →  actual MCP server container
  installed servers
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger("cogent.mcp_registry")

# ── Paths ──────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent
OPTIONAL_MCPS_DIR = ROOT_DIR / "optional-mcps"
CACHE_DIR = ROOT_DIR / "memory" / "cache"

GITHUB_REGISTRY_URL = "https://github.com/mcp"

# ── Data models ────────────────────────────────────────────────────────


@dataclass
class MCPServer:
    """A server entry from the GitHub MCP registry."""
    id: str
    name: str
    display_name: str
    description: str
    url: str
    stargazer_count: int = 0
    owner_avatar_url: str = ""
    primary_language: str = ""
    primary_language_color: str = ""
    license: str = ""
    topics: List[str] = field(default_factory=list)
    opengraph_image_url: str = ""
    name_with_owner: str = ""


@dataclass
class InstalledMCPServer:
    """An MCP server installed in the local manifest."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    transport: str = "stdio"
    command: str = ""
    args: List[str] = field(default_factory=list)
    url: str = ""
    base_url: str = ""
    auth: Optional[Dict[str, Any]] = None
    tools: List[Dict[str, str]] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    installed_at: str = ""
    source: str = ""  # GitHub registry server id


# ── Curated Server Catalog ────────────────────────────────────────
# A vetted catalog of known-working install methods for popular MCP servers.
# Servers listed here always work — they were manually verified against the
# actual npm/pip/docker packages.  Servers NOT in the catalog fall through to
# manifest-based auto-detection (GitHub package.json discovery); if that also
# fails, no install methods are returned and the user is offered manual config.
#
# To add a server: verify its install method works, then add its entry here.
CATALOG_PATH = OPTIONAL_MCPS_DIR / "servers-catalog.json"
_catalog_cache: Optional[Dict[str, Any]] = None


def _load_catalog() -> Dict[str, Any]:
    """Load the curated server catalog, with a module-level cache."""
    global _catalog_cache
    if _catalog_cache is not None:
        return _catalog_cache
    if not CATALOG_PATH.exists():
        _catalog_cache = {}
        return _catalog_cache
    try:
        raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        _catalog_cache = raw.get("servers", {})
        return _catalog_cache
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load server catalog: %s", e)
        _catalog_cache = {}
        return _catalog_cache


# ── Install Method Detection ──────────────────────────────────────


def detect_install_methods(
    registry_entry: Dict[str, Any],
    manifest_info: Optional[Dict[str, Any]] = None,
    readme_commands: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """Detect install methods for an MCP server.

    Priority order:
      1. Curated catalog (``optional-mcps/servers-catalog.json``) —
         manually verified, guaranteed to work.
      2. GitHub manifest discovery (package.json from the repo) —
         high confidence when the API succeeds.
      3. README command extraction from the GitHub page.

    If none of the above yield a method, returns an empty list — the UI
    shows the user manual config instead of generating wrong guesses.
    """
    # ── Phase 1: Curated catalog (verified entries always win) ─────
    server_id = registry_entry.get("name", "") if registry_entry else ""
    catalog = _load_catalog()
    if server_id in catalog:
        entry = catalog[server_id]
        curated_methods = entry.get("methods", [])
        # Normalise the curated entries into the expected output format
        out = []
        for m in curated_methods:
            out.append({
                "type": m["type"],
                "label": m["label"],
                "install_command": m.get("install_command", ""),
                "mcp_config": m["mcp_config"],
                "skip_install": m.get("skip_install", False),
                "from_catalog": True,
            })
        if out:
            logger.info("Using curated install method for '%s'", server_id)
            return out

    # ── Phase 2: Manifest-based detection ──────────────────────────
    manifest_info = manifest_info or {}
    real_pkg_name = (manifest_info.get("package_name") or "").strip()
    has_real_name = bool(real_pkg_name)

    lang = (registry_entry.get("primary_language") or "").strip()
    raw_name = (registry_entry.get("name") or "").strip()
    topics = registry_entry.get("topics") or []

    if "/" in raw_name:
        org, repo = raw_name.split("/", 1)
    else:
        org, repo = "", raw_name

    repo_pkg = repo.lower().replace("_", "-").replace(".", "-")
    org_pkg = org.lower().replace("_", "-").replace(".", "-")

    methods: List[Dict[str, Any]] = []
    seen_types: set = set()

    def add_method(mtype, label, install_cmd, mcp_cmd, transport="stdio", **extra):
        # npx as install command hangs — the server starts and waits on stdio.
        # Always use npm install -g for installation; keep npx only for the
        # MCP client's run command.
        if mtype.startswith("npx") and install_cmd.startswith("npx "):
            pkg_for_npm = install_cmd.removeprefix("npx -y ").removeprefix("npx ").strip()
            pkg_for_npm = re.sub(r"@[^/]+$", "", pkg_for_npm)
            install_cmd = f"npm install -g {pkg_for_npm}"
        if mtype in seen_types:
            return
        seen_types.add(mtype)
        method: Dict[str, Any] = {
            "type": mtype,
            "label": label,
            "install_command": install_cmd,
            "mcp_config": {
                "transport": transport,
            },
        }
        if transport == "stdio":
            method["mcp_config"]["command"] = mcp_cmd
        elif transport == "http":
            method["mcp_config"]["url"] = mcp_cmd
        method.update(extra)
        methods.append(method)

    # ── README commands (highest priority — from actual docs) ──────
    readme_commands = readme_commands or []
    for rc in readme_commands:
        rtype = rc.get("type", "")
        if rtype in seen_types:
            continue
        seen_types.add(rtype)
        install_cmd = rc.get("install_command", "")
        pkg = rc.get("package", "")
        method_type = rc.get("method_type", "npx")

        # Derive MCP command from method type
        if method_type == "npx":
            mcp_cmd = install_cmd if install_cmd else f"npx -y {pkg}"
            # npx as install command hangs — use npm install -g instead
            if install_cmd.startswith("npx "):
                bare_pkg = install_cmd.removeprefix("npx -y ").removeprefix("npx ").strip()
                bare_pkg = re.sub(r"@[^/]+$", "", bare_pkg)
                install_cmd = f"npm install -g {bare_pkg}"
        elif method_type == "npm":
            mcp_cmd = pkg
        elif method_type == "pip":
            mcp_cmd = pkg
        elif method_type == "uvx":
            mcp_cmd = f"uvx {pkg}"
        elif method_type == "go_install":
            # Go module path last segment as binary name
            mcp_cmd = pkg.rstrip("@latest").rsplit("/", 1)[-1]
        elif method_type in ("cargo", "gem", "brew"):
            mcp_cmd = pkg
        else:
            mcp_cmd = pkg

        methods.append({
            "type": rtype,
            "label": f"{install_cmd} (from README)",
            "install_command": install_cmd,
            "mcp_config": {
                "transport": "stdio",
                "command": mcp_cmd,
            },
            "from_readme": True,
        })

    # ── Best: Use real package name from manifest ──────────────────
    if has_real_name:
        manifest_type = manifest_info.get("manifest_type", "")
        pkg = real_pkg_name
        scope_pkg = pkg

        if manifest_type == "npm":
            add_method("npx", f"npx {pkg}",
                        f"npx -y {pkg}", f"npx -y {pkg}")
            add_method("npm", f"npm install -g {pkg}",
                        f"npm install -g {pkg}", pkg)
        elif manifest_type == "pip":
            add_method("pip", f"pip install {pkg}",
                        f"pip install {pkg}", pkg)
            add_method("uvx", f"uvx {pkg}",
                        f"uvx {pkg}", f"uvx {pkg}")
        elif manifest_type == "cargo":
            add_method("cargo", f"cargo install {pkg}",
                        f"cargo install {pkg}", pkg)
        elif manifest_type == "go":
            # Root module — works when main.go is at the module root
            add_method("go_install", f"go install {pkg}@latest",
                        f"go install {pkg}@latest", repo_pkg)
            # Some Go repos put main.go in a subdirectory like cmd/<name>/
            add_method("go_install_cmd", f"go install {pkg}/cmd/{repo_pkg}@latest",
                        f"go install {pkg}/cmd/{repo_pkg}@latest", repo_pkg)
        elif manifest_type == "gem":
            add_method("gem", f"gem install {pkg}",
                        f"gem install {pkg}", pkg)

        # Also add source and docker
        git_url = f"https://github.com/{org}/{repo}" if org else registry_entry.get("url", "")
        if git_url:
            add_method("source", f"git clone + build ({org}/{repo})",
                        f"git clone {git_url} && cd {repo} && make install", repo_pkg,
                        requires_build=True)

        docker_image = f"ghcr.io/{org}/{repo_pkg}:latest"
        add_method("docker", f"docker pull {docker_image}",
                    f"docker pull {docker_image}",
                    f"docker run --rm -i {docker_image}",
                    requires_build=False)

        # Manifest data gives us accurate package names — return what we have.
        return methods

    # No manifest data available and this server isn't in the curated catalog.
    # Return whatever README commands were found (if any), or empty list.
    # The UI will show manual config instead of generating wrong guesses.
    return methods


async def fetch_server_detail(server_id: str) -> Optional[Dict[str, Any]]:
    """Fetch the full detail page for a server from the GitHub MCP registry.

    Returns server metadata + README content + detected install methods,
    or None if the server isn't found.
    """
    # First check cache for the entry
    registry = get_cached_registry()
    registry_entry = None
    if registry:
        for s in registry["servers"]:
            if s["id"] == server_id or s["name"] == server_id:
                registry_entry = s
                break

    if not registry_entry:
        return None

    # Fetch the detail page to get the README
    raw_name = registry_entry.get("name", server_id)
    detail_url = f"{GITHUB_REGISTRY_URL}/{raw_name}"

    readme_text = ""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                detail_url,
                headers={
                    "Accept": "text/html",
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Extract README from embedded JSON payload
                    import re
                    match = re.search(
                        r'"readme":"((?:[^"\\]|\\.)*)"',
                        html,
                    )
                    if match:
                        readme_text = match.group(1).encode().decode("unicode_escape")
                    # Also extract the repository URL
                    url_match = re.search(
                        r'"url":"(https://github\.com/[^"]+)"',
                        html,
                    )
    except Exception as e:
        logger.warning("Failed to fetch server detail for %s: %s", server_id, e)

    # Fetch actual package manifest from GitHub repo to get real package name
    repo_url = registry_entry.get("url", "")
    manifest_info: Dict[str, Any] = {}
    try:
        manifest_info = await _fetch_package_manifest(repo_url)
    except Exception as e:
        logger.debug("Failed to fetch manifest for %s: %s", server_id, e)

    # Extract install commands from README (highest priority signal)
    readme_commands = _extract_readme_commands(readme_text) if readme_text else []

    # Detect install methods (README commands → manifest → heuristics)
    install_methods = detect_install_methods(registry_entry, manifest_info, readme_commands)

    return {
        "server": registry_entry,
        "readme": readme_text[:10000] if readme_text else "",
        "install_methods": install_methods,
        "repo_url": repo_url,
        "detail_url": detail_url,
        "manifest_info": manifest_info,
    }

async def _fetch_package_manifest(repo_url: str) -> Dict[str, Any]:
    """Dynamically explore a GitHub repo to find actual package manifests.

    Uses the GitHub Contents API (1 call) to list the root directory,
    discovers manifest files at root and in common monorepo sub-patterns,
    then fetches identified manifests via raw.githubusercontent.com.

    Falls back to the legacy fixed-path scanner on rate-limit or API failure.
    """
    result: Dict[str, Any] = {}
    if not repo_url:
        return result

    import re
    match = re.match(r"https://github\.com/([^/]+/[^/]+?)(?:/|$)", repo_url)
    if not match:
        return result
    full_name = match.group(1)

    MANIFEST_NAMES = ["package.json", "pyproject.toml", "setup.py",
                       "Cargo.toml", "go.mod", "Gemfile"]

    # ── Step 1: List root directory via GitHub Contents API (1 call) ────
    root_files: set = set()
    root_dirs: set = set()
    api_succeeded = False
    try:
        api_url = f"https://api.github.com/repos/{full_name}/contents"
        headers = {"User-Agent": "Cogent/1.0", "Accept": "application/vnd.github.v3+json"}
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    if isinstance(items, list):
                        for item in items:
                            if item["type"] == "file":
                                root_files.add(item["name"])
                            elif item["type"] == "dir":
                                root_dirs.add(item["name"])
                        api_succeeded = True
    except Exception as e:
        logger.debug("Contents API failed for %s: %s", full_name, e)

    # If API rate-limited or down, fall back to legacy fixed-path scanning
    if not api_succeeded:
        return await _legacy_fetch_package_manifest(repo_url)

    # ── Step 2: Build targeted file-check list from actual repo structure ──
    def _dedup_append(lst, item):
        if item not in lst:
            lst.append(item)

    paths_to_check: list = []

    # Root-level manifests first (fastest match)
    for name in MANIFEST_NAMES:
        if name in root_files:
            _dedup_append(paths_to_check, (name, name))

    # Detect monorepo patterns
    has_workspace = "packages" in root_dirs or "lerna.json" in root_files
    has_mcp_subdir = "mcp" in root_dirs
    has_server_subdir = "server" in root_dirs

    if has_workspace:
        for subdir in ["packages/mcp", "packages/server", "mcp", "server"]:
            for name in MANIFEST_NAMES:
                _dedup_append(paths_to_check, (f"{subdir}/{name}", name))

    if has_mcp_subdir:
        for name in MANIFEST_NAMES:
            _dedup_append(paths_to_check, (f"mcp/{name}", name))

    if has_server_subdir:
        for name in MANIFEST_NAMES:
            _dedup_append(paths_to_check, (f"server/{name}", name))

    # No root manifests and no monorepo -> try common subpaths as safety net
    if not any(name in root_files for name in MANIFEST_NAMES) and not has_workspace:
        for subdir in ["mcp", "server", "src"]:
            for name in MANIFEST_NAMES:
                _dedup_append(paths_to_check, (f"{subdir}/{name}", name))

    # ── Step 3: Fetch manifests via raw content (0 rate limit) ───────────
    async with aiohttp.ClientSession() as session:
        for filepath, pkg_type in paths_to_check:
            for branch in ("main", "master"):
                raw_url = f"https://raw.githubusercontent.com/{full_name}/{branch}/{filepath}"
                try:
                    async with session.get(
                        raw_url,
                        headers={"User-Agent": "Cogent/1.0"},
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        if resp.status != 200:
                            continue
                        content = await resp.text()
                        result["manifest_type"] = pkg_type
                        result["manifest_file"] = filepath

                        parsed = _parse_manifest_content(filepath, content)
                        result.update(parsed)

                        if result.get("package_name"):
                            return result
                except Exception:
                    continue
                break  # tried a branch, move to next file

    return result


async def _legacy_fetch_package_manifest(repo_url: str) -> Dict[str, Any]:
    """Fallback: fetch package.json / pyproject.toml by checking fixed paths.

    Used when the GitHub Contents API is rate-limited or unavailable.
    """
    result: Dict[str, Any] = {}
    if not repo_url:
        return result

    import re
    match = re.match(r"https://github\.com/([^/]+/[^/]+?)(?:/|$)", repo_url)
    if not match:
        logger.debug("_legacy_fetch_package_manifest: could not extract owner/repo from %s", repo_url)
        return result
    full_name = match.group(1)

    files_to_check = [
        # Monorepo sub-paths (MCP server is often in a subpackage) - check first
        ("packages/mcp/package.json", "npm"),
        ("packages/server/package.json", "npm"),
        ("packages/context7-mcp/package.json", "npm"),
        ("mcp/package.json", "npm"),
        ("server/package.json", "npm"),
        # Common monorepo Python
        ("packages/markitdown/pyproject.toml", "pip"),
        ("packages/mcp/pyproject.toml", "pip"),
        ("packages/server/pyproject.toml", "pip"),
        ("packages/mcp/setup.py", "pip"),
        ("packages/server/setup.py", "pip"),
        # Root-level manifests
        ("package.json", "npm"),
        ("pyproject.toml", "pip"),
        ("setup.py", "pip"),
        ("Cargo.toml", "cargo"),
        ("go.mod", "go"),
        ("Gemfile", "gem"),
    ]

    async with aiohttp.ClientSession() as session:
        for filename, pkg_type in files_to_check:
            for branch in ("main", "master"):
                raw_url = f"https://raw.githubusercontent.com/{full_name}/{branch}/{filename}"
                try:
                    async with session.get(
                        raw_url,
                        headers={"User-Agent": "Cogent/1.0"},
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        if resp.status != 200:
                            continue
                        content = await resp.text()
                        result["manifest_type"] = pkg_type
                        result["manifest_file"] = filename

                        parsed = _parse_manifest_content(filename, content)
                        result.update(parsed)

                        if result.get("package_name"):
                            break
                except Exception as e:
                    logger.debug("legacy manifest fetch failed for %s: %s", raw_url, e)
                    continue
            if result.get("package_name"):
                break

    return result



def _parse_manifest_content(filename: str, content: str) -> Dict[str, Any]:
    """Parse a manifest file content and extract package name + binary name.

    Uses endswith() matching so monorepo sub-path filenames like
    ``packages/mcp/package.json`` are handled correctly.
    """
    result: Dict[str, Any] = {}

    if filename.endswith("package.json"):
        try:
            data = json.loads(content)
            result["package_name"] = data.get("name", "")
            result["bin"] = data.get("bin", {})
            if isinstance(result["bin"], str):
                result["bin_name"] = result["bin"]
            elif isinstance(result["bin"], dict):
                result["bin_name"] = next(iter(result["bin"].values()), "")
        except json.JSONDecodeError:
            pass

    elif filename.endswith("pyproject.toml"):
        name_match = re.search(r'^name\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if name_match:
            result["package_name"] = name_match.group(1)

    elif filename.endswith("setup.py"):
        name_match = re.search(r'''name\s*=\s*['"]([^'"]+)['"]''', content)
        if name_match:
            result["package_name"] = name_match.group(1)

    elif filename.endswith("Cargo.toml"):
        name_match = re.search(r'^name\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if name_match:
            result["package_name"] = name_match.group(1)

    elif filename.endswith("go.mod"):
        module_match = re.search(r'^module\s+(.+)$', content, re.MULTILINE)
        if module_match:
            result["package_name"] = module_match.group(1)

    return result


def _extract_readme_commands(readme_text: str) -> List[Dict[str, str]]:
    """Extract install commands from a README text.

    Parses the README for known install command patterns (pip, npm, npx,
    go install, cargo install, etc.) and returns them as structured entries
    that get converted to install methods.
    """
    if not readme_text:
        return []

    commands: List[Dict[str, str]] = []

    # Patterns to search for (ordered by reliability for MCP context)
    patterns = [
        (r'(?<!//)npx\s+(?:-y\s+)?(\S+)', "npx"),
        (r'(?<!//)npm\s+(?:install|add)\s+(?:-g\s+)?(\S+)', "npm"),
        (r'(?<!//)pip(?:3)?\s+install\s+(\S+)', "pip"),
        (r'(?<!//)uvx\s+(\S+)', "uvx"),
        (r'(?<!//)go\s+install\s+(\S+@?(?:latest)?)', "go_install"),
        (r'(?<!//)cargo\s+install\s+(\S+)', "cargo"),
        (r'(?<!//)gem\s+install\s+(\S+)', "gem"),
        (r'(?<!//)brew\s+install\s+(\S+)', "brew"),
    ]

    import re
    for pattern, method_type in patterns:
        for match in re.finditer(pattern, readme_text, re.IGNORECASE | re.MULTILINE):
            full_cmd = match.group(0).strip().lstrip("$ ")
            pkg = match.group(1).strip().rstrip("'\"`")
            commands.append({
                "type": f"readme_{method_type}",
                "install_command": full_cmd,
                "package": pkg,
                "method_type": method_type,
            })

    # Deduplicate by install_command (keep first occurrence)
    seen: set = set()
    unique: List[Dict[str, str]] = []
    for cmd in commands:
        key = cmd["install_command"]
        if key not in seen:
            seen.add(key)
            unique.append(cmd)

    return unique

SHELL_OPERATORS_RE = re.compile(r'[&|;<>$()`]')


def _needs_shell(command: str) -> bool:
    """Check if a command string needs shell interpretation.

    Commands with ``&&``, ``|``, ``>``, ``<``, ``;``, ``$()```, backticks, or
    environment-variable-style tokens require ``sh -c`` wrapping because
    ``create_subprocess_exec`` passes every token as a literal argument.
    """
    return bool(SHELL_OPERATORS_RE.search(command))


async def _run_command(
    cmd: List[str],
    timeout: int = 120,
    cwd: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a shell command and return exit code + output.

    Commands that contain shell operators (``&&``, ``|``, ``;``, etc.) are
    automatically routed through ``sh -c`` so that the operators work as
    expected.
    """
    import shlex

    try:
        raw = shlex.join(cmd) if isinstance(cmd, list) else str(cmd)
        if _needs_shell(raw):
            proc = await asyncio.create_subprocess_shell(
                raw,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout,
        )
        return {
            "exit_code": proc.returncode or 0,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        }
    except asyncio.TimeoutError:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command not found: {cmd[0]}",
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
        }

# ── GitHub Registry Scraper ────────────────────────────────────────────


async def fetch_registry_page(page: int = 1) -> Dict[str, Any]:
    """Fetch one page of the GitHub MCP registry.

    Returns parsed JSON with 'servers' and 'metadata' keys,
    or raises on failure.
    """
    url = f"{GITHUB_REGISTRY_URL}?page={page}"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"GitHub registry returned HTTP {resp.status}")
            html = await resp.text()

    # Extract embedded JSON payload
    import json
    match = re.search(
        r'<script[^>]*type="application/json"[^>]*data-target="react-app\.embeddedData"[^>]*>'
        r'({.*?})</script>',
        html,
        re.DOTALL,
    )
    if not match:
        raise RuntimeError("Could not find registry data in page HTML")

    raw = json.loads(match.group(1))
    route = raw.get("payload", {}).get("mcpRegistryRoute", {})
    servers_data = route.get("serversData", {})

    return {
        "servers": servers_data.get("servers", []),
        "metadata": servers_data.get("metadata", {"count": 0, "total": 0, "total_pages": 1}),
    }


async def sync_registry() -> Dict[str, Any]:
    """Fetch all pages of the GitHub MCP registry and cache locally.

    Returns the full server list with metadata.
    """
    logger.info("Syncing GitHub MCP registry...")

    # Fetch first page to get total pages
    first_page = await fetch_registry_page(1)
    metadata = first_page["metadata"]
    total_pages = metadata.get("total_pages", 1)
    all_servers: List[Dict[str, Any]] = list(first_page["servers"])

    # Fetch remaining pages in parallel
    if total_pages > 1:
        tasks = [fetch_registry_page(p) for p in range(2, total_pages + 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning("Registry page fetch failed: %s", result)
                continue
            all_servers.extend(result["servers"])

    # Build cached registry
    registry = {
        "servers": all_servers,
        "total": len(all_servers),
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata,
    }

    # Write cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / "mcp_registry.json"
    cache_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    logger.info("Synced %d MCP servers from GitHub registry", len(all_servers))
    return registry


def get_cached_registry() -> Optional[Dict[str, Any]]:
    """Return cached registry, or None if never synced."""
    cache_path = CACHE_DIR / "mcp_registry.json"
    if not cache_path.exists():
        return None
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read registry cache: %s", e)
        return None


def search_registry(
    query: str = "",
    page: int = 1,
    per_page: int = 30,
    language: str = "",
    topic: str = "",
) -> Dict[str, Any]:
    """Search the cached registry. Falls back to empty results if not synced."""
    registry = get_cached_registry()
    if not registry:
        return {"servers": [], "total": 0, "page": 1, "total_pages": 0}

    servers = registry["servers"]
    
    # Filter
    q = query.lower().strip()
    if q:
        servers = [
            s for s in servers
            if q in s.get("display_name", "").lower()
            or q in s.get("description", "").lower()
            or q in s.get("name", "").lower()
            or q in s.get("name_with_owner", "").lower()
            or any(q in t.lower() for t in s.get("topics", []) if t)
        ]
    if language:
        servers = [s for s in servers if (s.get("primary_language") or "").lower() == language.lower()]
    if topic:
        servers = [s for s in servers if topic.lower() in [t.lower() for t in s.get("topics", [])]]

    # Paginate
    total = len(servers)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = start + per_page
    page_servers = servers[start:end]

    return {
        "servers": page_servers,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "synced_at": registry.get("synced_at", ""),
    }


def get_languages() -> List[Dict[str, Any]]:
    """List available programming languages in the registry with counts."""
    registry = get_cached_registry()
    if not registry:
        return []
    
    counts: Dict[str, int] = {}
    for s in registry["servers"]:
        lang = s.get("primary_language", "") or "Unknown"
        counts[lang] = counts.get(lang, 0) + 1

    return sorted(
        [{"name": k, "count": v} for k, v in counts.items()],
        key=lambda x: -x["count"],
    )


# ── Installed Server Management ────────────────────────────────────────


def get_installed_servers() -> List[Dict[str, Any]]:
    """List all installed MCP servers from the manifests directory."""
    if not OPTIONAL_MCPS_DIR.exists():
        return []

    installed = []
    for item in sorted(OPTIONAL_MCPS_DIR.iterdir()):
        manifest_file = item / "manifest.yaml"
        if not manifest_file.exists():
            continue

        try:
            manifest = _parse_manifest(manifest_file)
            if manifest:
                installed.append(manifest)
        except Exception as e:
            logger.warning("Failed to parse manifest %s: %s", manifest_file, e)
            installed.append({
                "name": item.name,
                "error": str(e),
                "installed_at": "",
            })

    return installed


def _parse_manifest(path: Path) -> Optional[Dict[str, Any]]:
    """Parse a manifest.yaml file into a dict.

    Handles our known format:
      key: scalar
      key:
        - item
      tools:
        - name: foo
          description: bar
    """
    text = path.read_text(encoding="utf-8")
    manifest: Dict[str, Any] = {}
    current_list_key: Optional[str] = None
    current_list: List[str] = []
    tools_list: List[Dict[str, str]] = []
    in_tools = False
    current_tool: Dict[str, str] = {}

    def _flush_list():
        """Save pending list to manifest if any."""
        nonlocal current_list_key, current_list
        if current_list_key and current_list and current_list_key != "tools":
            manifest[current_list_key] = current_list
        current_list = []

    def _flush_tool():
        """Save pending tool entry if any."""
        nonlocal current_tool
        if current_tool:
            tools_list.append(current_tool)
            current_tool = {}

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        if indent == 0 and not stripped.startswith("-"):
            # Top-level key: value
            _flush_list()
            in_tools = False
            current_list_key = None
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()
                if value == "":
                    current_list_key = key
                else:
                    manifest[key] = value
            continue

        if indent == 2 and stripped.startswith("- ") and current_list_key:
            if current_list_key == "tools":
                _flush_tool()
                in_tools = True
                current_tool = {}
                item_text = stripped[2:].strip()
                # Parse "- name: foo" → name = "foo"
                if item_text.startswith("name:"):
                    current_tool["name"] = item_text[5:].strip()
                else:
                    current_tool["name"] = item_text
            else:
                current_list.append(stripped[2:].strip())
            continue

        if in_tools and stripped.startswith("description:"):
            _, _, val = stripped.partition(":")
            current_tool["description"] = val.strip()
            continue

        if in_tools and not stripped.startswith("-"):
            # New tool entry or end of tools section
            _flush_tool()
            in_tools = False

    # Flush remaining
    _flush_tool()
    _flush_list()
    if tools_list:
        manifest["tools"] = tools_list

    return manifest


def _manifest_to_yaml(manifest: Dict[str, Any]) -> str:
    """Generate YAML string from an InstalledMCPServer dict."""
    lines = []
    
    # Basic fields
    for key in ("name", "version", "description", "transport", "source", "installed_at"):
        if manifest.get(key):
            lines.append(f"{key}: {manifest[key]}")
    
    # Command (stdio transport)
    if manifest.get("command"):
        lines.append(f"command: {manifest['command']}")
    
    # Args
    if manifest.get("args"):
        lines.append("args:")
        for arg in manifest["args"]:
            lines.append(f"  - {arg}")
    
    # URL (http transport)
    if manifest.get("url"):
        lines.append(f"url: {manifest['url']}")
    if manifest.get("base_url"):
        lines.append(f"base_url: {manifest['base_url']}")
    
    # Auth
    if manifest.get("auth"):
        lines.append("auth:")
        for k, v in manifest["auth"].items():
            if isinstance(v, list):
                lines.append(f"  {k}:")
                for item in v:
                    lines.append(f"    - {item}")
            else:
                lines.append(f"  {k}: {v}")
    
    # Tools
    if manifest.get("tools"):
        lines.append("tools:")
        for tool in manifest["tools"]:
            if isinstance(tool, dict):
                lines.append(f'  - name: {tool.get("name", "")}')
                if tool.get("description"):
                    lines.append(f'    description: {tool["description"]}')
            else:
                lines.append(f"  - {tool}")
    
    # Config (extra)
    if manifest.get("config"):
        lines.append("# Runtime config (set via Cogent UI)")
        lines.append("config:")
        for k, v in manifest["config"].items():
            lines.append(f"  {k}: {v}")
    
    return "\n".join(lines) + "\n"


async def install_server(
    server_id: str,
    registry_entry: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Install an MCP server from the GitHub MCP registry.

    Auto-detects install method from repo metadata, runs the actual
    package install command (pip/npm/go/cargo), and generates a valid
    MCP manifest.yaml pointing to the installed binary.

    Config can override auto-detection:
      - ``method`` — force a specific install method type
      - ``install_command`` — custom install command
      - ``mcp_command`` — the command the MCP client should run
      - ``transport`` — "stdio" (default) or "http"
      - ``skip_install`` — only write manifest, don't run install
    """
    config = config or {}

    # Resolve registry entry
    if not registry_entry:
        registry = get_cached_registry()
        if registry:
            for s in registry["servers"]:
                if s["id"] == server_id or s["name"] == server_id:
                    registry_entry = s
                    break

    # Derive server name
    if registry_entry:
        raw_name = registry_entry.get("name", server_id)
        if "/" in raw_name:
            server_name = raw_name.split("/")[-1]
        else:
            server_name = raw_name.replace("io.github.", "").replace(".", "-")
    else:
        server_name = server_id.replace("/", "-").replace("io.github.", "").replace(".", "-")

    description = registry_entry.get("description", "") if registry_entry else ""
    repo_url = registry_entry.get("url", "") if registry_entry else ""

    # Auto-detect install method if no explicit config
    method_config = config.get("method") if config.get("method") else None
    install_results: List[Dict[str, Any]] = []

    mcp_command = config.get("mcp_command", "")
    transport = config.get("transport", "stdio")
    install_command = config.get("install_command", "")

    # Fetch package manifest from GitHub API for more accurate install commands
    manifest_info: Dict[str, Any] = {}
    if registry_entry and not install_command:
        repo_url = registry_entry.get("url", "")
        try:
            manifest_info = await _fetch_package_manifest(repo_url)
        except Exception:
            manifest_info = {}

    if not install_command and registry_entry and method_config != "manual":
        methods = detect_install_methods(registry_entry, manifest_info)
        if methods:
            chosen = next(
                (m for m in methods if m["type"] == method_config),
                methods[0],  # default to first/best
            )
            install_command = chosen.get("install_command", "")
            mcp_command = mcp_command or chosen["mcp_config"].get("command", "")
            transport = chosen["mcp_config"].get("transport", "stdio")

    # Guard: if detection yielded nothing and nothing was provided manually,
    # there is nothing to install.  The frontend will show a manual config form.
    if not install_command and not mcp_command:
        logger.warning("MCP server '%s': no install method available", server_id)
        return {
            "name": server_name,
            "install_ok": False,
            "status": "install_failed",
            "error": "No install method available for this server. Configure it manually.",
        }

    # Run the install command
    skip_install = config.get("skip_install", False)
    if install_command and not skip_install:
        # Safety net: convert any npx install command to npm install -g
        # to avoid the npx hang (npx starts the server and blocks on stdio).
        stripped = install_command.strip()
        if stripped.startswith("npx "):
            bare_pkg = stripped.removeprefix("npx -y ").removeprefix("npx ").strip()
            # Strip @version tags like @latest for a clean npm install
            bare_pkg = re.sub(r"@[^/]+$", "", bare_pkg)
            install_command = f"npm install -g {bare_pkg}"
            logger.info("Converted npx install command to npm install -g: %s", install_command)

        # Parse the install command into args
        import shlex
        cmd_parts = shlex.split(install_command)

        result = await _run_command(cmd_parts, timeout=config.get("timeout", 120))
        install_results.append({
            "command": install_command,
            "exit_code": result["exit_code"],
            "stdout": result["stdout"][:2000],
            "stderr": result["stderr"][:1000],
        })

        if result["exit_code"] != 0:
            # If first method failed, try the second-best method
            if registry_entry and method_config != "manual":
                methods = detect_install_methods(registry_entry, manifest_info)
                if len(methods) > 1:
                    fallback = methods[1]
                    fb_cmd = fallback.get("install_command", "")
                    if fb_cmd and fb_cmd != install_command:
                        fb_parts = shlex.split(fb_cmd)
                        fb_result = await _run_command(fb_parts, timeout=120)
                        install_results.append({
                            "command": fb_cmd,
                            "exit_code": fb_result["exit_code"],
                            "stdout": fb_result["stdout"][:2000],
                            "stderr": fb_result["stderr"][:1000],
                        })
                        if fb_result["exit_code"] == 0:
                            install_command = fb_cmd
                            mcp_command = fallback["mcp_config"].get("command", mcp_command)
                            transport = fallback["mcp_config"].get("transport", transport)

    # Determine if install succeeded
    install_ok = skip_install or not install_command  # manual config always ok
    if install_command and install_results:
        install_ok = install_ok or any(r["exit_code"] == 0 for r in install_results)

    if not install_ok:
        logger.warning(
            "MCP server '%s' install failed (all methods returned non-zero)",
            server_id,
        )
        return {
            "name": server_name,
            "install_ok": False,
            "status": "install_failed",
            "install_results": install_results,
            "error": "All install methods failed. Check install_results for details.",
        }

    # Build the server name from installed binary
    if mcp_command and install_ok:
        # If mcp_command is a scoped npm package (starts with @), it won't
        # be directly executable — wrap with npx -y so the MCP client can run it.
        if mcp_command.startswith("@"):
            mcp_command = f"npx -y {mcp_command}"
        binary_name = mcp_command.split()[-1] if " " in mcp_command else mcp_command
        binary_name = binary_name.replace("@", "").replace("/", "-")
    else:
        binary_name = server_name

    # Write the manifest.yaml
    server_dir = OPTIONAL_MCPS_DIR / binary_name
    server_dir.mkdir(parents=True, exist_ok=True)

    manifest: Dict[str, Any] = {
        "name": binary_name,
        "version": "1.0.0",
        "description": description,
        "transport": transport,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "source": server_id,
    }

    if transport == "stdio" and mcp_command:
        cmd_parts = mcp_command.split()
        manifest["command"] = cmd_parts[0]
        if len(cmd_parts) > 1:
            manifest["args"] = cmd_parts[1:]
    elif transport == "http":
        manifest["url"] = config.get("url", "")
        if config.get("base_url"):
            manifest["base_url"] = config["base_url"]
    elif transport == "stdio" and config.get("command"):
        manifest["command"] = config["command"]
        if config.get("args"):
            manifest["args"] = config["args"]

    # Auth
    if config.get("auth"):
        manifest["auth"] = config["auth"]

    # Tools placeholder
    manifest["tools"] = config.get("tools", [
        {"name": f"{binary_name}_help", "description": f"Tools provided by {binary_name}"},
    ])

    # Extra runtime config
    if config.get("config"):
        manifest["config"] = config["config"]

    manifest_path = server_dir / "manifest.yaml"
    manifest_path.write_text(_manifest_to_yaml(manifest), encoding="utf-8")

    meta_path = server_dir / "meta.json"
    meta_path.write_text(
        json.dumps({
            "name": binary_name,
            "source": server_id,
            "registry_entry": registry_entry,
            "install_command": install_command,
            "install_results": install_results,
            "installed_at": manifest["installed_at"],
        }, indent=2),
        encoding="utf-8",
    )

    status = "installed"
    logger.info(
        "MCP server '%s' %s (method: %s)",
        binary_name, status,
        install_command or "manual",
    )

    return {
        "name": binary_name,
        "manifest": manifest,
        "path": str(server_dir),
        "transport": transport,
        "installed_at": manifest["installed_at"],
        "install_results": install_results,
        "install_ok": install_ok,
        "status": status,
    }


async def remove_server(server_name: str) -> bool:
    """Remove an installed MCP server (manifest dir)."""
    server_dir = OPTIONAL_MCPS_DIR / server_name
    if not server_dir.exists():
        logger.warning("MCP server '%s' not installed", server_name)
        return False

    shutil.rmtree(server_dir)
    logger.info("Removed MCP server: %s", server_name)
    return True


def update_server_config(
    server_name: str,
    config: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Update an installed server's runtime config (not the manifest)."""
    server_dir = OPTIONAL_MCPS_DIR / server_name
    manifest_file = server_dir / "manifest.yaml"
    if not manifest_file.exists():
        return None

    # Read existing manifest
    manifest = _parse_manifest(manifest_file)
    if not manifest:
        return None

    # Update config
    if "config" not in manifest:
        manifest["config"] = {}
    manifest["config"].update(config)

    # Re-write manifest
    manifest_file.write_text(_manifest_to_yaml(manifest), encoding="utf-8")
    return manifest


# ── Languages & topics index ───────────────────────────────────────────


def list_available_languages() -> List[str]:
    """Get sorted list of programming languages from the registry."""
    registry = get_cached_registry()
    if not registry:
        return []
    
    langs: set = set()
    for s in registry["servers"]:
        lang = s.get("primary_language")
        if lang:
            langs.add(lang)
    return sorted(langs)


def list_available_topics() -> List[Dict[str, int]]:
    """Get topic frequency from the registry."""
    registry = get_cached_registry()
    if not registry:
        return []
    
    counts: Dict[str, int] = {}
    for s in registry["servers"]:
        for t in s.get("topics", []):
            counts[t] = counts.get(t, 0) + 1
    
    return sorted(
        [{"topic": k, "count": v} for k, v in counts.items()],
        key=lambda x: -x["count"],
    )
