import axios from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// helper: extract list from various response shapes (envelope, paginated, raw array)
export const unwrapList = (res) => {
  if (!res) return [];
  if (Array.isArray(res)) return res;
  // envelope { success, data: [...] } or { success, data: { results: [...] } }
  const d = res.data ?? res;
  if (Array.isArray(d)) return d;
  if (Array.isArray(d?.data)) return d.data;
  if (Array.isArray(d?.results)) return d.results;
  if (Array.isArray(d?.data?.results)) return d.data.results;
  if (d && typeof d === 'object' && d !== null) {
    // if paginated envelope: { success, data: { count, results } }
    if (d.data && Array.isArray(d.data.results)) return d.data.results;
  }
  return [];
};

export const unwrapData = (res) => {
  if (!res) return null;
  if (res.data !== undefined && res.success !== undefined) return res.data;
  if (res.data !== undefined) return res.data;
  return res;
};

// Interceptor for JWT auth token injection
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor for response handling
api.interceptors.response.use(
  (response) => {
    if (response.data && response.data.success !== undefined) {
      return response.data;
    }
    return { success: true, data: response.data };
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // only clear if not a login attempt
      const isLogin = error.config?.url?.includes('/auth/login');
      if (!isLogin) {
        localStorage.removeItem('access_token');
        // keep user for debug but mark session expired
      }
    }
    // network error (API not running)
    if (!error.response) {
      return Promise.reject({
        detail: 'Network error: Could not reach the API. Please make sure the backend is running at ' + API_BASE_URL,
        errors: { detail: ['API unreachable at ' + API_BASE_URL] },
        status_code: 0,
      });
    }
    return Promise.reject(error.response ? error.response.data : error);
  }
);

// Lightweight backend pre-warming ping. The SPA is served from Vercel while the
// API sleeps on Render after ~15min idle; firing this when the landing/login
// page mounts (and on first input focus) means the container is already warm
// by the time the user clicks "Sign In". Never throws - failures are silent.
export const warmBackend = () => {
  try {
    // /healthz lives at the API root, not under /api/v1, and performs no DB I/O.
    const rootBase = API_BASE_URL.replace(/\/api\/v1\/?$/, '');
    const url = `${rootBase}/healthz/`;
    // Plain axios (no interceptors) + short timeout so this never blocks UI.
    return axios.get(url, { timeout: 8000 }).catch(() => null);
  } catch {
    return Promise.resolve(null);
  }
};

// Backwards-compatible helper referenced in the optimisation plan.
api.warmup = warmBackend;

export default api;
