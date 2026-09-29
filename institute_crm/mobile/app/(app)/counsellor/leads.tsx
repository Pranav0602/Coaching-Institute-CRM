import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import React, { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Chip, Searchbar, Text, useTheme } from 'react-native-paper';

import { LeadCard } from '@/components/leads/LeadCard';
import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { leadsApi } from '@/api/domain.api';
import { PIPELINE_STAGES, stageColor } from '@/constants/theme';
import { useDebounced } from '@/hooks';

const ALL = 'ALL';

const LeadsScreen = () => {
  const theme = useTheme();
  const [query, setQuery] = useState('');
  const [stage, setStage] = useState<string>(ALL);
  const search = useDebounced(query);

  const leads = useQuery({
    queryKey: ['leads', 'list', stage === ALL ? undefined : stage],
    queryFn: () => leadsApi.list(stage === ALL ? {} : { stage }),
  });

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return leads.data ?? [];
    return (leads.data ?? []).filter(
      (l) =>
        l.name.toLowerCase().includes(term) ||
        l.phone.includes(term) ||
        (l.email ?? '').toLowerCase().includes(term) ||
        (l.course_title ?? l.target_course ?? '').toLowerCase().includes(term),
    );
  }, [leads.data, search]);

  return (
    <Screen onRefresh={() => void leads.refetch()} refreshing={leads.isRefetching}>
      <ScreenHeader title="Leads" subtitle="Everything in your pipeline" />

      <Searchbar
        placeholder="Search name, number, email or course"
        value={query}
        onChangeText={setQuery}
        style={styles.search}
        inputStyle={styles.searchInput}
      />

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filters}
      >
        <Chip
          selected={stage === ALL}
          onPress={() => setStage(ALL)}
          style={styles.chip}
        >
          All
        </Chip>
        {PIPELINE_STAGES.map((s) => (
          <Chip
            key={s}
            selected={stage === s}
            onPress={() => setStage(s)}
            style={[
              styles.chip,
              stage === s ? { backgroundColor: `${stageColor(s)}22`, borderColor: stageColor(s) } : null,
            ]}
            textStyle={stage === s ? { color: stageColor(s), fontWeight: '700' } : undefined}
          >
            {s}
          </Chip>
        ))}
      </ScrollView>

      {leads.isLoading ? <LoadingState /> : null}
      {leads.isError ? (
        <ErrorState message={(leads.error as Error)?.message ?? 'Could not load leads.'} onRetry={() => void leads.refetch()} />
      ) : null}
      {!leads.isLoading && !leads.isError && filtered.length === 0 ? (
        <EmptyState title="Nothing here" message="No leads match this filter yet." />
      ) : null}

      <View style={{ gap: 12 }}>
        {filtered.map(lead => (
          <LeadCard
            key={lead.id}
            lead={lead}
            onPress={() => router.push({ pathname: '/(app)/lead/[id]', params: { id: lead.id } })}
            onViewSyllabus={
              lead.course
                ? () => router.push({ pathname: '/(app)/syllabus', params: { courseId: lead.course as string } })
                : undefined
            }
          />
        ))}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  search: { borderRadius: 12 },
  searchInput: { minHeight: 0 },
  filters: { gap: 8, paddingVertical: 12, paddingRight: 16 },
  chip: { borderRadius: 999 },
});

export default LeadsScreen;
