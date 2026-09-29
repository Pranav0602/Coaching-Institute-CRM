import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import { ArrowLeft, KeyRound, Lock, Mail, Phone, User } from 'lucide-react-native';
import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { Avatar, Button, Card, HelperText, Text, TextInput, useTheme } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { InfoRow } from '@/components/common/Primitives';
import { ApiError, authApi } from '@/api/client';
import { accountsApi } from '@/api/domain.api';
import { roleLabel } from '@/constants/roles';
import { useAuth } from '@/context/AuthContext';
import { initials } from '@/utils/format';

const ProfileScreen = () => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const { user, refreshUser, signOut } = useAuth();

  const [firstName, setFirstName] = useState(user?.first_name ?? '');
  const [lastName, setLastName] = useState(user?.last_name ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [phone, setPhone] = useState(user?.phone ?? '');
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () =>
      accountsApi.updateProfile({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        phone: phone.trim(),
      }),
    onSuccess: async () => {
      await refreshUser();
      setError(null);
      setSaved(true);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not save your profile.'),
  });

  const changePassword = useMutation({
    mutationFn: () => authApi.changePassword(oldPassword, newPassword),
    onSuccess: () => {
      setPasswordError(null);
      setOldPassword('');
      setNewPassword('');
      // The backend leaves the current access token valid but requires a fresh
      // sign-in, so honour that instead of pretending the change is invisible.
      setSaved(true);
    },
    onError: (err) =>
      setPasswordError(err instanceof ApiError ? err.message : 'Could not change your password.'),
  });

  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const profileDirty =
    firstName !== (user?.first_name ?? '') ||
    lastName !== (user?.last_name ?? '') ||
    email !== (user?.email ?? '') ||
    phone !== (user?.phone ?? '');

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: theme.colors.background }}
    >
      <View style={[styles.header, { paddingTop: insets.top + 8, borderBottomColor: theme.colors.outlineVariant }]}>
        <Button icon={ArrowLeft} onPress={() => router.back()} style={styles.back}>
          Back
        </Button>
        <Text variant="titleMedium" style={styles.headerTitle}>
          My profile
        </Text>
        <View style={{ width: 72 }} />
      </View>

      <ScrollView
        contentContainerStyle={[styles.body, { paddingBottom: insets.bottom + 32 }]}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.identity}>
          <Avatar.Text size={72} label={initials(user?.full_name || user?.username)} />
          <View>
            <Text variant="titleMedium" style={styles.bold}>
              {user?.full_name || user?.username}
            </Text>
            <Text variant="bodySmall" style={styles.muted}>
              {roleLabel(user?.role_code)}
              {user?.branch_name ? ` · ${user.branch_name}` : ''}
            </Text>
          </View>
        </View>

        <Card mode="contained" style={{ backgroundColor: theme.colors.surface }}>
          <Card.Content style={{ gap: 4 }}>
            <InfoRow label="Username" value={user?.username} icon={<User size={14} />} />
            <InfoRow label="Role" value={roleLabel(user?.role_code)} />
            <InfoRow label="Branch" value={user?.branch_name ?? 'Not assigned'} />
            <InfoRow label="Member since" value={user?.date_joined?.slice(0, 10) ?? '—'} />
          </Card.Content>
        </Card>

        <Text variant="labelSmall" style={styles.sectionLabel}>
          DETAILS
        </Text>
        <View style={{ gap: 12 }}>
          <TextInput mode="outlined" label="First name" value={firstName} onChangeText={setFirstName} autoCapitalize="words" />
          <TextInput mode="outlined" label="Last name" value={lastName} onChangeText={setLastName} autoCapitalize="words" />
          <TextInput
            mode="outlined"
            label="Email"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            left={<TextInput.Icon icon={Mail} />}
            error={email.length > 0 && !emailValid}
          />
          <TextInput
            mode="outlined"
            label="Phone"
            value={phone}
            onChangeText={setPhone}
            keyboardType="phone-pad"
            left={<TextInput.Icon icon={Phone} />}
          />
        </View>

        {error ? (
          <HelperText type="error" visible>
            {error}
          </HelperText>
        ) : null}

        <Button
          mode="contained"
          disabled={!profileDirty || !emailValid || save.isPending}
          loading={save.isPending}
          onPress={() => save.mutate()}
          contentStyle={{ height: 48 }}
        >
          Save changes
        </Button>

        <Text variant="labelSmall" style={styles.sectionLabel}>
          PASSWORD
        </Text>
        <View style={{ gap: 12 }}>
          <TextInput
            mode="outlined"
            label="Current password"
            value={oldPassword}
            onChangeText={setOldPassword}
            secureTextEntry
            autoCapitalize="none"
            left={<TextInput.Icon icon={Lock} />}
          />
          <TextInput
            mode="outlined"
            label="New password"
            value={newPassword}
            onChangeText={setNewPassword}
            secureTextEntry
            autoCapitalize="none"
            left={<TextInput.Icon icon={KeyRound} />}
          />
        </View>

        {passwordError ? (
          <HelperText type="error" visible>
            {passwordError}
          </HelperText>
        ) : null}

        <Button
          mode="outlined"
          disabled={!oldPassword || newPassword.length < 8}
          loading={changePassword.isPending}
          onPress={() => changePassword.mutate()}
        >
          Change password
        </Button>
        <Text variant="bodySmall" style={styles.muted}>
          Changing your password signs you out on every device, including this one.
        </Text>

        {saved ? (
          <HelperText type="info" visible>
            {newPassword ? 'Password changed. Please sign in again.' : 'Profile updated.'}
          </HelperText>
        ) : null}

        <Button
          mode="text"
          textColor={theme.colors.error}
          onPress={() => {
            void signOut();
            router.dismissAll();
          }}
        >
          Sign out of this device
        </Button>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 8,
    paddingBottom: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  back: { marginLeft: -12 },
  headerTitle: { fontWeight: '800', flex: 1, textAlign: 'center' },
  body: { padding: 16, gap: 12 },
  identity: { flexDirection: 'row', alignItems: 'center', gap: 16, marginBottom: 4 },
  sectionLabel: { marginTop: 16, letterSpacing: 0.8, opacity: 0.7 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default ProfileScreen;
