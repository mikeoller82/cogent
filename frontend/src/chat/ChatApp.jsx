import React, { useState, useEffect, useRef } from "react";
import { Routes, Route, useNavigate, useParams } from "react-router-dom";
import Sidebar from "./Sidebar";
import ChatThread from "./ChatThread";
import MemoryPanel from "./MemoryPanel";
import TasksPanel from "./TasksPanel";
import { listSessions, createSession, deleteSession } from "./apiClient";
import { toast } from "sonner";

function ChatHome() {
  return (
    <div className="flex-1 flex items-center justify-center text-center px-8">
      <div className="max-w-md">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-[#1d1813] border border-[#b5a8f5]/30 flex items-center justify-center mb-5">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L22 12L12 22L2 12L12 2Z" stroke="#b5a8f5" strokeWidth="1.8" />
            <path d="M12 7L17 12L12 17L7 12L12 7Z" fill="#b5a8f5" fillOpacity="0.4" />
          </svg>
        </div>
        <h2 className="text-[28px] tracking-[-0.02em] text-[#f5ede0]">
          What should Viktor do for you?
        </h2>
        <p className="mt-3 text-[14px] text-[#a8a092]">
          Start a new chat to begin. Viktor can research, build PDFs, deploy web apps,
          remember facts about your business, and schedule recurring tasks.
        </p>
      </div>
    </div>
  );
}

function ChatRoute({ sessions, refresh }) {
  const { id } = useParams();
  return <ChatThread key={id} sessionId={id} sessions={sessions} refreshSessions={refresh} />;
}

export default function ChatApp() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const refresh = async () => {
    try {
      const data = await listSessions();
      setSessions(data);
      return data;
    } catch (e) {
      console.error(e);
      return [];
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleNew = async () => {
    try {
      const s = await createSession(null);
      await refresh();
      navigate(`/app/c/${s.id}`);
    } catch (e) {
      toast.error("Failed to create chat");
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteSession(id);
      const data = await refresh();
      const current = window.location.pathname.split("/").pop();
      if (current === id) {
        if (data.length) navigate(`/app/c/${data[0].id}`);
        else navigate("/app");
      }
    } catch (e) {
      toast.error("Failed to delete");
    }
  };

  return (
    <div className="h-screen w-screen flex bg-[#15110d] text-[#f5ede0] overflow-hidden">
      <Sidebar
        sessions={sessions}
        loading={loading}
        onNew={handleNew}
        onDelete={handleDelete}
      />
      <main className="flex-1 flex flex-col min-w-0">
        <Routes>
          <Route index element={<ChatHome />} />
          <Route path="c/:id" element={<ChatRoute sessions={sessions} refresh={refresh} />} />
          <Route path="memory" element={<MemoryPanel />} />
          <Route path="tasks" element={<TasksPanel />} />
        </Routes>
      </main>
    </div>
  );
}
