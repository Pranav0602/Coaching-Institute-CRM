import { useEffect, useRef, useState } from 'react';
import * as Network from 'expo-network';

/**
 * Debounce a rapidly-changing value. Used by every search field so a 9-key
 * course query does not fire nine round trips.
 */
export const useDebounced = <T,>(value: T, delay = 350): T => {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
};

/**
 * Connectivity, polled rather than event-driven because `expo-network` has no
 * subscription API. Drives the offline banner; queries still go through
 * TanStack Query's own cache.
 */
export const useNetworkStatus = (pollMs = 10_000) => {
  const [isOnline, setIsOnline] = useState(true);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    const check = async () => {
      try {
        const state = await Network.getNetworkStateAsync();
        if (mounted.current) setIsOnline(state.isInternetReachable !== false && !!state.isConnected);
      } catch {
        // Assume online: a failure to *read* the state is not evidence of being
        // offline, and showing a false "no connection" banner is worse than
        // letting the request fail on its own.
      }
    };
    void check();
    const timer = setInterval(check, pollMs);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, [pollMs]);

  return isOnline;
};

/** Track an async loader so a screen can render loading, error and data states. */
export const useAsync = <T,>(loader: () => Promise<T>, deps: unknown[] = []) => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadIndex, setReloadIndex] = useState(0);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    loader()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Could not load this data.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadIndex]);

  return {
    data,
    loading,
    error,
    reload: () => setReloadIndex((i) => i + 1),
    setData,
  };
};
