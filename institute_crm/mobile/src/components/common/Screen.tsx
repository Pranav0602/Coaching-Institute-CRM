/**
 * The frame every tab screen renders inside.
 *
 * It owns the four things that would otherwise be re-implemented per screen and
 * inevitably drift: the safe-area padding, the header row, the connectivity
 * banner, and the AI assistant affordance.
 */
import { Bot, WifiOff } from 'lucide-react-native';
import { router } from 'expo-router';
import React from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { ActivityIndicator, IconButton, Surface, Text, useTheme } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useNetworkStatus } from '@/hooks';
import { BRAND } from '@/constants/theme';

export const Screen = ({
  children,
  scroll = true,
  onRefresh,
  refreshing = false,
  contentStyle,
}: {
  children: React.ReactNode;
  scroll?: boolean;
  onRefresh?: () => void;
  refreshing?: boolean;
  contentStyle?: object;
}) => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const isOnline = useNetworkStatus();

  const body = (
    <View style={[styles.body, { paddingHorizontal: 16, gap: 12 }, contentStyle]}>{children}</View>
  );

  return (
    <View style={[styles.root, { backgroundColor: theme.colors.background }]}>
      {!isOnline ? (
        <Surface
          elevation={0}
          style={[styles.offline, { backgroundColor: theme.colors.errorContainer }]}
        >
          <WifiOff size={14} color={theme.colors.onErrorContainer} />
          <Text variant="labelSmall" style={{ color: theme.colors.onErrorContainer, fontWeight: '700' }}>
            Offline — showing cached data
          </Text>
        </Surface>
      ) : null}

      {scroll ? (
        <ScrollView
          contentContainerStyle={{ paddingTop: insets.top + 8, paddingBottom: insets.bottom + 96 }}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          refreshControl={
            onRefresh ? (
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={theme.colors.primary}
                colors={[theme.colors.primary]}
              />
            ) : undefined
          }
        >
          {body}
        </ScrollView>
      ) : (
        <View style={{ flex: 1, paddingTop: insets.top + 8 }}>{children}</View>
      )}

      <AssistantFab bottomInset={insets.bottom} />
    </View>
  );
};

const AssistantFab = ({ bottomInset }: { bottomInset: number }) => {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.fab,
        { bottom: bottomInset + 80, backgroundColor: theme.colors.primary },
      ]}
    >
      <IconButton
        icon={({ size, color }) => <Bot size={size} color={color} />}
        onPress={() => router.push('/(app)/assistant')}
        accessibilityLabel="Ask the institute assistant"
      />
    </View>
  );
};

export const ScreenLoader = ({ label = 'Loading…' }: { label?: string }) => {
  const theme = useTheme();
  return (
    <View style={[styles.loader, { backgroundColor: theme.colors.background }]}>
      <ActivityIndicator size="large" color={BRAND.indigo500} />
      <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginTop: 12 }}>
        {label}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  root: { flex: 1 },
  body: { flex: 1 },
  offline: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 6,
  },
  loader: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  fab: { position: 'absolute', right: 16, borderRadius: 999, elevation: 6 },
});
