import { useQuery } from '@tanstack/react-query';
import * as Haptics from 'expo-haptics';
import { Banknote, Check, Wallet } from 'lucide-react-native';
import React, { useMemo, useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { Button, Card, Chip, Snackbar, Text, TextInput, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { ApiError } from '@/api/client';
import { financeApi } from '@/api/domain.api';
import { BRAND, INSTALLMENT_COLORS } from '@/constants/theme';
import type { Installment, Payment } from '@/types';
import { formatDate, formatINR, formatTime } from '@/utils/format';

const MODES = ['CASH', 'UPI', 'CARD', 'BANK_TRANSFER'] as const;

const AccountantHomeScreen = () => {
  const theme = useTheme();
  const [toast, setToast] = useState<string | null>(null);
  const [collecting, setCollecting] = useState<Installment | null>(null);
  const [amount, setAmount] = useState('');
  const [mode, setMode] = useState<(typeof MODES)[number]>('CASH');

  const installments = useQuery({ queryKey: ['installments'], queryFn: () => financeApi.installments() });
  const payments = useQuery({ queryKey: ['payments'], queryFn: () => financeApi.payments() });

  const summary = useMemo(() => {
    const rows = installments.data ?? [];
    const pending = rows.filter((i) => i.status !== 'PAID');
    const overdue = pending.filter((i) => i.status === 'OVERDUE');
    return {
      pending,
      overdue,
      due: pending.reduce((s, i) => s + Number(i.amount), 0),
      overdueValue: overdue.reduce((s, i) => s + Number(i.amount), 0),
    };
  }, [installments.data]);

  const collectedToday = useMemo(() => {
    const today = new Date().toDateString();
    return (payments.data ?? [])
      .filter((p) => new Date(p.payment_date).toDateString() === today)
      .reduce((s, p) => s + Number(p.amount), 0);
  }, [payments.data]);

  const record = async () => {
    if (!collecting) return;
    const value = Number(amount);
    if (!Number.isFinite(value) || value <= 0) {
      setToast('Enter an amount greater than zero.');
      return;
    }
    try {
      await financeApi.recordPayment({
        student_id: collecting.student,
        installment_id: collecting.id,
        amount: value,
        payment_mode: mode,
      });
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setCollecting(null);
      setAmount('');
      setToast('Payment recorded and receipt issued.');
      await Promise.all([installments.refetch(), payments.refetch()]);
    } catch (err) {
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      setToast(err instanceof ApiError ? err.message : 'Could not record the payment.');
    }
  };

  return (
    <Screen
      onRefresh={() => {
        void installments.refetch();
        void payments.refetch();
      }}
      refreshing={installments.isRefetching}
    >
      <ScreenHeader title="Collection" subtitle="Outstanding fees and quick payment capture" />

      <MetricGrid>
        <MetricCard
          label="Collected today"
          value={formatINR(collectedToday)}
          color={BRAND.emerald500}
        />
        <MetricCard label="Outstanding" value={formatINR(summary.due)} color={BRAND.amber500} />
        <MetricCard
          label="Overdue"
          value={formatINR(summary.overdueValue)}
          color={summary.overdue.length ? BRAND.rose500 : BRAND.emerald500}
        />
      </MetricGrid>

      <Text variant="labelSmall" style={styles.sectionLabel}>
        OUTSTANDING INSTALLMENTS
      </Text>

      {installments.isLoading ? <LoadingState /> : null}
      {installments.isError ? (
        <ErrorState
          message={(installments.error as Error)?.message ?? 'Could not load installments.'}
          onRetry={() => void installments.refetch()}
        />
      ) : null}
      {!installments.isLoading && summary.pending.length === 0 ? (
        <EmptyState
          icon={<Check size={28} color={theme.colors.secondary} />}
          title="Everything is collected"
          message="No outstanding installments in your branch."
        />
      ) : null}

      <View style={{ gap: 10 }}>
        {summary.pending.map((item) => (
          <Card
            key={item.id}
            mode="contained"
            style={[
              styles.card,
              { backgroundColor: theme.colors.surface, borderLeftColor: INSTALLMENT_COLORS[item.status] },
            ]}
          >
            <Card.Content style={{ gap: 8 }}>
              <View style={styles.header}>
                <View style={{ flex: 1 }}>
                  <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                    {item.student_name}
                  </Text>
                  <Text variant="bodySmall" style={styles.muted}>
                    Installment {item.installment_number} Â· due {formatDate(item.due_date)}
                  </Text>
                </View>
                <Text variant="titleSmall" style={styles.bold}>
                  {formatINR(item.amount)}
                </Text>
              </View>
              <View style={styles.actions}>
                {item.status === 'OVERDUE' ? (
                  <Chip
                    compact
                    style={{ backgroundColor: `${BRAND.rose500}22` }}
                    textStyle={{ color: BRAND.rose500, fontWeight: '700', fontSize: 10 }}
                  >
                    Overdue
                  </Chip>
                ) : null}
                <View style={{ flex: 1 }} />
                <Button
                  compact
                  mode="contained"
                  icon={Banknote}
                  onPress={() => {
                    setCollecting(item);
                    setAmount(String(item.amount));
                  }}
                >
                  Collect
                </Button>
              </View>
            </Card.Content>
          </Card>
        ))}
      </View>

      <Text variant="labelSmall" style={styles.sectionLabel}>
        RECENT PAYMENTS
      </Text>
      <View style={{ gap: 8 }}>
        {(payments.data ?? []).slice(0, 10).map((p: Payment) => (
          <Card key={p.id} mode="contained" style={{ backgroundColor: theme.colors.surface }}>
            <Card.Content style={styles.header}>
              <View style={{ flex: 1 }}>
                <Text variant="bodyMedium" style={styles.bold} numberOfLines={1}>
                  {p.student_name}
                </Text>
                <Text variant="bodySmall" style={styles.muted}>
                  {p.payment_mode} Â· {p.reference_number} Â· {formatTime(p.payment_date)}
                </Text>
              </View>
              <Text variant="bodyMedium" style={{ ...styles.bold, color: BRAND.emerald500 }}>
                {formatINR(p.amount)}
              </Text>
            </Card.Content>
          </Card>
        ))}
      </View>

      <Snackbar visible={!!toast} onDismiss={() => setToast(null)} duration={3500}>
        {toast}
      </Snackbar>

      <CollectDialog
        installment={collecting}
        amount={amount}
        onAmountChange={setAmount}
        mode={mode}
        onModeChange={setMode}
        onClose={() => setCollecting(null)}
        onConfirm={() => {
          Alert.alert('Record payment?', `${formatINR(Number(amount))} via ${mode}. A receipt will be issued.`, [
            { text: 'Cancel', style: 'cancel', onPress: () => setCollecting(null) },
            { text: 'Record', onPress: () => void record() },
          ]);
        }}
      />
    </Screen>
  );
};

const CollectDialog = ({
  installment,
  amount,
  onAmountChange,
  mode,
  onModeChange,
  onClose,
  onConfirm,
}: {
  installment: Installment | null;
  amount: string;
  onAmountChange: (v: string) => void;
  mode: (typeof MODES)[number];
  onModeChange: (m: (typeof MODES)[number]) => void;
  onClose: () => void;
  onConfirm: () => void;
}) => {
  const theme = useTheme();
  if (!installment) return null;
  return (
    <Card
      mode="contained"
      style={[
        styles.dialog,
        { position: 'absolute', left: 16, right: 16, bottom: 24, backgroundColor: theme.colors.surface },
      ]}
    >
      <Card.Content style={{ gap: 10 }}>
        <Text variant="titleSmall" style={styles.bold}>
          Collect from {installment.student_name}
        </Text>
        <TextInput
          mode="outlined"
          label="Amount"
          value={amount}
          onChangeText={onAmountChange}
          keyboardType="decimal-pad"
        />
        <View style={styles.modes}>
          {MODES.map((m) => (
            <Chip
              key={m}
              selected={mode === m}
              onPress={() => onModeChange(m)}
              style={styles.chip}
            >
              {m}
            </Chip>
          ))}
        </View>
        <View style={styles.dialogActions}>
          <Button onPress={onClose}>Cancel</Button>
          <Button mode="contained" icon={Wallet} onPress={onConfirm}>
            Record
          </Button>
        </View>
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  sectionLabel: { marginTop: 20, marginBottom: 8, letterSpacing: 0.8, opacity: 0.7 },
  card: { borderRadius: 14, borderLeftWidth: 4 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  modes: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  chip: { borderRadius: 999 },
  dialog: { borderRadius: 20, elevation: 8 },
  dialogActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default AccountantHomeScreen;

