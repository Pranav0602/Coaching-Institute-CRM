/**
 * The single HTTP client for the app.
 *
 * Responsibilities that are deliberately concentrated here rather than spread
 * across call sites:
 *
 *  * unwrapping the `{ success, message, data }` envelope,
 *  * attaching the bearer token from secure storage,
 *  * refreshing a stale access token *before* the request rather than after a
 *    visible 401, and transparently retrying once if a 401 slips through,
 *  * de-duplicating concurrent refreshes so a screen firing four queries does not
 *    trigger four rotations (which, with rotation on, would invalidate its own
 *    sibling tokens),
 *  * turning the `{ success: false, errors }` failure body back into a typed error
 *    carrying the first field message.
 */
import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios';

import {
  API_BASE_URL,
  COLD_BOOT_TIMEOUT_MS,
  HEALTHCHECK_URL,
  LOGIN_TIMEOUT_MS,
  REFRESH_SKEW_MS,
  REQUEST_TIMEOUT_MS,
} from '@/constants/config';
import { accessExpiry, tokens } from './storage';
import type { ApiErrorBody, ApiEnvelope, User } from '@/types';

const REFRESH_PATH = '/accounts/auth/token/refresh/';

/**
 * Endpoints that are unauthenticated by nature. A 401 from these means the
 * credentials were wrong, not that the session expired, so they are excluded
 * from the refresh-and-retry path.
 */
const UNAUTHENTICATED_ENDPOINTS = [
  '/accounts/auth/login/',
  '/accounts/auth/forgot-password/',
  '/accounts/auth/reset-password/',
  REFRESH_PATH,
];

export class ApiError extends Error {
  readonly status: number;
  readonly errors: ApiErrorBody['errors'];
  readonly code?: string;

  constructor(message: string, status: number, errors?: ApiErrorBody['errors'], code?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.errors = errors;
    this.code = code;
  }

  /** True when the failure is the device having no route to the API at all. */
  get isOffline(): boolean {
    return this.status === 0;
  }

  get isAuth(): boolean {
    return this.status === 401 || this.status === 403;
  }
}

const firstFieldMessage = (errors: ApiErrorBody['errors']): string | undefined => {
  if (!errors) return undefined;
  if ('detail' in errors && typeof errors.detail === 'string') return errors.detail;
  for (const value of Object.values(errors)) {
    if (Array.isArray(value) && value.length) return value[0];
    if (typeof value === 'string') return value;
  }
  return undefined;
};

// --------------------------------------------------------------- unwrapping

export const unwrapData = <T>(res: unknown): T => {
  const body = (res ?? {}) as ApiEnvelope<T> | T;
  const data = (body as ApiEnvelope<T>).data;
  return (data !== undefined ? data : body) as T;
};

export const unwrapList = <T>(res: unknown): T[] => {
  if (!res) return [];
  if (Array.isArray(res)) return res as T[];
  const body = res as ApiEnvelope<T[] | { results: T[] }> | { results: T[] };
  const data = (body as ApiEnvelope<T>).data ?? body;
  if (Array.isArray(data)) return data as T[];
  if (Array.isArray((data as { results?: T[] })?.results)) return (data as { results: T[] }).results;
  return [];
};

// ------------------------------------------------------------------ session

type SessionEvents = {
  onSignedOut: () => void;
  onRefreshed: (access: string) => void;
};

let events: SessionEvents = { onSignedOut: () => {}, onRefreshed: () => {} };

export const onSessionEvents = (next: Partial<SessionEvents>) => {
  events = { ...events, ...next };
};

/**
 * Wakes a sleeping Render instance before the user hits "Sign in", so the
 * ~50s cold start is paid during the splash screen instead of behind a spinner.
 * Fire-and-forget: a failure here is not an error worth surfacing.
 */
export const warmBackend = async (): Promise<boolean> => {
  try {
    await axios.get(HEALTHCHECK_URL, { timeout: COLD_BOOT_TIMEOUT_MS });
    return true;
  } catch {
    return false;
  }
};

// ------------------------------------------------------------------ refresh

let refreshInFlight: Promise<string | null> | null = null;

/**
 * A single shared promise, so N concurrent 401s cause exactly one rotation.
 */
const refreshAccessToken = async (): Promise<string | null> => {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const refresh = await tokens.getRefresh();
    if (!refresh) return null;
    try {
      const res = await axios.post<ApiEnvelope<{ access: string; refresh?: string }>>(
        `${API_BASE_URL}${REFRESH_PATH}`,
        { refresh },
        { timeout: REQUEST_TIMEOUT_MS, headers: { 'Content-Type': 'application/json' } },
      );
      // `res.data` is the envelope; `unwrapData` peels the payload out of it.
      // Passing the whole AxiosResponse here would return the envelope and
      // `data.access` would be undefined - i.e. the session would be wiped on
      // the first refresh.
      const data = unwrapData<{ access: string; refresh?: string; access_expires_in?: number }>(
        res.data,
      );
      await tokens.rotate(data.access, data.refresh);
      if (typeof data.access_expires_in === 'number' && data.access_expires_in > 0) {
        await accessExpiry.set(Date.now() + data.access_expires_in * 1000);
      } else {
        // Server did not report a lifetime: do not stamp `now` as the expiry, which
        // would mark every token stale and force a refresh before the next request.
        await accessExpiry.clear();
      }
      events.onRefreshed(data.access);
      return data.access;
    } catch {
      // The refresh token is spent, revoked or the session was never valid.
      // Nothing below can recover from that, so tear the session down.
      await tokens.clear();
      await accessExpiry.clear();
      events.onSignedOut();
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
};

/** True when the stored access token is missing or about to expire. */
const isAccessTokenStale = async (): Promise<boolean> => {
  const expiresAt = await accessExpiry.get();
  if (expiresAt === null) return false; // server did not report a lifetime
  return Date.now() >= expiresAt - REFRESH_SKEW_MS;
};

// ------------------------------------------------------------------- client

const http: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
});

