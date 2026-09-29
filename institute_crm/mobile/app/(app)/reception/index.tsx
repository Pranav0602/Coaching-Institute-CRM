import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Haptics from 'expo-haptics';
import { ChevronDown, IdCard, QrCode, UserPlus } from 'lucide-react-native';
import React, { useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { Button, Card, HelperText, Menu, Text, TextInput, useTheme } from 'react-native-paper';

import { ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { ApiError } from '@/api/client';
import { leadsApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';

const ReceptionDeskScreen = () => {
  const theme = useTheme();
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<string | null>(null);
  const [menuVisible, setMenuVisible] = useState(false);

  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [branch, setBranch] = useState<string | null>(null);

  const options = useQuery({ queryKey: ['public-options'], queryFn: () => leadsApi.publicOptions() });
  const branches = options.data?.branches ?? [];
  const nameValid = name.trim().length >= 2;
  const phoneValid = phone.replace(/\D/g, '').length >= 10;

  const create = useMutation({
    mutationFn: () =>
      leadsApi.create({
        name: name.trim(),
        phone: phone.trim(),
        email: '',
        branch: branch as string,
        source: 'WALK_IN',
        stage: 'New',
        target_course: 'General',
        notes: 'Captured at reception',
      }),
    onSuccess: () => {
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setName('');
      setPhone('');
      setToast('Walk-in captured. A counsellor can pick it up from the pipeline.');
      void queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
    onError: (err) => setToast(err instanceof ApiError ? err.message : 'Could not save the enquiry.'),
  });

  const currentBranch = branches.find((b) => b.id === branch);

  return (
    <Screen onRefresh={() => void options.refetch()} refreshing={options.isRefetching}>
      <ScreenHeader title="Reception" subtitle="Walk-ins, visitors and ID cards" />

      <Card mode="contained" style={{ backgroundColor: theme.colors.surface }}>
        <Card.Content style={{ gap: 12 }}>
          <Text variant="titleSmall" style={styles.bold}>
            <UserPlus size={16} style={{ marginRight: 6 }} />
            New walk-in enquiry
          </Text>
          <TextInput
            mode="outlined"
            label="Visitor name"
            value={name}
            onChangeText={setName}
            autoCapitalize="words"
            error={name.length > 0 && !nameValid}
          />
          <TextInput
            mode="outlined"
            label="Phone"
            value={phone}
            onChangeText={setPhone}
            keyboardType="phone-pad"
            error={phone.length > 0 && !phoneValid}
          />
          <Menu
            visible={menuVisible}
            onDismiss={() => setMenuVisible(false)}
            anchor={
              <TextInput
                mode="outlined"
                label="Branch"
                value={currentBranch?.name ?? ''}
                placeholder="Tap to choose"
                onPress={() => setMenuVisible(true)}
                editable={false}
                right={<TextInput.Icon icon={() => <ChevronDown size={18} color={theme.colors.onSurfaceVariant} />} />}
              />
            }
          >
            {branches.map((b) => (
              <Menu.Item
                key={b.id}
                title={b.name}
                onPress={() => {
                  setBranch(b.id);
                  setMenuVisible(false);
                }}
              />
            ))}
          </Menu>

          {options.isLoading ? <Text variant="bodySmall" style={styles.muted}>Loading branchesâ€¦</Text> : null}

          <Button
            mode="contained"
            disabled={!nameValid || !phoneValid || !branch}
            loading={create.isPending}
            onPress={() => {
              Alert.alert('Capture walk-in?', `${name.trim()} Â· ${phone.trim()}`, [
                { text: 'Cancel', style: 'cancel' },
                { text: 'Save', onPress: () => create.mutate() },
              ]);
            }}
            contentStyle={{ height: 48 }}
          >
            Save enquiry
          </Button>
          <HelperText type="info" visible padding="none">
            Reception captures the minimum; a counsellor enriches the record from the pipeline.
          </HelperText>
        </Card.Content>
      </Card>

      <View style={styles.navRow}>
        <NavCard
          icon={IdCard}
          title="Visitor log"
          subtitle="Who is in the building"
          onPress={() => {}}
          disabled
        />
        <NavCard
          icon={QrCode}
          title="ID cards"
          subtitle="Print or show a student QR"
          onPress={() => Alert.alert('Open the ID Cards tab', 'Use the ID Cards tab to scan and print.')}
          color={BRAND.indigo500}
        />
      </View>
    </Screen>
  );
};

const NavCard = ({
  icon: Icon,
  title,
  subtitle,
  onPress,
  color,
  disabled,
}: {
  icon: React.ComponentType<{ size?: number; color?: string }>;
  title: string;
  subtitle: string;
  onPress: () => void;
  color?: string;
  disabled?: boolean;
}) => {
  const theme = useTheme();
  return (
    <Card
      mode="contained"
      onPress={disabled ? undefined : onPress}
      style={[styles.navCard, { backgroundColor: theme.colors.surface, opacity: disabled ? 0.5 : 1 }]}
    >
      <Card.Content style={{ gap: 6 }}>
        <Icon size={22} color={color ?? theme.colors.primary} />
        <Text variant="titleSmall" style={styles.bold}>
          {title}
        </Text>
        <Text variant="bodySmall" style={styles.muted} numberOfLines={2}>
          {subtitle}
        </Text>
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  navRow: { flexDirection: 'row', gap: 12, marginTop: 16 },
  navCard: { flex: 1, borderRadius: 16 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default ReceptionDeskScreen;


