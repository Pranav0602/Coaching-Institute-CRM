import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { CalendarClock, Check, MessageCircle, Phone, X } from 'lucide-react-native';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, Chip, IconButton, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { leadsApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import type { Lead } from '@/types';
import { formatDateTime, formatRelative } from '@/utils/format';
import { callPhone, openWhatsApp } from '@/utils/linking';

const FollowUpsScreen = () => {
  const theme = useTheme();
  const queryClient = useQueryClient();

  const followUps = useQuery({
    queryKey: ['follow-ups'],
    queryFn: () => leadsApi.followUps(),
  });

  // Joined client-side: the follow-up payload carries only the lead's id.
  const leads = useQuery({
    queryKey: ['leads', 'list'],
    queryFn: () => leadsApi.list(),
  });

  const update = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'COMPLETED' | 'CANCELLED' }) =>
      leadsApi.updateFollowUp(id, { status }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['follow-ups'] }),
  });

  const byId = new Map<string, Lead>((leads.data ?? []).map((l) => [l.id, l]));
  const all = followUps.data ?? [];
  const pending = all.filter((f) => f.status === 'PENDING');
  const overdue = pending.filter((f) => new Date(f.scheduled_date).getTime() < Date.now());

  return (
    <Screen
      onRefresh={() => {
        void followUps.refetch();
        void leads.refetch();
      }}
      refreshing={followUps.isRefetching}
    >
      <ScreenHeader title="Follow-ups" subtitle="Scheduled callbacks and demo reminders" />

      <MetricGrid>
        <MetricCard label="Pending" value={pending.length} color={BRAND.indigo500} />
        <MetricCard label="Overdue" value={overdue.length} color={BRAND.rose500} />
        <MetricCard label="All" value={all.length} color={BRAND.emerald500} />
      </MetricGrid>

      {followUps.isLoading ? <LoadingState /> : null}
      {followUps.isError ? (
        <ErrorState
          message={(followUps.error as Error)?.message ?? 'Could not load follow-ups.'}
          onRetry={() => void followUps.refetch()}
        />
      ) : null}
      {!followUps.isLoading && !followUps.isError && all.length === 0 ? (
        <EmptyState
          icon={<CalendarClock size={30} color={theme.colors.onSurfaceVariant} />}
          title="No follow-ups scheduled"
          message="Callbacks and demo reminders you schedule will appear here."
        />
      ) : null}

      <View style={{ gap: 12 }}>
        {[...pending, ...all.filter((f) => f.status !== 'PENDING')].map(item => {
          const lead = byId.get(item.lead);
          const late = item.status === 'PENDING' && new Date(item.scheduled_date).getTime() < Date.now();
          const accent =
            item.status !== 'PENDING' ? BRAND.emerald500 : late ? BRAND.rose500 : BRAND.indigo500;
          return (
            <Card
              key={item.id}
              mode="contained"
              onPress={lead ? () => router.push({ pathname: '/(app)/lead/[id]', params: { id: lead.id } }) : undefined}
              style={[styles.card, { backgroundColor: theme.colors.surface, borderLeftColor: accent }]}
            >
              <Card.Content style={{ gap: 8 }}>
                <View style={styles.header}>
                  <View style={{ flex: 1 }}>
                    <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                      {lead?.name ?? 'Lead no longer available'}
                    </Text>
                    <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                      {lead?.course_title || lead?.target_course || 'Course not chosen'}
                    </Text>
                    <Text variant="bodySmall" style={styles.muted}>
                      {formatDateTime(item.scheduled_date)} · {formatRelative(item.scheduled_date)}
                    </Text>
                  </View>
                  <Chip
                    compact
                    style={{ backgroundColor: `${accent}22` }}
                    textStyle={{ color: accent, fontWeight: '700', fontSize: 11 }}
                  >
                    {late ? 'Overdue' : item.status}
                  </Chip>
                </View>

                {item.remarks ? (
                  <Text variant="bodySmall" style={styles.muted} numberOfLines={3}>
                    {item.remarks}
                  </Text>
                ) : null}

                <View style={styles.actions}>
                  {lead ? (
                    <>
                      <Button compact mode="contained-tonal" icon={Phone} onPress={() => callPhone(lead.phone)}>
                        Call
                      </Button>
                      <Button
                        compact
                        mode="text"
                        icon={MessageCircle}
                        onPress={() => openWhatsApp(lead.phone, `Hello ${lead.name}, `)}
                      >
                        WhatsApp
                      </Button>
                    </>
                  ) : null}
                  {item.status === 'PENDING' ? (
                    <View style={{ flexDirection: 'row', marginLeft: 'auto' }}>
                      <IconButton
                        icon={Check}
                        size={18}
                        onPress={() => update.mutate({ id: item.id, status: 'COMPLETED' })}
                        accessibilityLabel="Mark complete"
                      />
                      <IconButton
                        icon={X}
                        size={18}
                        onPress={() => update.mutate({ id: item.id, status: 'CANCELLED' })}
                        accessibilityLabel="Cancel follow-up"
                      />
                    </View>
                  ) : null}
                </View>
              </Card.Content>
            </Card>
          );
        })}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  card: { borderRadius: 16, borderLeftWidth: 4 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default FollowUpsScreen;
