import { useQuery } from '@tanstack/react-query';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { router } from 'expo-router';
import { ArrowLeft, IdCard, QrCode, UserCheck } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import React, { useCallback, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Card, Snackbar, Text, useTheme } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { SearchBar } from '@/components/common/SearchBar';
import { LoadingState } from '@/components/common/Layout';
import { ApiError } from '@/api/client';
import { studentsApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import type { StudentIdCard } from '@/types';
import { useDebounced } from '@/hooks';
import { formatDate } from '@/utils/format';
import { copyToClipboard, shareText } from '@/utils/linking';

const IdCardsScreen = () => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const [permission, requestPermission] = useCameraPermissions();
  const [scanning, setScanning] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [card, setCard] = useState<StudentIdCard | null>(null);
  const [query, setQuery] = useState('');
  const search = useDebounced(query);

  const students = useQuery({
    queryKey: ['id-card-search', search],
    queryFn: () => studentsApi.list({ search: search || undefined }),
    enabled: !scanning,
  });

  const resolve = useCallback(async (payload: string) => {
    if (!payload) return;
    try {
      const result = await studentsApi.resolveQr(payload);
      if (result.matched && result.student) {
        void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        const detail = await studentsApi.idCard(result.student.id);
        setCard(detail);
        setScanning(false);
        return;
      }
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      setToast(result.detail ?? 'No student matched that code.');
    } catch (err) {
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      setToast(err instanceof ApiError ? err.message : 'Could not read that code.');
    }
  }, []);

  if (scanning) {
    if (!permission?.granted) {
      return (
        <View style={[styles.root, styles.centered, { backgroundColor: theme.colors.background }]}>
          <Text variant="titleMedium" style={styles.bold}>
            Camera access is needed to scan ID cards
          </Text>
          <Text variant="bodyMedium" style={styles.muted}>
            Graphix CRM only uses the camera to read a student ID code.
          </Text>
          <View style={styles.centeredActions}>
            <Button mode="contained" onPress={() => void requestPermission()}>
              Allow camera
            </Button>
            <Button onPress={() => setScanning(false)}>Go back</Button>
          </View>
        </View>
      );
    }

    return (
      <View style={styles.root}>
        <CameraView
          style={StyleSheet.absoluteFill}
          facing="back"
          barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
          onBarcodeScanned={({ data }) => void resolve(data)}
        />
        <View style={[styles.scanOverlay, { paddingTop: insets.top + 12 }]}>
          <Button icon={ArrowLeft} onPress={() => setScanning(false)}>
            Cancel
          </Button>
          <View style={styles.reticle} />
          <Text variant="bodyMedium" style={styles.scanHint}>
            Hold the student&apos;s ID card inside the frame
          </Text>
        </View>
        {toast ? (
          <Snackbar
            visible={!!toast}
            onDismiss={() => setToast(null)}
            style={{ marginBottom: insets.bottom + 20 }}
          >
            {toast}
          </Snackbar>
        ) : null}
      </View>
    );
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      contentContainerStyle={[styles.body, { paddingTop: insets.top + 12, paddingBottom: insets.bottom + 32 }]}
    >
      <View style={styles.header}>
        <Text variant="headlineSmall" style={styles.bold}>
          Student ID cards
        </Text>
        <Button icon={ArrowLeft} onPress={() => router.back()}>
          Back
        </Button>
      </View>

      <Button mode="contained" icon={QrCode} onPress={() => setScanning(true)} contentStyle={{ height: 50 }}>
        Scan an ID card
      </Button>

      <SearchBar
        value={query}
        onChangeText={setQuery}
        placeholder="Search by name or enrollment number"
      />

      {students.isLoading ? <LoadingState /> : null}

      <View style={{ gap: 8 }}>
        {(students.data ?? []).slice(0, 25).map((student, i) => (
          <Card
            key={student.id}
            mode="contained"
            onPress={() => void studentsApi.idCard(student.id).then(setCard)}
            style={{ backgroundColor: theme.colors.surface }}
          >
            <Card.Content style={styles.row}>
              <IdCard size={18} color={theme.colors.primary} />
              <View style={{ flex: 1 }}>
                <Text variant="bodyMedium" style={styles.bold} numberOfLines={1}>
                  {student.user_detail?.full_name || student.user_detail?.username}
                </Text>
                <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                  {student.enrollment_number}
                  {student.batch_name ? ` · ${student.batch_name}` : ''}
                </Text>
              </View>
            </Card.Content>
          </Card>
        ))}
      </View>

      {card ? (
        <Card mode="contained" style={[styles.card, { backgroundColor: theme.colors.surfaceVariant }]}>
          <Card.Content style={{ gap: 8 }}>
            <View style={styles.row}>
              <UserCheck size={20} color={BRAND.emerald500} />
              <Text variant="titleMedium" style={styles.bold}>
                {card.full_name}
              </Text>
            </View>
            <Text variant="bodyMedium">{card.enrollment_number}</Text>
            <Text variant="bodySmall" style={styles.muted}>
              {[card.course_title, card.batch_name, card.branch_name].filter(Boolean).join(' · ')}
            </Text>
            <Text variant="bodySmall" style={styles.muted}>
              DOB {formatDate(card.dob)}
              {card.blood_group ? ` · ${card.blood_group}` : ''}
            </Text>
            <View style={[styles.qrBox, { backgroundColor: theme.colors.surface }]}>
              <QrCode size={96} color={theme.colors.onSurface} />
              <Text variant="bodySmall" style={styles.muted}>
                {card.qr_payload}
              </Text>
            </View>
            <View style={styles.actions}>
              <Button compact mode="contained-tonal" onPress={() => setCard(null)}>
                Close
              </Button>
              <Button compact mode="text" onPress={() => void copyToClipboard(card.qr_payload)}>
                Copy code
              </Button>
              <Button
                compact
                mode="text"
                onPress={() =>
                  void shareText(
                    `${card.full_name}\n${card.enrollment_number}\n${card.qr_payload}`,
                    'Student ID',
                  )
                }
              >
                Share
              </Button>
            </View>
          </Card.Content>
        </Card>
      ) : null}

      <Snackbar visible={!!toast} onDismiss={() => setToast(null)} duration={3500}>
        {toast}
      </Snackbar>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  root: { flex: 1 },
  centered: { alignItems: 'center', justifyContent: 'center', padding: 32, gap: 10 },
  centeredActions: { flexDirection: 'row', gap: 8, marginTop: 12 },
  body: { paddingHorizontal: 16, gap: 14 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  card: { borderRadius: 18 },
  qrBox: { borderRadius: 14, padding: 16, alignItems: 'center', gap: 8, marginTop: 8 },
  actions: { flexDirection: 'row', gap: 4, flexWrap: 'wrap' },
  scanOverlay: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#00000066' },
  reticle: {
    width: 240,
    height: 240,
    borderRadius: 20,
    borderWidth: 3,
    borderColor: '#FFFFFF',
  },
  scanHint: { color: '#FFFFFF', marginTop: 20, textAlign: 'center', paddingHorizontal: 32 },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default IdCardsScreen;
