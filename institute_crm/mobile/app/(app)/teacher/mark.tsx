/**
 * Pick a lecture to mark attendance for.
 *
 * Attendance is driven from the lecture, not the timetable, because that is what
 * the backend exposes a roster for - and a roster is the only way to know which
 * students are actually expected.
 */
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { ClipboardCheck } from 'lucide-react-native';
import React, { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, Chip, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { lecturesApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';
import { formatDate } from '@/utils/format';

const MarkScreen = () => {
  const theme = useTheme();
  const { user } = useAuth();
  const [tab, setTab] = useState<'pending' | 'done'>('pending');

  const lectures = useQuery({ queryKey: ['lectures'], queryFn: () => lecturesApi.list() });

  const mine = useMemo(
    () =>
      (lectures.data ?? []).filter(
        (l) => l.teacher_name === user?.full_name || l.teacher_name === user?.username,
      ),
    [lectures.data, user?.full_name, user?.username],
  );

  const pending = mine.filter((l) => l.status === 'SCHEDULED');
  const done = mine.filter((l) => l.status !== 'SCHEDULED');
  const list = tab === 'pending' ? pending : done;

  return (
    <Screen onRefresh={() => void lectures.refetch()} refreshing={lectures.isRefetching}>
      <ScreenHeader title="Mark attendance" subtitle="Pick a lecture, then mark the roster in one pass" />

      <View style={styles.tabs}>
        <Chip selected={tab === 'pending'} onPress={() => setTab('pending')} style={styles.tab}>
          Pending ({pending.length})
        </Chip>
        <Chip selected={tab === 'done'} onPress={() => setTab('done')} style={styles.tab}>
          Completed ({done.length})
        </Chip>
      </View>

      {lectures.isLoading ? <LoadingState /> : null}
      {lectures.isError ? (
        <ErrorState
          message={(lectures.error as Error)?.message ?? 'Could not load lectures.'}
          onRetry={() => void lectures.refetch()}
        />
      ) : null}
      {!lectures.isLoading && !lectures.isError && list.length === 0 ? (
        <EmptyState
          icon={<ClipboardCheck size={28} color={theme.colors.onSurfaceVariant} />}
          title={tab === 'pending' ? 'Nothing to mark' : 'No completed lectures'}
          message={
            tab === 'pending'
              ? 'Lectures you have conducted appear here ready for attendance.'
              : 'Completed lectures will be listed here for reference.'
          }
        />
      ) : null}

      <View style={{ gap: 10 }}>
        {list.map(lecture => (
          <Card
            key={lecture.id}
            mode="contained"
            style={{ backgroundColor: theme.colors.surface, borderLeftWidth: 4, borderLeftColor: tab === 'pending' ? BRAND.amber500 : BRAND.emerald500 }}
          >
            <Card.Content style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                  {lecture.subject_title}
                </Text>
                <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                  {lecture.batch_name} · {formatDate(lecture.date)}
                </Text>
                <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                  {lecture.topic}
                </Text>
              </View>
              <Button
                compact
                mode="contained"
                disabled={lecture.status === 'CANCELLED'}
                onPress={() =>
                  router.push({ pathname: '/(app)/attendance/[lectureId]', params: { lectureId: lecture.id } })
                }
              >
                {lecture.status === 'COMPLETED' ? 'Review' : 'Mark'}
              </Button>
            </Card.Content>
          </Card>
        ))}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  tabs: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  tab: { borderRadius: 999 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default MarkScreen;
