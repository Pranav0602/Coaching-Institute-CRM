import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const ROLES = {
  SUPER_ADMIN: 'SUPER_ADMIN',
  BRANCH_ADMIN: 'BRANCH_ADMIN',
  ADMISSION_COUNSELOR: 'ADMISSION_COUNSELOR',
  TEACHER: 'TEACHER',
  STUDENT: 'STUDENT',
  PARENT: 'PARENT',
  ACCOUNTANT: 'ACCOUNTANT',
  RECEPTIONIST: 'RECEPTIONIST',
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [activeRole, setActiveRole] = useState(() => {
    const savedRole = localStorage.getItem('active_role');
    return savedRole || (user?.role_code || ROLES.SUPER_ADMIN);
  });
  const [themeMode, setThemeMode] = useState('dark');

  // The server-assigned role is authoritative. Keep activeRole mirrored to it
  // so no stale/testing role can linger after login or page reload.
  useEffect(() => {
    const serverRole = user?.role_code;
    if (serverRole && serverRole !== activeRole) {
      setActiveRole(serverRole);
      localStorage.setItem('active_role', serverRole);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.role_code]);

  const toggleTheme = () => {
    setThemeMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const login = async (username, password) => {
    try {
      // 60s timeout (not the global 15s): on a cold Render instance the first
      // request boots the container (~30-50s). Failing fast here would turn
      // every cold start into a false "login failed".
      const res = await api.post('/accounts/auth/login/', { username, password }, { timeout: 60000 });
      const userData = res.data.user;
      const accessToken = res.data.access;

      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('active_role', userData.role_code || ROLES.SUPER_ADMIN);

      setUser(userData);
      setActiveRole(userData.role_code || ROLES.SUPER_ADMIN);
      return { success: true };
    } catch (err) {
      // No silent demo fallback: signing in with a mock token masks real outages
      // (and diverges from the mobile app, which correctly surfaces the error),
      // so an unreachable API is reported as a failure with the backend URL.
      // Auth failures propagate with the server message.
      const message =
        err?.detail ||
        err?.message ||
        err?.errors?.detail?.[0] ||
        'Invalid credentials. Please check username and password.';
      return { success: false, error: message, detail: err };
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    localStorage.removeItem('active_role');
    setUser(null);
  };

  const switchRole = (newRole) => {
    // Deprecated testing hook: retained only so older imports don't crash.
    // Production UI no longer exposes role switching; the server role wins.
    if (process.env.NODE_ENV !== 'production') {
      console.warn('[AuthContext] switchRole() is deprecated and has no effect in production.');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        activeRole,
        login,
        logout,
        switchRole,
        themeMode,
        toggleTheme,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
