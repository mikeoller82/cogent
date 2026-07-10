// Lightweight token store + axios interceptor setup.
// Tokens live in localStorage so the SPA survives page reloads.
// Refresh logic is best-effort and pulls a new access token via /auth/refresh.

const ACCESS_KEY  = "cogent.accessToken";
const REFRESH_KEY = "cogent.refreshToken";
const USER_KEY    = "cogent.user";

export function getAccessToken()  { return localStorage.getItem(ACCESS_KEY) || ""; }
export function getRefreshToken() { return localStorage.getItem(REFRESH_KEY) || ""; }
export function getStoredUser()   {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || "null"); }
  catch { return null; }
}

export function storeSession({ access_token, refresh_token, user }) {
  if (access_token)  localStorage.setItem(ACCESS_KEY,  access_token);
  if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token);
  if (user)          localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function updateAccessToken(access_token) {
  if (access_token) localStorage.setItem(ACCESS_KEY, access_token);
}

export function clearSession() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

/**
 * Attach an axios instance and intercept 401s to attempt a silent refresh.
 * If refresh fails, the session is cleared and the next render of AuthGate
 * will redirect to login.
 */
export function attachAuthInterceptors(axiosInstance, { onAuthFailed } = {}) {
  // ── Request: inject Bearer ─────────────────────────────────────────
  axiosInstance.interceptors.request.use((config) => {
    const token = getAccessToken();
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // ── Response: refresh on 401 ───────────────────────────────────────
  let refreshing = null;
  axiosInstance.interceptors.response.use(
    (resp) => resp,
    async (error) => {
      const status = error?.response?.status;
      const original = error?.config || {};
      if (status !== 401 || original._retry || !getRefreshToken()) {
        return Promise.reject(error);
      }

      original._retry = true;
      try {
        refreshing = refreshing || axiosInstance.post("/auth/refresh", {
          refresh_token: getRefreshToken(),
        });
        const { data } = await refreshing;
        refreshing = null;
        if (data?.access_token) {
          updateAccessToken(data.access_token);
          if (data.refresh_token) localStorage.setItem(REFRESH_KEY, data.refresh_token);
          if (data.user) localStorage.setItem(USER_KEY, JSON.stringify(data.user));
          original.headers = original.headers || {};
          original.headers.Authorization = `Bearer ${getAccessToken()}`;
          return axiosInstance.request(original);
        }
      } catch {
        refreshing = null;
        clearSession();
        if (typeof onAuthFailed === "function") onAuthFailed();
      }
      return Promise.reject(error);
    },
  );
}
