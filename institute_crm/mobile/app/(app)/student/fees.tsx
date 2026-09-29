import { useQuery } from '@tanstack/react-query';
import { Download, Wallet } from 'lucide-react-native';
import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, Chip, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { financeApi } from '@/api/domain.api';
import { BRAND, INSTALLMENT_COLORS } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';
import type { Installment, Payment, Receipt } from '@/types';
import { formatDate, formatINR } from '@/utils/format';
import { copyToClipboard, openExternal, shareText } from '@/utils/linking';

const StudentFeesScreen = () => {
  const theme = useTheme();
  const { user } = useAuth();

  const installments = useQuery({
    queryKey: ['installments', user?.id],
    queryFn: () => financeApi.installments({ student_id: user?.id }),
  });

  const payments = useQuery({
    queryKey: ['payments', user?.id],
    queryFn: () => financeApi.payments({ student_id: user?.id }),
  });

  const summary = useMemo(() => {
    const rows = installments.data ?? [];
    const paid = rows.filter((i) => i.status === 'PAID');
    const pending = rows.filter((i) => i.status !== 'PAID');
    return {
      paidTotal: paid.reduce((sum, i) => sum + Number(i.amount), 0),
      dueTotal: pending.reduce((sum, i) => sum + Number(i.amount), 0),
      overdue: pending.filter((i) => i.status === 'OVERDUE'),
      paidCount: paid.length,
      pendingCount: pending.length,
    };
  }, [installments.data]);

  const receipts: Array<{ receipt: Receipt; payment: Payment }> = useMemo(
    () =>
      (payments.data ?? [])
        .filter((p) => p.receipt)
        .map((p) => ({ receipt: p.receipt as Receipt, payment: p })),
    [payments.data],
  );

  const shareReceipt = (receipt: Receipt, payment: Payment) => {
    const lines = [
      `Receipt ${receipt.receipt_number}`,
      `Amount: ${formatINR(payment.amount)}`,
      `Mode: ${payment.payment_mode}`,
      `Reference: ${payment.reference_number}`,
      `Date: ${formatDate(payment.payment_date)}`,
      '',
      'Graphix Techno Services',
    ].join('\n');
    void shareText(lines, receipt.receipt_number);
  };

  return (
    <Screen
      onRefresh={() => {
        void installments.refetch();
        void payments.refetch();
      }}
      refreshing={installments.isRefetching}
    >
      <ScreenHeader title="Fees" subtitle="Your installments and receipts" />

      <MetricGrid>
        <MetricCard label="Paid" value={formatINR(summary.paidTotal)} color={BRAND.emerald500} />
        <MetricCard
          label="Due"
          value={formatINR(summary.dueTotal)}
          color={summary.overdue.length ? BRAND.rose500 : BRAND.amber500}
        />
        <MetricCard label="Installments" value={`${summary.paidCount}/${summary.paidCount + summary.pendingCount}`} color={BRAND.indigo500} />
      </MetricGrid>

      {installments.isLoading ? <LoadingState /> : null}
      {installments.isError ? (
        <ErrorState
          message={(installments.error as Error)?.message ?? 'Could not load your fees.'}
          onRetry={() => void installments.refetch()}
        />
      ) : null}
      {!installments.isLoading && !installments.isError && (installments.data ?? []).length === 0 ? (
        <EmptyState
          icon={<Wallet size={28} color={theme.colors.onSurfaceVariant} />}
          title="No fee plan yet"
          message="Your installments appear here once your branch admin sets up your fee structure."
        />
      ) : null}

      {(installments.data ?? []).length ? (
        <>
          <Text variant="labelSmall" style={styles.sectionLabel}>
            INSTALLMENTS
          </Text>
          <View style={{ gap: 10 }}>
            {(installments.data ?? []).map((item: Installment) => (
              <Card
                key={item.id}
                mode="contained"
                style={[styles.card, { backgroundColor: theme.colors.surface, borderLeftColor: INSTALLMENT_COLORS[item.status] }]}
              >
                <Card.Content style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text variant="titleSmall" style={styles.bold}>
                      Installment {item.installment_number}
                    </Text>
                    <Text variant="bodySmall" style={styles.muted}>
                      Due {formatDate(item.due_date)}
                    </Text>
                  </View>
                  <View style={{ alignItems: 'flex-end', gap: 4 }}>
                    <Text variant="titleSmall" style={styles.bold}>
                      {formatINR(item.amount)}
                    </Text>
                    <Chip
                      compact
                      style={{ backgroundColor: `${INSTALLMENT_COLORS[item.status]}22` }}
                      textStyle={{ color: INSTALLMENT_COLORS[item.status], fontWeight: '700', fontSize: 10 }}
                    >
                      {item.status}
                    </Chip>
                  </View>
                </Card.Content>
              </Card>
            ))}
          </View>
        </>
      ) : null}

      <Text variant="labelSmall" style={styles.sectionLabel}>
        RECEIPTS
      </Text>
      {receipts.length === 0 ? (
        <EmptyState title="No receipts yet" message="A receipt is issued for every payment you make." />
      ) : null}
      <View style={{ gap: 10 }}>
        {receipts.map(({ receipt, payment }) => (
          <Card key={receipt.id} mode="contained" style={{ backgroundColor: theme.colors.surface }}>
            <Card.Content style={{ gap: 8 }}>
              <View style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text variant="titleSmall" style={styles.bold}>
                    {receipt.receipt_number}
                  </Text>
                  <Text variant="bodySmall" style={styles.muted}>
                    {formatDate(receipt.issue_date)} · {formatINR(payment.amount)} · {payment.payment_mode}
                  </Text>
                </View>
              </View>
              <View style={styles.actions}>
                <Button
                  compact
                  mode="contained-tonal"
                  icon={Download}
                  disabled={!receipt.pdf_url}
                  onPress={() => openExternal(receipt.pdf_url)}
                >
                  PDF
                </Button>
                <Button compact mode="text" onPress={() => shareReceipt(receipt, payment)}>
                  Share
                </Button>
                <Button
                  compact
                  mode="text"
                  onPress={() =>
                    copyToClipboard(
                      `Receipt ${receipt.receipt_number} · ${formatINR(payment.amount)} · ${formatDate(receipt.issue_date)}`,
                    )
                  }
                >
                  Copy
                </Button>
              </View>
            </Card.Content>
          </Card>
        ))}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  sectionLabel: { marginTop: 20, marginBottom: 8, letterSpacing: 0.8, opacity: 0.7 },
  card: { borderRadius: 14, borderLeftWidth: 4 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  actions: { flexDirection: 'row', gap: 4, flexWrap: 'wrap' },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default StudentFeesScreen;
