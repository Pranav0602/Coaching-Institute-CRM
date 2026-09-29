import { useQuery } from '@tanstack/react-query';
import { LogIn, LogOut as LogOutIcon, Phone } from 'lucide-react-native';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, Chip, Button, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { leadsApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import type { Visitor } from '@/types';
import { formatDateTime, formatRelative, maskPhone } from '@/utils/format';
import { callPhone } from '@/utils/linking';

const ReceptionVisitorsScreen = () => {
  const theme = useTheme();

  const visitors = useQuery({ queryKey: ['visitors'], queryFn: () => leadsApi.visitors() });

  const rows = visitors.data ?? [];
  const onSite = rows.filter((v) => !v.check_out);

  return (
    <Screen onRefresh={() => void visitors.refetch()} refreshing={visitors.isRefetching}>
      <ScreenHeader title="Visitor log" subtitle="Everyone currently in the building" />

      <MetricGrid>
        <MetricCard label="On site" value={onSite.length} color={BRAND.emerald500} />
        <MetricCard label="Total logged" value={rows.length} color={BRAND.indigo500} />
      </MetricGrid>

      {visitors.isLoading ? <LoadingState /> : null}
      {visitors.isError ? (
        <ErrorState
          message={(visitors.error as Error)?.message ?? 'Could not load the visitor log.'}
          onRetry={() => void visitors.refetch()}
        />
      ) : null}
      {!visitors.isLoading && rows.length === 0 ? (
        <EmptyState
          icon={<LogIn size={28} color={theme.colors.onSurfaceVariant} />}
          title="No visitors logged"
          message="Sign visitors in from the Desk tab."
        />
      ) : null}

      <View style={{ gap: 10 }}>
        {rows.map((visitor: Visitor) => {
          const here = !visitor.check_out;
          return (
            <Card
              key={visitor.id}
              mode="contained"
              style={[
                styles.card,
                { backgroundColor: theme.colors.surface, borderLeftColor: here ? BRAND.emerald500 : BRAND.slate500 },
              ]}
            >
              <Card.Content style={{ gap: 8 }}>
                <View style={styles.header}>
                  <View style={{ flex: 1 }}>
                    <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                      {visitor.visitor_name}
                    </Text>
                    <Text variant="bodySmall" style={styles.muted} numberOfLines={2}>
                      {visitor.purpose}
                    </Text>
                    <Text variant="bodySmall" style={styles.muted}>
                      {visitor.host_staff_name ? `Host: ${visitor.host_staff_name} · ` : ''}
                      In {formatRelative(visitor.check_in)}
                    </Text>
                  </View>
                  <Chip
                    compact
                    style={{ backgroundColor: `${here ? BRAND.emerald500 : BRAND.slate500}22` }}
                    textStyle={{
                      color: here ? BRAND.emerald500 : BRAND.slate400,
                      fontWeight: '700',
                      fontSize: 10,
                    }}
                  >
                    {here ? 'On site' : 'Left'}
                  </Chip>
                </View>

                <View style={styles.actions}>
                  <Button compact mode="text" icon={Phone} onPress={() => callPhone(visitor.phone)}>
                    {maskPhone(visitor.phone)}
                  </Button>
                  {visitor.check_out ? (
                    <Text variant="bodySmall" style={styles.muted}>
                      Out {formatDateTime(visitor.check_out)}
                    </Text>
                  ) : null}
                </View>
              </Card.Content>
            </Card>
          );
        })}
      </View>

      <View style={{ height: 8 }} />
      <Text variant="bodySmall" style={styles.footnote}>
        <LogOutIcon size={12} style={{ marginRight: 4 }} />
        Sign-out is recorded from the web dashboard.
      </Text>
    </Screen>
  );
};

const styles = StyleSheet.create({
  card: { borderRadius: 14, borderLeftWidth: 4 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  actions: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  footnote: { textAlign: 'center', color: '#94A3B8' },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default ReceptionVisitorsScreen;
