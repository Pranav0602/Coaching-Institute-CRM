/**
 * Bulk attendance.
 *
 * Optimised for the real scenario: a teacher walks in, the class is already
 * sitting there, and marking should be a handful of taps rather than a form.
 * Everyone defaults to PRESENT, so the common case (nobody missing) is one submit
 * button, and only the exceptions get touched. Every toggle fires haptics so the
 * teacher can confirm a tap without looking down.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { ArrowLeft, Check, RotateCcw } from 'lucide-react-native';
import React, { useEffect, useMemo, useState } from 'react';
import { FlatList, StyleSheet, View, Alert } from 'react-native';
import { Button, Card, Chip, Snackbar, Text, useTheme } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { LoadingState } from '@/components/common/Layout';
import { ApiError } from '@/api/client';
import { lecturesApi } from '@/api/domain.api';
import { ATTENDANCE_COLORS } from '@/constants/theme';
import type { AttendanceStatus } from '@/types';
import { formatDate } from '@/utils/format';

const STATUSES: AttendanceStatus[] = ['PRESENT', 'ABSENT', 'LATE', 'EXCUSED'];

const MarkAttendance = () => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const { lectureId } = useLocalSearchParams<{ lectureId: string }>();
  const [toast, setToast] = useState<string | null>(null);

  const register = useQuery({
    queryKey: ['lecture-register', lectureId],
    queryFn: () => lecturesApi.register(lectureId as string),
    enabled: !!lectureId,
  });

  const [statuses, setStatuses] = useState<Record<string, AttendanceStatus>>({});

  // Seed every student PRESENT, matching how a class actually starts. Done in an
  // effect keyed on the roster so a refetch does not wipe in-progress edits.
  useEffect(() => {
    if (!register.data) return;
    setStatuses((prev) => {
      const next = { ...prev };
      for (const student of register.data.students) {
        if (!next[student.student_id]) next[student.student_id] = 'PRESENT';
      }
      return next;
    });
  }, [register.data]);

  const students = register.data?.students ?? [];
  const tally = useMemo(() => {
    const counts: Record<string, number> = { PRESENT: 0, ABSENT: 0, LATE: 0, EXCUSED: 0 };
    for (const s of students) {
      const status = statuses[s.student_id];
      if (status) counts[status] += 1;
    }
    return counts;
  }, [students, statuses]);

  const setStatus = (studentId: string, status: AttendanceStatus) => {
    void Haptics.selectionAsync();
    setStatuses((prev) => ({ ...prev, [studentId]: status }));
  };

  const markAll = (status: AttendanceStatus) => {
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setStatuses((prev) => {
      const next = { ...prev };
      for (const s of students) next[s.student_id] = status;
      return next;
    });
  };

  const submit = useMutation({
    mutationFn: () =>
      lecturesApi.bulkAttendance(
        lectureId as string,
        students.map((s) => ({ student_id: s.student_id, status: statuses[s.student_id] ?? 'PRESENT' })),
        true,
      ),
    onSuccess: (result) => {
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setToast(`Attendance saved for ${result.count} students.`);
      void queryClient.invalidateQueries({ queryKey: ['lectures'] });
      setTimeout(() => router.back(), 900);
    },
    onError: (error) => {
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      setToast(error instanceof ApiError ? error.message : 'Could not save attendance.');
    },
  });

  if (register.isLoading) return <LoadingState label="Loading roster…" />;

  if (register.isError) {
    return (
      <View style={[styles.errorRoot, { backgroundColor: theme.colors.background }]}>
        <Text variant="bodyMedium" style={styles.muted}>
          {(register.error as Error)?.message ?? 'Could not load the roster.'}
        </Text>
        <Button onPress={() => router.back()}>Go back</Button>
      </View>
    );
  }

  return (
    <View style={[styles.root, { backgroundColor: theme.colors.background }]}>
      <View style={[styles.header, { paddingTop: insets.top + 8, borderBottomColor: theme.colors.outlineVariant }]}>
        <Button icon={ArrowLeft} onPress={() => router.back()} style={styles.back}>
          Back
        </Button>
        <View style={{ flex: 1 }}>
          <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
            {register.data?.subject}
          </Text>
          <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
            {formatDate(register.data?.date)} · {students.length} students
          </Text>
        </View>
      </View>

      <View style={styles.bulkRow}>
        <Button compact mode="contained-tonal" onPress={() => markAll('PRESENT')}>
          All present
        </Button>
        <Button compact mode="text" icon={RotateCcw} onPress={() => markAll('PRESENT')}>
          Reset
        </Button>
      </View>

      <View style={styles.tallyRow}>
        {STATUSES.map(status => (
          <Chip
            key={status}
            compact
            style={{ backgroundColor: `${ATTENDANCE_COLORS[status]}22` }}
            textStyle={{ color: ATTENDANCE_COLORS[status], fontWeight: '700', fontSize: 11 }}
          >
            {tally[status]} {status.toLowerCase()}
          </Chip>
        ))}
      </View>

      <FlatList
        data={students}
        keyExtractor={(item) => item.student_id}
        contentContainerStyle={{ padding: 16, paddingBottom: insets.bottom + 120, gap: 10 }}
        renderItem={({ item }) => (
          <Card mode="contained" style={{ backgroundColor: theme.colors.surface }}>
            <Card.Content style={{ gap: 8 }}>
              <Text variant="bodyLarge" style={styles.bold} numberOfLines={1}>
                {item.student_name}
              </Text>
              <View style={styles.statusRow}>
                {STATUSES.map(status => {
                  const active = statuses[item.student_id] === status;
                  return (
                    <Chip
                      key={status}
                      compact
                      selected={active}
                      onPress={() => setStatus(item.student_id, status)}
                      style={[
                        styles.statusChip,
                        active && { backgroundColor: `${ATTENDANCE_COLORS[status]}33`, borderColor: ATTENDANCE_COLORS[status] },
                      ]}
                      textStyle={{
                        fontSize: 10,
                        color: active ? ATTENDANCE_COLORS[status] : theme.colors.onSurfaceVariant,
                        fontWeight: active ? '800' : '500',
                      }}
                    >
                      {status}
                    </Chip>
                  );
                })}
              </View>
            </Card.Content>
          </Card>
        )}
      />

      <View
        style={[
          styles.footer,
          { paddingBottom: insets.bottom + 12, backgroundColor: theme.colors.surface, borderTopColor: theme.colors.outlineVariant },
        ]}
      >
        <Button
          mode="contained"
          icon={Check}
          onPress={() => {
            Alert.alert(
              'Submit attendance?',
              `${tally.PRESENT} present, ${tally.ABSENT} absent, ${tally.LATE} late.`,
              [
                { text: 'Cancel', style: 'cancel' },
                { text: 'Submit', onPress: () => submit.mutate() },
              ],
            );
          }}
          loading={submit.isPending}
          contentStyle={{ height: 48 }}
        >
          Submit for {students.length} students
        </Button>
      </View>

      <Snackbar
        visible={!!toast}
        onDismiss={() => setToast(null)}
        duration={3000}
        style={{ marginBottom: insets.bottom + 90 }}
      >
        {toast}
      </Snackbar>
    </View>
  );
};

const styles = StyleSheet.create({
  root: { flex: 1 },
  errorRoot: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingBottom: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  back: { marginLeft: -12 },
  bulkRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 16, paddingTop: 10 },
  tallyRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap', paddingHorizontal: 16, paddingTop: 8 },
  statusRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  statusChip: { height: 28 },
  footer: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 16,
    paddingTop: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default MarkAttendance;
