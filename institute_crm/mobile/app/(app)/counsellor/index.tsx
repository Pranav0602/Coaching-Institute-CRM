import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { BookOpen, UserPlus } from 'lucide-react-native';
import React, { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, FAB, Searchbar, Text, useTheme } from 'react-native-paper';

import { LeadCard } from '@/components/leads/LeadCard';
import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { leadsApi } from '@/api/domain.api';
import { PIPELINE_STAGES, STAGE_COLORS, STAGE_DESCRIPTIONS, stageColor } from '@/constants/theme';
import { useDebounced } from '@/hooks';
import { formatNumber } from '@/utils/format';

const PipelineScreen = () => {
  const theme = useTheme();
  const [query, setQuery] = useState('');
  const search = useDebounced(query);

  const counts = useQuery({
    queryKey: ['leads', 'stage-counts'],
    queryFn: () => leadsApi.stageCounts(),
  });

  const leads = useQuery({
    queryKey: ['leads', 'list'],
    queryFn: () => leadsApi.list(),
  });

  const openLeads = useMemo(
    () => (leads.data ?? []).filter((l) => l.stage !== 'Admitted' && l.stage !== 'Lost'),
    [leads.data],
  );

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    const pool = term ? (leads.data ?? []) : openLeads;
    if (!term) return pool;
    return pool.filter(
      (l) =>
        l.name.toLowerCase().includes(term) ||
        l.phone.includes(term) ||
        (l.course_title ?? '').toLowerCase().includes(term) ||
        (l.target_course ?? '').toLowerCase().includes(term),
    );
  }, [leads.data, openLeads, search]);

  const total = Object.values(counts.data ?? {}).reduce((sum, n) => sum + n, 0);
  const needsAttention = (counts.data?.['New'] ?? 0) + (counts.data?.['Contacted'] ?? 0);
  const closing = (counts.data?.['Admission Pending'] ?? 0) + (counts.data?.Admitted ?? 0);

  return (
    <>
      <Screen onRefresh={() => { void leads.refetch(); void counts.refetch(); }} refreshing={leads.isRefetching}>
        <ScreenHeader
          title="Counselling Desk"
          subtitle="Your pipeline, ready for the next call"
          action={
            <Button mode="contained-tonal" icon={UserPlus} onPress={() => router.push('/(app)/new-lead')}>
              New
            </Button>
          }
        />

        <MetricGrid>
          <MetricCard label="Open leads" value={formatNumber(total)} color={theme.colors.primary} />
          <MetricCard label="Need a call" value={formatNumber(needsAttention)} color={STAGE_COLORS.Contacted} />
          <MetricCard label="Closing" value={formatNumber(closing)} color={STAGE_COLORS['Admission Pending']} />
        </MetricGrid>

        <Text variant="labelSmall" style={styles.sectionLabel}>
          PIPELINE
        </Text>
        <View style={styles.stageGrid}>
          {PIPELINE_STAGES.map(stage => {
            const count = counts.data?.[stage] ?? 0;
            return (
              <Card
                key={stage}
                mode="contained"
                onPress={() => router.push('/(app)/counsellor/leads')}
                style={[styles.stageCard, { backgroundColor: theme.colors.surface, borderColor: `${stageColor(stage)}55` }]}
              >
                <Card.Content style={{ paddingVertical: 12, gap: 2 }}>
                  <Text variant="headlineSmall" style={{ fontWeight: '800', color: stageColor(stage) }}>
                    {formatNumber(count)}
                  </Text>
                  <Text variant="labelMedium" style={styles.bold} numberOfLines={1}>
                    {stage}
                  </Text>
                  <Text variant="bodySmall" style={styles.muted} numberOfLines={2}>
                    {STAGE_DESCRIPTIONS[stage]}
                  </Text>
                </Card.Content>
              </Card>
            );
          })}
        </View>

        <Card
          mode="contained"
          onPress={() => router.push('/(app)/counsellor/syllabi')}
          style={[styles.syllabiCard, { backgroundColor: theme.colors.surfaceVariant }]}
        >
          <Card.Content style={styles.syllabiRow}>
            <BookOpen size={22} color={theme.colors.primary} />
            <View style={{ flex: 1 }}>
              <Text variant="titleSmall" style={styles.bold}>
                Course syllabus reference
              </Text>
              <Text variant="bodySmall" style={styles.muted}>
                29 industry syllabi — modules, tools, fees and durations, with a WhatsApp-ready summary.
              </Text>
            </View>
          </Card.Content>
        </Card>

        <Text variant="labelSmall" style={styles.sectionLabel}>
          {query ? 'SEARCH RESULTS' : 'OPEN LEADS'}
        </Text>
        <Searchbar
          placeholder="Search name, phone or course"
          value={query}
          onChangeText={setQuery}
          style={styles.search}
          inputStyle={styles.searchInput}
        />

        {leads.isLoading ? <LoadingState label="Loading your leads…" /> : null}
        {leads.isError ? (
          <ErrorState message={(leads.error as Error)?.message ?? 'Could not load leads.'} onRetry={() => void leads.refetch()} />
        ) : null}
        {!leads.isLoading && !leads.isError && filtered.length === 0 ? (
          <EmptyState
            title={query ? 'No matching leads' : 'No open leads'}
            message={query ? 'Try a different name, number or course.' : 'New enquiries will appear here as they arrive.'}
          />
        ) : null}

        <View style={{ gap: 12 }}>
          {filtered.slice(0, 20).map(lead => (
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
        {filtered.length > 20 ? (
          <Button mode="text" onPress={() => router.push('/(app)/counsellor/leads')}>
            View all {formatNumber(filtered.length)} leads
          </Button>
        ) : null}
      </Screen>
      <FAB
        icon={UserPlus}
        label="New lead"
        onPress={() => router.push('/(app)/new-lead')}
        style={[styles.fab, { backgroundColor: theme.colors.primary }]}
        color={theme.colors.onPrimary}
      />
    </>
  );
};

const styles = StyleSheet.create({
  sectionLabel: { marginTop: 20, marginBottom: 8, letterSpacing: 0.8, opacity: 0.7 },
  stageGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  stageCard: { flexGrow: 1, flexBasis: '47%', borderRadius: 14, borderWidth: 1 },
  syllabiCard: { marginTop: 20, borderRadius: 16 },
  syllabiRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  search: { marginBottom: 12, borderRadius: 12 },
  searchInput: { minHeight: 0 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
  fab: { position: 'absolute', right: 16, bottom: 20, borderRadius: 16 },
});

export default PipelineScreen;
