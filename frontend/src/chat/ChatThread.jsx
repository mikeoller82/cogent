import React, { useState, useEffect, useRef } from "react";
import { listMessages, streamMessage, uploadFile, artifactUrl } from "./apiClient";
import {
  Send, Loader2, FileText, Globe, Brain, Search, Calendar, Sparkles,
  Paperclip, X, FileSpreadsheet, FileType, Download,
} from "lucide-react";
import { toast } from "sonner";

const toolIconMap = {
  web_search: Search,
  generate_pdf: FileText,
  generate_webapp: Globe,
  save_memory: Brain,
  recall_memory: Brain,
  schedule_task: Calendar,
};

const toolLabelMap = {
  web_search: "Searched the web",
  generate_pdf: "Generated a PDF",
  generate_webapp: "Deployed a web app",
  save_memory: "Saved to memory",
  recall_memory: "Recalled memory",
  schedule_task: "Scheduled a task",
};

const toolActiveLabel = {
  web_search: "searching the web",
  generate_pdf: "writing the pdf",
  generate_webapp: "building the web app",
  save_memory: "saving to memory",
  recall_memory: "recalling memory",
  schedule_task: "scheduling task",
};

const SUGGESTIONS = [
  { icon: Search, text: "Research the top 5 AI agent startups in 2026 and summarize them." },
  { icon: FileText, text: "Make me a 1-page PDF brief on prompt-engineering best practices." },
  { icon: Globe, text: "Build me a small web app: a pomodoro timer with dark theme." },
  { icon: Brain, text: "Remember: my company is Acme Inc., we sell B2B SaaS to dentists." },
];

const LOOP_PHASE_LABELS = {
  plan: "planning",
  execute: "executing",
  verify: "verifying",
  done: "done",
  escalate: "escalating",
  error: "error",
};

const VERDICT_COLORS = {
  PASS: { bg: "#16a34a", label: "pass" },
  PARTIAL: { bg: "#d97706", label: "partial" },
  FAIL: { bg: "#dc2626", label: "fail" },
};

function LoopIndicator({ phase, iteration, verdict }) {
  if (!phase) return null;
  const phaseLabel = LOOP_PHASE_LABELS[phase] || phase;
  const vc = verdict ? VERDICT_COLORS[verdict] : null;
  return (
    <div className="inline-flex items-center gap-2 flex-wrap">
      <span className={`loop-dot loop-dot--${phase}`} />
      <span className="text-[11px] font-mono tracking-wide text-[#a8a092] uppercase">{phaseLabel}</span>
      {iteration > 0 && (
        <span className="text-[10px] font-mono text-[#6e6760]">iter {iteration}</span>
      )}
      {vc && (
        <span
          className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm"
          style={{ color: vc.bg, backgroundColor: `${vc.bg}18` }}
        >
          {vc.label}
        </span>
      )}
    </div>
  );
}

function fileIconFor(name) {
  const ext = (name || "").toLowerCase().split(".").pop();
  if (ext === "pdf") return { Icon: FileText, color: "#ef4444" };
  if (["csv", "xlsx", "xls", "tsv"].includes(ext)) return { Icon: FileSpreadsheet, color: "#22c55e" };
  return { Icon: FileType, color: "#60a5fa" };
}

