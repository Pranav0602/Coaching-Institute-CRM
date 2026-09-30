/**
 * Session state for the whole app.
 *
 * Three things live here that a plain token check would not cover:
 *
 *  1. Boot. On a cold start there is no in-memory session, so the stored one is
 *     read back and re-validated against `/auth/me/` before the UI commits to
 *     showing the app. Without that, a user whose account was deactivated sees a
 *     fully rendered (and empty) dashboard for a beat before every request 401s.
 *  2. Biometric unlock. Tokens stay in the Keychain/Keystore; the biometric prompt
 *     is what stands between a shoulder-surfer and the session, so a returning user
 *     can re-enter the app without re-typing a password.
 *  3. Cold-start warming. The health ping is fired here, not in a component, so it
 *     overlaps the user's typing instead of trailing their first request.
 */
import * as LocalAuthentication from 'expo-local-authentication';
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Platform } from 'react-native';

import { ApiError, authApi, clearSession, onSessionEvents, warmBackend } from '@/api/client';
import { biometricStore, sessionStore, tokens } from '@/api/storage';
import { accessExpiry } from '@/api/storage';
import { isKnownRole, type Role } from '@/constants/roles';
import type { SessionUser } from '@/types';

export type AuthStatus = 'loading' | 'signed-out' | 'signed-in';

interface AuthState {
  status: AuthStatus;
  user: SessionUser | null;
  role: Role | null;
  error: string | null;
  /** True while a biometric prompt is on screen. */
  unlocking: boolean;
  biometricsAvailable: boolean;
  biometricEnabled: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
  unlockWithBiometrics: () => Promise<boolean>;
  setBiometricEnabled: (enabled: boolean) => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const describeError = (error: unknown): string => {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'Something went wrong. Please try again.';
};

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<SessionUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState(false);
  const [biometricsAvailable, setBiometricsAvailable] = useState(false);
  const [biometricEnabled, setBiometricEnabledState] = useState(false);
  const mounted = useRef(true);

  /**
   * Bumped by every deliberate session change (sign in, sign out, forced
   * sign-out). The boot sequence captures it and refuses to write any status
   * once it has moved, so a sign-in that lands mid-boot is not clobbered by a
   * slower boot pass deciding there was no session.
   */
  const sessionIntent = useRef(0);

  useEffect(() => () => {
    mounted.current = false;
  }, []);

  // ------------------------------------------------------------ session events

  useEffect(
    () =>
      onSessionEvents({
        onSignedOut: () => {
          if (!mounted.current) return;
          sessionIntent.current += 1;
          setUser(null);
          setStatus('signed-out');
        },
      }),
    [],
  );

  // --------------------------------------------------------------------- boot

