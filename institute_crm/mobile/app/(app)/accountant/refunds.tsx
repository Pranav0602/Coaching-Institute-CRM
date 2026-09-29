import { useQuery } from '@tanstack/react-query';
import { Undo2 } from 'lucide-react-native';
import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, Chip, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { financeApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import type { Refund } from '@/types';
import { formatDate, formatINR } from '@/utils/format';

const STATUS_COLORS: Record<Refund['status'], string> = {
  REQUESTED: BRAND.amber500,
  APPROVED: BRAND.emerald500,
  REJECTED: BRAND.rose500,
};

const AccountantRefundsScreen = () => {
  const theme = useTheme();

  const refunds = useQuery({ queryKey: ['refunds'], queryFn: () => financeApi.refunds() });

  const counts = useMemo(() => {
    const rows = refunds.data ?? [];
    return {
      requested: rows.filter((r) => r.status === 'REQUESTED'),
      approved: rows.filter((r) => r.status === 'APPROVED'),
      rejected: rows.filter((r) => r.status === 'REJECTED'),
    };
  }, [refunds.data]);

  return (
    <Screen onRefresh={() => void refunds.refetch()} refreshing={refunds.isRefetching}>
      <ScreenHeader title="Refunds" subtitle="Requests raised by students" />

      <MetricGrid>
        <MetricCard label="Requested" value={counts.requested.length} color={BRAND.amber500} />
        <MetricCard label="Approved" value={counts.approved.length} color={BRAND.emerald500} />
        <MetricCard label="Rejected" value={counts.rejected.length} color={BRAND.rose500} />
      </MetricGrid>

      {refunds.isLoading ? <LoadingState /> : null}
      {refunds.isError ? (
        <ErrorState
          message={(refunds.error as Error)?.message ?? 'Could not load refunds.'}
          onRetry={() => void refunds.refetch()}
        />
      ) : null}
      {!refunds.isLoading && (refunds.data ?? []).length === 0 ? (
        <EmptyState
          icon={<Undo2 size={28} color={theme.colors.onSurfaceVariant} />}
          title="No refunds"
          message="Refund requests raised from the web dashboard will appear here."
        />
      ) : null}

      <View style={{ gap: 10 }}>
        {(refunds.data ?? []).map((refund: Refund) => (
          <Card
            key={refund.id}
            mode="contained"
            style={[
              styles.card,
              { backgroundColor: theme.colors.surface, borderLeftColor: STATUS_COLORS[refund.status] },
            ]}
          >
            <Card.Content style={{ gap: 6 }}>
              <View style={styles.header}>
                <View style={{ flex: 1 }}>
                  <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                    {refund.student_name}
                  </Text>
                  <Text variant="bodySmall" style={styles.muted}>
                    Raised {formatDate(refund.created_at)}
                  </Text>
                </View>
                <Text variant="titleSmall" style={styles.bold}>
                  {formatINR(refund.amount)}
                </Text>
              </View>
              {refund.reason ? (
                <Text variant="bodySmall" style={styles.muted} numberOfLines={3}>
                  {refund.reason}
                </Text>
              ) : null}
              <Chip
                compact
                style={{
                  alignSelf: 'flex-start',
                  backgroundColor: `${STATUS_COLORS[refund.status]}22`,
                }}
                textStyle={{ color: STATUS_COLORS[refund.status], fontWeight: '700', fontSize: 10 }}
              >
                {refund.status}
              </Chip>
            </Card.Content>
          </Card>
        ))}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  card: { borderRadius: 14, borderLeftWidth: 4 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default AccountantRefundsScreen;
