/**
 * Push notification registration.
 *
 * The handset's Expo push token is registered against the signed-in account so
 * the backend can target this device for fee reminders, batch changes and
 * holidays. Registration is re-run on every cold start because Expo rotates the
 * token, and the backend's register endpoint is idempotent, so a duplicate call
 * is a no-op rather than a duplicate row.
 *
 * `expo-notifications` is loaded lazily and behind a guard on purpose. Importing
 * it throws on Android in Expo Go - remote push was removed from Expo Go at SDK
 * 53 - and a throw at module scope takes down every screen that transitively
 * imports this hook. Lazy loading means Expo Go users get an honest "needs a
 * development build" answer instead of a red screen, and a development build
 * gets the real thing with no code change.
 */
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import { useCallback, useEffect, useRef, useState } from 'react';

import { devicesApi } from '@/api/domain.api';
import { APP_VERSION } from '@/constants/config';
import { useAuth } from '@/context/AuthContext';

export type PushPermission = 'unavailable' | 'needs-dev-build' | 'undetermined' | 'denied' | 'granted';

type NotificationsModule = typeof import('expo-notifications');

let cached: NotificationsModule | null | undefined;

/**
 * `undefined` = not tried yet, `null` = unavailable. Memoised so a failed attempt
 * is not retried on every render.
 */
const inExpoGo = (): boolean => {
  try {
    return Constants.appOwnership === 'expo';
  } catch {
    return false;
  }
};

/** True when the current runtime cannot host remote push at all. */
const hostUnsupported = (): boolean => Platform.OS === 'web' || (inExpoGo() && Platform.OS === 'android');

/**
 * `undefined` = not tried yet, `null` = unavailable. Memoised so a failed attempt
 * is not retried on every render.
 *
 * The `hostUnsupported()` check runs *before* the require on purpose. Merely
 * importing `expo-notifications` inside Expo Go on Android throws, and while the
 * throw is caught, Metro still paints a red error box for it. Not reaching for
 * the module at all is quieter and cheaper.
 */
const loadNotifications = (): NotificationsModule | null => {
  if (cached !== undefined) return cached;
  cached = null;
  if (hostUnsupported()) return cached;
  try {
    cached = require('expo-notifications') as NotificationsModule;
  } catch {
    cached = null;
    return cached;
  }
  // `setNotificationHandler` also throws outside a supported context.
  try {
    cached.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowBanner: true,
        shouldShowList: true,
        shouldPlaySound: false,
        shouldSetBadge: false,
      }),
    });
  } catch {
    cached = null;
  }
  return cached;
};

export const usePushRegistration = () => {
  const { user, status } = useAuth();
  const [permission, setPermission] = useState<PushPermission>('undetermined');
  const registered = useRef(false);

  const module = loadNotifications();
  const supported = module !== null;

  const readPermission = useCallback(async (): Promise<PushPermission> => {
    if (!module) return hostUnsupported() ? 'needs-dev-build' : 'unavailable';
    try {
      const current = await module.getPermissionsAsync();
      return current.status as PushPermission;
    } catch {
      return 'unavailable';
    }
  }, [module]);

  const register = useCallback(async () => {
    if (!module || !supported || !user) return;
    try {
      const existing = await module.getExpoPushTokenAsync();
      await devicesApi.register({
        expo_push_token: existing.data,
        platform: Platform.OS === 'ios' ? 'ios' : 'android',
        device_name: Device.deviceName ?? Device.osName ?? undefined,
        app_version: APP_VERSION,
      });
      registered.current = true;
    } catch {
      // A failed registration is not worth interrupting the user over; the
      // in-app notification centre still works without push.
    }
  }, [module, supported, user]);

  const requestPermission = useCallback(async () => {
    if (!module || !supported) return;
    try {
      const result = await module.requestPermissionsAsync();
      setPermission(result.status as PushPermission);
      if (result.status === 'granted') await register();
    } catch {
      setPermission('unavailable');
    }
  }, [module, register, supported]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const current = await readPermission();
      if (cancelled) return;
      setPermission(current);
      if (current === 'granted' && status === 'signed-in' && !registered.current) {
        await register();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [readPermission, register, status]);

  return { supported, permission, requestPermission, register };
};