http.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  // Never stamp an Authorization header on the refresh call itself.
  if (config.url?.includes(REFRESH_PATH)) return config;

  if (await isAccessTokenStale()) {
    const access = await refreshAccessToken();
    if (access) config.headers.Authorization = `Bearer ${access}`;
    return config;
  }

  const access = await tokens.getAccess();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

http.interceptors.response.use(
  (res) => res,
  async (error: AxiosError<ApiErrorBody>) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const status = error.response?.status ?? 0;

    /**
     * A 401 only means "session expired" for authenticated calls. On the login
     * and password endpoints it means "those credentials were wrong", and
     * attempting a refresh there is actively harmful: a failed refresh calls
     * `onSignedOut`, which would tear down whatever session the user was already
     * using (for instance when switching accounts from the login screen).
     */
    const refreshable =
      status === 401 &&
      original !== undefined &&
      !original._retried &&
      !UNAUTHENTICATED_ENDPOINTS.some((path) => original.url?.includes(path));

    if (refreshable && original) {
      original._retried = true;
      const access = await refreshAccessToken();
      if (access) {
        original.headers.Authorization = `Bearer ${access}`;
        return http.request(original);
      }
    }

    if (!error.response) {
      return Promise.reject(
        new ApiError(
          `Network error: could not reach the API at ${API_BASE_URL}. Check that the backend is running and reachable from this device.`,
          0,
        ),
      );
    }

    const body = error.response.data;
    const message =
      body?.message ??
      firstFieldMessage(body?.errors) ??
      (status === 404 ? 'That record no longer exists.' : 'Something went wrong. Please try again.');
    return Promise.reject(new ApiError(message, status, body?.errors, body?.code));
  },
);

/**
 * Query parameters are flattened straight onto the URL by axios, so anything
 * `undefined` is dropped and anything scalar is stringified for us.
 */
export type QueryParams = Record<string, string | number | boolean | undefined | null>;

/**
 * A thin typed wrapper. Every caller gets the unwrapped payload, and errors
 * arrive as `ApiError` rather than `AxiosError`.
 */
export const api = {
  async get<T>(path: string, params?: QueryParams, config?: AxiosRequestConfig) {
    const res = await http.get(path, { ...config, params });
    return unwrapData<T>(res.data);
  },
  async getList<T>(path: string, params?: QueryParams, config?: AxiosRequestConfig) {
    const res = await http.get(path, { ...config, params });
    return unwrapList<T>(res.data);
  },
  async post<T>(path: string, body?: unknown, config?: AxiosRequestConfig) {
    const res = await http.post(path, body, config);
    return unwrapData<T>(res.data);
  },
  async patch<T>(path: string, body?: unknown, config?: AxiosRequestConfig) {
    const res = await http.patch(path, body, config);
    return unwrapData<T>(res.data);
  },
  async put<T>(path: string, body?: unknown, config?: AxiosRequestConfig) {
    const res = await http.put(path, body, config);
    return unwrapData<T>(res.data);
  },
  async del<T>(path: string, config?: AxiosRequestConfig) {
    const res = await http.delete(path, config);
    return unwrapData<T>(res.data);
  },

  /** Multipart upload, for profile photos and similar. */
  async upload<T>(path: string, form: FormData, config?: AxiosRequestConfig) {
    const res = await http.post(path, form, {
      ...config,
      headers: { ...(config?.headers ?? {}), 'Content-Type': 'multipart/form-data' },
    });
    return unwrapData<T>(res.data);
  },
};

// -------------------------------------------------------------------- auth

export interface LoginResponse {
  access: string;
  refresh: string;
  access_expires_in: number;
  refresh_expires_in: number;
  user: User;
}

export const authApi = {
  login: (username: string, password: string) =>
    api.post<LoginResponse>(
      '/accounts/auth/login/',
      { username, password },
      { timeout: LOGIN_TIMEOUT_MS },
    ),

  me: () => api.get<User>('/accounts/auth/me/'),

  logout: (refresh: string | null) =>
    api.post<{ message: string }>('/accounts/auth/logout/', { refresh }),

  forgotPassword: (emailOrUsername: string) =>
    api.post<{ message: string; demo_otp?: string }>('/accounts/auth/forgot-password/', {
      email_or_username: emailOrUsername,
    }),

  resetPassword: (emailOrUsername: string, otp: string, newPassword: string) =>
    api.post<{ message: string }>('/accounts/auth/reset-password/', {
      email_or_username: emailOrUsername,
      otp,
      new_password: newPassword,
    }),

  changePassword: (oldPassword: string, newPassword: string) =>
    api.post<{ message: string }>('/accounts/auth/change-password/', {
      old_password: oldPassword,
      new_password: newPassword,
      confirm_password: newPassword,
    }),
};

export const clearSession = async () => {
  await tokens.clear();
  await accessExpiry.clear();
  const { sessionStore } = await import('./storage');
  await sessionStore.clear();
};

export default http;
