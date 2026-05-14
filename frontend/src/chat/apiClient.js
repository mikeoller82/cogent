import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

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
export const sendMessage = (sid, text) =>
  api.post(`/sessions/${sid}/messages`, { text }).then((r) => r.data);

export const listMemory = () => api.get("/memory").then((r) => r.data);
export const addMemory = (key, value) =>
  api.post("/memory", { key, value }).then((r) => r.data);
export const deleteMemory = (key) =>
  api.delete(`/memory/${encodeURIComponent(key)}`).then((r) => r.data);

export const listTasks = () => api.get("/tasks").then((r) => r.data);
export const deleteTask = (id) => api.delete(`/tasks/${id}`).then((r) => r.data);

export const artifactUrl = (path) => `${API.replace(/\/api$/, "")}${path}`;
