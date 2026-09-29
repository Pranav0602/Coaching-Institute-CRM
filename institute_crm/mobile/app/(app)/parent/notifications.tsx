import { useQuery } from '@tanstack/react-query';
import { BellRing } from 'lucide-react-native';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, Chip, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { commsApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import type { Announcement, Notification } from '@/types';
import { formatDateTime, formatRelative } from '@/utils/format';

const ParentNotificationsScreen = () => {
  const theme = useTheme();

  const notifications = useQuery({
    queryKey: ['notifications'],
    queryFn: () => commsApi.notifications(),
  });
  const announcements = useQuery({
    queryKey: ['announcements'],
    queryFn: () => commsApi.announcements(),
  });

  return (
    <Screen
      onRefresh={() => {
        void notifications.refetch();
        void announcements.refetch();
      }}
      refreshing={notifications.isRefetching}
    >
      <ScreenHeader title="Notices" subtitle="Announcements and messages for your family" />

      <Text variant="labelSmall" style={styles.sectionLabel}>
        ANNOUNCEMENTS
      </Text>
      {announcements.isLoading ? <LoadingState /> : null}
      {announcements.isError ? (
        <ErrorState
          message={(announcements.error as Error)?.message ?? 'Could not load announcements.'}
          onRetry={() => void announcements.refetch()}
        />
      ) : null}
      {!announcements.isLoading && (announcements.data ?? []).length === 0 ? (
        <EmptyState title="No announcements" message="Institute-wide notices will show up here." />
      ) : null}
      <View style={{ gap: 10 }}>
        {(announcements.data ?? []).map((item: Announcement) => (
          <Card key={item.id} mode="contained" style={{ backgroundColor: theme.colors.surface }}>
            <Card.Content style={{ gap: 6 }}>
              <Text variant="titleSmall" style={styles.bold}>
                {item.title}
              </Text>
              <Text variant="bodyMedium">{item.content}</Text>
              <Text variant="bodySmall" style={styles.muted}>
                {item.publisher_name} · {formatRelative(item.created_at)}
              </Text>
            </Card.Content>
          </Card>
        ))}
      </View>

      <Text variant="labelSmall" style={styles.sectionLabel}>
        MESSAGES
      </Text>
      {notifications.isLoading ? <LoadingState /> : null}
      {!notifications.isLoading && (notifications.data ?? []).length === 0 ? (
        <EmptyState
          icon={<BellRing size={26} color={theme.colors.onSurfaceVariant} />}
          title="No messages"
          message="Batch notices, holiday alerts and fee reminders land here."
        />
      ) : null}
      <View style={{ gap: 10 }}>
        {(notifications.data ?? []).map((item: Notification) => (
          <Card
            key={item.id}
            mode="contained"
            style={[
              styles.card,
              {
                backgroundColor: theme.colors.surface,
                borderLeftColor: item.is_read ? theme.colors.outlineVariant : BRAND.indigo500,
              },
            ]}
          >
            <Card.Content style={{ gap: 6 }}>
              <View style={styles.header}>
                <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                  {item.title}
                </Text>
                {!item.is_read ? (
                  <Chip compact style={styles.unread} textStyle={styles.unreadText}>
                    New
                  </Chip>
                ) : null}
              </View>
              <Text variant="bodyMedium">{item.message}</Text>
              <Text variant="bodySmall" style={styles.muted}>
                {item.batch_name ? `${item.batch_name} · ` : ''}
                {formatDateTime(item.created_at)}
              </Text>
            </Card.Content>
          </Card>
        ))}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  sectionLabel: { marginTop: 16, marginBottom: 8, letterSpacing: 0.8, opacity: 0.7 },
  card: { borderRadius: 14, borderLeftWidth: 4 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  unread: { backgroundColor: `${BRAND.indigo500}22` },
  unreadText: { fontSize: 10, color: BRAND.indigo500, fontWeight: '800' },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default ParentNotificationsScreen;
