/**
 * Native storage for the session.
 *
 * `expo-secure-store` is hardware-backed (iOS Keychain / Android Keystore), so
 * the refresh token never lands in AsyncStorage alongside the cache. That split
 * matters: a cache can be dumped from a device backup, a Keychain entry cannot.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import { STORAGE_KEYS } from '@/constants/config';
import type { SessionUser } from '@/types';

const cache = new Map<string, string | null>();

/** SecureStore keys are restricted to alphanumerics, `.`, `-` and `_`. */
const secureKey = (key: string) => key.replace(/[^A-Za-z0-9._-]/g, '_');

const secureGet = async (key: string): Promise<string | null> => {
  if (Platform.OS === 'web') {
    // Keychain is unavailable in browsers. Persist to AsyncStorage (localStorage)
    // so a web reload keeps the session; the in-memory map is a fast path only.
    // Never ship tokens this way to production web.
    const cached = cache.get(key);
    if (cached !== undefined) return cached;
    try {
      const stored = await AsyncStorage.getItem(key);
      cache.set(key, stored);
      return stored;
    } catch {
      return cache.get(key) ?? null;
    }
  }
  return SecureStore.getItemAsync(secureKey(key));
};

const secureSet = async (key: string, value: string | null) => {
  cache.set(key, value);
  if (Platform.OS === 'web') {
    try {
      if (value === null) await AsyncStorage.removeItem(key);
      else await AsyncStorage.setItem(key, value);
    } catch {
      // In-memory cache already updated; persistence is best-effort on web.
    }
    return;
  }
  if (value === null) await SecureStore.deleteItemAsync(secureKey(key));
  else await SecureStore.setItemAsync(secureKey(key), value);
};

// ------------------------------------------------------------------ tokens

export const tokens = {
  getAccess: () => secureGet(STORAGE_KEYS.accessToken),
  getRefresh: () => secureGet(STORAGE_KEYS.refreshToken),

  async set(access: string, refresh: string) {
    await Promise.all([
      secureSet(STORAGE_KEYS.accessToken, access),
      secureSet(STORAGE_KEYS.refreshToken, refresh),
    ]);
  },

  /**
   * Persist a rotated pair. Rotation retires the old refresh token server-side,
   * so failing to write the new one would sign the user out on the next call.
   */
  async rotate(access: string, refresh?: string | null) {
    const current = refresh ?? (await this.getRefresh());
    if (current) await secureSet(STORAGE_KEYS.refreshToken, current);
    await secureSet(STORAGE_KEYS.accessToken, access);
  },

  clear: () =>
    Promise.all([
      secureSet(STORAGE_KEYS.accessToken, null),
      secureSet(STORAGE_KEYS.refreshToken, null),
      safeRemove(STORAGE_KEYS.accessExpiresAt),
    ]),
};

/**
 * Reads never reject. A cache is an optimisation; if it cannot be read the app
 * should fall back to "no cache" and carry on, not fail the boot sequence. This
 * matters because `Promise.all` over these reads in `AuthContext` would otherwise
 * reject wholesale and strand the user on the splash screen.
 */
const safeGet = async (key: string): Promise<string | null> => {
  try {
    return await AsyncStorage.getItem(key);
  } catch {
    return null;
  }
};

const safeSet = async (key: string, value: string): Promise<void> => {
  try {
    await AsyncStorage.setItem(key, value);
  } catch {
    // Nothing actionable; the value is a cache or a preference.
  }
};

const safeRemove = async (key: string): Promise<void> => {
  try {
    await AsyncStorage.removeItem(key);
  } catch {
    // As above.
  }
};

export const accessExpiry = {
  get: async (): Promise<number | null> => {
    const raw = await safeGet(STORAGE_KEYS.accessExpiresAt);
    return raw ? Number(raw) : null;
  },
  set: (epochMs: number) => safeSet(STORAGE_KEYS.accessExpiresAt, String(epochMs)),
  clear: () => safeRemove(STORAGE_KEYS.accessExpiresAt),
};

// ------------------------------------------------------------ session user

export const sessionStore = {
  get: async (): Promise<SessionUser | null> => {
    const raw = await safeGet(STORAGE_KEYS.sessionUser);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as SessionUser;
    } catch {
      return null;
    }
  },
  set: (user: SessionUser) => safeSet(STORAGE_KEYS.sessionUser, JSON.stringify(user)),
  clear: () => safeRemove(STORAGE_KEYS.sessionUser),
};

// --------------------------------------------------------------- biometrics

export const biometricStore = {
  get: async (): Promise<boolean> => (await safeGet(STORAGE_KEYS.biometricEnabled)) === 'true',
  set: (enabled: boolean) => safeSet(STORAGE_KEYS.biometricEnabled, String(enabled)),
};
