/**
 * Entry route. Decides where the app should be, and shows a branded splash while
 * the session is being restored so the first paint is never a blank screen.
 */
import { LinearGradient } from 'expo-linear-gradient';
import { Redirect } from 'expo-router';
import { GraduationCap } from 'lucide-react-native';
import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { Button, Text } from 'react-native-paper';

import { BRAND } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';

const Index = () => {
  const { status, role, user, signOut } = useAuth();

  if (status === 'loading') {
    return (
      <View style={styles.splash}>
        <LinearGradient
          colors={[BRAND.indigo500, BRAND.indigoDeep]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.logo}
        >
          <GraduationCap size={40} color="#fff" />
        </LinearGradient>
        <Text variant="titleLarge" style={styles.brand}>
          Graphix Techno Services
        </Text>
        <ActivityIndicator style={{ marginTop: 24 }} color={BRAND.emerald500} />
      </View>
    );
  }

  if (status === 'signed-out') return <Redirect href="/login" />;

  // A signed-in session without a known server role must not silently land in the
  // student shell (empty timetables/fees look like "login worked but dashboard is
  // broken"). Park here with a sign-out instead so the account can be fixed
  // server-side (User.role is nullable; seed or assign a role).
  if (!role) {
    return (
      <View style={styles.splash}>
        <Text variant="titleMedium" style={styles.brand}>
          Account setup incomplete
        </Text>
        <Text style={{ color: BRAND.slate400, textAlign: 'center', marginTop: 8 }}>
          {`Signed in as ${user?.username ?? 'unknown'}, but no role is assigned to this account. Ask your branch administrator to assign a role, then sign in again.`}
        </Text>
        <Button mode="contained" onPress={() => signOut()} style={{ marginTop: 20 }}>
          Sign out
        </Button>
      </View>
    );
  }

  // Both admin roles share one shell, so the redirect is by persona not by role.
  const persona =
    role === 'SUPER_ADMIN' || role === 'BRANCH_ADMIN'
      ? 'admin'
      : role === 'ADMISSION_COUNSELOR'
        ? 'counsellor'
        : role === 'TEACHER'
          ? 'teacher'
          : role === 'STUDENT'
            ? 'student'
            : role === 'PARENT'
              ? 'parent'
              : role === 'ACCOUNTANT'
                ? 'accountant'
                : 'reception';

  return <Redirect href={`/(app)/${persona}`} />;
};

const styles = StyleSheet.create({
  splash: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: BRAND.slate900 },
  logo: {
    width: 88,
    height: 88,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  brand: { color: BRAND.slate50, fontWeight: '800' },
});

export default Index;
