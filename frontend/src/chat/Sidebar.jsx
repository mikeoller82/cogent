import React from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { Plus, MessageSquare, Brain, Calendar, Wrench, Trash2, Home, Server, Settings } from "lucide-react";

export default function Sidebar({ sessions, loading, onNew, onDelete }) {
  const location = useLocation();
  const params = useParams();
  const activeId = params.id;

  const navItem = (to, Icon, label) => {
    const active = location.pathname === to;
    return (
      <Link
        to={to}
        className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] transition-colors sidebar-item ${
          active
            ? "bg-[#f5ede0]/10 text-[#f5ede0] sidebar-item--active"
            : "text-[#a8a092] hover:bg-[#f5ede0]/5 hover:text-[#f5ede0]"
        }`}
      >
        <Icon className="w-4 h-4" /> {label}
      </Link>
    );
  };

  return (
    <aside className="w-[280px] flex-shrink-0 h-screen flex flex-col border-r border-[#f5ede0]/8 bg-[#16110c] glass-heavy depth-1 z-10">
      <div className="px-4 py-4 border-b border-[#f5ede0]/8">
        <Link to="/" className="flex items-center gap-2 mb-4">
          <svg width="22" height="22" viewBox="0 0 32 32" fill="none">
            <path d="M4 16 Q 16 4, 28 16" stroke="#b5a8f5" strokeWidth="2.2" strokeLinecap="round" fill="none" />
            <path d="M4 16 Q 16 28, 28 16" stroke="#b5a8f5" strokeWidth="2.2" strokeLinecap="round" fill="none" />
            <circle cx="16" cy="16" r="2.4" fill="#b5a8f5" />
          </svg>
          <span className="font-mono text-[15px] text-[#f5ede0] lowercase">
            co<span className="text-[#b5a8f5]">gent</span>
          </span>
        </Link>
        <button
          onClick={onNew}
          className="w-full inline-flex items-center justify-center gap-2 px-3 py-2.5 rounded-md bg-[#f5ede0] text-[#15110d] text-[12px] font-mono uppercase tracking-wider hover:bg-white btn-cinema transition-colors"
        >
          <Plus className="w-4 h-4" /> New chat
        </button>
      </div>

      <div className="px-2 py-3 space-y-0.5">
        {navItem("/app", Home, "Home")}
        {navItem("/app/memory", Brain, "Memory")}
        {navItem("/app/skills", Wrench, "Skills")}
        {navItem("/app/tasks", Calendar, "Scheduled")}
        {navItem("/app/mcp", Server, "MCP Servers")}
        {navItem("/app/settings", Settings, "Settings")}
      </div>

      <div className="px-4 pt-3 pb-2">
        <p className="text-[10px] uppercase tracking-wider font-mono text-[#6e6760]">Chats</p>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
        {loading && (
          <div className="px-3 py-2 text-[12px] text-[#6e6760]">Loading...</div>
        )}
        {!loading && sessions.length === 0 && (
          <div className="px-3 py-2 text-[12px] text-[#6e6760]">No chats yet.</div>
        )}
        {sessions.map((s) => {
          const active = s.id === activeId;
          return (
            <div
              key={s.id}
              className={`group flex items-center gap-2 rounded-md transition-colors ${
                active ? "bg-[#f5ede0]/10" : "hover:bg-[#f5ede0]/5"
              }`}
            >
              <Link
                to={`/app/c/${s.id}`}
                className={`flex-1 min-w-0 flex items-center gap-2 px-3 py-2 text-[13px] truncate ${
                  active ? "text-[#f5ede0]" : "text-[#a8a092] hover:text-[#f5ede0]"
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="truncate">{s.title || "New chat"}</span>
              </Link>
              <button
                onClick={() => onDelete(s.id)}
                className="opacity-0 group-hover:opacity-100 p-1.5 mr-1 text-[#6e6760] hover:text-[#ef4444] transition-all"
                aria-label="delete"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </nav>

      <div className="px-4 py-3 border-t border-[#f5ede0]/8 text-[10px] font-mono text-[#6e6760]">
        Powered by Kilo Gateway
      </div>
    </aside>
  );
}
