import { ArrowLeft, KeyRound, MailCheck, ShieldCheck } from 'lucide-react-native';
import { router } from 'expo-router';
import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { Button, HelperText, Text, TextInput, useTheme } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ApiError, authApi } from '@/api/client';

const ForgotPasswordScreen = () => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();

  const [step, setStep] = useState<0 | 1>(0);
  const [identifier, setIdentifier] = useState('');
  const [otp, setOtp] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [demoOtp, setDemoOtp] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const requestCode = async () => {
    if (!identifier.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await authApi.forgotPassword(identifier.trim());
      setDemoOtp(res.demo_otp ?? null);
      setStep(1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not send the reset code.');
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    if (password.length < 8) {
      setError('Choose a password of at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('The two passwords do not match.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await authApi.resetPassword(identifier.trim(), otp.trim(), password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reset your password.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: theme.colors.background }}
    >
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + 24, paddingBottom: insets.bottom + 24 },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        <Button icon={ArrowLeft} onPress={() => router.back()} style={styles.back}>
          Back
        </Button>

        <View style={styles.hero}>
          <KeyRound size={28} color={theme.colors.primary} />
        </View>

        <Text variant="headlineSmall" style={styles.title}>
          Reset your password
        </Text>

        {done ? (
          <View style={styles.doneCard}>
            <ShieldCheck size={22} color={theme.colors.secondary} />
            <Text variant="bodyMedium" style={{ marginTop: 8 }}>
              Your password has been reset. Sign in with the new one.
            </Text>
            <Button mode="contained" onPress={() => router.replace('/login')} style={{ marginTop: 16 }}>
              Go to sign in
            </Button>
          </View>
        ) : step === 0 ? (
          <>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              Enter the username or email on your account and we will send a verification code.
            </Text>
            <TextInput
              mode="outlined"
              label="Username or email"
              value={identifier}
              onChangeText={setIdentifier}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              left={<TextInput.Icon icon={MailCheck} />}
              style={{ marginTop: 20 }}
            />
            <Button
              mode="contained"
              onPress={requestCode}
              loading={busy}
              disabled={!identifier.trim()}
              style={{ marginTop: 16 }}
            >
              Send code
            </Button>
          </>
        ) : (
          <>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              Enter the code sent to <Text style={{ fontWeight: '700' }}>{identifier}</Text>.
            </Text>
            {demoOtp ? (
              <HelperText type="info" visible>
                Development mode — your code is {demoOtp}
              </HelperText>
            ) : null}

            <TextInput
              mode="outlined"
              label="Verification code"
              value={otp}
              onChangeText={setOtp}
              keyboardType="number-pad"
              style={{ marginTop: 12 }}
            />
            <TextInput
              mode="outlined"
              label="New password"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoCapitalize="none"
              style={{ marginTop: 12 }}
            />
            <TextInput
              mode="outlined"
              label="Confirm new password"
              value={confirm}
              onChangeText={setConfirm}
              secureTextEntry
              autoCapitalize="none"
              style={{ marginTop: 12 }}
            />
            <Button
              mode="contained"
              onPress={reset}
              loading={busy}
              disabled={!otp.trim() || password.length < 8}
              style={{ marginTop: 16 }}
            >
              Set new password
            </Button>
          </>
        )}

        {error ? (
          <HelperText type="error" visible padding="none" style={{ marginTop: 12 }}>
            {error}
          </HelperText>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  content: { paddingHorizontal: 24, flexGrow: 1 },
  back: { alignSelf: 'flex-start', marginLeft: -12 },
  hero: { alignSelf: 'center', marginBottom: 16 },
  title: { fontWeight: '800', marginBottom: 8 },
  doneCard: { marginTop: 24, alignItems: 'center' },
});

export default ForgotPasswordScreen;
