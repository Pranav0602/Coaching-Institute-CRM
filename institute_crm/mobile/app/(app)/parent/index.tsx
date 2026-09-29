import { useQueries } from '@tanstack/react-query';
import React, { useMemo } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Card, Chip, ProgressBar, Text, useTheme } from 'react-native-paper';

import { EmptyState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { attendanceApi, examsApi, financeApi, studentsApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';
import { formatDate, formatINR } from '@/utils/format';
import type { AttendanceSummary, Installment, Result, StudentProfile } from '@/types';

/**
 * `ProfileService.filter_students` already narrows a PARENT to their own linked
 * children, and `/attendances/summary/` answers with one row per linked child in
 * the same call. So the whole screen is three queries and a join, with no
 * client-side guessing about who is whose child.
 */
const ParentHomeScreen = () => {
  const theme = useTheme();
  const { user } = useAuth();

  const [children, summary, installments, results] = useQueries({
    queries: [
      { queryKey: ['children'], queryFn: () => studentsApi.list() },
      { queryKey: ['children-attendance'], queryFn: () => attendanceApi.summary() },
      { queryKey: ['children-installments'], queryFn: () => financeApi.installments() },
      { queryKey: ['children-results'], queryFn: () => examsApi.results() },
    ],
  });

  const summaryById = useMemo(
    () => new Map((summary.data ?? []).map((s: AttendanceSummary) => [s.student_id, s])),
    [summary.data],
  );

  const installmentsByStudent = useMemo(() => {
    const map = new Map<string, Installment[]>();
    for (const item of (installments.data ?? []) as Installment[]) {
      map.set(item.student, [...(map.get(item.student) ?? []), item]);
    }
    return map;
  }, [installments.data]);

  const resultsByStudent = useMemo(() => {
    const map = new Map<string, Result[]>();
    for (const result of (results.data ?? []) as Result[]) {
      map.set(result.student, [...(map.get(result.student) ?? []), result]);
    }
    return map;
  }, [results.data]);

  const loading = children.isLoading || summary.isLoading;
  const list = (children.data ?? []) as StudentProfile[];

  return (
    <Screen
      onRefresh={() => {
        void children.refetch();
        void summary.refetch();
        void installments.refetch();
        void results.refetch();
      }}
      refreshing={children.isRefetching}
    >
      <ScreenHeader
        title="My children"
        subtitle={`Signed in as ${user?.full_name || user?.username}`}
      />

      {loading ? <LoadingState label="Loading your children…" /> : null}

      {!loading && list.length === 0 ? (
        <EmptyState
          title="No children linked yet"
          message={`Once ${user?.full_name?.split(' ')[0] ?? 'a guardian'} is linked to a student profile by the branch, their record appears here automatically.`}
        />
      ) : null}

      <View style={{ gap: 14 }}>
        {list.map(child => {
          const stats = summaryById.get(child.user);
          const dues = (installmentsByStudent.get(child.user) ?? []).filter((i) => i.status !== 'PAID');
          const childResults = resultsByStudent.get(child.user) ?? [];
          const pct = stats?.percentage ?? null;
          const atRisk = stats?.below_threshold ?? false;

          return (
            <Card key={child.id} mode="contained" style={{ backgroundColor: theme.colors.surface }}>
              <Card.Content style={{ gap: 12 }}>
                <View style={styles.header}>
                  <View style={{ flex: 1 }}>
                    <Text variant="titleMedium" style={styles.bold} numberOfLines={1}>
                      {child.user_detail?.full_name || child.user_detail?.username}
                    </Text>
                    <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                      {child.enrollment_number}
                      {child.batch_name ? ` · ${child.batch_name}` : ''}
                    </Text>
                  </View>
                  <Chip
                    compact
                    style={{
                      backgroundColor: atRisk ? `${BRAND.rose500}22` : `${BRAND.emerald500}22`,
                    }}
                    textStyle={{
                      color: atRisk ? BRAND.rose500 : BRAND.emerald500,
                      fontWeight: '700',
                      fontSize: 11,
                    }}
                  >
                    {pct === null ? 'No data' : `${Math.round(pct)}%`}
                  </Chip>
                </View>

                <MetricGrid>
                  <MetricCard
                    label="Attendance"
                    value={pct === null ? '—' : `${Math.round(pct)}%`}
                    color={atRisk ? BRAND.rose500 : BRAND.emerald500}
                    progress={pct}
                    note={stats ? `${stats.present} of ${stats.total_sessions} sessions` : undefined}
                  />
                  <MetricCard
                    label="Fees due"
                    value={dues.length ? formatINR(dues.reduce((s, d) => s + Number(d.amount), 0)) : 'Clear'}
                    color={dues.length ? BRAND.amber500 : BRAND.emerald500}
                    note={dues.length ? `Next ${formatDate(dues[0].due_date)}` : 'Nothing outstanding'}
                  />
                </MetricGrid>

                {atRisk ? (
                  <Text variant="bodySmall" style={{ color: BRAND.rose500 }}>
                    Below the {stats?.threshold ?? 75}% exam-eligibility threshold.
                  </Text>
                ) : null}

                {childResults.length ? (
                  <View>
                    <Text variant="labelSmall" style={styles.muted}>
                      RECENT RESULTS
                    </Text>
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
                      {childResults.slice(0, 8).map((r) => (
                        <Chip key={r.id} compact style={styles.chip} textStyle={styles.chipText}>
                          {r.grade ? `Grade ${r.grade}` : `${r.marks_obtained} marks`}
                        </Chip>
                      ))}
                    </ScrollView>
                  </View>
                ) : null}

                {dues.length ? (
                  <View style={styles.dueBlock}>
                    <ProgressBar
                      progress={Math.min(
                        1,
                        (dues.reduce((s, d) => s + Number(d.amount), 0) / (dues.length * 10000 || 1)),
                      )}
                      color={BRAND.amber500}
                      style={styles.dueBar}
                    />
                    <Text variant="bodySmall" style={styles.muted}>
                      {dues.length} installment{dues.length === 1 ? '' : 's'} outstanding
                    </Text>
                  </View>
                ) : null}
              </Card.Content>
            </Card>
          );
        })}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  chips: { gap: 6, paddingTop: 6, paddingRight: 12 },
  chip: { backgroundColor: `${BRAND.indigo500}22` },
  chipText: { fontSize: 10, color: BRAND.indigo500, fontWeight: '700' },
  dueBlock: { gap: 4 },
  dueBar: { height: 5, borderRadius: 3 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default ParentHomeScreen;
