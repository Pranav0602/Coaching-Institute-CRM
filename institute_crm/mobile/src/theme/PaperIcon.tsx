/**
 * One icon system for the whole app.
 *
 * Paper resolves a *string* icon name through MaterialCommunityIcons. This
 * override routes those through Lucide instead, so the handful of components
 * that take an icon name (`List.Item`, `Menu.Item`) match the lucide icons the
 * screens pass directly. It does not remove the MaterialCommunityIcons typeface
 * from the bundle - Paper imports it unconditionally - but it stops the two
 * systems from being visibly mixed.
 *
 * Lucide has no general name-to-icon lookup, so the names Paper can be asked for
 * by string are mapped explicitly. Anything unmapped falls back to a neutral
 * glyph rather than crashing; callers that want a specific icon pass the
 * component itself (`icon={Camera}`), which Paper renders directly.
 */
import {
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Circle,
  X,
} from 'lucide-react-native';
import React from 'react';

export interface PaperIconProps {
  name: unknown;
  color?: string;
  size?: number;
  direction?: 'ltr' | 'rtl';
}

type LucideIcon = React.ComponentType<{ size?: number; color?: string; strokeWidth?: number }>;

const LUCIDE_BY_NAME: Record<string, LucideIcon> = {
  check: Check,
  close: X,
  cancel: X,
  delete: X,
  backarrow: ChevronLeft,
  'chevron-down': ChevronDown,
  'chevron-up': ChevronUp,
  'chevron-left': ChevronLeft,
  'chevron-right': ChevronRight,
};

export const PaperIcon = ({ name, color, size }: PaperIconProps) => {
  if (typeof name !== 'string') return null;
  const Icon: LucideIcon = LUCIDE_BY_NAME[name] ?? Circle;
  return <Icon size={size ?? 24} color={color} strokeWidth={2} />;
};
