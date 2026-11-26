import { Redirect, Stack } from 'expo-router';
import React from 'react';
import { useTheme } from 'react-native-paper';

import { useAuth } from '@/context/AuthContext';

const AuthLayout = () => {
  const theme = useTheme();
  const { status } = useAuth();

  // Once sign-in commits a session there is no screen under (auth) that should
  // stay mounted. Without this guard a successful login left the user sitting
  // on /login with no error and no dashboard, because the boot-time <Redirect>
  // in app/index.tsx had already unmounted.
  if (status === 'signed-in') return <Redirect href="/" />;

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: theme.colors.background },
        animation: 'fade',
      }}
    />
  );
};

export default AuthLayout;