  useEffect(() => {
    let cancelled = false;
    const intentAtStart = sessionIntent.current;
    /** True once the user has taken over, so this pass must not decide anything. */
    const superseded = () => cancelled || sessionIntent.current !== intentAtStart;

    (async () => {
      // Fire and forget: overlap with the splash rather than block it.
      void warmBackend();

      // Each read is settled independently. A bare `Promise.all` would reject
      // wholesale on the first failure and leave the user staring at
      // "Restoring your session..." forever, which is exactly what a
      // native-module problem looks like from the inside.
      const [cached, refresh, hasBiometrics, enrolled] = await Promise.all([
        sessionStore.get().catch(() => null),
        tokens.getRefresh().catch(() => null),
        biometricStore.get().catch(() => false),
        LocalAuthentication.hasHardwareAsync().catch(() => false),
      ]);
      if (superseded()) return;
      setBiometricEnabledState(hasBiometrics);

      // Desktop and simulator builds report no hardware; never offer the toggle.
      const usable =
        enrolled && Platform.OS !== 'web' && (await LocalAuthentication.isEnrolledAsync().catch(() => false));
      if (superseded()) return;
      setBiometricsAvailable(usable);

      if (!refresh || !cached) {
        setStatus('signed-out');
        return;
      }

      // A biometric lock is opt-in per device. When it is on, the app comes back
      // locked and the shell renders the unlock screen instead of the dashboard.
      if (hasBiometrics && usable) {
        setUser(cached);
        setStatus('signed-in');
        setUnlocking(true);
        return;
      }

      // Validate against the server so a revoked or deactivated account does not
      // get a rendered-but-empty app.
      try {
        const fresh = await authApi.me();
        if (superseded()) return;
        const merged = { ...cached, ...fresh };
        setUser(merged);
        await sessionStore.set(merged);
        setStatus('signed-in');
      } catch (err) {
        if (superseded()) return;
        if (err instanceof ApiError && err.isAuth) {
          await clearSession();
          setStatus('signed-out');
          return;
        }
        // A network failure is not proof the session is dead. Keep the cached user
        // so the app opens into its offline cache instead of a login wall.
        setUser(cached);
        setStatus('signed-in');
      }
    })();

    return () => {
      cancelled = true;
    };
    // Intentionally empty. This sequence must run exactly once: re-running it
    // re-decides the session status, which is what raced against sign-in.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ----------------------------------------------------------------- actions

  const signIn = useCallback(async (username: string, password: string) => {
    setError(null);
    // Claim the session before awaiting anything, so an in-flight boot pass can no
    // longer downgrade this attempt.
    sessionIntent.current += 1;
    try {
      const result = await authApi.login(username.trim(), password);

      if (!result?.access || !result?.user) {
        throw new Error(
          'The server accepted the sign-in but returned no session. Check that the API base URL points at this backend.',
        );
      }

      await tokens.set(result.access, result.refresh);
      if (typeof result.access_expires_in === 'number' && result.access_expires_in > 0) {
        await accessExpiry.set(Date.now() + result.access_expires_in * 1000);
      } else {
        await accessExpiry.clear();
      }
      await sessionStore.set(result.user);

      // Read the token back. A secure-storage write that silently fails produces
      // exactly the "correct password, no sign-in" symptom, and the failure is
      // only visible here - committing state optimistically would bounce the user
      // back to this screen with no explanation.
      const persisted = await tokens.getAccess();
      if (persisted !== result.access) {
        throw new Error(
          'Signed in, but this device could not store the session securely. Restart the app and try again.',
        );
      }

      setUser(result.user);
      setStatus('signed-in');
    } catch (err) {
      const message = describeError(err);
      setError(message);
      throw err;
    }
  }, []);

  const signOut = useCallback(async () => {
    sessionIntent.current += 1;
    // Stop this handset delivering the outgoing user's alerts before dropping the
    // tokens, otherwise a shared device keeps buzzing with their reminders.
    const { devicesApi } = await import('@/api/domain.api');
    await devicesApi.unregisterAll().catch(() => undefined);
    await authApi.logout(await tokens.getRefresh()).catch(() => undefined);
    await clearSession();
    setUser(null);
    setStatus('signed-out');
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const fresh = await authApi.me();
      setUser((prev) => (prev ? { ...prev, ...fresh } : fresh));
      await sessionStore.set(fresh);
    } catch (err) {
      if (err instanceof ApiError && err.isAuth) {
        await clearSession();
        setUser(null);
        setStatus('signed-out');
      }
    }
  }, []);

  const unlockWithBiometrics = useCallback(async () => {
    if (!biometricsAvailable) {
      setUnlocking(false);
      return true;
    }
    setUnlocking(true);
    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Unlock Graphix CRM',
        cancelLabel: 'Use password',
        disableDeviceFallback: false,
      });
      if (!result.success) return false;

      // Unlocking proves presence, not validity. Re-check the session so a revoked
      // account cannot hide behind a successful fingerprint match.
      try {
        const fresh = await authApi.me();
        const merged = { ...(user ?? {}), ...fresh } as SessionUser;
        setUser(merged);
        await sessionStore.set(merged);
      } catch (err) {
        if (err instanceof ApiError && err.isAuth) {
          await clearSession();
          setUser(null);
          setStatus('signed-out');
          return false;
        }
      }
      return true;
    } catch {
      return false;
    } finally {
      if (mounted.current) setUnlocking(false);
    }
  }, [biometricsAvailable, user]);

  const setBiometricEnabled = useCallback(
    async (enabled: boolean) => {
      if (enabled && biometricsAvailable) {
        const result = await LocalAuthentication.authenticateAsync({
          promptMessage: 'Confirm to enable biometric unlock',
        });
        if (!result.success) return;
      }
      await biometricStore.set(enabled);
      setBiometricEnabledState(enabled);
    },
    [biometricsAvailable],
  );

  const value = useMemo<AuthState>(
    () => ({
      status,
      user,
      role: isKnownRole(user?.role_code) ? user.role_code : null,
      error,
      unlocking,
      biometricsAvailable,
      biometricEnabled,
      signIn,
      signOut,
      refreshUser,
      unlockWithBiometrics,
      setBiometricEnabled,
      clearError: () => setError(null),
    }),
    [
      status,
      user,
      error,
      unlocking,
      biometricsAvailable,
      biometricEnabled,
      signIn,
      signOut,
      refreshUser,
      unlockWithBiometrics,
      setBiometricEnabled,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthState => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
};
