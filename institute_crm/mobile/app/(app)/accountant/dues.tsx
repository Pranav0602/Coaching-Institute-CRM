import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, CalendarClock } from 'lucide-react-native';
import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { financeApi } from '@/api/domain.api';
import { BRAND, INSTALLMENT_COLORS } from '@/constants/theme';
import type { Installment } from '@/types';
import { formatDate, formatINR } from '@/utils/format';

const AccountantDuesScreen = () => {
  const theme = useTheme();

  const installments = useQuery({ queryKey: ['installments'], queryFn: () => financeApi.installments() });

  const buckets = useMemo(() => {
    const rows = installments.data ?? [];
    const now = Date.now();
    const overdue = rows.filter((i) => i.status === 'OVERDUE');
    const thisWeek = rows.filter(
      (i) => i.status === 'PENDING' && new Date(i.due_date).getTime() - now <= 7 * 86_400_000,
    );
    const later = rows.filter(
      (i) => i.status === 'PENDING' && new Date(i.due_date).getTime() - now > 7 * 86_400_000,
    );
    const sum = (list: Installment[]) => list.reduce((s, i) => s + Number(i.amount), 0);
    return { overdue, thisWeek, later, overdueTotal: sum(overdue), weekTotal: sum(thisWeek) };
  }, [installments.data]);

  return (
    <Screen onRefresh={() => void installments.refetch()} refreshing={installments.isRefetching}>
      <ScreenHeader title="Dues" subtitle="What is due, and when" />

      <MetricGrid>
        <MetricCard label="Overdue" value={formatINR(buckets.overdueTotal)} color={BRAND.rose500} />
        <MetricCard label="Next 7 days" value={formatINR(buckets.weekTotal)} color={BRAND.amber500} />
        <MetricCard label="Overdue count" value={buckets.overdue.length} color={BRAND.rose500} />
      </MetricGrid>

      {installments.isLoading ? <LoadingState /> : null}
      {installments.isError ? (
        <ErrorState
          message={(installments.error as Error)?.message ?? 'Could not load installments.'}
          onRetry={() => void installments.refetch()}
        />
      ) : null}
      {!installments.isLoading && (installments.data ?? []).length === 0 ? (
        <EmptyState title="Nothing due" message="No fee installments have been raised in your branch." />
      ) : null}

      <Section
        title="OVERDUE"
        color={BRAND.rose500}
        icon={<AlertTriangle size={14} color={BRAND.rose500} />}
        rows={buckets.overdue}
        emptyMessage="Nothing is overdue."
      />
      <Section
        title="DUE IN THE NEXT 7 DAYS"
        color={BRAND.amber500}
        icon={<CalendarClock size={14} color={BRAND.amber500} />}
        rows={buckets.thisWeek}
        emptyMessage="Nothing falls due this week."
      />
      <Section
        title="LATER"
        color={BRAND.indigo500}
        icon={<CalendarClock size={14} color={BRAND.indigo500} />}
        rows={buckets.later}
        emptyMessage="Nothing scheduled further out."
      />
    </Screen>
  );
};

const Section = ({
  title,
  color,
  icon,
  rows,
  emptyMessage,
}: {
  title: string;
  color: string;
  icon: React.ReactNode;
  rows: Installment[];
  emptyMessage: string;
}) => {
  const theme = useTheme();
  const total = rows.reduce((s, i) => s + Number(i.amount), 0);
  return (
    <>
      <View style={styles.sectionHeader}>
        {icon}
        <Text variant="labelSmall" style={[styles.sectionLabel, { color }]}>
          {title} · {formatINR(total)}
        </Text>
      </View>
      {rows.length === 0 ? (
        <Text variant="bodySmall" style={styles.muted}>
          {emptyMessage}
        </Text>
      ) : (
        <View style={{ gap: 8 }}>
          {rows.slice(0, 25).map(item => (
            <Card
              key={item.id}
              mode="contained"
              style={[styles.card, { backgroundColor: theme.colors.surface, borderLeftColor: INSTALLMENT_COLORS[item.status] }]}
            >
              <Card.Content style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text variant="bodyMedium" style={styles.bold} numberOfLines={1}>
                    {item.student_name}
                  </Text>
                  <Text variant="bodySmall" style={styles.muted}>
                    Installment {item.installment_number} · {formatDate(item.due_date)}
                  </Text>
                </View>
                <Text variant="bodyMedium" style={styles.bold}>
                  {formatINR(item.amount)}
                </Text>
              </Card.Content>
            </Card>
          ))}
        </View>
      )}
    </>
  );
};

const styles = StyleSheet.create({
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 20, marginBottom: 8 },
  sectionLabel: { letterSpacing: 0.8, fontWeight: '700' },
  card: { borderRadius: 12, borderLeftWidth: 4 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default AccountantDuesScreen;
