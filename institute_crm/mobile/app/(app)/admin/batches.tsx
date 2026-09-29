import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, Users } from 'lucide-react-native';
import React, { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, ProgressBar, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { attendanceApi, batchesApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import { formatDate } from '@/utils/format';

const AdminBatchesScreen = () => {
  const theme = useTheme();
  const [onlyAtRisk, setOnlyAtRisk] = useState(false);

  const batches = useQuery({ queryKey: ['batches'], queryFn: () => batchesApi.list() });
  const progress = useQuery({ queryKey: ['batch-progress'], queryFn: () => batchesApi.progress() });
  const lowAttendance = useQuery({
    queryKey: ['low-attendance'],
    queryFn: () => attendanceApi.lowAttendance({ threshold: 75 }),
  });

  const byId = useMemo(() => new Map((batches.data ?? []).map((b) => [b.id, b])), [batches.data]);

  const rows = useMemo(() => {
    const all = (progress.data ?? []).filter((p) => byId.has(p.id));
    return onlyAtRisk ? all.filter((p) => p.at_risk_count > 0) : all;
  }, [progress.data, byId, onlyAtRisk]);

  return (
    <Screen
      onRefresh={() => {
        void batches.refetch();
        void progress.refetch();
        void lowAttendance.refetch();
      }}
      refreshing={batches.isRefetching}
    >
      <ScreenHeader
        title="Batches"
        subtitle="Fill, attendance and health across every batch"
        action={
          <Card
            mode="contained"
            onPress={() => setOnlyAtRisk((v) => !v)}
            style={{
              backgroundColor: onlyAtRisk ? `${BRAND.rose500}22` : theme.colors.surfaceVariant,
              borderRadius: 999,
            }}
          >
            <Card.Content style={{ paddingVertical: 6, paddingHorizontal: 12 }}>
              <Text variant="labelSmall" style={{ fontWeight: '700' }}>
                At risk
              </Text>
            </Card.Content>
          </Card>
        }
      />

      {(lowAttendance.data?.count ?? 0) > 0 ? (
        <Card mode="contained" style={[styles.alert, { backgroundColor: `${BRAND.rose500}1A` }]}>
          <Card.Content style={styles.alertRow}>
            <AlertTriangle size={20} color={BRAND.rose500} />
            <Text variant="bodySmall" style={{ flex: 1, color: BRAND.rose500 }}>
              {lowAttendance.data?.count} students are below the{' '}
              {lowAttendance.data?.threshold ?? 75}% attendance threshold and may lose exam
              eligibility.
            </Text>
          </Card.Content>
        </Card>
      ) : null}

      {progress.isLoading ? <LoadingState /> : null}
      {progress.isError ? (
        <ErrorState
          message={(progress.error as Error)?.message ?? 'Could not load batch progress.'}
          onRetry={() => void progress.refetch()}
        />
      ) : null}
      {!progress.isLoading && !progress.isError && rows.length === 0 ? (
        <EmptyState title="No batches" message="Batches appear here once they are created." />
      ) : null}

      <View style={{ gap: 12 }}>
        {rows.map(row => {
          const batch = byId.get(row.id);
          return (
            <Card
              key={row.id}
              mode="contained"
              style={[
                styles.card,
                {
                  backgroundColor: theme.colors.surface,
                  borderLeftColor: row.at_risk_count > 0 ? BRAND.rose500 : BRAND.emerald500,
                },
              ]}
            >
              <Card.Content style={{ gap: 10 }}>
                <View style={styles.header}>
                  <View style={{ flex: 1 }}>
                    <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                      {row.name}
                    </Text>
                    <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                      {row.course_title} · {row.branch_name}
                    </Text>
                    {batch ? (
                      <Text variant="bodySmall" style={styles.muted}>
                        {formatDate(batch.start_date)} – {formatDate(batch.end_date)}
                      </Text>
                    ) : null}
                  </View>
                  <View style={styles.enrolled}>
                    <Users size={13} color={theme.colors.onSurfaceVariant} />
                    <Text variant="labelMedium" style={styles.bold}>
                      {row.enrolled_count}/{row.max_capacity}
                    </Text>
                  </View>
                </View>

                <Bar label="Attendance" value={row.attendance_pct} color={BRAND.emerald500} />
                <Bar label="Assignments" value={row.assignment_submission_pct} color={BRAND.blue500} />
                <Bar label="Exam pass rate" value={row.exam_pass_rate_pct} color={BRAND.indigo500} />
                <Bar label="Syllabus" value={row.syllabus_progress_pct} color={BRAND.amber500} />

                {row.at_risk_count > 0 ? (
                  <Text variant="labelSmall" style={{ color: BRAND.rose500, fontWeight: '700' }}>
                    {row.at_risk_count} at risk · {row.status}
                  </Text>
                ) : (
                  <Text variant="labelSmall" style={styles.muted}>
                    {row.status}
                  </Text>
                )}
              </Card.Content>
            </Card>
          );
        })}
      </View>
    </Screen>
  );
};

const Bar = ({ label, value, color }: { label: string; value: number; color: string }) => (
  <View style={{ gap: 2 }}>
    <Text variant="labelSmall" style={styles.muted}>
      {label} · {Math.round(value ?? 0)}%
    </Text>
    <ProgressBar progress={Math.min(1, Math.max(0, (value ?? 0) / 100))} color={color} style={styles.bar} />
  </View>
);

const styles = StyleSheet.create({
  alert: { borderRadius: 16, borderLeftWidth: 4, borderLeftColor: BRAND.rose500, marginBottom: 14 },
  alertRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  card: { borderRadius: 16, borderLeftWidth: 4 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  enrolled: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  bar: { height: 6, borderRadius: 3 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default AdminBatchesScreen;