function Artifact({ a }) {
  const url = artifactUrl(a.url);
  if (a.type === "pdf") {
    const dlUrl = `${url}${url.includes("?") ? "&" : "?"}dl=1`;
    return (
      <div className="group flex items-center gap-3 px-4 py-3 rounded-lg bg-[#221b15] border border-[#f5ede0]/10 hover:border-[#b5a8f5]/40 transition-colors">
        <a href={url} target="_blank" rel="noreferrer" className="flex items-center gap-3 flex-1 min-w-0">
          <div className="w-10 h-10 rounded-md bg-[#ef4444]/15 flex items-center justify-center flex-shrink-0">
            <FileText className="w-5 h-5 text-[#ef4444]" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[13px] font-medium text-[#f5ede0] truncate">{a.title}.pdf</div>
            <div className="text-[11px] text-[#8a8278]">{a.size_kb} KB · click to preview</div>
          </div>
        </a>
        <a
          href={dlUrl}
          download={`cogent-${(a.title || "doc").replace(/[^a-z0-9-_]+/gi, "-")}.pdf`}
          className="px-2.5 py-1.5 rounded-md bg-[#f5ede0]/5 hover:bg-[#b5a8f5]/20 text-[11px] font-mono uppercase tracking-wider text-[#b5a8f5] inline-flex items-center gap-1.5 transition-colors flex-shrink-0"
          title="Download PDF"
        >
          <Download className="w-3 h-3" /> Save
        </a>
      </div>
    );
  }
  if (a.type === "webapp") {
    return (
      <a href={url} target="_blank" rel="noreferrer" className="group flex items-center gap-3 px-4 py-3 rounded-lg bg-[#221b15] border border-[#f5ede0]/10 hover:border-[#b5a8f5]/40 transition-colors">
        <div className="w-10 h-10 rounded-md bg-[#b5a8f5]/15 flex items-center justify-center flex-shrink-0">
          <Globe className="w-5 h-5 text-[#b5a8f5]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-medium text-[#f5ede0] truncate">{a.title}</div>
          <div className="text-[11px] text-[#8a8278]">Live web app · click to open</div>
        </div>
      </a>
    );
  }
  if (a.type === "schedule") {
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-[#221b15] border border-[#f5ede0]/10">
        <div className="w-10 h-10 rounded-md bg-[#22c55e]/15 flex items-center justify-center flex-shrink-0">
          <Calendar className="w-5 h-5 text-[#22c55e]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-medium text-[#f5ede0] truncate">{a.title}</div>
          <div className="text-[11px] text-[#8a8278]">Runs {a.cadence} at {a.time}</div>
        </div>
      </div>
    );
  }
  return null;
}

function ToolBadge({ use }) {
  const Icon = toolIconMap[use.tool] || Sparkles;
  const label = toolLabelMap[use.tool] || use.tool;
  return (
    <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#221b15] border border-[#f5ede0]/8 text-[11px] text-[#a8a092]">
      <Icon className="w-3 h-3 text-[#b5a8f5]" /> {label}
    </div>
  );
}

function AttachmentChip({ a, onRemove }) {
  const { Icon, color } = fileIconFor(a.filename);
  return (
    <div className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-[#221b15] border border-[#f5ede0]/10 text-[12px] text-[#d8d0c2]">
      <Icon className="w-3.5 h-3.5" style={{ color }} />
      <span className="truncate max-w-[180px]">{a.filename}</span>
      {onRemove && (
        <button onClick={() => onRemove(a.id)} className="text-[#6e6760] hover:text-[#ef4444]">
          <X className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}

function UserBubble({ m }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[78%] flex flex-col items-end gap-2">
        {m.attachments && m.attachments.length > 0 && (
          <div className="flex flex-wrap gap-1.5 justify-end">
            {m.attachments.map((a) => <AttachmentChip key={a.id} a={a} />)}
          </div>
        )}
        {m.content && (
          <div className="px-4 py-2.5 rounded-2xl bg-[#b5a8f5]/15 border border-[#b5a8f5]/20 text-[#f5ede0] text-[14.5px] leading-[1.55] whitespace-pre-wrap">
            {m.content}
          </div>
        )}
      </div>
    </div>
  );
}

function AssistantBubble({ m, liveStatus, liveTools, liveArtifacts, livePhase, liveIteration, liveVerdict, isStreaming }) {
  const tools = isStreaming ? liveTools : (m.tool_uses || []);
  const arts = isStreaming ? liveArtifacts : (m.artifacts || []);
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-md bg-[#1d1813] border border-[#b5a8f5]/30 flex items-center justify-center flex-shrink-0">
        <svg width="18" height="18" viewBox="0 0 32 32" fill="none">
          <path d="M4 16 Q 16 4, 28 16" stroke="#b5a8f5" strokeWidth="2.4" strokeLinecap="round" fill="none" />
          <path d="M4 16 Q 16 28, 28 16" stroke="#b5a8f5" strokeWidth="2.4" strokeLinecap="round" fill="none" />
          <circle cx="16" cy="16" r="2.4" fill="#b5a8f5" />
        </svg>
      </div>
      <div className="flex-1 min-w-0 space-y-2.5">
        <div className="flex items-baseline gap-2">
          <span className="text-[13px] font-medium text-[#f5ede0]">Cogent</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#b5a8f5]/15 text-[#b5a8f5] font-mono">APP</span>
          {m.created_at && (
            <span className="text-[11px] text-[#6e6760]">
              {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </div>
        {tools && tools.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {tools.map((t, i) => <ToolBadge key={i} use={t} />)}
          </div>
        )}
        {isStreaming && livePhase && (
          <LoopIndicator phase={livePhase} iteration={liveIteration} verdict={liveVerdict} />
        )}
        {isStreaming && liveStatus && (
          <div className="flex items-center gap-2 text-[13px] text-[#a8a092]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#b5a8f5] pulse-soft" />
            <span className="italic">{liveStatus}…</span>
          </div>
        )}
        {m.content && (
          <div className="text-[14.5px] leading-[1.6] text-[#d8d0c2] whitespace-pre-wrap">{m.content}</div>
        )}
        {arts && arts.length > 0 && (
          <div className="space-y-2 max-w-[420px]">
            {arts.map((a) => <Artifact key={a.id} a={a} />)}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatThread({ sessionId, refreshSessions }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [attachments, setAttachments] = useState([]); // staged uploads
  const [uploading, setUploading] = useState(false);

  // loop engineering live state
  const [livePhase, setLivePhase] = useState("");
  const [liveIteration, setLiveIteration] = useState(0);
  const [liveVerdict, setLiveVerdict] = useState("");
  const [liveVerdictNotes, setLiveVerdictNotes] = useState("");

  const scrollerRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      const el = scrollerRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    });
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLiveStatus("");
    setLiveTools([]);
    setLiveArtifacts([]);
    setAttachments([]);
    listMessages(sessionId)
      .then((data) => {
        if (!cancelled) {
          setMessages(data);
          setLoading(false);
          scrollToBottom();
        }
      })
      .catch(() => setLoading(false));
    return () => { cancelled = true; };
  }, [sessionId]);

  const handleFiles = async (files) => {
    if (!files || !files.length) return;
    setUploading(true);
    try {
      for (const f of files) {
        if (f.size > 20 * 1024 * 1024) {
          toast.error(`${f.name} is too large (max 20MB)`);
          continue;
        }
        const res = await uploadFile(f);
        setAttachments((prev) => [...prev, res]);
      }
    } catch (e) {
      toast.error("Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const removeAttachment = (id) =>
    setAttachments((prev) => prev.filter((a) => a.id !== id));

  const handleSend = async () => {
    const text = input.trim();
    if ((!text && attachments.length === 0) || sending) return;
    setInput("");
    const sentAttachments = attachments;
    setAttachments([]);
    setSending(true);
    setLiveStatus("thinking");
    setLiveTools([]);
    setLiveArtifacts([]);

    const optimistic = {
      id: `tmp-${Date.now()}`,
      role: "user",
      content: text,
      tool_uses: [],
      artifacts: [],
      attachments: sentAttachments,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    scrollToBottom();

    try {
      await streamMessage(sessionId, text, sentAttachments, (evt) => {
        if (evt.type === "status") {
          if (evt.content === "thinking") setLiveStatus("thinking");
          else setLiveStatus(evt.content);
        } else if (evt.type === "loop") {
          const d = evt.data || {};
          if (d.phase) setLivePhase(d.phase);
          if (d.iteration) setLiveIteration(d.iteration);
          if (d.verdict !== undefined) {
            setLiveVerdict(d.verdict);
            setLiveVerdictNotes(d.notes || "");
          }
          if (d.phase === "done" || d.phase === "error") {
            // keep final phase visible until stream ends
          }
        } else if (evt.type === "tool") {
          setLiveStatus(toolActiveLabel[evt.data.tool] || `using ${evt.data.tool}`);
          setLiveTools((prev) => [...prev, evt.data]);
        } else if (evt.type === "tool_result") {
          // no-op visually
        } else if (evt.type === "artifact") {
          setLiveArtifacts((prev) => [...prev, evt.data]);
        } else if (evt.type === "final") {
          setLiveStatus("");
        } else if (evt.type === "done") {
          // final assistant message will be appended via refresh below
        } else if (evt.type === "error") {
          toast.error(evt.content);
        }
        scrollToBottom();
      });
      const fresh = await listMessages(sessionId);
      setMessages(fresh);
      if (refreshSessions) refreshSessions();
    } catch (e) {
      toast.error("Cogent failed to respond. Try again.");
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
    } finally {
      setSending(false);
      setLiveStatus("");
      setLiveTools([]);
      setLiveArtifacts([]);
      setLivePhase("");
      setLiveIteration(0);
      setLiveVerdict("");
      setLiveVerdictNotes("");
      scrollToBottom();
    }
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files?.length) handleFiles(Array.from(e.dataTransfer.files));
  };

  return (
    <div className="flex-1 flex flex-col min-h-0" onDragOver={(e) => e.preventDefault()} onDrop={onDrop}>
      <div ref={scrollerRef} className="flex-1 overflow-y-auto">
        <div className="max-w-[820px] mx-auto px-6 py-8 space-y-6">
          {loading && (
            <div className="flex items-center gap-2 text-[#8a8278] text-[13px]">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> loading messages…
            </div>
          )}
          {!loading && messages.length === 0 && (
            <div className="py-10">
              <h2 className="text-[26px] tracking-[-0.02em] text-[#f5ede0]">Hi, I’m Cogent.</h2>
              <p className="mt-2 text-[14px] text-[#a8a092]">
                Ask me to research, write, build, or remember something. You can also attach files (PDF, CSV, Excel, text).
              </p>
              <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-2">
                {SUGGESTIONS.map((s, i) => (
                  <button key={i} onClick={() => setInput(s.text)} className="group text-left px-4 py-3 rounded-lg bg-[#1d1813] border border-[#f5ede0]/8 hover:border-[#b5a8f5]/30 transition-colors">
                    <s.icon className="w-4 h-4 text-[#b5a8f5] mb-2" />
                    <div className="text-[13px] text-[#d8d0c2] leading-[1.5]">{s.text}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) =>
            m.role === "user"
              ? <UserBubble key={m.id} m={m} />
              : <AssistantBubble key={m.id} m={m} />
          )}
          {sending && (
            <AssistantBubble
              m={{ content: "" }}
              liveStatus={liveStatus}
              liveTools={liveTools}
              liveArtifacts={liveArtifacts}
              livePhase={livePhase}
              liveIteration={liveIteration}
              liveVerdict={liveVerdict}
              isStreaming
          )}
        </div>
      </div>

      <div className="border-t border-[#f5ede0]/8 bg-[#16110c]">
        <div className="max-w-[820px] mx-auto px-6 py-4">
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {attachments.map((a) => (
                <AttachmentChip key={a.id} a={a} onRemove={removeAttachment} />
              ))}
            </div>
          )}
          <div className="flex items-end gap-2 bg-[#1d1813] border border-[#f5ede0]/10 rounded-xl p-2 focus-within:border-[#b5a8f5]/40 transition-colors">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="h-10 w-10 rounded-lg text-[#8a8278] hover:text-[#f5ede0] hover:bg-[#f5ede0]/5 transition-colors flex items-center justify-center disabled:opacity-50"
              aria-label="attach"
            >
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              hidden
              onChange={(e) => { handleFiles(Array.from(e.target.files || [])); e.target.value = ""; }}
              accept=".pdf,.csv,.tsv,.xlsx,.xls,.txt,.md,.json,.html,.log,.py,.js,.jsx,.ts,.tsx,.css,.yaml,.yml"
            />
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              placeholder="Message Cogent…"
              rows={1}
              className="flex-1 bg-transparent resize-none outline-none px-2 py-2 text-[14.5px] text-[#f5ede0] placeholder:text-[#6e6760] max-h-[200px]"
              style={{ minHeight: "40px" }}
            />
            <button
              onClick={handleSend}
              disabled={(!input.trim() && attachments.length === 0) || sending}
              className="h-10 w-10 rounded-lg bg-[#f5ede0] text-[#15110d] disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center hover:bg-white transition-colors"
            >
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
          <p className="mt-2 text-[11px] text-[#6e6760] text-center font-mono">
            cogent can search the web, build pdfs & web apps, remember facts, schedule tasks, read your files.
          </p>
        </div>
      </div>
    </div>
  );
}
