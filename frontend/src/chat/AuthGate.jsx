import React, { useEffect, useState } from "react";
import {
  getAccessToken, getStoredUser, storeSession, clearSession,
} from "./auth";
import { registerUser, loginUser, fetchMe, logout as doLogout } from "./apiClient";
import { toast } from "sonner";

/**
 * Shows a minimal login/register screen when no token is present,
 * otherwise renders children. Listens for `cogent:auth-failed` so the
 * axios auth interceptor can force a logout without prop chains.
 */
export default function AuthGate({ children }) {
  const [authed, setAuthed] = useState(Boolean(getAccessToken()));
  const [user, setUser] = useState(getStoredUser());

  useEffect(() => {
    const handler = () => { setAuthed(false); setUser(null); };
    window.addEventListener("cogent:auth-failed", handler);
    return () => window.removeEventListener("cogent:auth-failed", handler);
  }, []);

  // Verify the stored token on first mount so we surface stale sessions early.
  useEffect(() => {
    if (!authed) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await fetchMe();
        if (!cancelled) { setUser(me); storeSession({ user: me }); }
      } catch {
        if (!cancelled) {
          clearSession();
          setAuthed(false);
          setUser(null);
          toast.error("Session expired. Please log in again.");
        }
      }
    })();
    return () => { cancelled = true; };
  }, [authed]);

  const handleLogout = () => { doLogout(); };

  if (!authed) {
    return <LoginScreen onAuthed={(s) => { setAuthed(true); setUser(s.user); }} />;
  }

  return (
    <>
      {React.Children.map(children, (child) => {
        if (!React.isValidElement(child)) return child;
        return React.cloneElement(child, { currentUser: user, onLogout: handleLogout });
      })}
    </>
  );
}

function LoginScreen({ onAuthed }) {
  const [mode, setMode] = useState("login"); // login | register
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const data = mode === "register"
        ? await registerUser(email, password, name || undefined)
        : await loginUser(email, password);
      storeSession(data);
      onAuthed(data);
      toast.success(mode === "register" ? "Account created." : "Welcome back.");
    } catch (e2) {
      const detail = e2?.response?.data?.detail || e2?.message || "Authentication failed.";
      setErr(typeof detail === "string" ? detail : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-[#15110d] text-[#f5ede0]">
      <div className="w-full max-w-sm p-8 rounded-2xl bg-[#1d1813] border border-[#2a241c] shadow-xl">
        <div className="flex items-center gap-3 mb-6">
          <img src="/cogentfinal.png" alt="Cogent" className="w-10 h-10 rounded-xl" />
          <div>
            <div className="text-lg tracking-tight font-semibold">Cogent</div>
            <div className="text-xs text-[#a8a092]">
              {mode === "register" ? "Create an account" : "Sign in to continue"}
            </div>
          </div>
        </div>

        <form onSubmit={submit} className="flex flex-col gap-3">
          {mode === "register" && (
            <input
              type="text" placeholder="Display name (optional)"
              className="px-3 py-2 rounded-md bg-[#15110d] border border-[#2a241c] text-sm focus:outline-none focus:border-[#7c5cf5]"
              value={name} onChange={(e) => setName(e.target.value)}
              autoComplete="name"
            />
          )}
          <input
            type="email" placeholder="Email" required
            className="px-3 py-2 rounded-md bg-[#15110d] border border-[#2a241c] text-sm focus:outline-none focus:border-[#7c5cf5]"
            value={email} onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
          <input
            type="password" placeholder="Password" required minLength={8}
            className="px-3 py-2 rounded-md bg-[#15110d] border border-[#2a241c] text-sm focus:outline-none focus:border-[#7c5cf5]"
            value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "register" ? "new-password" : "current-password"}
          />
          {err && (
            <div className="text-xs text-[#dc2626] bg-[#1c1410] border border-[#3a1f1c] rounded p-2">
              {err}
            </div>
          )}
          <button
            type="submit" disabled={busy}
            className="mt-2 px-3 py-2 rounded-md bg-[#7c5cf5] hover:bg-[#6a4ce0] disabled:opacity-50 text-sm font-medium transition"
          >
            {busy ? "Working…" : (mode === "register" ? "Create account" : "Sign in")}
          </button>
        </form>

        <div className="mt-5 text-xs text-[#a8a092] text-center">
          {mode === "register" ? (
            <>Already have an account?{" "}
              <button onClick={() => setMode("login")}
                className="text-[#7c5cf5] hover:underline">Sign in</button></>
          ) : (
            <>New here?{" "}
              <button onClick={() => setMode("register")}
                className="text-[#7c5cf5] hover:underline">Create an account</button></>
          )}
        </div>
      </div>
    </div>
  );
}
