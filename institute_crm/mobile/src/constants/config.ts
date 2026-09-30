/**
 * Runtime configuration.
 *
 * The API base URL is the one value that has to change between a developer's
 * machine, a physical handset on the same LAN, an Android emulator and
 * production, so it is resolved once, here, with the platform-specific
 * fallbacks spelled out.
 */
import Constants from 'expo-constants';
import { Platform } from 'react-native';

const DEFAULT_PRODUCTION_URL = 'https://coaching-institute-crm.onrender.com/api/v1';

/**
 * `10.0.2.2` is the loopback alias inside the Android emulator. iOS simulators
 * share the host's network stack, so `127.0.0.1` is correct there. A real
 * handset needs the machine's LAN IP and must supply it explicitly.
 */
const LOCAL_FALLBACK =
  Platform.OS === 'android' ? 'http://10.0.2.2:8000/api/v1' : 'http://127.0.0.1:8000/api/v1';

const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const envUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
const extraUrl = (Constants.expoConfig?.extra as Record<string, unknown> | undefined)?.apiBaseUrl;

// In dev without an explicit override, talk to the developer's backend instead of
// production: seeded users (admin/Admin@123, ...) exist only in the dev database,
// so pointing a dev build at production is the single most common "correct password,
// won't sign in" report.
const isDevBuild =
  typeof __DEV__ !== 'undefined'
    ? __DEV__
    : process.env.NODE_ENV !== 'production';

export const API_BASE_URL = trimTrailingSlash(
  (typeof envUrl === 'string' && envUrl) ||
    (typeof extraUrl === 'string' && extraUrl) ||
    (isDevBuild ? LOCAL_FALLBACK : DEFAULT_PRODUCTION_URL),
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
