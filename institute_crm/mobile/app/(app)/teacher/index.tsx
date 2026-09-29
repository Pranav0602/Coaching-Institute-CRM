import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { ClipboardCheck, Clock, MapPin, Users } from 'lucide-react-native';
import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { batchesApi, lecturesApi, timetableApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';
import type { TimetableEntry } from '@/types';
import { currentDayCode, dayLabel, formatTime } from '@/utils/format';

const TeacherTodayScreen = () => {
  const theme = useTheme();
  const { user } = useAuth();

  const batches = useQuery({ queryKey: ['batches'], queryFn: () => batchesApi.list() });
  const mine = useMemo(
    () => (batches.data ?? []).filter((b) => b.teacher_details?.some((t) => t.id === user?.id)),
    [batches.data, user?.id],
  );

  const today = currentDayCode();

  const weekly = useQuery({
    queryKey: ['timetable', 'teacher', user?.id],
    queryFn: () => timetableApi.weekly({ teacher_id: user?.id as string }),
    enabled: !!user?.id,
  });

  const todaysClasses = (weekly.data?.[today] ?? []).filter((entry) => entry.teacher === user?.id);

  const lectures = useQuery({
    queryKey: ['lectures', 'teacher', user?.id],
    queryFn: () => lecturesApi.list(),
  });

  const pendingLectures = useMemo(
    () =>
      (lectures.data ?? []).filter(
        (l) => l.teacher_name === user?.full_name || l.teacher_name === user?.username,
      ),
    [lectures.data, user?.full_name, user?.username],
  );

  return (
    <Screen
      onRefresh={() => {
        void batches.refetch();
        void weekly.refetch();
        void lectures.refetch();
      }}
      refreshing={batches.isRefetching}
    >
      <ScreenHeader title="Today" subtitle={`${dayLabel(today)} · your classes and marking queue`} />

      <MetricGrid>
        <MetricCard label="Classes today" value={todaysClasses.length} color={BRAND.indigo500} />
        <MetricCard label="My batches" value={mine.length} color={BRAND.emerald500} />
        <MetricCard
          label="Awaiting marks"
          value={pendingLectures.filter((l) => l.status === 'SCHEDULED').length}
          color={BRAND.amber500}
        />
      </MetricGrid>

      <Text variant="labelSmall" style={styles.sectionLabel}>
        TODAY&apos;S CLASSES
      </Text>
      {weekly.isLoading ? <LoadingState /> : null}
      {weekly.isError ? (
        <ErrorState message={(weekly.error as Error)?.message ?? 'Could not load your timetable.'} onRetry={() => void weekly.refetch()} />
      ) : null}
      {!weekly.isLoading && !weekly.isError && todaysClasses.length === 0 ? (
        <EmptyState
          icon={<Clock size={28} color={theme.colors.onSurfaceVariant} />}
          title="No classes today"
          message="Enjoy the gap — or mark yesterday's pending attendance."
        />
      ) : null}

      <View style={{ gap: 12 }}>
        {todaysClasses.map((entry) => (
          <ClassCard key={entry.id} entry={entry} />
        ))}
      </View>

      <Text variant="labelSmall" style={styles.sectionLabel}>
        RECENT LECTURES
      </Text>
      {pendingLectures.length === 0 ? (
        <EmptyState title="Nothing to mark" message="Lectures you conduct will appear here for attendance." />
      ) : null}
      <View style={{ gap: 10 }}>
        {pendingLectures.slice(0, 8).map(lecture => (
          <Card key={lecture.id} mode="contained" style={{ backgroundColor: theme.colors.surface }}>
            <Card.Content style={styles.lectureRow}>
              <View style={{ flex: 1 }}>
                <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                  {lecture.subject_title}
                </Text>
                <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                  {lecture.batch_name} · {lecture.date} · {lecture.status}
                </Text>
              </View>
              <Button
                compact
                mode="contained-tonal"
                icon={ClipboardCheck}
                onPress={() =>
                  router.push({ pathname: '/(app)/attendance/[lectureId]', params: { lectureId: lecture.id } })
                }
              >
                Mark
              </Button>
            </Card.Content>
          </Card>
        ))}
      </View>
    </Screen>
  );
};

const ClassCard = ({ entry }: { entry: TimetableEntry }) => {
  const theme = useTheme();
  return (
    <Card mode="contained" style={{ backgroundColor: theme.colors.surface }}>
      <Card.Content style={{ gap: 8 }}>
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
              {entry.subject_title}
            </Text>
            <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
              {entry.batch_name}
            </Text>
          </View>
          <Text variant="labelLarge" style={{ color: theme.colors.primary, fontWeight: '800' }}>
            {formatTime(entry.start_time)}
          </Text>
        </View>
        <View style={styles.metaRow}>
          <Clock size={13} color={theme.colors.onSurfaceVariant} />
          <Text variant="bodySmall" style={styles.muted}>
            {formatTime(entry.start_time)} – {formatTime(entry.end_time)}
          </Text>
          {entry.room_number ? (
            <>
              <MapPin size={13} color={theme.colors.onSurfaceVariant} style={{ marginLeft: 12 }} />
              <Text variant="bodySmall" style={styles.muted}>
                {entry.room_number}
              </Text>
            </>
          ) : null}
          <Users size={13} color={theme.colors.onSurfaceVariant} style={{ marginLeft: 12 }} />
        </View>
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  sectionLabel: { marginTop: 20, marginBottom: 8, letterSpacing: 0.8, opacity: 0.7 },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  lectureRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default TeacherTodayScreen;
