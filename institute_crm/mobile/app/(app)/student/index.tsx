import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { AlertTriangle, BookOpen, CalendarDays, Receipt, Wallet } from 'lucide-react-native';
import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, ProgressBar, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { attendanceApi, examsApi, financeApi, timetableApi } from '@/api/domain.api';
import { BRAND, INSTALLMENT_COLORS } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';
import { currentDayCode, dayLabel, formatDate, formatINR, formatTime } from '@/utils/format';
import type { Installment } from '@/types';

const StudentHomeScreen = () => {
  const theme = useTheme();
  const { user } = useAuth();

  const weekly = useQuery({
    queryKey: ['timetable', 'student'],
    queryFn: () => timetableApi.weekly({}),
  });

  const attendance = useQuery({
    queryKey: ['attendance-summary', 'me'],
    queryFn: () => attendanceApi.summary(),
  });

  const installments = useQuery({
    queryKey: ['installments', user?.id],
    queryFn: () => financeApi.installments({ student_id: user?.id }),
  });

  const results = useQuery({
    queryKey: ['results', user?.id],
    queryFn: () => examsApi.results({ student_id: user?.id }),
  });

  const today = currentDayCode();
  const todaysClasses = weekly.data?.[today] ?? [];

  const dues = useMemo(() => {
    const rows = (installments.data ?? []) as Installment[];
    const pending = rows.filter((i) => i.status !== 'PAID');
    return {
      pending,
      total: pending.reduce((sum, i) => sum + Number(i.amount), 0),
      overdue: pending.filter((i) => i.status === 'OVERDUE'),
    };
  }, [installments.data]);

  const mySummary = attendance.data?.[0];
  const attendancePct = mySummary?.percentage ?? null;
  const hasAttendance = attendancePct !== null;
  const lowAttendance = mySummary?.below_threshold ?? false;

  const latestResults = useMemo(
    () => (results.data ?? []).slice().sort((a, b) => b.id.localeCompare(a.id)).slice(0, 3),
    [results.data],
  );

  return (
    <Screen
      onRefresh={() => {
        void weekly.refetch();
        void attendance.refetch();
        void installments.refetch();
        void results.refetch();
      }}
      refreshing={weekly.isRefetching}
    >
      <ScreenHeader
        title={`Hi, ${user?.full_name?.split(' ')[0] ?? 'there'}`}
        subtitle={`${dayLabel(today)} · ${user?.branch_name ? `at ${user.branch_name}` : 'your day at a glance'}`}
      />

      {lowAttendance ? (
        <Card mode="contained" style={[styles.alert, { backgroundColor: `${BRAND.rose500}1A` }]}>
          <Card.Content style={styles.alertRow}>
            <AlertTriangle size={20} color={BRAND.rose500} />
            <View style={{ flex: 1 }}>
              <Text variant="titleSmall" style={{ color: BRAND.rose500, fontWeight: '700' }}>
                Attendance is {Math.round(attendancePct ?? 0)}%
              </Text>
              <Text variant="bodySmall" style={styles.muted}>
                Most institutes require 75% to be eligible for exams.
              </Text>
            </View>
          </Card.Content>
        </Card>
      ) : null}

      <MetricGrid>
        <MetricCard
          label="Attendance"
          value={hasAttendance ? `${Math.round(attendancePct)}%` : '—'}
          color={lowAttendance ? BRAND.rose500 : BRAND.emerald500}
          progress={hasAttendance ? attendancePct : null}
        />
        <MetricCard label="Classes today" value={todaysClasses.length} color={BRAND.indigo500} />
        <MetricCard
          label="Fees due"
          value={dues.pending.length ? formatINR(dues.total) : 'Clear'}
          color={dues.overdue.length ? BRAND.rose500 : BRAND.emerald500}
        />
      </MetricGrid>

      <View style={styles.navRow}>
        <NavButton
          icon={CalendarDays}
          label="Schedule"
          onPress={() => router.push('/(app)/student/schedule')}
        />
        <NavButton
          icon={Receipt}
          label="Fees"
          onPress={() => router.push('/(app)/student/fees')}
        />
        <NavButton
          icon={BookOpen}
          label="Syllabi"
          onPress={() => router.push('/(app)/counsellor/syllabi')}
        />
      </View>

      <Text variant="labelSmall" style={styles.sectionLabel}>
        TODAY&apos;S CLASSES
      </Text>
      {weekly.isLoading ? <LoadingState /> : null}
      {weekly.isError ? (
        <ErrorState
          message={(weekly.error as Error)?.message ?? 'Could not load your timetable.'}
          onRetry={() => void weekly.refetch()}
        />
      ) : null}
      {!weekly.isLoading && !weekly.isError && todaysClasses.length === 0 ? (
        <EmptyState
          title="No classes today"
          message="Use this time to revise — or check your pending assignments."
        />
      ) : null}

      <View style={{ gap: 10 }}>
        {todaysClasses.map(entry => (
          <Card key={entry.id} mode="contained" style={{ backgroundColor: theme.colors.surface }}>
            <Card.Content style={styles.classRow}>
              <View style={{ flex: 1 }}>
                <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                  {entry.subject_title}
                </Text>
                <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                  {formatTime(entry.start_time)} – {formatTime(entry.end_time)}
                  {entry.teacher_name ? ` · ${entry.teacher_name}` : ''}
                  {entry.room_number ? ` · Room ${entry.room_number}` : ''}
                </Text>
              </View>
            </Card.Content>
          </Card>
        ))}
      </View>

      {latestResults.length ? (
        <>
          <Text variant="labelSmall" style={styles.sectionLabel}>
            RECENT RESULTS
          </Text>
          <View style={{ gap: 10 }}>
            {latestResults.map(result => (
              <Card key={result.id} mode="contained" style={{ backgroundColor: theme.colors.surface }}>
                <Card.Content style={styles.classRow}>
                  <View style={{ flex: 1 }}>
                    <Text variant="bodyMedium" style={styles.bold} numberOfLines={1}>
                      {result.grade ? `Grade ${result.grade}` : 'Result published'}
                    </Text>
                    <Text variant="bodySmall" style={styles.muted}>
                      {result.marks_obtained} marks
                    </Text>
                  </View>
                </Card.Content>
              </Card>
            ))}
          </View>
        </>
      ) : null}

      {dues.pending.length ? (
        <>
          <Text variant="labelSmall" style={styles.sectionLabel}>
            PENDING FEES
          </Text>
          <Card mode="contained" style={{ backgroundColor: theme.colors.surface }}>
            <Card.Content style={{ gap: 10 }}>
              {dues.pending.slice(0, 4).map(item => (
                <View key={item.id} style={styles.dueRow}>
                  <Wallet size={15} color={INSTALLMENT_COLORS[item.status]} />
                  <View style={{ flex: 1 }}>
                    <Text variant="bodyMedium" style={styles.bold}>
                      Installment {item.installment_number}
                    </Text>
                    <Text variant="bodySmall" style={styles.muted}>
                      Due {formatDate(item.due_date)}
                    </Text>
                  </View>
                  <Text variant="bodyMedium" style={styles.bold}>
                    {formatINR(item.amount)}
                  </Text>
                </View>
              ))}
              <Button mode="text" onPress={() => router.push('/(app)/student/fees')}>
                View all fees
              </Button>
            </Card.Content>
          </Card>
        </>
      ) : null}
    </Screen>
  );
};

const NavButton = ({
  icon: Icon,
  label,
  onPress,
}: {
  icon: React.ComponentType<{ size?: number; color?: string }>;
  label: string;
  onPress: () => void;
}) => {
  const theme = useTheme();
  return (
    <Card
      mode="contained"
      onPress={onPress}
      style={[styles.navCard, { backgroundColor: theme.colors.surface }]}
    >
      <Card.Content style={{ alignItems: 'center', gap: 6, paddingVertical: 14 }}>
        <Icon size={22} color={theme.colors.primary} />
        <Text variant="labelSmall" style={styles.bold}>
          {label}
        </Text>
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  sectionLabel: { marginTop: 20, marginBottom: 8, letterSpacing: 0.8, opacity: 0.7 },
  alert: { borderRadius: 16, borderLeftWidth: 4, borderLeftColor: BRAND.rose500 },
  alertRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  navRow: { flexDirection: 'row', gap: 10, marginTop: 16 },
  navCard: { flex: 1, borderRadius: 14 },
  classRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  dueRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default StudentHomeScreen;
