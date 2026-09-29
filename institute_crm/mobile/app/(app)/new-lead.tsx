/**
 * Quick lead capture.
 *
 * A walk-in is standing in front of the counter, so the form is short by design:
 * name, phone and a course are enough to save it, and everything else can be
 * filled in from the lead detail screen afterwards. Branch is pre-selected from
 * the signed-in user and, for a non-global user, is not editable - the backend
 * would reject a cross-branch write anyway, so the UI does not pretend otherwise.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { ChevronDown } from 'lucide-react-native';
import React, { useMemo, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { Button, HelperText, Menu, Text, TextInput, useTheme } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ApiError } from '@/api/client';
import { coursesApi, leadsApi } from '@/api/domain.api';
import { ROLES } from '@/constants/roles';
import { useAuth } from '@/context/AuthContext';

const NewLeadScreen = () => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [courseId, setCourseId] = useState<string | null>(null);
  const [targetCourse, setTargetCourse] = useState('');
  const [notes, setNotes] = useState('');
  const [menuVisible, setMenuVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const courses = useQuery({ queryKey: ['courses'], queryFn: () => coursesApi.list() });
  const options = useQuery({ queryKey: ['public-options'], queryFn: () => leadsApi.publicOptions() });

  const canChooseBranch = user?.role === ROLES.SUPER_ADMIN;
  const branches = options.data?.branches ?? [];
  const [branchId, setBranchId] = useState<string | null>(user?.branch ?? null);
  const [branchMenuVisible, setBranchMenuVisible] = useState(false);

  const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const phoneDigits = phone.replace(/\D/g, '');
  const phoneValid = phoneDigits.length >= 10 && phoneDigits.length <= 15;
  const nameValid = name.trim().length >= 2;
  const branchValid = !!branchId;

  const create = useMutation({
    mutationFn: () =>
      leadsApi.create({
        name: name.trim(),
        phone: phone.trim(),
        email: email.trim(),
        branch: branchId as string,
        course: courseId,
        target_course: targetCourse.trim() || course?.title || 'General',
        source: 'WALK_IN',
        stage: 'New',
        notes: notes.trim(),
      }),
    onSuccess: () => {
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      void queryClient.invalidateQueries({ queryKey: ['leads'] });
      router.back();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not save this lead.'),
  });

  const canSubmit = nameValid && phoneValid && branchValid && !create.isPending;

  const course = useMemo(
    () => courses.data?.find((c) => c.id === courseId) ?? null,
    [courseId, courses.data],
  );

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: theme.colors.background }}
    >
      <ScrollView
        contentContainerStyle={[styles.content, { paddingTop: insets.top + 16, paddingBottom: insets.bottom + 32 }]}
        keyboardShouldPersistTaps="handled"
      >
        <Text variant="headlineSmall" style={styles.title}>
          New enquiry
        </Text>
        <Text variant="bodyMedium" style={styles.muted}>
          Capture it now, enrich it later.
        </Text>

        <View style={styles.form}>
          <TextInput
            mode="outlined"
            label="Full name"
            value={name}
            onChangeText={setName}
            autoCapitalize="words"
            error={name.length > 0 && !nameValid}
          />
          <TextInput
            mode="outlined"
            label="Phone"
            value={phone}
            onChangeText={setPhone}
            keyboardType="phone-pad"
            error={phone.length > 0 && !phoneValid}
          />
          <TextInput
            mode="outlined"
            label="Email (optional)"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            error={email.length > 0 && !isEmail}
          />

          <Menu
            visible={menuVisible}
            onDismiss={() => setMenuVisible(false)}
            anchor={
              <TextInput
                mode="outlined"
                label="Course of interest"
                value={course?.title ?? targetCourse}
                placeholder="Tap to choose"
                onPress={() => setMenuVisible(true)}
                editable={false}
                right={<TextInput.Icon icon={() => <ChevronDown size={18} color={theme.colors.onSurfaceVariant} />} />}
              />
            }
          >
            <Menu.Item
              title="Not decided yet"
              onPress={() => {
                setCourseId(null);
                setMenuVisible(false);
              }}
            />
            {(courses.data ?? []).map((c) => (
              <Menu.Item
                key={c.id}
                title={c.title}
                onPress={() => {
                  setCourseId(c.id);
                  setTargetCourse(c.title);
                  setMenuVisible(false);
                }}
              />
            ))}
          </Menu>

          {canChooseBranch ? (
            <Menu
              visible={branchMenuVisible}
              onDismiss={() => setBranchMenuVisible(false)}
              anchor={
                <TextInput
                  mode="outlined"
                  label="Branch"
                  value={branches.find((b) => b.id === branchId)?.name ?? ''}
                  onPress={() => setBranchMenuVisible(true)}
                  editable={false}
                  right={<TextInput.Icon icon={() => <ChevronDown size={18} color={theme.colors.onSurfaceVariant} />} />}
                />
              }
            >
              {branches.map((b) => (
                <Menu.Item
                  key={b.id}
                  title={b.name}
                  onPress={() => {
                    setBranchId(b.id);
                    setBranchMenuVisible(false);
                  }}
                />
              ))}
            </Menu>
          ) : null}

          <TextInput
            mode="outlined"
            label="Notes"
            value={notes}
            onChangeText={setNotes}
            multiline
            numberOfLines={3}
          />
        </View>

        {error ? (
          <HelperText type="error" visible>
            {error}
          </HelperText>
        ) : null}

        <Button
          mode="contained"
          onPress={() => {
            setError(null);
            create.mutate();
          }}
          disabled={!canSubmit}
          loading={create.isPending}
          contentStyle={{ height: 50 }}
          style={{ marginTop: 12 }}
        >
          Save lead
        </Button>
        <Button onPress={() => router.back()} style={{ marginTop: 4 }}>
          Cancel
        </Button>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  content: { paddingHorizontal: 20 },
  title: { fontWeight: '800' },
  form: { gap: 12, marginTop: 20 },
  muted: { color: '#94A3B8' },
});

export default NewLeadScreen;

