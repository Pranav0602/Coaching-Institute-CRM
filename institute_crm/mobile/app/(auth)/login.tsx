import { LinearGradient } from 'expo-linear-gradient';
import { Eye, EyeOff, Fingerprint, GraduationCap, Lock, ServerCrash, User } from 'lucide-react-native';
import React, { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { Button, HelperText, Text, TextInput, useTheme } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ApiError, warmBackend } from '@/api/client';
import { API_BASE_URL } from '@/constants/config';
import { BRAND } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';

/** `http://10.0.2.2:8000/api/v1` -> `10.0.2.2:8000` */
const apiHost = API_BASE_URL.replace(/^https?:\/\//, '').replace(/\/api\/v1\/?$/, '');

const LoginScreen = () => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const { signIn, error, clearError, biometricsAvailable, biometricEnabled, setBiometricEnabled } =
    useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [revealPassword, setRevealPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [waking, setWaking] = useState(false);
  const [warmed, setWarmed] = useState(false);
  const [touched, setTouched] = useState(false);
  const [submitHint, setSubmitHint] = useState<string | null>(null);

  // Warm on mount: AuthContext already pings during boot, but a deep link straight
  // to /login would otherwise skip it and pay the ~50s cold start inside the spinner.
  useEffect(() => {
    let cancelled = false;
    void warmBackend().then((ok) => {
      if (!cancelled && ok) setWarmed(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const canSubmit = username.trim().length > 0 && password.length > 0 && !submitting;

  const onSubmit = async () => {
    setTouched(true);
    if (!canSubmit) return;
    setSubmitting(true);
    setSubmitHint(null);
    try {
      await signIn(username, password);
    } catch (err) {
      // `error` already carries the message to the banner; add a cold-start hint
      // for unreachable/timeout failures so "correct password, no sign-in" reads as
      // infrastructure, not credentials.
      if (err instanceof ApiError && err.isOffline) {
        setSubmitHint(
          'Could not reach the server. If it just woke from sleep, tap "Wake the server" below and retry.',
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  /**
   * A cold Render instance can take the best part of a minute to wake. Rather
   * than let the first login attempt silently eat that, the user can warm it
   * deliberately and watch the progress instead of wondering whether their tap
   * registered.
   */
  const onWarm = async () => {
    setWaking(true);
    const ok = await warmBackend();
    setWaking(false);
    setWarmed(ok);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: theme.colors.background }}
    >
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + 56, paddingBottom: insets.bottom + 24 },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        <LinearGradient
          colors={[BRAND.indigo500, BRAND.indigoDeep]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.hero}
        >
          <GraduationCap size={36} color="#fff" />
        </LinearGradient>

        <Text variant="headlineMedium" style={styles.title}>
          Graphix Techno CRM
        </Text>
        <Text
          variant="bodyMedium"
          style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}
        >
          Sign in with the username or email issued by your branch
        </Text>

        <View style={styles.form}>
          <TextInput
            mode="outlined"
            label="Username or email"
            value={username}
            onChangeText={(next) => {
              setUsername(next);
              if (error) clearError();
            }}
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="username"
            keyboardType="email-address"
            textContentType="username"
            left={<TextInput.Icon icon={User} />}
            error={touched && username.trim().length === 0}
          />

          <TextInput
            mode="outlined"
            label="Password"
            value={password}
            onChangeText={(next) => {
              setPassword(next);
              if (error) clearError();
            }}
            secureTextEntry={!revealPassword}
            autoCapitalize="none"
            autoComplete="current-password"
            textContentType="password"
            left={<TextInput.Icon icon={Lock} />}
            right={
              <TextInput.Icon
                icon={revealPassword ? EyeOff : Eye}
                onPress={() => setRevealPassword((v) => !v)}
              />
            }
            error={touched && password.length === 0}
            onSubmitEditing={onSubmit}
            returnKeyType="go"
          />
        </View>

        {error ? (
          <HelperText type="error" visible padding="none" style={{ marginTop: 8 }}>
            {error}
          </HelperText>
        ) : null}
        {submitHint ? (
          <HelperText type="info" visible padding="none" style={{ marginTop: 4 }}>
            {submitHint}
          </HelperText>
        ) : null}

        {/*
          The single most common cause of "my password is right but it will not
          sign in" is an app pointed at a different database than the one the
          credentials were created in - the app targets the Render production
          backend unless EXPO_PUBLIC_API_BASE_URL (or extra.apiBaseUrl) says
          otherwise. Showing the host makes a mismatch obvious without needing
          the Metro logs.
        */}
        <View style={styles.hostRow}>
          <Text variant="labelSmall" style={styles.hostLabel}>
            API
          </Text>
          <Text variant="labelSmall" style={styles.host} numberOfLines={1}>
            {apiHost}
          </Text>
        </View>

        {biometricsAvailable ? (
          <Button
            mode={biometricEnabled ? 'contained-tonal' : 'text'}
            icon={Fingerprint}
            onPress={() => setBiometricEnabled(!biometricEnabled)}
            style={{ marginTop: 12, alignSelf: 'center' }}
          >
            {biometricEnabled ? 'Biometric unlock on' : 'Enable biometric unlock'}
          </Button>
        ) : null}

        <Button
          mode="contained"
          onPress={onSubmit}
          loading={submitting}
          disabled={!canSubmit}
          style={{ marginTop: 20 }}
          contentStyle={styles.primaryCta}
          labelStyle={styles.ctaLabel}
        >
          Sign in
        </Button>

        {warmed ? (
          <HelperText type="info" visible padding="none" style={{ textAlign: 'center' }}>
            Server is awake — signing in should be quick now.
          </HelperText>
        ) : (
          <Button
            mode="text"
            icon={ServerCrash}
            onPress={onWarm}
            loading={waking}
            style={{ marginTop: 8 }}
          >
            {waking ? 'Waking the server…' : 'Signing in is slow? Wake the server'}
          </Button>
        )}

        <View style={styles.footer}>
          <Text
            variant="bodySmall"
            style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}
          >
            Trouble signing in? Ask your branch administrator to reset your password.
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  content: { paddingHorizontal: 24, flexGrow: 1 },
  hero: {
    width: 76,
    height: 76,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    marginBottom: 20,
  },
  title: { fontWeight: '800', textAlign: 'center' },
  form: { gap: 12, marginTop: 28 },
  hostRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 12, alignSelf: 'center' },
  hostLabel: { opacity: 0.5, letterSpacing: 0.8 },
  host: { opacity: 0.8 },
  primaryCta: { height: 50 },
  ctaLabel: { fontWeight: '700' },
  footer: { marginTop: 'auto', paddingTop: 32 },
});

export default LoginScreen;
