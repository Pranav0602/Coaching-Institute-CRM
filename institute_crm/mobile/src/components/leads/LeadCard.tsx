/**
 * The lead card - the single most-used surface in the CRM.
 *
 * A counsellor reads this while someone is talking to them on the phone, so the
 * actions that matter mid-call (call, WhatsApp, syllabus) are one tap from the
 * top of the card rather than behind a menu.
 */
import { BookOpen, Mail, MapPin, MessageCircle, Phone, User } from 'lucide-react-native';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, Chip, IconButton, Text, Tooltip, useTheme } from 'react-native-paper';

import { stageColor } from '@/constants/theme';
import type { Lead } from '@/types';
import type { CourseFacts } from '@/utils/counselling';
import { formatRelative, initials, maskPhone } from '@/utils/format';
import { callPhone, openWhatsApp, sendEmail } from '@/utils/linking';

export const LeadCard = ({
  lead,
  onPress,
  onViewSyllabus,
  messagePreview,
}: {
  lead: Lead;
  onPress?: () => void;
  onViewSyllabus?: () => void;
  messagePreview?: CourseFacts | null;
}) => {
  const theme = useTheme();
  const accent = stageColor(lead.stage);

  return (
    <Card
      mode="contained"
      onPress={onPress}
      style={[styles.card, { backgroundColor: theme.colors.surface, borderLeftColor: accent }]}
    >
      <Card.Content style={{ gap: 10 }}>
        <View style={styles.headerRow}>
          <View style={[styles.avatar, { backgroundColor: `${accent}22` }]}>
            <Text style={{ color: accent, fontWeight: '800' }}>{initials(lead.name)}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text variant="titleMedium" style={styles.bold} numberOfLines={1}>
              {lead.name}
            </Text>
            <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
              {lead.target_course || lead.course_title || 'Course not chosen yet'}
            </Text>
          </View>
          <Chip
            compact
            style={{ backgroundColor: `${accent}22` }}
            textStyle={{ color: accent, fontWeight: '700', fontSize: 11 }}
          >
            {lead.stage}
          </Chip>
        </View>

        <View style={styles.metaRow}>
          <Phone size={13} color={theme.colors.onSurfaceVariant} />
          <Text variant="bodySmall" style={styles.muted}>
            {maskPhone(lead.phone)}
          </Text>
          <MapPin size={13} color={theme.colors.onSurfaceVariant} style={{ marginLeft: 12 }} />
          <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
            {lead.branch_name}
          </Text>
        </View>

        <Text variant="bodySmall" style={styles.muted}>
          Added {formatRelative(lead.created_at)}
          {lead.source ? ` · ${lead.source.replace('_', ' ').toLowerCase()}` : ''}
        </Text>

        <View style={styles.actions}>
          <Button
            compact
            mode="contained-tonal"
            icon={Phone}
            onPress={() => callPhone(lead.phone)}
          >
            Call
          </Button>
          <Button
            compact
            mode="contained-tonal"
            icon={MessageCircle}
            onPress={() => openWhatsApp(lead.phone, messagePreview ? '' : `Hello ${lead.name}, `)}
          >
            WhatsApp
          </Button>
          <Button compact mode="text" icon={Mail} onPress={() => sendEmail(lead.email)}>
            Email
          </Button>
          {onViewSyllabus ? (
            <Tooltip title="Course syllabus">
              <IconButton
                icon={BookOpen}
                size={18}
                onPress={onViewSyllabus}
                accessibilityLabel="View course syllabus"
              />
            </Tooltip>
          ) : null}
        </View>
      </Card.Content>
    </Card>
  );
};

/** Compact variant used in the stage picker and search results. */
export const LeadRow = ({ lead, onPress }: { lead: Lead; onPress?: () => void }) => {
  const theme = useTheme();
  const accent = stageColor(lead.stage);
  return (
    <Card
      mode="contained"
      onPress={onPress}
      style={[styles.row, { backgroundColor: theme.colors.surface }]}
    >
      <View style={[styles.rowAccent, { backgroundColor: accent }]} />
      <View style={{ flex: 1, gap: 2 }}>
        <Text variant="bodyLarge" style={styles.bold} numberOfLines={1}>
          {lead.name}
        </Text>
        <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
          {lead.course_title || lead.target_course} · {maskPhone(lead.phone)}
        </Text>
      </View>
      <User size={16} color={theme.colors.onSurfaceVariant} />
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { borderRadius: 16, borderLeftWidth: 4 },
  row: { flexDirection: 'row', alignItems: 'center', borderRadius: 12, overflow: 'hidden' },
  rowAccent: { width: 4, alignSelf: 'stretch' },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  avatar: { width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, alignItems: 'center' },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});
