import React, { useState, useEffect, useRef, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { listMessages, streamMessage, uploadFile, artifactUrl } from "./apiClient";
import {
  Send, Loader2, FileText, Globe, Brain, Search, Calendar, Sparkles,
  Paperclip, X, FileSpreadsheet, FileType, Download, Check, Copy,
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
  activate_skill: "loading a skill",
  web_scrape: "reading a web page",
  import_skill: "importing skills",
  youtube_transcript: "fetching transcript",
  github_repo_info: "looking up repo",
  github_search: "searching GitHub",
  rss_read: "reading feed",
  v2ex_hot_topics: "fetching V2EX topics",
  bilibili_search: "searching Bilibili",
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

function CodeBlock({ language, value }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <div className="group relative my-3 rounded-xl overflow-hidden border border-[#f5ede0]/10 bg-[#0d0a08]">
      {language && (
        <div className="flex items-center justify-between px-4 py-1.5 bg-[#1a1510] border-b border-[#f5ede0]/8">
          <span className="text-[11px] font-mono text-[#8a8278] uppercase tracking-wider">{language}</span>
          <button
            onClick={handleCopy}
            className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1.5 px-2 py-1 rounded text-[11px] text-[#a8a092] hover:text-[#f5ede0] hover:bg-[#f5ede0]/8"
          >
            {copied ? <Check className="w-3 h-3 text-[#22c55e]" /> : <Copy className="w-3 h-3" />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      )}
      <pre className="overflow-x-auto p-4 text-[13px] leading-[1.6]">
        <code className="font-mono text-[#e2dcd0]">{value}</code>
      </pre>
    </div>
  );
}

function MarkdownRenderer({ content }) {
  const components = useMemo(() => ({
    h1: ({ children, ...props }) => (
      <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-[#f5ede0] mt-8 mb-3 pb-2 border-b border-[#f5ede0]/10" {...props}>
        {children}
      </h1>
    ),
    h2: ({ children, ...props }) => (
      <h2 className="text-[18px] font-semibold tracking-[-0.01em] text-[#f5ede0] mt-6 mb-2.5" {...props}>
        {children}
      </h2>
    ),
    h3: ({ children, ...props }) => (
      <h3 className="text-[16px] font-semibold text-[#d8d0c2] mt-5 mb-2" {...props}>
        {children}
      </h3>
    ),
    h4: ({ children, ...props }) => (
      <h4 className="text-[14.5px] font-semibold text-[#c8c0b2] mt-4 mb-1.5" {...props}>
        {children}
      </h4>
    ),
    p: ({ children, ...props }) => {
      if (typeof children === "string" && /^[:\-*•✅🔹🔸✨💡📌📍🎯🔥⭐💪🚀📊📈📉🔍🎉👏👍🙌💯]+/.test(children.trim().charAt(0))) {
        return <p className="text-[14.5px] leading-[1.65] text-[#d8d0c2] my-1.5" {...props}>{children}</p>;
      }
      return <p className="text-[14.5px] leading-[1.65] text-[#d8d0c2] my-1.5" {...props}>{children}</p>;
    },
    ul: ({ children, ...props }) => (
      <ul className="list-none my-2 space-y-1" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }) => (
      <ol className="list-decimal list-inside my-2 space-y-1 text-[14.5px] text-[#d8d0c2]" {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }) => {
      return (
        <li className="flex items-start gap-2.5 text-[14.5px] leading-[1.6] text-[#d8d0c2]" {...props}>
          <span className="mt-[7px] w-1.5 h-1.5 rounded-full bg-[#b5a8f5]/60 flex-shrink-0" />
          <span className="flex-1">{children}</span>
        </li>
      );
    },
    code: ({ inline, className, children, ...props }) => {
      const match = /language-(\w+)/.exec(className || "");
      if (!inline && match) {
        return <CodeBlock language={match[1]} value={String(children).replace(/\n$/, "")} />;
      }
      if (!inline) {
        return <CodeBlock language="" value={String(children).replace(/\n$/, "")} />;
      }
      return (
        <code className="px-1.5 py-0.5 rounded-md bg-[#1d1813] border border-[#f5ede0]/10 text-[13px] font-mono text-[#b5a8f5]" {...props}>
          {children}
        </code>
      );
    },
    blockquote: ({ children, ...props }) => (
      <blockquote className="relative my-4 pl-4 py-2 text-[14px] italic text-[#a8a092] border-l-[3px] border-[#b5a8f5]/50 bg-[#b5a8f5]/5 rounded-r-lg" {...props}>
        {children}
      </blockquote>
    ),
    table: ({ children, ...props }) => (
      <div className="my-3 overflow-x-auto rounded-xl border border-[#f5ede0]/10">
        <table className="w-full text-[13px] border-collapse" {...props}>
          {children}
        </table>
      </div>
    ),
    thead: ({ children, ...props }) => (
      <thead className="bg-[#1a1510]" {...props}>{children}</thead>
    ),
    th: ({ children, ...props }) => (
      <th className="px-4 py-2.5 text-left font-semibold text-[#f5ede0] border-b border-[#f5ede0]/10" {...props}>
        {children}
      </th>
    ),
    td: ({ children, ...props }) => (
      <td className="px-4 py-2.5 text-[#d8d0c2] border-b border-[#f5ede0]/8" {...props}>
        {children}
      </td>
    ),
    a: ({ children, href, ...props }) => (
      <a href={href} target="_blank" rel="noreferrer" className="text-[#b5a8f5] underline decoration-[#b5a8f5]/30 hover:decoration-[#b5a8f5] underline-offset-2 transition-all" {...props}>
        {children}
      </a>
    ),
    hr: () => <hr className="my-6 border-t border-[#f5ede0]/10" />,
    strong: ({ children, ...props }) => <strong className="font-semibold text-[#f5ede0]" {...props}>{children}</strong>,
    em: ({ children, ...props }) => <em className="italic text-[#e2dcd0]" {...props}>{children}</em>,
    img: ({ src, alt, ...props }) => (
      <img src={src} alt={alt || ""} className="max-w-full rounded-xl my-3 border border-[#f5ede0]/10" loading="lazy" {...props} />
    ),
    del: ({ children, ...props }) => <del className="line-through text-[#6e6760]" {...props}>{children}</del>,
  }), []);

  return (
    <div className="prose-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
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
          <div className="px-4 py-2.5 rounded-2xl bg-[#b5a8f5]/15 border border-[#b5a8f5]/20 text-[#f5ede0]">
            <MarkdownRenderer content={m.content} />
          </div>
        )}
      </div>
    </div>
  );
}


function ActivityLog({ entries }) {
  if (!entries || entries.length === 0) return null;
  return (
    <div className="activity-log space-y-1 py-2">
      {entries.map((entry) => (
        <div key={entry.id} className="flex items-center gap-2 text-[12px] leading-[1.5]">
          {entry.type === "phase" && (
            <span className={`w-1.5 h-1.5 rounded-full loop-dot--${entry.phase}`} />
          )}
          {entry.type === "tool" && (
            <span className="w-1.5 h-1.5 rounded-full bg-[#b5a8f5] pulse-soft flex-shrink-0" />
          )}
          {entry.type === "tool_result" && (
            <span className="flex-shrink-0 w-3 h-3 rounded-full bg-[#22c55e]/30 flex items-center justify-center">
              <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
            </span>
          )}
          {entry.type === "think" && (
            <span className="flex-shrink-0 text-[#8a8278]">&#9654;</span>
          )}
          <span className={entry.type === "tool_result" ? "text-[#8a8278]" : "text-[#a8a092]"}>
            {entry.text}
          </span>
        </div>
      ))}
    </div>
  );
}

function ThinkingLog({ entries, isOpen, onToggle }) {
  if (!entries || entries.length === 0) return null;
  const lastEntry = entries[entries.length - 1];
  const preview = lastEntry && lastEntry.type === "reasoning"
    ? lastEntry.text.slice(0, 120).replace(/\n/g, " ")
    : `${entries.length} log entries`;
  return (
    <div className="mt-3 border border-[#f5ede0]/10 rounded-lg overflow-hidden bg-[#0d0a08]/50">
      <button
        onClick={onToggle}
        className="flex items-center gap-2 w-full px-3 py-2 text-[11px] font-mono text-[#8a8278] hover:text-[#a8a092] hover:bg-[#f5ede0]/5 transition-colors"
      >
        <svg
          className={`w-3 h-3 transition-transform ${isOpen ? "rotate-90" : ""}`}
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <span className="uppercase tracking-wider">Thinking Log</span>
        <span className="text-[10px] text-[#6e6760]">({entries.length})</span>
        {!isOpen && preview && (
          <span className="ml-auto truncate max-w-[300px] text-[10px] text-[#6e6760] italic">
            {preview}
          </span>
        )}
      </button>
      {isOpen && (
        <div className="max-h-[400px] overflow-y-auto border-t border-[#f5ede0]/10">
          {entries.map((entry, i) => (
            <div key={i} className="px-3 py-2 border-b border-[#f5ede0]/5 last:border-b-0">
              <div className="flex items-start gap-2">
                <span className="text-[10px] font-mono text-[#6e6760] mt-0.5 flex-shrink-0 w-8 text-right">
                  {i + 1}
                </span>
                {entry.type === "reasoning" && entry.text.startsWith("[auto-continue") ? (
                  <span className="text-[11px] font-mono text-[#d97706]">{entry.text}</span>
                ) : (
                  <pre className="text-[11px] font-mono leading-[1.5] text-[#a8a092] whitespace-pre-wrap break-words flex-1 min-w-0">
                    {entry.text}
                  </pre>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AssistantBubble({ m, liveStatus, liveTools, liveArtifacts, livePhase, liveIteration, liveVerdict, isStreaming, activityLog, thinkingLog, showThinkingLog, onToggleThinkingLog }) {
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
        {isStreaming && activityLog && activityLog.length > 0 && (
          <div className="border-l-2 border-[#f5ede0]/10 pl-3 ml-1">
            <ActivityLog entries={activityLog} />
          </div>
        )}
        {isStreaming && thinkingLog && thinkingLog.length > 0 && (
          <ThinkingLog
            entries={thinkingLog}
            isOpen={showThinkingLog}
            onToggle={onToggleThinkingLog}
          />
        )}
        {m.content && (
          <div className="cogent-markdown">
            <MarkdownRenderer content={m.content} />
          </div>
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
  const [liveStatus, setLiveStatus] = useState("");
  const [liveTools, setLiveTools] = useState([]);
  const [liveArtifacts, setLiveArtifacts] = useState([]);
  // activity log — list of recent actions with detailed labels
  const [activityLog, setActivityLog] = useState([]);
  // thinking log — raw reasoning text from the LLM
  const [thinkingLog, setThinkingLog] = useState([]);
  const [showThinkingLog, setShowThinkingLog] = useState(false);
  const activityIdRef = useRef(0);
  const scrollerRef = useRef(null);
  const fileInputRef = useRef(null);
  
  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      const el = scrollerRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    });
  };

  const pushActivity = (entry) => {
    const id = ++activityIdRef.current;
    setActivityLog((prev) => [...prev.slice(-9), { ...entry, id }]);
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
    setThinkingLog([]);
    setShowThinkingLog(false);
    setActivityLog([]);
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
          const statusText = evt.content || "";
          setLiveStatus(statusText);
          if (statusText && statusText !== "thinking") {
            pushActivity({ type: "think", text: statusText });
          }
        } else if (evt.type === "loop") {
          const d = evt.data || {};
          if (d.phase) setLivePhase(d.phase);
          if (d.iteration) setLiveIteration(d.iteration);
          if (d.verdict !== undefined) {
            setLiveVerdict(d.verdict);
            setLiveVerdictNotes(d.notes || "");
            pushActivity({ type: "tool_result", text: `verdict: ${d.verdict}${d.notes ? " — " + d.notes.slice(0, 120) : ""}` });
          }
          if (d.phase && d.phase !== "done" && d.phase !== "error") {
            pushActivity({ type: "phase", phase: d.phase, text: `phase: ${d.phase}` });
          }
          if (d.phase === "done" || d.phase === "error") {
            // keep final phase visible until stream ends
          }
        } else if (evt.type === "tool") {
          const label = evt.data.label || toolActiveLabel[evt.data.tool] || `using ${evt.data.tool}`;
          setLiveStatus(label);
          setLiveTools((prev) => [...prev, evt.data]);
          pushActivity({ type: "tool", tool: evt.data.tool, text: label });
        } else if (evt.type === "tool_result") {
          const display = evt.data.display || "completed";
          if (display) {
            pushActivity({ type: "tool_result", text: display });
          }
        } else if (evt.type === "reasoning") {
          const text = evt.content || "";
          setThinkingLog((prev) => [...prev, { type: "reasoning", text, ts: Date.now() }]);
          // Auto-show thinking log on first reasoning event or auto-continue marker
          if (text.includes("[auto-continue") || text.includes("[plan detected")) {
            setShowThinkingLog(true);
          }
        } else if (evt.type === "artifact") {
          setLiveArtifacts((prev) => [...prev, evt.data]);
        } else if (evt.type === "final") {
          setLiveStatus("");
          pushActivity({ type: "tool_result", text: "generating final response" });
        } else if (evt.type === "done") {
          // final assistant message will be appended via refresh below
        } else if (evt.type === "error") {
          toast.error(evt.content);
          pushActivity({ type: "tool_result", text: `error: ${evt.content}` });
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
              activityLog={activityLog}
              thinkingLog={thinkingLog}
              showThinkingLog={showThinkingLog}
              onToggleThinkingLog={() => setShowThinkingLog((p) => !p)}
            />
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
