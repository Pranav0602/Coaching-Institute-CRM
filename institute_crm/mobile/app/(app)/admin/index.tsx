import { useQuery } from '@tanstack/react-query';
import React, { useMemo } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Text, useTheme } from 'react-native-paper';
import { BarChart, LineChart, PieChart } from 'react-native-gifted-charts';

import { ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { analyticsApi } from '@/api/domain.api';
import { BRAND, PIPELINE_STAGES, stageColor } from '@/constants/theme';
import { formatCompactINR, formatNumber } from '@/utils/format';

/**
 * The analytics endpoint is role-shaped: `scope.shows_finance` and the presence of
 * a chart key are how the server says "you may see this". Each block below is
 * therefore gated on the payload, not on a client-side role check that could
 * drift out of step with the service.
 */
const AdminOverviewScreen = () => {
  const theme = useTheme();

  const dashboard = useQuery({
    queryKey: ['analytics', 'dashboard'],
    queryFn: () => analyticsApi.dashboard(),
  });

  const data = dashboard.data;
  const cards = data?.cards;
  const charts = data?.charts;

  const attendanceSeries = useMemo(
    () =>
      (charts?.attendance_trend ?? [])
        .map((point) => ({ ...point, value: point.percentage ?? 0 }))
        .filter((point) => point.sessions_marked > 0),
    [charts?.attendance_trend],
  );

  const pipeline = useMemo(
    () =>
      (charts?.lead_funnel ?? []).map((row) => ({
        ...row,
        stage: PIPELINE_STAGES.find((s) => s.toLowerCase() === row.stage.toLowerCase()) ?? row.stage,
      })),
    [charts?.lead_funnel],
  );

  if (dashboard.isLoading) return <Screen><LoadingState label="Building your dashboard…" /></Screen>;
  if (dashboard.isError || !data || !cards) {
    return (
      <Screen>
        <ErrorState
          message={(dashboard.error as Error)?.message ?? 'Could not load analytics.'}
          onRetry={() => void dashboard.refetch()}
        />
      </Screen>
    );
  }

  return (
    <Screen onRefresh={() => void dashboard.refetch()} refreshing={dashboard.isRefetching}>
      <ScreenHeader
        title={data.scope.all_branches ? 'All Branches' : data.scope.branch_name ?? 'Overview'}
        subtitle={`${formatNumber(data.scope.visible_batches)} batches in your scope`}
      />

      <MetricGrid>
        <MetricCard label="Students" value={formatNumber(cards.total_students)} color={BRAND.indigo500} />
        <MetricCard label="Teachers" value={formatNumber(cards.total_teachers)} color={BRAND.emerald500} />
        <MetricCard label="Active batches" value={formatNumber(cards.active_batches)} color={BRAND.blue500} />
        <MetricCard label="Courses" value={formatNumber(cards.active_courses)} color={BRAND.amber500} />
        <MetricCard
          label="Today's attendance"
          value={cards.todays_attendance_pct === null ? '—' : `${Math.round(cards.todays_attendance_pct)}%`}
          color={
            cards.todays_attendance_pct !== null && cards.todays_attendance_pct < 75
              ? BRAND.rose500
              : BRAND.emerald500
          }
          progress={cards.todays_attendance_pct}
        />
        <MetricCard label="Upcoming exams" value={formatNumber(cards.upcoming_exams)} color={BRAND.rose500} />
        {cards.open_leads !== undefined ? (
          <MetricCard label="Open leads" value={formatNumber(cards.open_leads)} color={BRAND.indigo400} />
        ) : null}
        {cards.admissions_this_month !== undefined ? (
          <MetricCard
            label="Admissions (MTD)"
            value={formatNumber(cards.admissions_this_month)}
            color={BRAND.emerald500}
          />
        ) : null}
      </MetricGrid>

      {attendanceSeries.length >= 2 ? (
        <>
          <Text variant="labelSmall" style={styles.sectionLabel}>
            ATTENDANCE TREND
          </Text>
          <View style={[styles.chartCard, { backgroundColor: theme.colors.surface }]}>
            <LineChart
              data={attendanceSeries.map((p) => ({ value: p.value, label: p.month.split(' ')[0] }))}
              width={280}
              height={170}
              color={BRAND.emerald500}
              dataPointsColor={BRAND.emerald500}
              thickness={3}
              hideRules
              yAxisColor="transparent"
              xAxisColor={theme.colors.outlineVariant}
              yAxisLabelSuffix="%"
              maxValue={100}
              noOfSections={4}
              isAnimated
            />
          </View>
        </>
      ) : null}

      {pipeline.length ? (
        <>
          <Text variant="labelSmall" style={styles.sectionLabel}>
            LEAD FUNNEL
          </Text>
          <View style={[styles.chartCard, { backgroundColor: theme.colors.surface }]}>
            <Text variant="headlineSmall" style={styles.funnelTotal}>
              {pipeline.reduce((s, r) => s + r.count, 0)}
            </Text>
            <PieChart
              data={pipeline.map((row) => ({
                value: row.count,
                color: stageColor(row.stage),
                label: row.stage,
              }))}
              radius={70}
              innerRadius={40}
              sectionAutoFocus
            />
            <View style={styles.legend}>
              {pipeline.map((row) => (
                <View key={row.stage} style={styles.legendItem}>
                  <View style={[styles.dot, { backgroundColor: stageColor(row.stage) }]} />
                  <Text variant="labelSmall" style={styles.muted}>
                    {row.stage}
                  </Text>
                  <Text variant="labelSmall" style={styles.bold}>
                    {row.count}
                  </Text>
                </View>
              ))}
            </View>
          </View>
        </>
      ) : null}

      {charts?.course_popularity?.length ? (
        <>
          <Text variant="labelSmall" style={styles.sectionLabel}>
            TOP COURSES BY ENROLMENT
          </Text>
          <View style={[styles.chartCard, { backgroundColor: theme.colors.surface }]}>
            <BarChart
              data={charts.course_popularity.slice(0, 6).map((row) => ({
                value: row.enrolments,
                label: row.course.split(' ').slice(0, 2).join(' '),
                frontColor: BRAND.indigo500,
              }))}
              width={280}
              height={180}
              barWidth={22}
              spacing={12}
              yAxisColor="transparent"
              xAxisColor={theme.colors.outlineVariant}
              hideRules
              isAnimated
            />
          </View>
        </>
      ) : null}

      {data.scope.shows_finance && cards.total_fee_collection !== undefined ? (
        <>
          <Text variant="labelSmall" style={styles.sectionLabel}>
            REVENUE
          </Text>
          <MetricGrid>
            <MetricCard
              label="Collected (all time)"
              value={formatCompactINR(cards.total_fee_collection)}
              color={BRAND.emerald500}
            />
            <MetricCard
              label="This month"
              value={formatCompactINR(cards.collection_this_month)}
              color={BRAND.indigo500}
            />
            <MetricCard
              label="Pending"
              value={formatCompactINR(cards.pending_fees)}
              color={BRAND.amber500}
            />
            <MetricCard
              label="Overdue"
              value={formatCompactINR(cards.overdue_fees)}
              color={BRAND.rose500}
            />
          </MetricGrid>
        </>
      ) : null}

      {charts?.growth_and_revenue?.length ? (
        <>
          <Text variant="labelSmall" style={styles.sectionLabel}>
            ADMISSIONS &amp; REVENUE
          </Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={[styles.chartCard, { backgroundColor: theme.colors.surface }]}>
              <LineChart
                data={charts.growth_and_revenue.map((p) => ({
                  value: Number(p.revenue ?? 0),
                  label: p.month.split(' ')[0],
                }))}
                width={280}
                height={170}
                color={BRAND.indigo500}
                dataPointsColor={BRAND.indigo500}
                thickness={3}
                hideRules
                yAxisColor="transparent"
                xAxisColor={theme.colors.outlineVariant}
                isAnimated
              />
            </View>
          </ScrollView>
        </>
      ) : null}
    </Screen>
  );
};

const styles = StyleSheet.create({
  sectionLabel: { marginTop: 22, marginBottom: 8, letterSpacing: 0.8, opacity: 0.7 },
  chartCard: { borderRadius: 18, padding: 16, gap: 12 },
  funnelTotal: { fontWeight: '800', textAlign: 'center' },
  legend: { gap: 6, alignSelf: 'stretch' },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  dot: { width: 10, height: 10, borderRadius: 5 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8', flex: 1 },
});

export default AdminOverviewScreen;
