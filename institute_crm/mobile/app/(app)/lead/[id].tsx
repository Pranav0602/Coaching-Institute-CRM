/**
 * Lead detail, reached from any lead card.
 *
 * A counsellor works through this during the call itself, so the actions are
 * immediate and destructive ones (moving stage, converting) are behind an
 * explicit confirmation with the consequence spelled out.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { ArrowLeft, BookOpen, Check, Mail, MessageCircle, Phone, UserCheck } from 'lucide-react-native';
import React, { useState } from 'react';
import { ScrollView, StyleSheet, View, Alert } from 'react-native';
import { Button, Card, Chip, Menu, Text, useTheme } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { LoadingState } from '@/components/common/Layout';
import { InfoRow } from '@/components/common/Primitives';
import { ApiError } from '@/api/client';
import { batchesApi, coursesApi, leadsApi } from '@/api/domain.api';
import { PIPELINE_STAGES, stageColor } from '@/constants/theme';
import type { Lead } from '@/types';
import { courseFacts, prospectSummary } from '@/utils/counselling';
import { formatDate, formatDateTime } from '@/utils/format';
import { callPhone, openWhatsApp, sendEmail } from '@/utils/linking';

const LeadDetail = () => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [menuVisible, setMenuVisible] = useState(false);
  const [pendingStage, setPendingStage] = useState<string | null>(null);

  const lead = useQuery({
    queryKey: ['lead', id],
    queryFn: async () => {
      const all = await leadsApi.list();
      return all.find((l) => l.id === id) ?? null;
    },
    enabled: !!id,
  });

  const syllabus = useQuery({
    queryKey: ['lead-syllabus', lead.data?.course],
    queryFn: () => coursesApi.syllabus(lead.data!.course as string),
    enabled: !!lead.data?.course,
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });

  const courses = useQuery({ queryKey: ['courses'], queryFn: () => coursesApi.list() });
  const batches = useQuery({ queryKey: ['batches'], queryFn: () => batchesApi.list() });

  const moveStage = useMutation({
    mutationFn: (stage: string) => leadsApi.update(id as string, { stage }),
    onSuccess: () => {
      setMenuVisible(false);
      setPendingStage(null);
      void queryClient.invalidateQueries({ queryKey: ['leads'] });
      void queryClient.invalidateQueries({ queryKey: ['lead', id] });
    },
  });

  const convert = useMutation({
    mutationFn: (body: { course_id: string; batch_id: string; agreed_fee: number }) =>
      leadsApi.convert(id as string, body),
    onSuccess: (result) => {
      Alert.alert(
        'Lead converted',
        `${result.enrollment_number} created.\n\nUsername: ${result.username}\nTemporary password: ${result.temporary_password}`,
        [{ text: 'Done', onPress: () => router.back() }],
      );
    },
    onError: (error) =>
      Alert.alert('Could not convert', error instanceof ApiError ? error.message : 'Please try again.'),
  });

  const facts = courseFacts(courses.data?.find((c) => c.id === lead.data?.course) ?? null, syllabus.data ?? null);
  const eligibleBatches = batches.data?.filter((b) => b.course === lead.data?.course) ?? [];
  const record: Lead | null = lead.data ?? null;

  if (lead.isLoading) return <LoadingState label="Loading lead…" />;

  if (!record) {
    return (
      <View style={[styles.missing, { backgroundColor: theme.colors.background }]}>
        <Text variant="titleMedium">This lead is no longer available.</Text>
        <Button onPress={() => router.back()}>Go back</Button>
      </View>
    );
  }

  const confirmStage = (stage: string) => {
    if (stage === record.stage) {
      setMenuVisible(false);
      return;
    }
    // Admitting a stage is the step that makes the lead disappear from the
    // working pipeline, so it gets a confirmation rather than a silent move.
    if (stage === 'Admitted') {
      Alert.alert(
        'Move to Admitted?',
        'The lead will leave your open pipeline. If they have actually joined, convert them instead so a student account is created.',
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Move', onPress: () => moveStage.mutate(stage) },
        ],
      );
      setMenuVisible(false);
      return;
    }
    moveStage.mutate(stage);
  };

  const onConvert = () => {
    if (!record.course) {
      Alert.alert('Choose a course first', 'Assign a course to this lead before converting them.');
      return;
    }
    if (eligibleBatches.length === 0) {
      Alert.alert('No batch available', 'Create a batch for this course before converting.');
      return;
    }
    const course = courses.data?.find((c) => c.id === record.course);
    setPendingStage(eligibleBatches[0].id);
    Alert.alert(
      'Convert to student',
      `${record.name} will be enrolled in ${course?.title} · ${eligibleBatches[0].name}.\n\nA student login and enrollment number will be created.`,
      [
        { text: 'Cancel', style: 'cancel', onPress: () => setPendingStage(null) },
        {
          text: 'Convert',
          onPress: () =>
            convert.mutate({
              course_id: record.course as string,
              batch_id: pendingStage ?? eligibleBatches[0].id,
              agreed_fee: Number(course?.total_fee ?? 0),
            }),
        },
      ],
    );
  };

  return (
    <View style={[styles.root, { backgroundColor: theme.colors.background }]}>
      <View style={[styles.header, { paddingTop: insets.top + 8, borderBottomColor: theme.colors.outlineVariant }]}>
        <Button icon={ArrowLeft} onPress={() => router.back()} style={styles.back}>
          Back
        </Button>
        <Text variant="titleMedium" style={styles.headerTitle} numberOfLines={1}>
          {record.name}
        </Text>
        <Menu
          visible={menuVisible}
          onDismiss={() => setMenuVisible(false)}
          anchor={
            <Button
              compact
              mode="contained-tonal"
              onPress={() => setMenuVisible(true)}
              textColor={stageColor(record.stage)}
            >
              {record.stage}
            </Button>
          }
        >
          {PIPELINE_STAGES.map((stage) => (
            <Menu.Item
              key={stage}
              title={stage}
              onPress={() => confirmStage(stage)}
              leadingIcon={stage === record.stage ? Check : undefined}
            />
          ))}
        </Menu>
      </View>

      <ScrollView
        contentContainerStyle={[styles.body, { paddingBottom: insets.bottom + 32 }]}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.actions}>
          <Button mode="contained" icon={Phone} onPress={() => callPhone(record.phone)}>
            Call
          </Button>
          <Button
            mode="contained-tonal"
            icon={MessageCircle}
            onPress={() => openWhatsApp(record.phone, facts ? prospectSummary(facts) : `Hello ${record.name}, `)}
          >
            WhatsApp
          </Button>
          <Button mode="outlined" icon={Mail} onPress={() => sendEmail(record.email)}>
            Email
          </Button>
        </View>

        <Card mode="contained" style={styles.card}>
          <Card.Content style={{ gap: 4 }}>
            <InfoRow label="Phone" value={record.phone} />
            <InfoRow label="Email" value={record.email || '—'} />
            <InfoRow label="Branch" value={record.branch_name} />
            <InfoRow label="Interested in" value={record.course_title || record.target_course} />
            <InfoRow label="Batch" value={record.batch_name ?? 'Not assigned'} />
            <InfoRow label="Source" value={record.source?.replace('_', ' ') ?? '—'} />
            <InfoRow label="Owner" value={record.lead_owner_name ?? 'Unassigned'} />
            <InfoRow label="Added" value={formatDate(record.created_at)} />
            <InfoRow
              label="Demo"
              value={record.demo_schedule_date ? formatDateTime(record.demo_schedule_date) : 'Not scheduled'}
            />
          </Card.Content>
        </Card>

        {record.notes ? (
          <Card mode="contained" style={styles.card}>
            <Card.Content>
              <Text variant="labelSmall" style={styles.label}>
                NOTES
              </Text>
              <Text variant="bodyMedium">{record.notes}</Text>
            </Card.Content>
          </Card>
        ) : null}

        {facts ? (
          <Card
            mode="contained"
            onPress={() =>
              router.push({ pathname: '/(app)/syllabus', params: { courseId: String(record.course) } })
            }
            style={[styles.card, { backgroundColor: theme.colors.surfaceVariant }]}
          >
            <Card.Content style={styles.syllabusRow}>
              <BookOpen size={20} color={theme.colors.primary} />
              <View style={{ flex: 1 }}>
                <Text variant="titleSmall" style={styles.bold}>
                  {facts.title}
                </Text>
                <Text variant="bodySmall" style={styles.muted}>
                  {facts.duration ?? '—'} · {facts.tools.slice(0, 3).join(', ') || 'Syllabus pending'}
                </Text>
              </View>
            </Card.Content>
          </Card>
        ) : null}

        <Button
          mode="contained-tonal"
          icon={UserCheck}
          onPress={onConvert}
          loading={convert.isPending}
          disabled={record.stage === 'Admitted'}
          contentStyle={{ height: 48 }}
        >
          {record.stage === 'Admitted' ? 'Already admitted' : 'Convert to student'}
        </Button>
      </ScrollView>
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
  actions: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  card: { borderRadius: 16 },
  syllabusRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  label: { letterSpacing: 0.8, opacity: 0.7, marginBottom: 4 },
  missing: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default LeadDetail;
