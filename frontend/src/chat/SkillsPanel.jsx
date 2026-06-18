import React, { useState, useEffect, useCallback } from "react";
import {
  listSkills, importSkills, forgeSkill, deleteSkill,
} from "./apiClient";
import {
  Wrench, Plus, Trash2, Loader2, CheckCircle2, AlertCircle,
  ExternalLink, Github, Hammer, Search, RefreshCw, FileText,
} from "lucide-react";
import { toast } from "sonner";

export default function SkillsPanel() {
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyLabel, setBusyLabel] = useState("");
  const [result, setResult] = useState(null); // {mode, data} from last operation
  const [deleting, setDeleting] = useState({});

  const refresh = useCallback(async () => {
    try {
      const data = await listSkills();
      setSkills(data);
    } catch {
      // silent — panel may load before backend is reachable
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // ── Import ──────────────────────────────────────────────────────────
  const handleImport = async () => {
    const repo = url.trim();
    if (!repo) return;
    setBusy(true);
    setBusyLabel("Cloning repo and scanning for skills…");
    setResult(null);
    try {
      const data = await importSkills(repo, false);
      setResult({ mode: "import", data });
      toast.success(
        data.skills
          ? `Imported ${data.skills.filter((s) => s.action === "created").length} skill(s)`
          : "Import complete"
      );
      refresh();
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || "Import failed";
      toast.error(msg);
      setResult({ mode: "error", data: msg });
    } finally {
      setBusy(false);
      setBusyLabel("");
    }
  };

  // ── Forge ───────────────────────────────────────────────────────────
  const handleForge = async () => {
    const repo = url.trim();
    if (!repo) return;
    setBusy(true);
    setBusyLabel("Cloning repo and analysing with LLM…");
    setResult(null);
    try {
      const data = await forgeSkill(repo, false);
      setResult({ mode: "forge", data });
      if (data.forge_status === "created" || data.forge_status === "updated") {
        toast.success(`Forged skill: ${data.name}`);
      }
      refresh();
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || "Forge failed";
      toast.error(msg);
      setResult({ mode: "error", data: msg });
    } finally {
      setBusy(false);
      setBusyLabel("");
    }
  };

  // ── Delete ──────────────────────────────────────────────────────────
  const handleDelete = async (name) => {
    setDeleting((p) => ({ ...p, [name]: true }));
    try {
      await deleteSkill(name);
      toast.success(`Deleted "${name}"`);
      refresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Delete failed");
    } finally {
      setDeleting((p) => ({ ...p, [name]: false }));
    }
  };

  // ── Key handler ─────────────────────────────────────────────────────
  const onKeyDown = (e) => {
    if (e.key === "Enter" && !busy) handleImport();
  };

  // ── Results card ────────────────────────────────────────────────────
  const ResultCard = () => {
    if (!result) return null;
    if (result.mode === "error") {
      return (
        <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/20 text-[13px] text-[#f5ede0]">
          <AlertCircle className="w-4 h-4 text-[#ef4444] mt-0.5 flex-shrink-0" />
          <span>{result.data}</span>
        </div>
      );
    }
    const { data } = result;
    return (
      <div className="rounded-xl glass-card border border-[#f5ede0]/8 overflow-hidden">        {/* result card */}
        {/* header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-[#f5ede0]/8">
          {result.mode === "import" ? (
            <Github className="w-4 h-4 text-[#b5a8f5]" />
          ) : (
            <Hammer className="w-4 h-4 text-[#b5a8f5]" />
          )}
          <span className="text-[12px] font-mono uppercase tracking-wider text-[#a8a092]">
            {result.mode === "import" ? "Import" : "Forge"} result
          </span>
          <span className="text-[11px] text-[#6e6760] ml-1">{data.repo}</span>
          <a
            href={`https://github.com/${data.repo}`}
            target="_blank"
            rel="noreferrer"
            className="ml-auto text-[#6e6760] hover:text-[#b5a8f5] transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* import results */}
        {result.mode === "import" && data.skills && data.skills.length > 0 && (
          <div className="divide-y divide-[#f5ede0]/5">
            {data.skills.map((s, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5">
                {s.action === "created" ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#22c55e] flex-shrink-0" />
                ) : s.action === "skipped" ? (
                  <div className="w-3.5 h-3.5 rounded-full border border-[#6e6760] flex items-center justify-center flex-shrink-0">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#6e6760]" />
                  </div>
                ) : (
                  <AlertCircle className="w-3.5 h-3.5 text-[#ef4444] flex-shrink-0" />
                )}
                <code className="text-[12px] font-mono text-[#f5ede0]">{s.name}</code>
                <span className={`text-[11px] font-mono uppercase tracking-wider ${
                  s.action === "created" ? "text-[#22c55e]" :
                  s.action === "skipped" ? "text-[#6e6760]" : "text-[#ef4444]"
                }`}>
                  {s.action}
                </span>
                {s.error && <span className="text-[11px] text-[#ef4444] ml-auto">{s.error}</span>}
              </div>
            ))}
          </div>
        )}

        {/* forge result */}
        {result.mode === "forge" && (
          <div className="px-4 py-3">
            {data.forge_status === "failed" ? (
              <div className="flex items-center gap-2 text-[13px] text-[#ef4444]">
                <AlertCircle className="w-4 h-4" /> {data.error || "Forge failed"}
              </div>
            ) : data.forge_status === "skipped" ? (
              <div className="text-[13px] text-[#6e6760]">{data.error}</div>
            ) : (
              <div className="flex items-center gap-2 text-[13px] text-[#f5ede0]">
                <CheckCircle2 className="w-4 h-4 text-[#22c55e]" />
                <code className="font-mono text-[#b5a8f5]">{data.name}</code>
                <span className="text-[#a8a092]">— {data.description}</span>
              </div>
            )}
          </div>
        )}

        {/* errors */}
        {data.errors && data.errors.length > 0 && (
          <div className="px-4 py-2 bg-[#ef4444]/5 border-t border-[#ef4444]/10">
            {data.errors.map((e, i) => (
              <div key={i} className="text-[11px] text-[#ef4444] font-mono">{e}</div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[820px] mx-auto px-6 py-10">
        {/* Header */}
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-md bg-[#1d1813] border border-[#b5a8f5]/30 flex items-center justify-center glow-accent">
            <Wrench className="w-4 h-4 text-[#b5a8f5]" />
          </div>
          <h1 className="text-[26px] tracking-[-0.02em] text-[#f5ede0]">
            Skill Forge
          </h1>
        </div>
        <p className="text-[14px] text-[#a8a092] mb-8">
          Import or forge agent skills from any GitHub repository. Skills teach Cogent how to work
          with libraries, tools, and codebases — extracted directly from their source.
        </p>

        {/* URL input + action buttons */}
        <div className="glass-card rounded-xl p-4 mb-6">          {/* URL input card */}
          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_auto] gap-2">
            <div className="relative">
              <Github className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6e6760]" />
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="GitHub URL or owner/repo (e.g. armelhbobdad/oh-my-skills)"
                disabled={busy}
                className="w-full bg-[#15110d] border border-[#f5ede0]/10 rounded-md pl-9 pr-3 py-2 text-[13px] text-[#f5ede0] placeholder:text-[#6e6760] outline-none focus:border-[#b5a8f5]/40 disabled:opacity-50"
              />
            </div>
            <button
              onClick={handleImport}
              disabled={busy || !url.trim()}
              className="px-4 py-2 rounded-md bg-[#f5ede0] text-[#15110d] text-[12px] font-mono uppercase tracking-wider hover:bg-white inline-flex items-center gap-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed btn-cinema"
            >
              <Search className="w-3.5 h-3.5" /> Import
            </button>
            <button
              onClick={handleForge}
              disabled={busy || !url.trim()}
              className="px-4 py-2 rounded-md border border-[#b5a8f5]/40 text-[#b5a8f5] text-[12px] font-mono uppercase tracking-wider hover:bg-[#b5a8f5]/10 inline-flex items-center gap-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed btn-cinema"
            >
              <Hammer className="w-3.5 h-3.5" /> Forge
            </button>
          </div>
          <div className="flex gap-3 mt-2 text-[11px] text-[#6e6760]">
            <span><strong className="text-[#a8a092]">Import</strong> — clones repo, finds SKILL.md files, installs them</span>
            <span><strong className="text-[#a8a092]">Forge</strong> — uses LLM to generate a skill from code analysis</span>
          </div>
        </div>

        {/* Busy indicator */}
        {busy && (
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-[#b5a8f5]/10 border border-[#b5a8f5]/20 mb-6">
            <Loader2 className="w-4 h-4 animate-spin text-[#b5a8f5]" />
            <span className="text-[13px] text-[#d8d0c2]">{busyLabel}</span>
          </div>
        )}

        {/* Last result */}
        <ResultCard />

        {/* Separator */}
        {result && skills.length > 0 && (
          <div className="my-6 border-t border-[#f5ede0]/8" />
        )}

        {/* Installed skills list */}
        <div className="flex items-center gap-2 mt-8 mb-4">
          <FileText className="w-4 h-4 text-[#b5a8f5]" />
          <h2 className="text-[16px] font-medium text-[#f5ede0]">
            Installed skills
          </h2>
          <span className="text-[12px] text-[#6e6760] font-mono">
            ({loading ? "…" : skills.length})
          </span>
          {!loading && (
            <button
              onClick={refresh}
              className="ml-auto p-1 text-[#6e6760] hover:text-[#b5a8f5] transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="space-y-2">
          {loading && (
            <div className="flex items-center gap-2 text-[13px] text-[#6e6760] py-6">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading…
            </div>
          )}
          {!loading && skills.length === 0 && (
            <div className="text-[13px] text-[#6e6760] py-6 text-center">
              No skills installed yet. Paste a GitHub URL above and click Import.
            </div>
          )}
          {skills.map((s) => (
            <div
              key={s.name}
              className="group flex items-start gap-3 px-4 py-3 rounded-lg glass-card border border-[#f5ede0]/8 hover:border-[#f5ede0]/15 transition-colors"
            >
              <div className="w-7 h-7 rounded-md bg-[#b5a8f5]/10 border border-[#b5a8f5]/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <FileText className="w-3.5 h-3.5 text-[#b5a8f5]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <code className="text-[13px] font-mono text-[#f5ede0]">{s.name}</code>
                  {s.resource_count > 0 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#f5ede0]/8 text-[#a8a092] font-mono">
                      +{s.resource_count}
                    </span>
                  )}
                </div>
                <div className="text-[12px] text-[#a8a092] mt-0.5 line-clamp-2">
                  {s.description}
                </div>
                <div className="flex items-center gap-3 mt-1.5">
                  {s.source_repo && (
                    <a
                      href={`https://github.com/${s.source_repo}`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-[10px] font-mono text-[#6e6760] hover:text-[#b5a8f5] transition-colors"
                    >
                      <Github className="w-3 h-3" /> {s.source_repo}
                    </a>
                  )}
                  {s.imported_at && (
                    <span className="text-[10px] text-[#6e6760] font-mono">
                      {new Date(s.imported_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleDelete(s.name)}
                disabled={deleting[s.name]}
                className="opacity-0 group-hover:opacity-100 p-1.5 text-[#6e6760] hover:text-[#ef4444] transition-all disabled:opacity-30"
                title={`Delete ${s.name}`}
              >
                {deleting[s.name] ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
