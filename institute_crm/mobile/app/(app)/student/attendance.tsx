import { useQuery } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react-native';
import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, ProgressBar, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { attendanceApi } from '@/api/domain.api';
import { ATTENDANCE_COLORS, BRAND } from '@/constants/theme';
import { formatDate } from '@/utils/format';
import type { Attendance } from '@/types';

/**
 * The backend answers `/attendances/summary/` with a list even for a single
 * student, because a parent gets one row per linked child from the same call.
 * A student therefore picks their own row out of that list.
 */
const StudentAttendanceScreen = () => {
  const theme = useTheme();

  const summary = useQuery({
    queryKey: ['attendance-summary', 'me'],
    queryFn: () => attendanceApi.summary(),
  });

  const records = useQuery({
    queryKey: ['attendance-records', 'me'],
    queryFn: () => attendanceApi.list({}),
  });

  const mine = summary.data?.[0];
  const pct = mine?.percentage ?? null;
  const threshold = mine?.threshold ?? 75;
  const eligible = pct !== null && pct >= threshold;

  const recent = useMemo(
    () =>
      (records.data ?? [])
        .slice()
        .sort((a, b) => b.lecture_date.localeCompare(a.lecture_date))
        .slice(0, 25),
    [records.data],
  );

  return (
    <Screen
      onRefresh={() => {
        void summary.refetch();
        void records.refetch();
      }}
      refreshing={summary.isRefetching}
    >
      <ScreenHeader title="Attendance" subtitle={`Eligibility needs ${threshold}%`} />

      {summary.isLoading ? <LoadingState /> : null}
      {summary.isError ? (
        <ErrorState
          message={(summary.error as Error)?.message ?? 'Could not load attendance.'}
          onRetry={() => void summary.refetch()}
        />
      ) : null}

      {mine ? (
        <>
          <MetricGrid>
            <MetricCard
              label="Overall"
              value={pct === null ? '—' : `${Math.round(pct)}%`}
              color={eligible ? BRAND.emerald500 : BRAND.rose500}
              progress={pct}
            />
            <MetricCard label="Present" value={mine.present} color={BRAND.emerald500} />
            <MetricCard label="Absent" value={mine.absent} color={BRAND.rose500} />
            <MetricCard label="Late" value={mine.late} color={BRAND.amber500} />
          </MetricGrid>

          <Card
            mode="contained"
            style={[styles.verdict, { borderLeftColor: eligible ? BRAND.emerald500 : BRAND.rose500 }]}
          >
            <Card.Content>
              <Text
                variant="titleSmall"
                style={{ fontWeight: '700', color: eligible ? BRAND.emerald500 : BRAND.rose500 }}
              >
                {eligible ? 'Eligible for exams' : 'Below the eligibility threshold'}
              </Text>
              <Text variant="bodySmall" style={styles.muted}>
                {pct === null
                  ? `No classes have been marked yet, so there is nothing to count against the ${threshold}% requirement.`
                  : eligible
                    ? `${(threshold - Math.round(pct)).toFixed(0)} points of headroom left before you fall below ${threshold}%.`
                    : `You are ${(threshold - Math.round(pct)).toFixed(0)} points short. Speak to your branch admin.`}
              </Text>
            </Card.Content>
          </Card>
        </>
      ) : null}

      {mine && mine.below_threshold ? (
        <View style={styles.warningRow}>
          <AlertTriangle size={16} color={BRAND.rose500} />
          <Text variant="bodySmall" style={{ color: BRAND.rose500, flex: 1 }}>
            Missing classes is the fastest way to lose exam eligibility. Speak to your teacher about
            making up the sessions you missed.
          </Text>
        </View>
      ) : null}

      <Text variant="labelSmall" style={styles.sectionLabel}>
        RECENT CLASSES
      </Text>
      {recent.length === 0 ? (
        <EmptyState title="No classes marked yet" message="Attendance appears here once a lecturer marks a session." />
      ) : null}

      <View style={{ gap: 8 }}>
        {recent.map((record: Attendance) => (
          <Card
            key={record.id}
            mode="contained"
            style={[
              styles.record,
              { backgroundColor: theme.colors.surface, borderLeftColor: ATTENDANCE_COLORS[record.status] },
            ]}
          >
            <Card.Content style={styles.recordRow}>
              <View style={{ flex: 1 }}>
                <Text variant="bodyMedium" style={styles.bold} numberOfLines={1}>
                  {record.subject_title ?? 'Class'}
                </Text>
                <Text variant="bodySmall" style={styles.muted}>
                  {formatDate(record.lecture_date)}
                </Text>
              </View>
              <Text variant="labelMedium" style={{ color: ATTENDANCE_COLORS[record.status], fontWeight: '800' }}>
                {record.status}
              </Text>
            </Card.Content>
          </Card>
        ))}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  sectionLabel: { marginTop: 20, marginBottom: 8, letterSpacing: 0.8, opacity: 0.7 },
  verdict: { borderRadius: 16, borderLeftWidth: 4, marginTop: 12 },
  warningRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 12 },
  record: { borderRadius: 12, borderLeftWidth: 4 },
  recordRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default StudentAttendanceScreen;
