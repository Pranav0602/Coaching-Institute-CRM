import { Stack } from 'expo-router';
import React from 'react';
import { useTheme } from 'react-native-paper';

const AuthLayout = () => {
  const theme = useTheme();
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
