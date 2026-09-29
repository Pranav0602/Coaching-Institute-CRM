import { useQuery } from '@tanstack/react-query';
import React, { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Card, Chip, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { timetableApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';
import { DAY_ORDER, currentDayCode, dayLabel, formatTime } from '@/utils/format';

const StudentScheduleScreen = () => {
  const theme = useTheme();
  const { user } = useAuth();
  const today = currentDayCode();
  const [selected, setSelected] = useState(today);

  const weekly = useQuery({
    queryKey: ['timetable', 'student'],
    queryFn: () => timetableApi.weekly({}),
  });

  const entries = weekly.data?.[selected] ?? [];

  const totalHours = useMemo(
    () =>
      entries.reduce((hours, entry) => {
        const [sh, sm] = entry.start_time.split(':').map(Number);
        const [eh, em] = entry.end_time.split(':').map(Number);
        return hours + Math.max(0, eh + em / 60 - (sh + sm / 60));
      }, 0),
    [entries],
  );

  return (
    <Screen onRefresh={() => void weekly.refetch()} refreshing={weekly.isRefetching}>
      <ScreenHeader
        title="Schedule"
        subtitle={`${user?.branch_name ?? 'Your branch'} · ${Math.round(totalHours * 10) / 10}h on ${dayLabel(selected)}`}
      />

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.days}>
        {DAY_ORDER.map((day, i) => {
          const count = weekly.data?.[day]?.length ?? 0;
          return (
            <Chip
              key={day}
              selected={selected === day}
              onPress={() => setSelected(day)}
              style={[
                styles.dayChip,
                selected === day && { backgroundColor: `${BRAND.indigo500}22`, borderColor: BRAND.indigo500 },
              ]}
              textStyle={{ color: selected === day ? BRAND.indigo500 : theme.colors.onSurfaceVariant }}
            >
              {i < 5 ? dayLabel(day).slice(0, 3) : dayLabel(day).slice(0, 2)}
              {count ? ` · ${count}` : ''}
            </Chip>
          );
        })}
      </ScrollView>

      {weekly.isLoading ? <LoadingState /> : null}
      {weekly.isError ? (
        <ErrorState
          message={(weekly.error as Error)?.message ?? 'Could not load the timetable.'}
          onRetry={() => void weekly.refetch()}
        />
      ) : null}
      {!weekly.isLoading && !weekly.isError && entries.length === 0 ? (
        <EmptyState title={`Nothing on ${dayLabel(selected)}`} message="No classes are scheduled for this day." />
      ) : null}

      <View style={{ gap: 10 }}>
        {entries.map(entry => (
          <Card
            key={entry.id}
            mode="contained"
            style={{ backgroundColor: theme.colors.surface, borderLeftWidth: 4, borderLeftColor: BRAND.indigo500 }}
          >
            <Card.Content style={styles.row}>
              <View style={styles.timeBox}>
                <Text variant="labelMedium" style={styles.time}>
                  {formatTime(entry.start_time)}
                </Text>
                <Text variant="labelSmall" style={styles.muted}>
                  {formatTime(entry.end_time)}
                </Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                  {entry.subject_title}
                </Text>
                <Text variant="bodySmall" style={styles.muted} numberOfLines={2}>
                  {entry.batch_name}
                  {entry.teacher_name ? ` · ${entry.teacher_name}` : ''}
                </Text>
                {entry.room_number ? (
                  <Text variant="bodySmall" style={styles.muted}>
                    Room {entry.room_number}
                  </Text>
                ) : null}
              </View>
            </Card.Content>
          </Card>
        ))}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  days: { gap: 8, paddingVertical: 4, paddingRight: 16 },
  dayChip: { borderRadius: 999 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  timeBox: { width: 62 },
  time: { fontWeight: '800' },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default StudentScheduleScreen;
