import React, { useState, useEffect, useRef } from "react";
import { listMessages, sendMessage, artifactUrl } from "./apiClient";
import { Send, Loader2, FileText, Globe, Brain, Search, Calendar, Sparkles, ArrowDown, Download, ExternalLink } from "lucide-react";
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

const SUGGESTIONS = [
  { icon: Search, text: "Research the top 5 AI agent startups in 2026 and summarize them." },
  { icon: FileText, text: "Make me a 1-page PDF brief on prompt-engineering best practices." },
  { icon: Globe, text: "Build me a small web app: a pomodoro timer with dark theme." },
  { icon: Brain, text: "Remember: my company is Acme Inc., we sell B2B SaaS to dentists." },
];

function Artifact({ a }) {
  const url = artifactUrl(a.url);
  if (a.type === "pdf") {
    return (
      <a
        href={url}
        target="_blank"
        rel="noreferrer"
        className="group flex items-center gap-3 px-4 py-3 rounded-lg bg-[#221b15] border border-[#f5ede0]/10 hover:border-[#b5a8f5]/40 transition-colors"
      >
        <div className="w-10 h-10 rounded-md bg-[#ef4444]/15 flex items-center justify-center flex-shrink-0">
          <FileText className="w-5 h-5 text-[#ef4444]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-medium text-[#f5ede0] truncate">{a.title}.pdf</div>
          <div className="text-[11px] text-[#8a8278]">{a.size_kb} KB • PDF</div>
        </div>
        <Download className="w-4 h-4 text-[#8a8278] group-hover:text-[#b5a8f5]" />
      </a>
    );
  }
  if (a.type === "webapp") {
    return (
      <a
        href={url}
        target="_blank"
        rel="noreferrer"
        className="group flex items-center gap-3 px-4 py-3 rounded-lg bg-[#221b15] border border-[#f5ede0]/10 hover:border-[#b5a8f5]/40 transition-colors"
      >
        <div className="w-10 h-10 rounded-md bg-[#b5a8f5]/15 flex items-center justify-center flex-shrink-0">
          <Globe className="w-5 h-5 text-[#b5a8f5]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-medium text-[#f5ede0] truncate">{a.title}</div>
          <div className="text-[11px] text-[#8a8278]">Live web app • click to open</div>
        </div>
        <ExternalLink className="w-4 h-4 text-[#8a8278] group-hover:text-[#b5a8f5]" />
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

function MessageBubble({ m }) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[78%] px-4 py-2.5 rounded-2xl bg-[#b5a8f5]/15 border border-[#b5a8f5]/20 text-[#f5ede0] text-[14.5px] leading-[1.55] whitespace-pre-wrap">
          {m.content}
        </div>
      </div>
    );
  }
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-md bg-[#1d1813] border border-[#b5a8f5]/30 flex items-center justify-center flex-shrink-0">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M12 2L22 12L12 22L2 12L12 2Z" stroke="#b5a8f5" strokeWidth="2" />
        </svg>
      </div>
      <div className="flex-1 min-w-0 space-y-2.5">
        <div className="flex items-baseline gap-2">
          <span className="text-[13px] font-medium text-[#f5ede0]">Viktor</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#b5a8f5]/15 text-[#b5a8f5] font-mono">APP</span>
          <span className="text-[11px] text-[#6e6760]">{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
        </div>
        {m.tool_uses && m.tool_uses.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {m.tool_uses.map((t, i) => <ToolBadge key={i} use={t} />)}
          </div>
        )}
        {m.content && (
          <div className="text-[14.5px] leading-[1.6] text-[#d8d0c2] whitespace-pre-wrap">{m.content}</div>
        )}
        {m.artifacts && m.artifacts.length > 0 && (
          <div className="space-y-2 max-w-[420px]">
            {m.artifacts.map((a) => <Artifact key={a.id} a={a} />)}
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
  const scrollerRef = useRef(null);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      const el = scrollerRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    });
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
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

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setSending(true);
    const optimistic = {
      id: `tmp-${Date.now()}`,
      role: "user",
      content: text,
      tool_uses: [],
      artifacts: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    scrollToBottom();
    try {
      const reply = await sendMessage(sessionId, text);
      const fresh = await listMessages(sessionId);
      setMessages(fresh);
      if (refreshSessions) refreshSessions();
      scrollToBottom();
    } catch (e) {
      toast.error("Viktor failed to respond. Try again.");
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
    } finally {
      setSending(false);
    }
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div ref={scrollerRef} className="flex-1 overflow-y-auto">
        <div className="max-w-[820px] mx-auto px-6 py-8 space-y-6">
          {loading && (
            <div className="flex items-center gap-2 text-[#8a8278] text-[13px]">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> loading messages…
            </div>
          )}
          {!loading && messages.length === 0 && (
            <div className="py-10">
              <h2 className="text-[26px] tracking-[-0.02em] text-[#f5ede0]">Hi, I’m Viktor.</h2>
              <p className="mt-2 text-[14px] text-[#a8a092]">
                Ask me to research, write, build, or remember something. Try one of these:
              </p>
              <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-2">
                {SUGGESTIONS.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(s.text)}
                    className="group text-left px-4 py-3 rounded-lg bg-[#1d1813] border border-[#f5ede0]/8 hover:border-[#b5a8f5]/30 transition-colors"
                  >
                    <s.icon className="w-4 h-4 text-[#b5a8f5] mb-2" />
                    <div className="text-[13px] text-[#d8d0c2] leading-[1.5]">{s.text}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => <MessageBubble key={m.id} m={m} />)}
          {sending && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-md bg-[#1d1813] border border-[#b5a8f5]/30 flex items-center justify-center flex-shrink-0">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L22 12L12 22L2 12L12 2Z" stroke="#b5a8f5" strokeWidth="2" />
                </svg>
              </div>
              <div className="flex items-center gap-2 text-[13px] text-[#8a8278]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#b5a8f5] pulse-soft" />
                Viktor is working…
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-[#f5ede0]/8 bg-[#16110c]">
        <div className="max-w-[820px] mx-auto px-6 py-4">
          <div className="flex items-end gap-2 bg-[#1d1813] border border-[#f5ede0]/10 rounded-xl p-2 focus-within:border-[#b5a8f5]/40 transition-colors">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              placeholder="Message Viktor…"
              rows={1}
              className="flex-1 bg-transparent resize-none outline-none px-2 py-2 text-[14.5px] text-[#f5ede0] placeholder:text-[#6e6760] max-h-[200px]"
              style={{ minHeight: "40px" }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="h-10 w-10 rounded-lg bg-[#f5ede0] text-[#15110d] disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center hover:bg-white transition-colors"
            >
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
          <p className="mt-2 text-[11px] text-[#6e6760] text-center font-mono">
            viktor can search the web, build pdfs & web apps, remember facts, schedule tasks.
          </p>
        </div>
      </div>
    </div>
  );
}
