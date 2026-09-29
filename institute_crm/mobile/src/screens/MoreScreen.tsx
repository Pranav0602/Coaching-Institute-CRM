/**
 * Settings, reachable as the last tab of every persona shell.
 *
 * Deliberately one screen for all roles: what a user can change about their own
 * account does not depend on their job, and a single screen means a single place
 * to fix sign-out, biometrics and theme. Each persona's `more.tsx` is a one-line
 * re-export of this.
 */
import { router } from 'expo-router';
import {
  Bell,
  Fingerprint,
  LogOut,
  Moon,
  Sun,
  User as UserIcon,
} from 'lucide-react-native';
import React from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { Avatar, Button, Card, Divider, List, Switch, Text, useTheme } from 'react-native-paper';

import { Screen } from '@/components/common/Screen';
import { roleLabel } from '@/constants/roles';
import { useAuth } from '@/context/AuthContext';
import { useThemeMode } from '@/context/ThemeContext';
import { usePushRegistration } from '@/hooks/usePushRegistration';
import { initials } from '@/utils/format';

const MoreScreen = () => {
  const theme = useTheme();
  const { user, role, signOut, biometricsAvailable, biometricEnabled, setBiometricEnabled } =
    useAuth();
  const { mode, toggle } = useThemeMode();
  const { permission, requestPermission, supported } = usePushRegistration();

  const confirmSignOut = () => {
    Alert.alert(
      'Sign out?',
      'This device will stop delivering your notifications until you sign in again.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Sign out', style: 'destructive', onPress: () => void signOut() },
      ],
    );
  };

  const pushDescription = !supported
    ? permission === 'needs-dev-build'
      ? 'Needs a development build — Expo Go removed push on Android at SDK 53'
      : 'Not available in this build'
    : permission === 'granted'
      ? 'Fee reminders, batch changes and holidays'
      : permission === 'denied'
        ? 'Blocked — enable them in your device settings'
        : 'Tap Allow for fee reminders and batch updates';

  return (
    <Screen>
      <Card mode="contained" style={styles.card}>
        <Card.Content style={styles.identity}>
          <Avatar.Text size={56} label={initials(user?.full_name || user?.username)} />
          <View style={{ flex: 1 }}>
            <Text variant="titleMedium" style={styles.bold}>
              {user?.full_name || user?.username}
            </Text>
            <Text variant="bodySmall" style={styles.muted}>
              {roleLabel(role)}
              {user?.branch_name ? ` · ${user.branch_name}` : ''}
            </Text>
            <Text variant="bodySmall" style={styles.muted}>
              {user?.username}
            </Text>
          </View>
        </Card.Content>
      </Card>

      <Text variant="labelSmall" style={styles.sectionLabel}>
        ACCOUNT
      </Text>
      <Card mode="contained" style={styles.card}>
        <List.Item
          title="My profile"
          description="Name, email and phone"
          left={(props) => <List.Icon {...props} icon={UserIcon} />}
          onPress={() => router.push('/(app)/profile')}
        />
        <Divider />
        <List.Item
          title="Dark theme"
          left={(props) => <List.Icon {...props} icon={mode === 'dark' ? Moon : Sun} />}
          right={() => <Switch value={mode === 'dark'} onValueChange={toggle} />}
        />
        {biometricsAvailable ? (
          <>
            <Divider />
            <List.Item
              title="Biometric unlock"
              description="Face ID or fingerprint on launch"
              left={(props) => <List.Icon {...props} icon={Fingerprint} />}
              right={() => (
                <Switch
                  value={biometricEnabled}
                  onValueChange={(next) => void setBiometricEnabled(next)}
                />
              )}
            />
          </>
        ) : null}
      </Card>

      <Text variant="labelSmall" style={styles.sectionLabel}>
        NOTIFICATIONS
      </Text>
      <Card mode="contained" style={styles.card}>
        <List.Item
          title="Push notifications"
          description={pushDescription}
          left={(props) => <List.Icon {...props} icon={Bell} />}
          right={() =>
            supported && permission !== 'granted' && permission !== 'denied' ? (
              <Button compact onPress={() => void requestPermission()}>
                Allow
              </Button>
            ) : undefined
          }
        />
      </Card>

      <Button
        mode="outlined"
        icon={LogOut}
        onPress={confirmSignOut}
        textColor={theme.colors.error}
        style={{ marginTop: 20 }}
      >
        Sign out
      </Button>

      <View style={styles.footer}>
        <Text variant="bodySmall" style={styles.muted}>
          Graphix Techno Services CRM
        </Text>
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  card: { marginBottom: 4 },
  identity: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
  sectionLabel: { marginTop: 20, marginBottom: 8, letterSpacing: 0.8, opacity: 0.7 },
  footer: { alignItems: 'center', marginTop: 28 },
});

export default MoreScreen;
