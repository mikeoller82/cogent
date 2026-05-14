import React, { useState, useEffect } from "react";
import { listTasks, deleteTask } from "./apiClient";
import { Calendar, Trash2, Clock } from "lucide-react";
import { toast } from "sonner";

export default function TasksPanel() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const data = await listTasks();
      setItems(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const handleDelete = async (id) => {
    try {
      await deleteTask(id);
      refresh();
    } catch (e) {
      toast.error("Failed to delete");
    }
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[820px] mx-auto px-6 py-10">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-md bg-[#1d1813] border border-[#b5a8f5]/30 flex items-center justify-center">
            <Calendar className="w-4 h-4 text-[#b5a8f5]" />
          </div>
          <h1 className="text-[26px] tracking-[-0.02em] text-[#f5ede0]">Scheduled tasks</h1>
        </div>
        <p className="text-[14px] text-[#a8a092] mb-8">
          Recurring work Viktor runs automatically. Ask Viktor in chat to schedule a new task.
        </p>

        <div className="space-y-2">
          {loading && <div className="text-[13px] text-[#6e6760]">Loading…</div>}
          {!loading && items.length === 0 && (
            <div className="text-[13px] text-[#6e6760] py-6 text-center">
              No scheduled tasks. In chat say: “Every Monday 9am, summarize last week’s news on AI agents.”
            </div>
          )}
          {items.map((t) => (
            <div
              key={t.id}
              className="group px-5 py-4 rounded-xl bg-[#1d1813] border border-[#f5ede0]/8 hover:border-[#f5ede0]/15 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="text-[15px] font-medium text-[#f5ede0]">{t.name}</div>
                <button
                  onClick={() => handleDelete(t.id)}
                  className="opacity-0 group-hover:opacity-100 p-1.5 text-[#6e6760] hover:text-[#ef4444] transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="flex items-center gap-3 text-[12px] text-[#a8a092] font-mono mb-3">
                <span className="inline-flex items-center gap-1.5">
                  <Clock className="w-3 h-3" /> {t.cadence} at {t.time}
                </span>
                <span className="text-[#6e6760]">•</span>
                <span className={`uppercase tracking-wider ${t.status === "active" ? "text-[#22c55e]" : "text-[#6e6760]"}`}>
                  {t.status}
                </span>
              </div>
              <div className="text-[13px] text-[#d8d0c2] leading-[1.55] bg-[#15110d]/50 border border-[#f5ede0]/5 rounded-md p-3">
                {t.prompt}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
