/**
 * Post-login shell.
 *
 * Three states, in order of precedence:
 *   1. still restoring the session  -> splash,
 *   2. no session                   -> redirect to /login,
 *   3. session + biometric lock on  -> unlock prompt.
 *
 * Only then does the persona stack mount. The persona directory is chosen from
 * the *server* role, never from anything the client stored, so a stale or edited
 * local preference cannot widen what a user can reach.
 */
import { Redirect, Stack } from 'expo-router';
import React, { useEffect, useRef } from 'react';
import { View } from 'react-native';
import { Button, Text, useTheme } from 'react-native-paper';

import { ScreenLoader } from '@/components/common/Screen';
import { useAuth } from '@/context/AuthContext';

const UnlockGate = () => {
  const theme = useTheme();
  const { unlockWithBiometrics, unlocking, signOut, user } = useAuth();
  const attempted = useRef(false);

  // Offer the prompt once on arrival; after that it is a deliberate tap, so a
  // user who dismissed it is not trapped in a loop.
  useEffect(() => {
    if (attempted.current) return;
    attempted.current = true;
    void unlockWithBiometrics();
  }, [unlockWithBiometrics]);

  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 16 }}>
      <Text variant="headlineSmall" style={{ fontWeight: '800', textAlign: 'center' }}>
        Welcome back{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
      </Text>
      <Text
        variant="bodyMedium"
        style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}
      >
        Unlock Graphix CRM with Face ID or your fingerprint to continue.
      </Text>
      <Button
        mode="contained"
        onPress={() => unlockWithBiometrics()}
        loading={unlocking}
        style={{ marginTop: 8 }}
      >
        Unlock
      </Button>
      <Button mode="text" onPress={() => signOut()}>
        Sign out instead
      </Button>
    </View>
  );
};

const AppLayout = () => {
  const theme = useTheme();
  const { status, role, biometricEnabled, unlocking } = useAuth();

  if (status === 'loading') return <ScreenLoader label="Restoring your session…" />;
  if (status === 'signed-out') return <Redirect href="/login" />;
  if (biometricEnabled && unlocking) return <UnlockGate />;

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: theme.colors.background },
        animation: 'fade',
      }}
    >
      <Stack.Screen name="counsellor" />
      <Stack.Screen name="teacher" />
      <Stack.Screen name="student" />
      <Stack.Screen name="parent" />
      <Stack.Screen name="admin" />
      <Stack.Screen name="accountant" />
      <Stack.Screen name="reception" />
    </Stack>
  );
};

export default AppLayout;
