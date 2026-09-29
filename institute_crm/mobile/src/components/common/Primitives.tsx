import React from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { Card, ProgressBar, Text, useTheme } from 'react-native-paper';

import { formatNumber } from '@/utils/format';

export const ScreenHeader = ({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) => (
  <View style={styles.header}>
    <View style={{ flex: 1 }}>
      <Text variant="headlineSmall" style={styles.title}>
        {title}
      </Text>
      {subtitle ? (
        <Text variant="bodyMedium" style={{ color: '#94A3B8' }} numberOfLines={2}>
          {subtitle}
        </Text>
      ) : null}
    </View>
    {action}
  </View>
);

export const SectionHeader = ({ title, action }: { title: string; action?: React.ReactNode }) => {
  const theme = useTheme();
  return (
    <View style={styles.sectionHeader}>
      <Text variant="titleSmall" style={{ color: theme.colors.onSurfaceVariant, fontWeight: '700' }}>
        {title.toUpperCase()}
      </Text>
      {action}
    </View>
  );
};

export const MetricCard = ({
  label,
  value,
  note,
  color,
  progress,
  style,
}: {
  label: string;
  value: React.ReactNode;
  note?: string;
  color?: string;
  progress?: number | null;
  style?: StyleProp<ViewStyle>;
}) => {
  const theme = useTheme();
  const accent = color ?? theme.colors.primary;
  return (
    <Card
      mode="contained"
      style={[styles.metric, { backgroundColor: theme.colors.surface, borderLeftColor: accent }, style]}
    >
      <Card.Content>
        <Text
          variant="labelSmall"
          style={{ color: theme.colors.onSurfaceVariant, textTransform: 'uppercase', letterSpacing: 0.6 }}
          numberOfLines={1}
        >
          {label}
        </Text>
        <Text variant="headlineSmall" style={{ fontWeight: '800', marginTop: 4 }} numberOfLines={1}>
          {value}
        </Text>
        {note ? (
          <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }} numberOfLines={1}>
            {note}
          </Text>
        ) : null}
        {progress !== null && progress !== undefined ? (
          <ProgressBar progress={Math.min(1, Math.max(0, progress / 100))} color={accent} style={styles.progress} />
        ) : null}
      </Card.Content>
    </Card>
  );
};

export const InfoRow = ({
  label,
  value,
  icon,
}: {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
}) => {
  const theme = useTheme();
  return (
    <View style={styles.infoRow}>
      {icon ? <View style={{ marginRight: 8 }}>{icon}</View> : null}
      <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginRight: 12 }}>
        {label}
      </Text>
      <Text variant="bodyMedium" style={{ flex: 1 }} numberOfLines={2}>
        {value ?? '—'}
      </Text>
    </View>
  );
};

export const StatusPill = ({ label, color }: { label: string; color: string }) => (
  <View style={[styles.pill, { backgroundColor: `${color}22`, borderColor: color }]}>
    <View style={[styles.dot, { backgroundColor: color }]} />
    <Text variant="labelSmall" style={{ color, fontWeight: '700' }}>
      {label}
    </Text>
  </View>
);

/** Two-column grid that collapses to one column on a phone. */
export const MetricGrid = ({ children }: { children: React.ReactNode }) => (
  <View style={styles.grid}>{children}</View>
);

export const countLabel = (value: number, singular: string, plural = `${singular}s`): string =>
  `${formatNumber(value)} ${value === 1 ? singular : plural}`;

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
    marginBottom: 16,
  },
  title: { fontWeight: '800' },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
    marginTop: 4,
  },
  metric: { flex: 1, minWidth: 150, borderRadius: 16, borderLeftWidth: 4 },
  metricContent: { paddingVertical: 14 },
  progress: { marginTop: 8, height: 4, borderRadius: 2 },
  infoRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 4 },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
  },
  dot: { width: 6, height: 6, borderRadius: 3 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
});
