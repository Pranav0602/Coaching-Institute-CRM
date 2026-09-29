import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { BookOpen, FileText } from 'lucide-react-native';
import React, { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Card, Chip, Searchbar, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { MetricCard, MetricGrid, ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { coursesApi, ragApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import { useDebounced } from '@/hooks';
import type { KnowledgeDocument } from '@/types';
import { formatINR } from '@/utils/format';

const ALL = 'ALL';

const SyllabiScreen = () => {
  const theme = useTheme();
  const [query, setQuery] = useState('');
  const [discipline, setDiscipline] = useState(ALL);
  const search = useDebounced(query);

  const courses = useQuery({ queryKey: ['courses'], queryFn: () => coursesApi.list() });
  const guides = useQuery({
    queryKey: ['syllabi'],
    queryFn: () => ragApi.documents({ category: 'STUDY_GUIDE' }),
  });  const catalogue = useQuery({
    queryKey: ['master-catalogue'],
    queryFn: () => coursesApi.masterCatalogue(),
  });

  const docByCourse = useMemo(() => {
    const map = new Map<string, KnowledgeDocument>();
    for (const doc of guides.data ?? []) {
      const courseId = doc.metadata_json?.course_id;
      if (courseId) map.set(String(courseId), doc);
    }
    return map;
  }, [guides.data]);

  const master = useMemo(
    () => (catalogue.data ?? []).find((d) => d.metadata_json?.doc_type === 'MASTER_CATALOGUE') ?? null,
    [catalogue.data],
  );

  const disciplines = useMemo(
    () => [ALL, ...new Set((courses.data ?? []).map((c) => c.field_of_engineering).filter(Boolean) as string[])],
    [courses.data],
  );

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return (courses.data ?? []).filter((course) => {
      if (discipline !== ALL && course.field_of_engineering !== discipline) return false;
      if (!term) return true;
      const doc = docByCourse.get(String(course.id));
      const tools = (doc?.metadata_json?.tools ?? []).join(' ').toLowerCase();
      return (
        course.title.toLowerCase().includes(term) ||
        course.code.toLowerCase().includes(term) ||
        (course.field_of_engineering ?? '').toLowerCase().includes(term) ||
        tools.includes(term) ||
        (doc?.content ?? '').toLowerCase().includes(term)
      );
    });
  }, [courses.data, discipline, docByCourse, search]);

  const loading = courses.isLoading || guides.isLoading;

  return (
    <Screen
      onRefresh={() => {
        void courses.refetch();
        void guides.refetch();
        void catalogue.refetch();
      }}
      refreshing={courses.isRefetching}
    >
      <ScreenHeader
        title="Course Syllabi"
        subtitle="Answer curriculum, tool, duration and fee questions while the prospect is on the line"
      />

      <MetricGrid>
        <MetricCard label="Courses" value={courses.data?.length ?? 0} color={BRAND.indigo500} />
        <MetricCard label="Syllabi ready" value={docByCourse.size} color={BRAND.emerald500} />
        <MetricCard label="Master catalogue" value={master ? 'Ready' : '—'} color={BRAND.amber500} />
      </MetricGrid>

      {master ? (
        <Card
          mode="contained"
          onPress={() => router.push({ pathname: '/(app)/syllabus', params: { courseId: 'master' } })}
          style={[styles.master, { backgroundColor: theme.colors.surfaceVariant }]}
        >
          <Card.Content style={styles.masterRow}>
            <FileText size={20} color={theme.colors.primary} />
            <View style={{ flex: 1 }}>
              <Text variant="titleSmall" style={styles.bold}>
                Master syllabus &amp; curriculum catalogue
              </Text>
              <Text variant="bodySmall" style={styles.muted} numberOfLines={2}>
                {master.title} · {master.chunks_count} indexed sections
              </Text>
            </View>
          </Card.Content>
        </Card>
      ) : null}

      <Searchbar
        placeholder="Search course, code, software or topic"
        value={query}
        onChangeText={setQuery}
        style={styles.search}
        inputStyle={styles.searchInput}
      />

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filters}>
        {disciplines.map((d) => (
          <Chip
            key={d}
            selected={discipline === d}
            onPress={() => setDiscipline(d)}
            style={styles.chip}
          >
            {d === ALL ? 'All domains' : d}
          </Chip>
        ))}
      </ScrollView>

      {loading ? <LoadingState label="Loading syllabi…" /> : null}
      {courses.isError ? (
        <ErrorState
          message={(courses.error as Error)?.message ?? 'Could not load courses.'}
          onRetry={() => void courses.refetch()}
        />
      ) : null}
      {!loading && filtered.length === 0 ? (
        <EmptyState
          icon={<BookOpen size={30} color={theme.colors.onSurfaceVariant} />}
          title="No courses match"
          message="Try a different software name, course code or domain."
        />
      ) : null}

      <View style={styles.grid}>
        {filtered.map((course) => {
          const doc = docByCourse.get(String(course.id));
          const tools = doc?.metadata_json?.tools ?? [];
          return (
            <Card
              key={course.id}
              mode="contained"
              style={[styles.course, { backgroundColor: theme.colors.surface }]}
            >
              <Card.Content style={{ gap: 8 }}>
                <Text variant="titleSmall" style={styles.bold} numberOfLines={2}>
                  {course.title}
                </Text>
                <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                  {course.code}
                  {course.field_of_engineering ? ` · ${course.field_of_engineering}` : ''}
                </Text>
                <Text variant="bodySmall" style={styles.muted}>
                  {course.duration_months} months · {formatINR(course.total_fee)}
                </Text>

                {tools.length ? (
                  <View style={styles.tools}>
                    {tools.slice(0, 3).map((tool) => (
                      <Chip key={tool} compact style={styles.toolChip} textStyle={styles.toolText}>
                        {tool}
                      </Chip>
                    ))}
                    {tools.length > 3 ? (
                      <Chip compact style={styles.toolChip} textStyle={styles.toolText}>
                        +{tools.length - 3}
                      </Chip>
                    ) : null}
                  </View>
                ) : (
                  <Text variant="labelSmall" style={{ color: BRAND.amber500 }}>
                    Syllabus pending
                  </Text>
                )}

                <Card.Actions style={{ paddingHorizontal: 0 }}>
                  <Text
                    variant="labelLarge"
                    style={{ color: theme.colors.primary, fontWeight: '700' }}
                    onPress={() =>
                      router.push({ pathname: '/(app)/syllabus', params: { courseId: String(course.id) } })
                    }
                  >
                    View full syllabus
                  </Text>
                </Card.Actions>
              </Card.Content>
            </Card>
          );
        })}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  master: { marginTop: 16, borderRadius: 16 },
  masterRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  search: { marginTop: 16, borderRadius: 12 },
  searchInput: { minHeight: 0 },
  filters: { gap: 8, paddingVertical: 12, paddingRight: 16 },
  chip: { borderRadius: 999 },
  grid: { gap: 12 },
  course: { borderRadius: 16 },
  tools: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  toolChip: { height: 26 },
  toolText: { fontSize: 10, marginVertical: 0 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default SyllabiScreen;
