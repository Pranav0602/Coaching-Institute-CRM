import { useQuery } from '@tanstack/react-query';
import { Mail, Phone, UserCog } from 'lucide-react-native';
import React, { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Avatar, Card, Chip, Searchbar, Text, useTheme } from 'react-native-paper';

import { EmptyState, ErrorState, LoadingState } from '@/components/common/Layout';
import { ScreenHeader } from '@/components/common/Primitives';
import { Screen } from '@/components/common/Screen';
import { accountsApi } from '@/api/domain.api';
import { ALL_ROLES, roleLabel } from '@/constants/roles';
import { useDebounced } from '@/hooks';
import type { User } from '@/types';
import { initials, maskPhone } from '@/utils/format';
import { callPhone, sendEmail } from '@/utils/linking';

const ALL = 'ALL';

const AdminUsersScreen = () => {
  const theme = useTheme();
  const [query, setQuery] = useState('');
  const [role, setRole] = useState(ALL);
  const search = useDebounced(query);

  // The backend already scopes the list (a branch admin sees only their branch, a
  // non-admin sees only themselves), so the client only narrows further.
  const users = useQuery({
    queryKey: ['users', role],
    queryFn: () => accountsApi.users(role === ALL ? {} : { role }),
  });

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    const list = users.data ?? [];
    if (!term) return list;
    return list.filter(
      (u) =>
        u.full_name?.toLowerCase().includes(term) ||
        u.username.toLowerCase().includes(term) ||
        (u.email ?? '').toLowerCase().includes(term) ||
        (u.phone ?? '').includes(term),
    );
  }, [users.data, search]);

  return (
    <Screen onRefresh={() => void users.refetch()} refreshing={users.isRefetching}>
      <ScreenHeader title="People" subtitle="Everyone you can see in your scope" />

      <Searchbar
        placeholder="Search name, username, email or phone"
        value={query}
        onChangeText={setQuery}
        style={styles.search}
        inputStyle={styles.searchInput}
      />

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filters}>
        <Chip selected={role === ALL} onPress={() => setRole(ALL)} style={styles.chip}>
          All
        </Chip>
        {ALL_ROLES.map((r) => (
          <Chip key={r} selected={role === r} onPress={() => setRole(r)} style={styles.chip}>
            {roleLabel(r)}
          </Chip>
        ))}
      </ScrollView>

      {users.isLoading ? <LoadingState /> : null}
      {users.isError ? (
        <ErrorState
          message={(users.error as Error)?.message ?? 'Could not load people.'}
          onRetry={() => void users.refetch()}
        />
      ) : null}
      {!users.isLoading && !users.isError && filtered.length === 0 ? (
        <EmptyState
          icon={<UserCog size={28} color={theme.colors.onSurfaceVariant} />}
          title="No one matches"
          message="Try a different name or clear the role filter."
        />
      ) : null}

      <View style={{ gap: 10 }}>
        {filtered.map((person: User) => (
          <Card key={person.id} mode="contained" style={{ backgroundColor: theme.colors.surface }}>
            <Card.Content style={styles.row}>
              <Avatar.Text size={40} label={initials(person.full_name || person.username)} />
              <View style={{ flex: 1 }}>
                <Text variant="bodyLarge" style={styles.bold} numberOfLines={1}>
                  {person.full_name || person.username}
                </Text>
                <Text variant="bodySmall" style={styles.muted} numberOfLines={1}>
                  {roleLabel(person.role_code)}
                  {person.branch_name ? ` · ${person.branch_name}` : ''}
                </Text>
              </View>
              <View style={styles.actions}>
                <Chip compact onPress={() => callPhone(person.phone)} style={styles.chip}>
                  <Phone size={12} style={{ marginRight: 4 }} />
                  {maskPhone(person.phone)}
                </Chip>
                <Chip compact onPress={() => sendEmail(person.email)} style={styles.chip}>
                  <Mail size={12} style={{ marginRight: 4 }} />
                  Email
                </Chip>
              </View>
            </Card.Content>
          </Card>
        ))}
      </View>
    </Screen>
  );
};

const styles = StyleSheet.create({
  search: { borderRadius: 12 },
  searchInput: { minHeight: 0 },
  filters: { gap: 8, paddingVertical: 12, paddingRight: 16 },
  chip: { borderRadius: 999 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  actions: { gap: 6, alignItems: 'flex-end' },
  bold: { fontWeight: '700' },
  muted: { color: '#94A3B8' },
});

export default AdminUsersScreen;
