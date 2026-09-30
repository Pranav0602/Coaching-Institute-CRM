/**
 * Runtime configuration.
 *
 * The app talks to the Render production backend by default. A developer
 * pointing at a local backend (Android emulator via `10.0.2.2`, iOS simulator
 * via `127.0.0.1`, or a physical handset via the machine's LAN IP) must say so
 * explicitly with `EXPO_PUBLIC_API_BASE_URL` or `extra.apiBaseUrl` - the
 * default never points at a loopback address, because a physical handset cannot
 * reach one and fails with "could not reach the API at http://10.0.2.2...".
 */
import Constants from 'expo-constants';

const DEFAULT_PRODUCTION_URL = 'https://coaching-institute-crm.onrender.com/api/v1';

const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const envUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
const extraUrl = (Constants.expoConfig?.extra as Record<string, unknown> | undefined)?.apiBaseUrl;

export const API_BASE_URL = trimTrailingSlash(
  (typeof envUrl === 'string' && envUrl) ||
    (typeof extraUrl === 'string' && extraUrl) ||
    DEFAULT_PRODUCTION_URL,
);

/** Absolute origin, used for `/healthz/` which is not under the `/api/v1` prefix. */
export const API_ORIGIN = API_BASE_URL.replace(/\/api\/v1$/, '');

export const HEALTHCHECK_URL = `${API_ORIGIN}/healthz/`;

/**
 * Render's free tier parks a scaled-to-zero instance cold. Waking it can take
 * ~50s, so the app fires this the moment it opens and the user never pays that
 * cost inside a login spinner.
 */
export const COLD_BOOT_TIMEOUT_MS = 50_000;
export const REQUEST_TIMEOUT_MS = 30_000;
/**
 * Login gets the cold-boot budget, not the normal request budget: on a scaled-to-zero
 * Render instance the first POST boots the container (~30-50s) and a 20-30s timeout
 * turns every cold start into a false "wrong password".
 */
export const LOGIN_TIMEOUT_MS = 50_000;

/** Ask for a fresh access token this long before it actually expires. */
export const REFRESH_SKEW_MS = 60_000;

export const STORAGE_KEYS = {
  accessToken: 'graphix.access_token',
  refreshToken: 'graphix.refresh_token',
  accessExpiresAt: 'graphix.access_expires_at',
  sessionUser: 'graphix.session_user',
  biometricEnabled: 'graphix.biometric_enabled',
  themeMode: 'graphix.theme_mode',
} as const;

export const APP_VERSION = String(Constants.expoConfig?.version ?? '1.0.0');
