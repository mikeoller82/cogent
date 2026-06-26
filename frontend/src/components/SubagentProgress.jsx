import React, { useState } from "react";
import { ChevronDown, Loader2, Check, AlertTriangle, Search, Code, Eye, FileText, Merge } from "lucide-react";

const ROLE_CONFIG = {
  researcher: { icon: Search, color: "#60a5fa", label: "Researcher" },
  coder: { icon: Code, color: "#22c55e", label: "Coder" },
  validator: { icon: Eye, color: "#f59e0b", label: "Validator" },
  explorer: { icon: FileText, color: "#a78bfa", label: "Explorer" },
  synthesizer: { icon: Merge, color: "#ec4899", label: "Synthesizer" },
};

function AgentCard({ agent }) {
  const [expanded, setExpanded] = useState(false);
  const config = ROLE_CONFIG[agent.role] || ROLE_CONFIG.researcher;
  const Icon = config.icon;

  const statusColor = {
    starting: "#a8a092",
    running: config.color,
    warning: "#f59e0b",
    finalizing: "#22c55e",
    completed: "#22c55e",
    failed: "#ef4444",
    "budget exhausted": "#f59e0b",
  };

  const isRunning = !["completed", "failed"].includes(agent.status);
  const hasTools = agent.toolCalls && agent.toolCalls.length > 0;

  return (
    <div className="border border-[#f5ede0]/8 rounded-lg overflow-hidden bg-[#0d0a08]/30">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2.5 w-full px-3 py-2.5 text-left hover:bg-[#f5ede0]/5 transition-colors"
      >
        {isRunning ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin flex-shrink-0" style={{ color: config.color }} />
        ) : agent.status === "completed" ? (
          <Check className="w-3.5 h-3.5 flex-shrink-0 text-[#22c55e]" />
        ) : (
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 text-[#ef4444]" />
        )}
        <Icon className="w-3.5 h-3.5 flex-shrink-0" style={{ color: config.color }} />
        <span className="text-[12px] font-medium text-[#f5ede0]">{config.label}</span>
        {agent.task && (
          <span className="text-[11px] text-[#8a8278] truncate flex-1 min-w-0">
            {agent.task.slice(0, 80)}
          </span>
        )}
        {agent.elapsed > 0 && (
          <span className="text-[10px] font-mono text-[#6e6760] flex-shrink-0">
            {agent.elapsed.toFixed(1)}s
          </span>
        )}
        {hasTools && (
          <span className="text-[10px] font-mono text-[#6e6760] flex-shrink-0">
            {agent.toolCalls.length} tools
          </span>
        )}
        <ChevronDown
          className={`w-3 h-3 text-[#6e6760] transition-transform flex-shrink-0 ${expanded ? "rotate-180" : ""}`}
        />
      </button>

      {expanded && (
        <div className="border-t border-[#f5ede0]/5 px-3 py-2 space-y-1.5 max-h-[300px] overflow-y-auto">
          {/* Status messages */}
          {agent.statusMessages && agent.statusMessages.map((msg, i) => (
            <div key={`status-${i}`} className="flex items-start gap-2 text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" style={{ backgroundColor: statusColor[msg.text] || config.color }} />
              <span className="text-[#a8a092]">{msg.text}</span>
              {msg.ts && (
                <span className="text-[10px] text-[#6e6760] ml-auto flex-shrink-0">
                  {new Date(msg.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
              )}
            </div>
          ))}

          {/* Tool calls */}
          {agent.toolCalls && agent.toolCalls.map((tc, i) => (
            <div key={`tool-${i}`} className="flex items-start gap-2 text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#b5a8f5] mt-1.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-[#b5a8f5] font-mono">{tc.name}</span>
                {tc.args && (
                  <span className="text-[#6e6760] ml-1 truncate">
                    {tc.args.query || tc.args.url || tc.args.pattern || tc.args.command || ""}
                  </span>
                )}
              </div>
            </div>
          ))}

          {/* Tool results */}
          {agent.toolResults && agent.toolResults.map((tr, i) => (
            <div key={`result-${i}`} className="flex items-start gap-2 text-[11px]">
              <span className="flex-shrink-0 w-3 h-3 rounded-full bg-[#22c55e]/30 flex items-center justify-center mt-0.5">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
              </span>
              <span className="text-[#8a8278]">{tr.summary}</span>
            </div>
          ))}

          {/* Error */}
          {agent.error && (
            <div className="flex items-start gap-2 text-[11px] text-[#ef4444]">
              <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
              <span>{agent.error}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SubagentProgress({ agents, plan, result, isVisible }) {
  const [collapsed, setCollapsed] = useState(false);

  if (!isVisible || (!agents || agents.length === 0)) return null;

  const running = agents.filter((a) => !["completed", "failed"].includes(a.status));
  const done = agents.filter((a) => ["completed", "failed"].includes(a.status));

  return (
    <div className="my-3 border border-[#f5ede0]/10 rounded-xl overflow-hidden bg-[#0d0a08]/50">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2 w-full px-4 py-3 text-left hover:bg-[#f5ede0]/5 transition-colors"
      >
        {running.length > 0 ? (
          <Loader2 className="w-4 h-4 animate-spin text-[#b5a8f5]" />
        ) : (
          <Check className="w-4 h-4 text-[#22c55e]" />
        )}
        <span className="text-[12px] font-medium text-[#f5ede0]">
          Subagents
        </span>
        <span className="text-[11px] text-[#8a8278]">
          {running.length > 0
            ? `${running.length} running, ${done.length} done`
            : `${done.length} completed`}
        </span>
        {plan && plan.reasoning && (
          <span className="text-[10px] text-[#6e6760] truncate flex-1 min-w-0 ml-2 italic">
            {plan.reasoning.slice(0, 100)}
          </span>
        )}
        <ChevronDown
          className={`w-4 h-4 text-[#6e6760] transition-transform ${collapsed ? "" : "rotate-180"}`}
        />
      </button>

      {!collapsed && (
        <div className="border-t border-[#f5ede0]/5 px-4 py-3 space-y-2">
          {/* Plan reasoning */}
          {plan && plan.reasoning && (
            <div className="text-[11px] text-[#8a8278] italic mb-2">
              {plan.reasoning}
            </div>
          )}

          {/* Subtask list from plan */}
          {plan && plan.subtasks && plan.subtasks.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {plan.subtasks.map((st, i) => (
                <span
                  key={i}
                  className="text-[10px] font-mono px-2 py-0.5 rounded-md border border-[#f5ede0]/10 text-[#a8a092]"
                >
                  {st.role}: {st.prompt?.slice(0, 40)}
                </span>
              ))}
            </div>
          )}

          {/* Running agents first */}
          {running.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}

          {/* Completed agents */}
          {done.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}

          {/* Final result */}
          {result && (
            <div className="mt-2 pt-2 border-t border-[#f5ede0]/5">
              <div className="text-[11px] text-[#22c55e] font-medium">Complete</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
