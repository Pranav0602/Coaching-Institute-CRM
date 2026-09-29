/**
 * Entry route. Decides where the app should be, and shows a branded splash while
 * the session is being restored so the first paint is never a blank screen.
 */
import { LinearGradient } from 'expo-linear-gradient';
import { Redirect } from 'expo-router';
import { GraduationCap } from 'lucide-react-native';
import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';

import { BRAND } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';

const Index = () => {
  const { status, role } = useAuth();

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
                : role === 'RECEPTIONIST'
                  ? 'reception'
                  : 'student';

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
