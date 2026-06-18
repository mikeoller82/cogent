import React, { useState, useEffect } from "react";
import { listMemory, addMemory, deleteMemory } from "./apiClient";
import { Brain, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

export default function MemoryPanel() {
  const [items, setItems] = useState([]);
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const data = await listMemory();
      setItems(data);
    } catch (e) {
      toast.error("Failed to load memory");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const handleAdd = async () => {
    if (!key.trim() || !value.trim()) return;
    try {
      await addMemory(key.trim(), value.trim());
      setKey("");
      setValue("");
      refresh();
    } catch (e) {
      toast.error("Failed to save");
    }
  };

  const handleDelete = async (k) => {
    try {
      await deleteMemory(k);
      refresh();
    } catch (e) {
      toast.error("Failed to delete");
    }
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[820px] mx-auto px-6 py-10">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-md bg-[#1d1813] border border-[#b5a8f5]/30 flex items-center justify-center glow-accent">
            <Brain className="w-4 h-4 text-[#b5a8f5]" />
          </div>
          <h1 className="text-[26px] tracking-[-0.02em] text-[#f5ede0]">Memory</h1>
        </div>
        <p className="text-[14px] text-[#a8a092] mb-8">
          Facts Cogent remembers across all conversations. Cogent adds these automatically when you share context—you can also add them manually.
        </p>

        <div className="glass-card rounded-xl p-4 mb-6">          {/* border + bg handled by glass-card */}
          <div className="grid grid-cols-1 md:grid-cols-[200px_1fr_auto] gap-2">
            <input
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="key (e.g. company_name)"
              className="bg-[#15110d] border border-[#f5ede0]/10 rounded-md px-3 py-2 text-[13px] text-[#f5ede0] placeholder:text-[#6e6760] outline-none focus:border-[#b5a8f5]/40"
            />
            <input
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              placeholder="value (e.g. Acme Inc.)"
              className="bg-[#15110d] border border-[#f5ede0]/10 rounded-md px-3 py-2 text-[13px] text-[#f5ede0] placeholder:text-[#6e6760] outline-none focus:border-[#b5a8f5]/40"
            />
            <button
              onClick={handleAdd}
              className="px-4 py-2 rounded-md bg-[#f5ede0] text-[#15110d] text-[12px] font-mono uppercase tracking-wider hover:bg-white inline-flex items-center gap-2 btn-cinema"
            >
              <Plus className="w-3.5 h-3.5" /> Add
            </button>
          </div>
        </div>

        <div className="space-y-2">
          {loading && <div className="text-[13px] text-[#6e6760]">Loading…</div>}
          {!loading && items.length === 0 && (
            <div className="text-[13px] text-[#6e6760] py-6 text-center">
              No memories yet. Tell Cogent about yourself in a chat.
            </div>
          )}
          {items.map((m) => (
            <div
              key={m.key}
              className="group flex items-center gap-4 px-4 py-3 rounded-lg glass-card border border-[#f5ede0]/8 hover:border-[#f5ede0]/15 transition-colors"
            >
              <code className="text-[12px] font-mono text-[#b5a8f5] min-w-[140px] truncate">{m.key}</code>
              <div className="flex-1 text-[13px] text-[#d8d0c2] min-w-0">{m.value}</div>
              <button
                onClick={() => handleDelete(m.key)}
                className="opacity-0 group-hover:opacity-100 p-1.5 text-[#6e6760] hover:text-[#ef4444] transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
