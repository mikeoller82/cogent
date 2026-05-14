import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;
export const BASE = BACKEND_URL;

export const api = axios.create({
  baseURL: API,
  timeout: 180000,
});

export const listSessions = () => api.get("/sessions").then((r) => r.data);
export const createSession = (title) =>
  api.post("/sessions", { title }).then((r) => r.data);
export const deleteSession = (id) => api.delete(`/sessions/${id}`).then((r) => r.data);

export const listMessages = (sid) =>
  api.get(`/sessions/${sid}/messages`).then((r) => r.data);
export const sendMessage = (sid, text, attachments = []) =>
  api.post(`/sessions/${sid}/messages`, { text, attachments }).then((r) => r.data);

export const listMemory = () => api.get("/memory").then((r) => r.data);
export const addMemory = (key, value) =>
  api.post("/memory", { key, value }).then((r) => r.data);
export const deleteMemory = (key) =>
  api.delete(`/memory/${encodeURIComponent(key)}`).then((r) => r.data);

export const listTasks = () => api.get("/tasks").then((r) => r.data);
export const deleteTask = (id) => api.delete(`/tasks/${id}`).then((r) => r.data);
export const runTaskNow = (id) => api.post(`/tasks/${id}/run`).then((r) => r.data);

export const uploadFile = (file) => {
  const fd = new FormData();
  fd.append("file", file);
  return api
    .post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } })
    .then((r) => r.data);
};

export const artifactUrl = (path) => `${API.replace(/\/api$/, "")}${path}`;

/**
 * Stream a message. onEvent(event) is called for each parsed SSE event.
 * Returns the final 'done' event with the persisted assistant message.
 */
export async function streamMessage(sessionId, text, attachments, onEvent) {
  const resp = await fetch(`${API}/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, attachments }),
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`Stream failed: ${resp.status}`);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let lastDone = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const line = raw.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      try {
        const evt = JSON.parse(payload);
        if (evt.type === "done") lastDone = evt;
        onEvent && onEvent(evt);
      } catch {}
    }
  }
  return lastDone;
}
