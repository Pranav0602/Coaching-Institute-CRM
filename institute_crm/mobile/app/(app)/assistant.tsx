/**
 * AI knowledge assistant, ported from the web's `RagAssistantWidget`.
 *
 * Rendered as a full screen rather than a floating sheet: on a phone the answers
 * are long (module lists, fee tables, refund policy) and a sheet would either
 * truncate them or fight the keyboard.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Bot, Send, Sparkles, Trash2, X } from 'lucide-react-native';
import React, { useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, View } from 'react-native';
import {
  Button,
  Card,
  IconButton,
  Text,
  TextInput,
  useTheme,
} from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ApiError } from '@/api/client';
import { ragApi } from '@/api/domain.api';
import { BRAND } from '@/constants/theme';
import type { RagAnswer } from '@/types';

interface Turn {
  id: string;
  role: 'user' | 'assistant';
  text: string;
}

const STARTERS = [
  'What is the eligibility for exam attendance?',
  'What software does the Full Stack course cover?',
  'What are the fee refund guidelines?',
  'Which courses run in the evening batch?',
];

/** The generator returns a shaped payload; tolerate the field names drifting. */
const answerText = (result: RagAnswer): string => {
  const candidate =
    (result.answer as string | undefined) ??
    (result.response as string | undefined) ??
    (result.response_text as string | undefined) ??
    (result.text as string | undefined) ??
    (result.result as string | undefined);
  if (typeof candidate === 'string' && candidate.trim()) return candidate;
  return JSON.stringify(result, null, 2);
};

const AssistantScreen = () => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const scrollRef = useRef<View | null>(null);
  const sessionId = useRef<string | undefined>(undefined);

  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState('');

  const ask = useMutation({
    mutationFn: (question: string) => ragApi.ask(question, sessionId.current),
    onSuccess: (result) => {
      if (result.session_id) sessionId.current = result.session_id;
      setTurns((prev) => [
        ...prev,
        { id: `a-${prev.length}`, role: 'assistant', text: answerText(result) },
      ]);
    },
    onError: (error) => {
      setTurns((prev) => [
        ...prev,
        {
          id: `e-${prev.length}`,
          role: 'assistant',
          text:
            error instanceof ApiError
              ? error.message
              : 'The assistant is unavailable right now. Please try again shortly.',
        },
      ]);
    },
    // RAG answers come from a vector search over the indexed corpus; a second
    // concurrent call would double the embedding cost for no benefit.
    onSettled: () => void queryClient.invalidateQueries(),
  });

  const send = (question: string) => {
    const text = question.trim();
    if (!text || ask.isPending) return;
    setTurns((prev) => [...prev, { id: `q-${prev.length}`, role: 'user', text }]);
    setDraft('');
    ask.mutate(text);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={[styles.root, { backgroundColor: theme.colors.background }]}
    >
      <View style={[styles.header, { paddingTop: insets.top + 8, borderBottomColor: theme.colors.outlineVariant }]}>
        <View style={styles.headerText}>
          <Text variant="titleSmall" style={styles.bold}>
            Institute assistant
          </Text>
          <Text variant="bodySmall" style={styles.muted}>
            Answers from our own syllabi, policies and FAQs
          </Text>
        </View>
        {turns.length ? (
          <IconButton
            icon={Trash2}
            size={20}
            onPress={() => {
              setTurns([]);
              sessionId.current = undefined;
            }}
            accessibilityLabel="Clear conversation"
          />
        ) : null}
        <IconButton icon={X} size={22} onPress={() => router.back()} accessibilityLabel="Close" />
      </View>

      <View style={styles.body}>
        {turns.length === 0 ? (
          <View style={styles.starterBlock}>
            <View style={[styles.starterIcon, { backgroundColor: `${BRAND.indigo500}22` }]}>
              <Sparkles size={26} color={BRAND.indigo500} />
            </View>
            <Text variant="titleMedium" style={styles.bold}>
              Ask anything about the institute
            </Text>
            <Text variant="bodyMedium" style={styles.muted}>
              Curricula, software covered, durations, fees, eligibility, refunds and batch timings.
            </Text>
            <View style={{ gap: 8, marginTop: 12, alignSelf: 'stretch' }}>
              {STARTERS.map(question => (
                <Card
                  key={question}
                  mode="contained"
                  onPress={() => send(question)}
                  style={{ backgroundColor: theme.colors.surface }}
                >
                  <Card.Content>
                    <Text variant="bodyMedium">{question}</Text>
                  </Card.Content>
                </Card>
              ))}
            </View>
          </View>
        ) : (
          <View style={{ gap: 12 }}>
            {turns.map(turn => (
              <View
                key={turn.id}
                style={[
                  styles.bubble,
                  turn.role === 'user'
                    ? { backgroundColor: theme.colors.primary, alignSelf: 'flex-end' }
                    : { backgroundColor: theme.colors.surface, alignSelf: 'flex-start', borderRadius: 16, borderTopLeftRadius: 4 },
                ]}
              >
                {turn.role === 'assistant' ? (
                  <Bot size={14} color={theme.colors.primary} style={{ marginBottom: 4 }} />
                ) : null}
                <Text variant="bodyMedium" style={{ lineHeight: 21 }}>
                  {turn.text}
                </Text>
              </View>
            ))}
            {ask.isPending ? (
              <View style={[styles.bubble, { backgroundColor: theme.colors.surface, alignSelf: 'flex-start' }]}>
                <Text variant="bodySmall" style={styles.muted}>
                  Searching our knowledge base…
                </Text>
              </View>
            ) : null}
          </View>
        )}
      </View>

      <View
        style={[
          styles.composer,
          { paddingBottom: insets.bottom + 12, borderTopColor: theme.colors.outlineVariant, backgroundColor: theme.colors.surface },
        ]}
      >
        <TextInput
          mode="outlined"
          value={draft}
          onChangeText={setDraft}
          placeholder="Ask about courses, fees or policies…"
          multiline
          onSubmitEditing={() => send(draft)}
          style={{ flex: 1 }}
        />
        <Button
          mode="contained"
          icon={Send}
          disabled={!draft.trim() || ask.isPending}
          onPress={() => send(draft)}
          contentStyle={{ width: 48, height: 48 }}
        >
          <Text style={{ opacity: 0 }}> </Text>
        </Button>
      </View>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingBottom: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  headerText: { flex: 1 },
  body: { flex: 1, padding: 16 },
  starterBlock: { alignItems: 'center', gap: 8, paddingTop: 40, paddingHorizontal: 12 },
  starterIcon: {
    width: 56,
    height: 56,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  bubble: { maxWidth: '88%', paddingHorizontal: 14, paddingVertical: 10, borderRadius: 16 },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
    paddingHorizontal: 12,
    paddingTop: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8', textAlign: 'center' },
});

export default AssistantScreen;
