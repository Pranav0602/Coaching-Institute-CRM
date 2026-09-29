import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { CalendarRange, Users } from 'lucide-react-native';
import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, ProgressBar, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { batchesApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import { formatDate } from '@/utils/format';

const TeacherBatchesScreen = () => {
  const theme = useTheme();

  const batches = useQuery({ queryKey: ['batches'], queryFn: () => batchesApi.list() });
  const progress = useQuery({ queryKey: ['batch-progress'], queryFn: () => batchesApi.progress() });

  const byId = useMemo(
    () => new Map((batches.data ?? []).map((b) => [b.id, b])),
    [batches.data],
  );

  const rows = useMemo(
    () => (progress.data ?? []).filter((p) => byId.has(p.id)),
    [progress.data, byId],
  );

  return (
    <Screen
      onRefresh={() => {
        void batches.refetch();
        void progress.refetch();
      }}
      refreshing={batches.isRefetching}
    >
      <ScreenHeader title="Batches" subtitle="Progress across the batches you teach" />

      {progress.isLoading ? <LoadingState label="Loading batch progress…" /> : null}
      {progress.isError ? (
        <ErrorState
          message={(progress.error as Error)?.message ?? 'Could not load batch progress.'}
          onRetry={() => void progress.refetch()}
        />
      ) : null}
      {!progress.isLoading && !progress.isError && rows.length === 0 ? (
        <EmptyState
          icon={<CalendarRange size={28} color={theme.colors.onSurfaceVariant} />}
          title="No batches assigned"
          message="Branch admins assign teachers to batches from the web dashboard."
        />
      ) : null}

      <View style={{ gap: 12 }}>
        {rows.map(row => {
          const batch = byId.get(row.id);
          return (
            <Card key={row.id} mode="contained" style={{ backgroundColor: theme.colors.surface }}>
              <Card.Content style={{ gap: 10 }}>
                <View style={styles.header}>
                  <View style={{ flex: 1 }}>
                    <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                      {row.name}
                    </Text>
                    <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                      {row.course_title} · {row.branch_name}
                    </Text>
                  </View>
                  <View style={styles.countBox}>
                    <Users size={13} color={theme.colors.onSurfaceVariant} />
                    <Text variant="labelMedium" style={styles.bold}>
                      {row.enrolled_count}/{row.max_capacity}
                    </Text>
                  </View>
                </View>

                <Metric label="Timeline" value={row.timeline_pct} />
                <Metric label="Attendance" value={row.attendance_pct} color={BRAND.emerald500} />
                <Metric label="Assignments" value={row.assignment_submission_pct} color={BRAND.blue500} />
                <Metric label="Syllabus" value={row.syllabus_progress_pct} color={BRAND.indigo500} />

                {row.at_risk_count > 0 ? (
                  <Text variant="labelSmall" style={{ color: BRAND.rose500, fontWeight: '700' }}>
                    {row.at_risk_count} student{row.at_risk_count === 1 ? '' : 's'} at risk
                  </Text>
                ) : null}

                {batch ? (
                  <Text variant="bodySmall" style={styles.muted}>
                    {formatDate(batch.start_date)} – {formatDate(batch.end_date)}
                  </Text>
                ) : null}
              </Card.Content>
            </Card>
          );
        })}
      </View>
    </Screen>
  );
};

const Metric = ({ label, value, color }: { label: string; value: number; color?: string }) => (
  <View style={{ gap: 2 }}>
    <Text variant="labelSmall" style={styles.muted}>
      {label} · {Math.round(value ?? 0)}%
    </Text>
    <ProgressBar
      progress={Math.min(1, Math.max(0, (value ?? 0) / 100))}
      color={color ?? BRAND.indigo500}
      style={styles.bar}
    />
  </View>
);

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  countBox: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  bar: { height: 6, borderRadius: 3 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default TeacherBatchesScreen;
