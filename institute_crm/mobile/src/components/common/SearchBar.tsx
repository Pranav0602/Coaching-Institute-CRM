import { Search, X } from 'lucide-react-native';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { TextInput, useTheme } from 'react-native-paper';

export const SearchBar = ({
  value,
  onChangeText,
  placeholder = 'Search…',
  autoFocus,
  onSubmitEditing,
  onClear,
  right,
}: {
  value: string;
  onChangeText: (next: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  onSubmitEditing?: () => void;
  onClear?: () => void;
  right?: React.ReactNode;
}) => {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.container,
        { backgroundColor: theme.colors.surfaceVariant, borderColor: theme.colors.outlineVariant },
      ]}
    >
      <Search size={18} color={theme.colors.onSurfaceVariant} />
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={theme.colors.onSurfaceVariant}
        autoCapitalize="none"
        autoCorrect={false}
        autoFocus={autoFocus}
        onSubmitEditing={onSubmitEditing}
        returnKeyType="search"
        style={[styles.input, { color: theme.colors.onSurface }]}
        underlineColor="transparent"
        activeUnderlineColor="transparent"
      />
      {value.length > 0 ? (
        <X
          size={18}
          color={theme.colors.onSurfaceVariant}
          onPress={() => {
            onChangeText('');
            onClear?.();
          }}
        />
      ) : null}
      {right}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 12,
    height: 46,
    borderRadius: 12,
    borderWidth: StyleSheet.hairlineWidth,
  },
  input: { flex: 1, margin: 0, paddingVertical: 0 },
});
