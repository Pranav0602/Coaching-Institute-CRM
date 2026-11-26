import { useQuery } from '@tanstack/react-query';
import { Download } from 'lucide-react-native';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, Chip, Text } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { examsApi } from '@/api/academics.api';
import { useAuth } from '@/context/AuthContext';
import { formatDate } from '@/utils/format';
import { openExternal } from '@/utils/linking';

const StudentAssignmentsScreen = () => {
  const { user } = useAuth();

  const assignments = useQuery({
    queryKey: ['assignments', user?.id],
    queryFn: () => examsApi.assignments(),
  });

  return (
    <Screen
      onRefresh={() => void assignments.refetch()}
      refreshing={assignments.isRefetching}
    >
      <ScreenHeader title="Assignments" subtitle="Your pending and submitted work" />

      {assignments.isLoading ? <LoadingState /> : null}
      {assignments.isError ? (
        <ErrorState
          message={(assignments.error as Error)?.message ?? 'Could not load your assignments.'}
          onRetry={() => void assignments.refetch()}
        />
      ) : null}
      {!assignments.isLoading && !assignments.isError && (assignments.data ?? []).length === 0 ? (
        <EmptyState
          title="No assignments"
          message="Assignments your teachers set will appear here."
        />
      ) : null}

      <View style={{ gap: 10, marginTop: assignments.data?.length ? 12 : 0 }}>
        {(assignments.data ?? []).map(item => (
          <Card key={item.id} mode="contained">
            <Card.Content style={{ gap: 8 }}>
              <View style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                    {item.title}
                  </Text>
                  <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                    {item.subject_title ?? 'Subject'}
                    {item.batch_name ? ` · ${item.batch_name}` : ''}
                  </Text>
                </View>
                <Chip compact style={styles.dueChip} textStyle={styles.dueChipText}>
                  Due {formatDate(item.due_date)}
                </Chip>
              </View>
              {item.description ? (
                <Text variant="bodySmall" style={styles.muted} numberOfLines={2}>
                  {item.description}
                </Text>
              ) : null}
              <View style={styles.metaRow}>
                <Text variant="bodySmall" style={styles.muted}>
                  {item.total_marks} marks
                </Text>
                <Button
                  compact
                  mode="contained-tonal"
                  icon={Download}
                  disabled={!item.file_url}
                  onPress={() => openExternal(item.file_url)}
                >
                  Attachment
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
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  metaRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  dueChip: { backgroundColor: '#EEF2FF' },
  dueChipText: { color: '#4F46E5', fontWeight: '700', fontSize: 11 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default StudentAssignmentsScreen;
