import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useColorScheme } from 'react-native';

import { STORAGE_KEYS } from '@/constants/config';
import AsyncStorage from '@react-native-async-storage/async-storage';

type ThemeMode = 'light' | 'dark';

interface ThemeState {
  mode: ThemeMode;
  isDark: boolean;
  toggle: () => void;
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeState | null>(null);

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  const system = useColorScheme();
  const [mode, setModeState] = useState<ThemeMode>('dark');

  // Stored choice wins over the OS; the app defaults to the dark theme the brand
  // is designed around, which is also what the web CRM opens on.
  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEYS.themeMode)
      .then((stored) => {
        const next = stored === 'light' || stored === 'dark' ? stored : null;
        setModeState(next ?? (system === 'light' ? 'light' : 'dark'));
      })
      .catch(() => setModeState(system === 'light' ? 'light' : 'dark'));
  }, [system]);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    void AsyncStorage.setItem(STORAGE_KEYS.themeMode, next).catch(() => undefined);
  }, []);

  const toggle = useCallback(() => {
    setModeState((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark';
      void AsyncStorage.setItem(STORAGE_KEYS.themeMode, next).catch(() => undefined);
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ mode, isDark: mode === 'dark', toggle, setMode }),
    [mode, toggle, setMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useThemeMode = (): ThemeState => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useThemeMode must be used inside <ThemeProvider>');
  return ctx;
};
