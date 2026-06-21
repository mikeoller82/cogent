import React, { useState, useEffect, useCallback } from "react";
import {
  listMCPRegistry, syncMCPRegistry, listInstalledMCP,
  installMCP, removeMCP, configMCP,
  getMCPLanguages, getMCPTopics, getMCPStatus,
  getMCPServerDetail,
} from "./apiClient";
import {
  Server, Search, RefreshCw, Download, Trash2, Settings,
  Loader2, CheckCircle2, AlertCircle, ExternalLink, Star,
  Globe, Terminal, X, ChevronLeft, ChevronRight,
  Wifi, WifiOff, Package, Layers, Code, BookOpen,
} from "lucide-react";
import { toast } from "sonner";
const PER_PAGE = 24;

export default function MCPPanel() {
  const [tab, setTab] = useState("browse");
  const [servers, setServers] = useState([]);
  const [installed, setInstalled] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [languages, setLanguages] = useState([]);
  const [selectedLang, setSelectedLang] = useState("");
  const [status, setStatus] = useState(null);

  // Install modal
  const [installTarget, setInstallTarget] = useState(null);
  const [installConfig, setInstallConfig] = useState({});
  const [installing, setInstalling] = useState(false);

  // Remove confirmation
  const [removing, setRemoving] = useState({});
  const [serverDetail, setServerDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [selectedMethod, setSelectedMethod] = useState(null);
  const [installLog, setInstallLog] = useState([]);

  const refreshInstalled = useCallback(async () => {
    try {
      const data = await listInstalledMCP();
      setInstalled(data);
    } catch (e) {
      console.error("Failed to list installed MCP servers:", e);
    }
  }, []);

  const loadRegistry = useCallback(async (q, pg, lang) => {
    try {
      setLoading(true);
      const data = await listMCPRegistry({
        query: q || undefined,
        page: pg || 1,
        per_page: PER_PAGE,
        language: lang || undefined,
      });
      setServers(data.servers || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 1);
      setPage(data.page || 1);
    } catch (e) {
      toast.error("Failed to load MCP registry");
      setServers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const s = await getMCPStatus();
      setStatus(s);
    } catch { setStatus(null); }
  }, []);

  useEffect(() => {
    loadRegistry(query, page, selectedLang);
    refreshInstalled();
    loadStatus();
  }, []);

  // ── Sync ───────────────────────────────────────────────────────
  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await syncMCPRegistry();
      toast.success(`Synced ${result.total} MCP servers`);
      await loadRegistry(query, 1, selectedLang);
      await loadStatus();
    } catch (e) {
      toast.error("Sync failed: " + (e?.response?.data?.detail || e.message));
    } finally {
      setSyncing(false);
    }
  };

  // ── Search ──────────────────────────────────────────────────────
  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    loadRegistry(query, 1, selectedLang);
  };

  // ── Install ─────────────────────────────────────────────────────
  const openInstall = async (server) => {
    setInstallTarget(server);
    setServerDetail(null);
    setSelectedMethod(null);
    setInstallLog([]);
    setDetailLoading(true);
    const sid = server.id || server.name;
    try {
      const detail = await getMCPServerDetail(sid);
      setServerDetail(detail);
      const methods = detail.install_methods || [];
      if (methods.length > 0) setSelectedMethod(methods[0]);
    } catch (e) {
      // Fallback to manual config
      setServerDetail({ server, readme: "", install_methods: [], repo_url: server.url || "" });
    } finally {
      setDetailLoading(false);
    }
  };

  const handleInstall = async (method) => {
    if (!installTarget) return;
    setInstalling(true);
    setInstallLog([]);
    const sid = installTarget.id || installTarget.name;
    try {
      const cfg = {
        method: method?.type || "",
        install_command: method?.install_command || "",
        mcp_command: method?.mcp_config?.command || "",
        transport: method?.mcp_config?.transport || "stdio",
        skip_install: false,
      };
      const result = await installMCP(sid, cfg);
      const status = result.status || "installed";
      if (status === "installed") {
        toast.success(`Installed: ${result.name}`);
      } else if (status === "install_failed") {
        toast.error(`Install failed for ${result.name} — check logs`);
      }
      setInstallLog(result.install_results || []);
      if (status === "installed") {
        setInstallTarget(null);
        setInstallLog([]);
      }
      await refreshInstalled();
      await loadStatus();
    } catch (e) {
      toast.error("Install failed: " + (e?.response?.data?.detail || e.message));
    } finally {
      setInstalling(false);
    }
  };

  // ── Remove ──────────────────────────────────────────────────────
  const handleRemove = async (name) => {
    setRemoving((p) => ({ ...p, [name]: true }));
    try {
      await removeMCP(name);
      toast.success(`Removed MCP server: ${name}`);
      await refreshInstalled();
      await loadStatus();
    } catch (e) {
      toast.error("Remove failed: " + (e?.response?.data?.detail || e.message));
    } finally {
      setRemoving((p) => ({ ...p, [name]: false }));
    }
  };

  // ── Render: status bar ──────────────────────────────────────────
  const StatusBar = () => {
    const dockerOk = status?.docker_available;
    const registryOk = status?.registry_synced;
    return (
      <div className="flex items-center gap-4 px-4 py-2 text-[11px] font-mono text-[#8a8278] border-b border-[#f5ede0]/8 bg-[#1a1612]">
        <span className="flex items-center gap-1.5">
          {dockerOk
            ? <><Wifi className="w-3 h-3 text-green-400" /> Docker available</>
            : <><WifiOff className="w-3 h-3 text-amber-400" /> Docker unavailable</>
          }
        </span>
        <span className="flex items-center gap-1.5">
          {registryOk
            ? <><CheckCircle2 className="w-3 h-3 text-green-400" /> Registry cached</>
            : <><AlertCircle className="w-3 h-3 text-amber-400" /> Registry not synced</>
          }
        </span>
        <span className="text-[#6e6760]">
          {status?.installed_count ?? "?"} installed
        </span>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded text-[10px]
            bg-[#f5ede0]/8 hover:bg-[#f5ede0]/12 transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-3 h-3 ${syncing ? "animate-spin" : ""}`} />
          {syncing ? "Syncing..." : "Sync"}
        </button>
      </div>
    );
  };

  // ── Render: server card ─────────────────────────────────────────
  const ServerCard = ({ server }) => {
    const name = server.display_name || server.name?.split("/")?.pop() || server.id;
    const installedServer = installed.find(
      (i) => i.source === server.id || i.name === name.toLowerCase()
    );
    const isInstalled = !!installedServer;

    return (
      <div className="group relative bg-[#1a1612] border border-[#f5ede0]/10 rounded-lg
        hover:border-[#f5ede0]/25 transition-all duration-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-start gap-3 p-4 pb-2">
          {server.owner_avatar_url && (
            <img
              src={server.owner_avatar_url}
              alt=""
              className="w-10 h-10 rounded-full flex-shrink-0 bg-[#f5ede0]/5"
            />
          )}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-[14px] font-medium text-[#f5ede0] truncate">{name}</h3>
              {isInstalled && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-green-900/40 text-green-400 border border-green-700/30">
                  installed
                </span>
              )}
            </div>
            <p className="text-[12px] text-[#8a8278] mt-0.5 line-clamp-2">
              {server.description}
            </p>
          </div>
        </div>

        {/* Meta */}
        <div className="flex items-center gap-3 px-4 py-2 text-[10px] font-mono text-[#6e6760]">
          {server.stargazer_count > 0 && (
            <span className="flex items-center gap-1">
              <Star className="w-3 h-3" /> {server.stargazer_count.toLocaleString()}
            </span>
          )}
          {server.primary_language && (
            <span className="flex items-center gap-1">
              <Code className="w-3 h-3" style={{ color: server.primary_language_color || undefined }} />
              {server.primary_language}
            </span>
          )}
          {server.license && (
            <span className="truncate">{server.license}</span>
          )}
        </div>

        {/* Topics */}
        {server.topics?.length > 0 && (
          <div className="flex flex-wrap gap-1 px-4 pb-3">
            {server.topics.slice(0, 4).map((t) => (
              <span key={t} className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-[#f5ede0]/5 text-[#8a8278]">
                {t}
              </span>
            ))}
            {server.topics.length > 4 && (
              <span className="text-[9px] text-[#6e6760]">+{server.topics.length - 4}</span>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 px-4 py-2.5 border-t border-[#f5ede0]/8 bg-[#16110c]">
          {server.url && (
            <a
              href={server.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[11px] text-[#6e6760] hover:text-[#f5ede0] transition-colors"
            >
              <ExternalLink className="w-3 h-3" /> View on GitHub
            </a>
          )}
          <div className="ml-auto">
            {isInstalled ? (
              <span className="text-[11px] text-green-500/70 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Installed
              </span>
            ) : (
              <button
                onClick={() => openInstall(server)}
                className="flex items-center gap-1 px-3 py-1 rounded text-[11px] font-medium
                  bg-[#7c5cf5] hover:bg-[#6a4ae3] text-white transition-colors"
              >
                <Download className="w-3 h-3" /> Install
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ── Render: install modal ───────────────────────────────────────
  const InstallModal = () => {
    if (!installTarget) return null;
    const name = installTarget.display_name || installTarget.name?.split("/")?.pop() || installTarget.id;
    const methods = serverDetail?.install_methods || [];
    const readme = serverDetail?.readme || "";
    const repoUrl = serverDetail?.detail_url || installTarget.url || "#";

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div className="bg-[#1a1612] border border-[#f5ede0]/12 rounded-xl shadow-2xl w-full max-w-2xl mx-4
          max-h-[85vh] flex flex-col overflow-hidden">

          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#f5ede0]/8 shrink-0">
            <h2 className="text-[16px] font-medium text-[#f5ede0]">Install MCP Server</h2>
            <button
              onClick={() => { setInstallTarget(null); setInstallLog([]); }}
              className="p-1 rounded hover:bg-[#f5ede0]/8 text-[#6e6760] hover:text-[#f5ede0] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex flex-1 overflow-hidden">
            {/* Left: server info + install methods */}
            <div className="w-1/2 border-r border-[#f5ede0]/8 overflow-y-auto p-5 space-y-4">
              <div>
                <p className="text-[14px] text-[#f5ede0] font-medium">{name}</p>
                <p className="text-[11px] text-[#8a8278] mt-1">{installTarget.description}</p>
                {installTarget.url && (
                  <a href={installTarget.url} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 mt-2 text-[11px] text-[#7c5cf5] hover:underline">
                    <ExternalLink className="w-3 h-3" /> View repo
                  </a>
                )}
              </div>

              {installTarget.primary_language && (
                <div>
                  <span className="text-[10px] font-mono text-[#6e6760] uppercase tracking-wider">Language</span>
                  <p className="text-[12px] text-[#f5ede0] mt-0.5">{installTarget.primary_language}</p>
                </div>
              )}

              {detailLoading ? (
                <div className="flex items-center gap-2 text-[12px] text-[#6e6760] py-4">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Detecting install method...
                </div>
              ) : methods.length > 0 ? (
                <div>
                  <span className="text-[10px] font-mono text-[#6e6760] uppercase tracking-wider">Install Method</span>
                  <div className="mt-2 space-y-1.5">
                    {methods.map((m) => (
                      <button
                        key={m.type}
                        onClick={() => setSelectedMethod(m)}
                        className={`w-full text-left px-3 py-2 rounded text-[12px] border transition-colors ${
                          selectedMethod?.type === m.type
                            ? "border-[#7c5cf5] bg-[#7c5cf5]/10 text-[#f5ede0]"
                            : "border-[#f5ede0]/10 hover:border-[#f5ede0]/20 text-[#8a8278] hover:text-[#f5ede0]"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Code className="w-3 h-3 shrink-0" />
                          <span className="font-medium">{m.label}</span>
                        </div>
                        {selectedMethod?.type === m.type && m.install_command && (
                          <code className="block mt-1.5 text-[11px] font-mono text-[#7c5cf5] break-all">
                            {m.install_command}
                          </code>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-[12px] text-[#6e6760] py-4 leading-relaxed">
                  No auto-install method available for this server.
                  <br />
                  <a href={repoUrl} target="_blank" rel="noopener noreferrer"
                     className="text-[#7c5cf5] hover:underline">
                    View the README on GitHub
                  </a> for manual setup instructions.
                </div>
              )}

              {installTarget.topics?.length > 0 && (
                <div>
                  <span className="text-[10px] font-mono text-[#6e6760] uppercase tracking-wider">Topics</span>
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {installTarget.topics.slice(0, 8).map((t) => (
                      <span key={t}
                        className="px-2 py-0.5 rounded text-[10px] bg-[#f5ede0]/6 text-[#6e6760] font-mono">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Right: install log / instructions */}
            <div className="w-1/2 overflow-y-auto p-5 space-y-4">
              {installLog.length > 0 ? (
                <div>
                  <span className="text-[10px] font-mono text-[#6e6760] uppercase tracking-wider">Install Log</span>
                  <div className="mt-2 space-y-2">
                    {installLog.map((log, i) => (
                      <div key={i} className={`px-3 py-2 rounded text-[11px] font-mono ${
                        log.exit_code === 0
                          ? "bg-green-500/8 text-green-400/80"
                          : "bg-red-500/8 text-red-400/80"
                      }`}>
                        <div className="flex items-center gap-1.5 mb-1">
                          {log.exit_code === 0
                            ? <CheckCircle2 className="w-3 h-3" />
                            : <AlertCircle className="w-3 h-3" />
                          }
                          <span className="font-medium">
                            {log.exit_code === 0 ? "Success" : `Failed (exit ${log.exit_code})`}
                          </span>
                        </div>
                        <code className="text-[10px] opacity-70 block">{log.command}</code>
                        {log.stderr && <pre className="mt-1 text-[10px] text-red-400/60 whitespace-pre-wrap">{log.stderr.slice(0, 300)}</pre>}
                      </div>
                    ))}
                  </div>
                </div>
              ) : readme ? (
                <div>
                  <span className="text-[10px] font-mono text-[#6e6760] uppercase tracking-wider">README</span>
                  <div className="mt-2 text-[11px] text-[#8a8278] leading-relaxed max-h-60 overflow-y-auto
                    whitespace-pre-wrap font-mono bg-[#0d0a08] rounded p-3 border border-[#f5ede0]/6">
                    {readme.slice(0, 3000)}
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-[12px] text-[#4a443e]">
                  <p>Select an install method on the left, then click Install</p>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-[#f5ede0]/8 shrink-0">
            <a
              href={repoUrl}
              target="_blank" rel="noopener noreferrer"
              className="text-[11px] text-[#6e6760] hover:text-[#7c5cf5] flex items-center gap-1 transition-colors"
            >
              <ExternalLink className="w-3 h-3" /> View install instructions on GitHub
            </a>
            <div className="flex items-center gap-3">
              <button
                onClick={() => { setInstallTarget(null); setInstallLog([]); }}
                className="px-4 py-1.5 rounded text-[12px] text-[#8a8278] hover:text-[#f5ede0] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleInstall(selectedMethod)}
                disabled={installing || detailLoading || !selectedMethod}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded text-[12px] font-medium
                  bg-[#7c5cf5] hover:bg-[#6a4ae3] text-white transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {installing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                {installing ? "Installing..." : "Install"}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ── Render: installed tab ───────────────────────────────────────
  const InstalledTab = () => (
    <div className="space-y-2">
      {installed.length === 0 ? (
        <div className="text-center py-16">
          <Package className="w-10 h-10 mx-auto mb-3 text-[#4a443e]" />
          <p className="text-[14px] text-[#6e6760]">No MCP servers installed</p>
          <p className="text-[12px] text-[#4a443e] mt-1">
            Browse the registry and click Install to add one
          </p>
        </div>
      ) : (
        installed.map((srv) => (
          <div
            key={srv.name}
            className="flex items-center justify-between px-4 py-3 rounded-lg bg-[#1a1612]
              border border-[#f5ede0]/10 hover:border-[#f5ede0]/20 transition-colors"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500/60 flex-shrink-0" />
                <h4 className="text-[13px] font-medium text-[#f5ede0]">{srv.name}</h4>
                <span className="text-[10px] font-mono text-[#6e6760] bg-[#f5ede0]/5 px-1.5 py-0.5 rounded">
                  {srv.transport || "stdio"}
                </span>
              </div>
              {srv.description && (
                <p className="text-[11px] text-[#8a8278] mt-0.5 truncate">{srv.description}</p>
              )}
              {srv.source && (
                <p className="text-[10px] text-[#4a443e] mt-0.5 font-mono">source: {srv.source}</p>
              )}
            </div>
            <button
              onClick={() => handleRemove(srv.name)}
              disabled={removing[srv.name]}
              className="flex items-center gap-1 px-3 py-1 rounded text-[11px] text-[#8a8278]
                hover:text-red-400 hover:bg-red-900/20 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed ml-3 flex-shrink-0"
            >
              {removing[srv.name]
                ? <Loader2 className="w-3 h-3 animate-spin" />
                : <Trash2 className="w-3 h-3" />
              }
              Remove
            </button>
          </div>
        ))
      )}
    </div>
  );

  // ── Render ──────────────────────────────────────────────────────
  return (
    <div className="flex-1 overflow-y-auto">
      <StatusBar />

      {/* Search bar */}
      <div className="px-6 pt-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="flex rounded-lg border border-[#f5ede0]/12 overflow-hidden">
            <button
              onClick={() => setTab("browse")}
              className={`px-4 py-2 text-[12px] font-medium transition-colors ${
                tab === "browse"
                  ? "bg-[#7c5cf5] text-white"
                  : "bg-[#0d0a08] text-[#8a8278] hover:text-[#f5ede0]"
              }`}
            >
              Browse Registry
            </button>
            <button
              onClick={() => setTab("installed")}
              className={`px-4 py-2 text-[12px] font-medium transition-colors ${
                tab === "installed"
                  ? "bg-[#7c5cf5] text-white"
                  : "bg-[#0d0a08] text-[#8a8278] hover:text-[#f5ede0]"
              }`}
            >
              Installed ({installed.length})
            </button>
          </div>
        </div>

        {tab === "browse" && (
          <form onSubmit={handleSearch} className="flex items-center gap-2 mb-5">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6e6760]" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search MCP servers by name, description, or topic..."
                className="w-full pl-9 pr-3 py-2 rounded-lg text-[13px] bg-[#0d0a08] border border-[#f5ede0]/12
                  text-[#f5ede0] placeholder-[#6e6760] focus:border-[#7c5cf5] outline-none transition-colors"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-[12px] font-medium bg-[#f5ede0]/8 text-[#8a8278]
                hover:bg-[#f5ede0]/12 hover:text-[#f5ede0] transition-colors"
            >
              Search
            </button>
          </form>
        )}
      </div>

      <div className="px-6 pb-10">
        {tab === "browse" ? (
          <>
            {/* Server grid */}
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-6 h-6 animate-spin text-[#7c5cf5]" />
              </div>
            ) : servers.length === 0 ? (
              <div className="text-center py-16">
                <Server className="w-10 h-10 mx-auto mb-3 text-[#4a443e]" />
                <p className="text-[14px] text-[#6e6760]">No servers found</p>
                {query && (
                  <p className="text-[12px] text-[#4a443e] mt-1">
                    Try a different search term or sync the registry
                  </p>
                )}
              </div>
            ) : (
              <>
                {/* Results info */}
                <p className="text-[11px] font-mono text-[#6e6760] mb-3">
                  {total} server{total !== 1 ? "s" : ""} found
                  {query && <> for &quot;{query}&quot;</>}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {servers.map((s) => (
                    <ServerCard key={s.id} server={s} />
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-3 mt-8">
                    <button
                      onClick={() => { setPage((p) => Math.max(1, p - 1)); loadRegistry(query, page - 1, selectedLang); }}
                      disabled={page <= 1}
                      className="flex items-center gap-1 px-3 py-1.5 rounded text-[12px]
                        bg-[#f5ede0]/8 hover:bg-[#f5ede0]/12 text-[#8a8278] hover:text-[#f5ede0]
                        disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" /> Previous
                    </button>
                    <span className="text-[12px] font-mono text-[#6e6760]">
                      {page} / {totalPages}
                    </span>
                    <button
                      onClick={() => { setPage((p) => Math.min(totalPages, p + 1)); loadRegistry(query, page + 1, selectedLang); }}
                      disabled={page >= totalPages}
                      className="flex items-center gap-1 px-3 py-1.5 rounded text-[12px]
                        bg-[#f5ede0]/8 hover:bg-[#f5ede0]/12 text-[#8a8278] hover:text-[#f5ede0]
                        disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      Next <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </>
            )}
          </>
        ) : (
          <InstalledTab />
        )}
      </div>

      {/* Install modal */}
      {installTarget && <InstallModal />}
    </div>
  );
}
