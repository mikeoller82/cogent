import React, { useState, useEffect, useCallback } from "react";
import { getCredentials, setCredential, deleteCredential } from "./apiClient";
import { Settings, Key, Trash2, CheckCircle2, AlertCircle, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

const PROVIDERS = [
  { id: "opencode-zen", name: "OpenCode", model: "deepseek-v4-flash-free", envVar: "OPENCODE_API_KEY", description: "OpenCode Zen API (free tier)" },
  { id: "kilocode", name: "KiloCode", model: "nvidia/nemotron-3-ultra-550b-a55b:free", envVar: "KILOCODE_API_KEY", description: "KiloCode Gateway (free tier)" },
  { id: "openrouter", name: "OpenRouter", model: "openrouter/owl-alpha", envVar: "OPENROUTER_API_KEY", description: "OpenRouter unified API" },
  { id: "openai", name: "OpenAI", model: "gpt-5.5, gpt-5.4", envVar: "OPENAI_API_KEY", description: "OpenAI API (GPT-5.5, GPT-5.4)" },
  { id: "anthropic", name: "Anthropic", model: "claude-sonnet-4-6, claude-opus-4-8", envVar: "ANTHROPIC_API_KEY", description: "Anthropic API (Claude models)" },
  { id: "gemini", name: "Google Gemini", model: "gemini-flash-3.5, gemini-pro-3.1", envVar: "GEMINI_API_KEY", description: "Google Gemini API (OpenAI-compatible)" },
];

export default function SettingsPanel() {
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [keyInputs, setKeyInputs] = useState({});
  const [saving, setSaving] = useState({});
  const [showKeys, setShowKeys] = useState({});

  const refresh = useCallback(async () => {
    try {
      const data = await getCredentials();
      setCredentials(data);
    } catch {
      // silent — panel may load before backend is reachable
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleSave = async (serviceId) => {
    const key = keyInputs[serviceId]?.trim();
    if (!key) {
      toast.error("Enter an API key first");
      return;
    }
    setSaving((s) => ({ ...s, [serviceId]: true }));
    try {
      await setCredential(serviceId, key);
      toast.success(`${PROVIDERS.find((p) => p.id === serviceId)?.name || serviceId} key saved`);
      setKeyInputs((s) => ({ ...s, [serviceId]: "" }));
      refresh();
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || "Save failed";
      toast.error(msg);
    } finally {
      setSaving((s) => ({ ...s, [serviceId]: false }));
    }
  };

  const handleDelete = async (serviceId) => {
    setSaving((s) => ({ ...s, [serviceId]: true }));
    try {
      await deleteCredential(serviceId);
      toast.success(`${PROVIDERS.find((p) => p.id === serviceId)?.name || serviceId} key removed`);
      refresh();
    } catch (e) {
      if (e?.response?.status === 404) {
        toast.error("No key stored for this provider");
      } else {
        const msg = e?.response?.data?.detail || e.message || "Delete failed";
        toast.error(msg);
      }
    } finally {
      setSaving((s) => ({ ...s, [serviceId]: false }));
    }
  };

  const getKeyStatus = (serviceId) => {
    return credentials.find((c) => c.service === serviceId);
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[820px] mx-auto px-6 py-10">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-md bg-[#1d1813] border border-[#b5a8f5]/30 flex items-center justify-center glow-accent">
            <Settings className="w-4 h-4 text-[#b5a8f5]" />
          </div>
          <h1 className="text-[26px] tracking-[-0.02em] text-[#f5ede0]">Settings</h1>
        </div>
        <p className="text-[14px] text-[#a8a092] mb-8">
          Manage API keys for LLM providers. Keys are stored locally in <code className="text-[#b5a8f5]">memory/auth.json</code> and never leave your machine.
          Cogent uses a fallback chain — if one provider is rate-limited, it automatically tries the next.
        </p>

        {loading ? (
          <div className="text-[13px] text-[#6e6760]">Loading…</div>
        ) : (
          <div className="space-y-3">
            {PROVIDERS.map((provider) => {
              const status = getKeyStatus(provider.id);
              const hasKey = status?.has_key;
              const preview = status?.key_preview || "";

              return (
                <div
                  key={provider.id}
                  className="glass-card rounded-xl p-5 border border-[#f5ede0]/8 hover:border-[#f5ede0]/15 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2.5 mb-1">
                        <h3 className="text-[15px] font-medium text-[#f5ede0]">{provider.name}</h3>
                        {hasKey ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-[#22c55e] bg-[#22c55e]/10 px-1.5 py-0.5 rounded">
                            <CheckCircle2 className="w-3 h-3" />
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-[#6e6760] bg-[#f5ede0]/5 px-1.5 py-0.5 rounded">
                            <AlertCircle className="w-3 h-3" />
                            No key
                          </span>
                        )}
                      </div>
                      <p className="text-[12px] text-[#a8a092]">{provider.description}</p>
                      <p className="text-[11px] text-[#6e6760] font-mono mt-1">
                        Model: {provider.model} | Env: {provider.envVar}
                      </p>
                      {hasKey && (
                        <p className="text-[11px] text-[#6e6760] font-mono mt-1">
                          Stored key: {preview}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="relative flex-1 max-w-md">
                      <input
                        type={showKeys[provider.id] ? "text" : "password"}
                        value={keyInputs[provider.id] || ""}
                        onChange={(e) => setKeyInputs((s) => ({ ...s, [provider.id]: e.target.value }))}
                        onKeyDown={(e) => e.key === "Enter" && handleSave(provider.id)}
                        placeholder={hasKey ? "Enter new key to replace…" : `Enter ${provider.name} API key…`}
                        className="w-full bg-[#15110d] border border-[#f5ede0]/10 rounded-md px-3 py-2 pr-9 text-[13px] text-[#f5ede0] placeholder:text-[#6e6760] outline-none focus:border-[#b5a8f5]/40"
                      />
                      <button
                        type="button"
                        onClick={() => setShowKeys((s) => ({ ...s, [provider.id]: !s[provider.id] }))}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-[#6e6760] hover:text-[#a8a092] transition-colors"
                      >
                        {showKeys[provider.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    <button
                      onClick={() => handleSave(provider.id)}
                      disabled={saving[provider.id] || !keyInputs[provider.id]?.trim()}
                      className="px-4 py-2 rounded-md bg-[#f5ede0] text-[#15110d] text-[12px] font-mono uppercase tracking-wider hover:bg-white btn-cinema transition-colors disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                    >
                      <Key className="w-3.5 h-3.5" />
                      {saving[provider.id] ? "Saving…" : "Save"}
                    </button>
                    {hasKey && (
                      <button
                        onClick={() => handleDelete(provider.id)}
                        disabled={saving[provider.id]}
                        className="px-3 py-2 rounded-md border border-[#f5ede0]/10 text-[#6e6760] text-[12px] font-mono hover:border-[#ef4444]/40 hover:text-[#ef4444] transition-colors disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Remove
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-8 glass-card rounded-xl p-5 border border-[#f5ede0]/8">
          <h3 className="text-[14px] font-medium text-[#f5ede0] mb-2">How it works</h3>
          <ul className="text-[12px] text-[#a8a092] space-y-1.5 list-disc list-inside">
            <li>Cogent tries providers in priority order (OpenCode → KiloCode → OpenRouter → OpenAI → Anthropic → Gemini)</li>
            <li>If a provider returns 429 (rate limited), Cogent automatically falls back to the next one</li>
            <li>Providers without API keys are skipped in the fallback chain</li>
            <li>Keys are stored in <code className="text-[#b5a8f5]">memory/auth.json</code> — you can also set them via environment variables in <code className="text-[#b5a8f5]">backend/.env</code></li>
          </ul>
        </div>
      </div>
    </div>
  );
}
