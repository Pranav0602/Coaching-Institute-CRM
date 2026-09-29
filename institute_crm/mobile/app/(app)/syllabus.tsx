/**
 * Syllabus viewer.
 *
 * Reached from a lead card, a course row or the syllabi hub, so it takes either a
 * course id or the literal `master` for the catalogue. The headline feature is
 * "Copy prospect summary": a counsellor on a live call needs to answer "which
 * software, how long, how much" in one breath, and pasting a formatted answer is
 * faster and more accurate than reading a bullet list aloud.
 *
 * No markdown library is pulled in: the syllabus format is a known, narrow
 * `##`/`-` shape, so the content is split into sections and rendered as text.
 */
import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { ArrowLeft, Check, Copy, ExternalLink, Share2, TriangleAlert } from 'lucide-react-native';
import * as Clipboard from 'expo-clipboard';
import React, { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Card, Chip, Snackbar, Text, useTheme } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { LoadingState } from '@/components/common/Layout';
import { InfoRow } from '@/components/common/Primitives';
import { coursesApi, ragApi } from '@/api/domain.api';
import { ApiError } from '@/api/client';
import { BRAND } from '@/constants/theme';
import type { KnowledgeDocument } from '@/types';
import { courseFacts, prospectSummary } from '@/utils/counselling';
import { formatDate } from '@/utils/format';
import { openExternal } from '@/utils/linking';

const MASTER = 'master';

