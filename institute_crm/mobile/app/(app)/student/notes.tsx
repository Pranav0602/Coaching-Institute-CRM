import { useQuery } from '@tanstack/react-query';
import { FileText, Link2 } from 'lucide-react-native';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, Text } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { studyMaterialsApi } from '@/api/academics.api';
import { useAuth } from '@/context/AuthContext';
import { formatDate } from '@/utils/format';
import { openExternal } from '@/utils/linking';

const StudentNotesScreen = () => {
  const { user } = useAuth();

  const materials = useQuery({
    queryKey: ['study-materials', 'notes', user?.id],
    queryFn: () => studyMaterialsApi.list({ material_type: 'NOTES' }),
  });

  return (
    <Screen
      onRefresh={() => void materials.refetch()}
      refreshing={materials.isRefetching}
    >
      <ScreenHeader title="Notes" subtitle="Class notes your teachers have shared" />

      {materials.isLoading ? <LoadingState /> : null}
      {materials.isError ? (
        <ErrorState
          message={(materials.error as Error)?.message ?? 'Could not load your notes.'}
          onRetry={() => void materials.refetch()}
        />
      ) : null}
      {!materials.isLoading && !materials.isError && (materials.data ?? []).length === 0 ? (
        <EmptyState
          title="No notes yet"
          message="When your teachers upload class notes, they will show up here."
        />
      ) : null}

      <View style={{ gap: 10, marginTop: materials.data?.length ? 12 : 0 }}>
        {(materials.data ?? []).map(item => (
          <Card
            key={item.id}
            mode="contained"
            onPress={() => openExternal(item.file_url ?? item.external_link)}
          >
            <Card.Content style={styles.row}>
              <FileText size={20} color="#6366F1" />
              <View style={{ flex: 1 }}>
                <Text variant="titleSmall" style={styles.bold} numberOfLines={1}>
                  {item.title}
                </Text>
                <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                  {item.subject_title ?? 'Subject'}
                  {item.batch_name ? ` · ${item.batch_name}` : ''}
                  {item.created_at ? ` · ${formatDate(item.created_at)}` : ''}
                </Text>
              </View>
              <Link2 size={16} color="#94A3B8" />
            </Card.Content>
          </Card>
        ))}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default StudentNotesScreen;
