import React from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { ActivityIndicator, Text, useTheme } from 'react-native-paper';

interface Props {
  children: React.ReactNode;
  /** Vertical rhythm between stacked children. */
  gap?: number;
  style?: StyleProp<ViewStyle>;
}

export const Stack = ({ children, gap = 12, style }: Props) => {
  const items = React.Children.toArray(children).filter(Boolean);
  return (
    <View style={[styles.stack, { gap }, style]}>
      {items.map((child, i) => (
        <View key={i}>{child}</View>
      ))}
    </View>
  );
};

export const Row = ({
  children,
  gap = 8,
  style,
  wrap = false,
  align = 'center',
}: Props & { wrap?: boolean; align?: ViewStyle['alignItems'] }) => {
  const items = React.Children.toArray(children).filter(Boolean);
  return (
    <View
      style={[
        { flexDirection: 'row', alignItems: align, gap, flexWrap: wrap ? 'wrap' : 'nowrap' },
        style,
      ]}
    >
      {items.map((child, i) => (
        <View key={i} style={wrap ? undefined : { flexShrink: 1 }}>
          {child}
        </View>
      ))}
    </View>
  );
};

export const Divider = ({ style }: { style?: StyleProp<ViewStyle> }) => {
  const theme = useTheme();
  return <View style={[styles.divider, { backgroundColor: theme.colors.outlineVariant }, style]} />;
};

export const LoadingState = ({ label = 'Loading…' }: { label?: string }) => (
  <View style={styles.centered}>
    <ActivityIndicator size="large" />
    <Text variant="bodyMedium" style={styles.centeredText}>
      {label}
    </Text>
  </View>
);

export const EmptyState = ({
  icon,
  title,
  message,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  message?: string;
  action?: React.ReactNode;
}) => {
  const theme = useTheme();
  return (
    <View style={styles.centered}>
      {icon ? <View style={{ marginBottom: 12 }}>{icon}</View> : null}
      <Text variant="titleMedium" style={styles.centeredText}>
        {title}
      </Text>
      {message ? (
        <Text
          variant="bodyMedium"
          style={[styles.centeredText, { color: theme.colors.onSurfaceVariant, marginTop: 4 }]}
        >
          {message}
        </Text>
      ) : null}
      {action ? <View style={{ marginTop: 16 }}>{action}</View> : null}
    </View>
  );
};

export const ErrorState = ({ message, onRetry }: { message: string; onRetry?: () => void }) => {
  const theme = useTheme();
  return (
    <View style={styles.centered}>
      <Text variant="titleMedium" style={{ color: theme.colors.error }}>
        Something went wrong
      </Text>
      <Text
        variant="bodyMedium"
        style={[styles.centeredText, { color: theme.colors.onSurfaceVariant, marginTop: 4 }]}
      >
        {message}
      </Text>
      {onRetry ? (
        <View style={{ marginTop: 16 }}>
          <Text
            variant="labelLarge"
            onPress={onRetry}
            style={{ color: theme.colors.primary, fontWeight: '700' }}
          >
            Try again
          </Text>
        </View>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  stack: {},
  divider: { height: StyleSheet.hairlineWidth, width: '100%' },
  centered: { alignItems: 'center', justifyContent: 'center', paddingVertical: 48, paddingHorizontal: 24 },
  centeredText: { textAlign: 'center' },
});