/** Splits the stored markdown into `{ heading, body }` sections on `##`. */
const sections = (content: string) =>
  content
    .split(/^##\s+/m)
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .map((chunk) => {
      const newline = chunk.indexOf('\n');
      const heading = (newline === -1 ? chunk : chunk.slice(0, newline)).trim();
      const body = newline === -1 ? '' : chunk.slice(newline + 1).trim();
      return { heading, body };
    });

const SyllabusViewer = () => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const { courseId } = useLocalSearchParams<{ courseId: string }>();
  const [toast, setToast] = useState<string | null>(null);

  const isMaster = courseId === MASTER;

  const course = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => coursesApi.list({ search: '' }).then((all) => all.find((c) => c.id === courseId) ?? null),
    enabled: !isMaster && !!courseId,
  });

  const syllabus = useQuery({
    queryKey: ['syllabus', courseId],
    queryFn: () => coursesApi.syllabus(courseId as string),
    enabled: !isMaster && !!courseId,
    // A course with no syllabus is a real state, not a failure - fall through to
    // the empty message instead of an error banner.
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });

  const master = useQuery({
    queryKey: ['master-catalogue-doc'],
    queryFn: async () => {
      const docs = await coursesApi.masterCatalogue();
      return docs.find((d) => d.metadata_json?.doc_type === 'MASTER_CATALOGUE') ?? docs[0] ?? null;
    },
    enabled: isMaster,
  });

  const doc: KnowledgeDocument | null | undefined = isMaster ? master.data : syllabus.data;
  const facts = useMemo(
    () => (isMaster ? null : courseFacts(course.data ?? null, doc ?? null)),
    [course.data, doc, isMaster],
  );

  const copySummary = async () => {
    if (!facts) return;
    await Clipboard.setStringAsync(prospectSummary(facts));
    setToast('Prospect summary copied — paste it into WhatsApp or email.');
  };

  const shareSummary = async () => {
    if (!facts) return;
    const { shareText } = await import('@/utils/linking');
    await shareText(prospectSummary(facts), facts.title);
  };

  const content = doc?.content ?? '';
  const parsed = useMemo(() => sections(content), [content]);
  const loading = (isMaster ? master.isLoading : syllabus.isLoading) || (!isMaster && course.isLoading);

  return (
    <View style={[styles.root, { backgroundColor: theme.colors.background }]}>
      <View style={[styles.header, { paddingTop: insets.top + 8, borderBottomColor: theme.colors.outlineVariant }]}>
        <Button icon={ArrowLeft} onPress={() => router.back()} style={styles.back}>
          Back
        </Button>
        <Text variant="titleMedium" style={styles.headerTitle} numberOfLines={1}>
          {isMaster ? 'Master catalogue' : facts?.title ?? 'Course syllabus'}
        </Text>
        <View style={{ width: 72 }} />
      </View>

      <ScrollView
        contentContainerStyle={[styles.body, { paddingBottom: insets.bottom + 120 }]}
        showsVerticalScrollIndicator={false}
      >
        {loading ? <LoadingState label="Loading syllabus…" /> : null}

        {!loading && !doc ? (
          <View style={styles.missing}>
            <TriangleAlert size={28} color={BRAND.amber500} />
            <Text variant="titleMedium" style={styles.bold}>
              No syllabus uploaded yet
            </Text>
            <Text variant="bodyMedium" style={styles.muted}>
              Ask your Branch Admin to publish one from the Knowledge Base, and it will appear here
              automatically.
            </Text>
          </View>
        ) : null}

        {doc ? (
          <>
            {facts ? (
              <Card mode="contained" style={styles.card}>
                <Card.Content style={{ gap: 6 }}>
                  <View style={styles.chips}>
                    <Chip compact style={styles.chip} textStyle={styles.chipText}>
                      {facts.code || 'Course'}
                    </Chip>
                    {facts.discipline ? (
                      <Chip compact style={styles.chip} textStyle={styles.chipText}>
                        {facts.discipline}
                      </Chip>
                    ) : null}
                  </View>
                  <InfoRow label="Duration" value={facts.duration ?? '—'} />
                  <InfoRow label="Total fee" value={facts.fee != null ? facts.fee.toLocaleString('en-IN') : '—'} />
                  <InfoRow label="Last updated" value={formatDate(doc.updated_at)} />
                </Card.Content>
              </Card>
            ) : null}

            {facts?.tools.length ? (
              <View style={styles.tools}>
                {facts.tools.map((tool) => (
                  <Chip key={tool} compact style={styles.toolChip} textStyle={styles.chipText}>
                    {tool}
                  </Chip>
                ))}
              </View>
            ) : null}

            {parsed.map((section, i) => (
              <Card key={`${section.heading}-${i}`} mode="contained" style={styles.card}>
                <Card.Content style={{ gap: 6 }}>
                  <Text variant="titleSmall" style={styles.heading}>
                    {section.heading}
                  </Text>
                  <Text variant="bodyMedium" style={{ lineHeight: 21 }}>
                    {section.body}
                  </Text>
                </Card.Content>
              </Card>
            ))}
          </>
        ) : null}
      </ScrollView>

      <View
        style={[
          styles.footer,
          { paddingBottom: insets.bottom + 12, backgroundColor: theme.colors.surface, borderTopColor: theme.colors.outlineVariant },
        ]}
      >
        {facts ? (
          <Button
            mode="contained"
            icon={Copy}
            onPress={copySummary}
            style={styles.flex}
            contentStyle={styles.cta}
          >
            Copy summary
          </Button>
        ) : null}
        {facts ? (
          <Button
            mode="contained-tonal"
            icon={Share2}
            onPress={shareSummary}
            style={styles.iconCta}
            accessibilityLabel="Share prospect summary"
          >
            Share
          </Button>
        ) : null}
        {doc?.source_url ? (
          <Button
            mode="outlined"
            icon={ExternalLink}
            onPress={() => openExternal(doc.source_url)}
            style={styles.flex}
          >
            Source
          </Button>
        ) : null}
      </View>

      <Snackbar
        visible={!!toast}
        onDismiss={() => setToast(null)}
        duration={4000}
        style={{ marginBottom: insets.bottom + 80 }}
      >
        <Text variant="bodySmall">
          <Check size={14} /> {toast}
        </Text>
      </Snackbar>
    </View>
  );
};

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 8,
    paddingBottom: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  back: { marginLeft: -12 },
  headerTitle: { fontWeight: '800', flex: 1, textAlign: 'center' },
  body: { padding: 16, gap: 12 },
  card: { borderRadius: 16 },
  chips: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  chip: { backgroundColor: '#6366F122' },
  toolChip: { backgroundColor: '#10B98122' },
  chipText: { fontSize: 10, color: BRAND.slate50 },
  tools: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  heading: { fontWeight: '800' },
  missing: { alignItems: 'center', gap: 10, paddingVertical: 48, paddingHorizontal: 24 },
  footer: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 16,
    paddingTop: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  flex: { flex: 1 },
  cta: { height: 46 },
  iconCta: { paddingHorizontal: 14 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8', textAlign: 'center' },
});

export default SyllabusViewer;
