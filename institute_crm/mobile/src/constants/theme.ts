/**
 * Graphix brand tokens, mirrored from `frontend/src/theme/theme.js` so the
 * handset and the desktop CRM are recognisably the same product.
 */
import { MD3DarkTheme, MD3LightTheme, type MD3Theme } from 'react-native-paper';

export const BRAND = {
  indigo500: '#6366F1',
  indigo600: '#4F46E5',
  indigo400: '#818CF8',
  indigoDeep: '#3730A3',
  emerald500: '#10B981',
  emerald400: '#34D399',
  emeraldDeep: '#059669',
  slate900: '#0F172A',
  slate800: '#1E293B',
  slate700: '#334155',
  slate500: '#64748B',
  slate400: '#94A3B8',
  slate100: '#F1F5F9',
  slate50: '#F8FAFC',
  white: '#FFFFFF',
  amber500: '#F59E0B',
  rose500: '#EF4444',
  blue500: '#3B82F6',
} as const;

export const FONTS = {
  sans: 'PlusJakartaSans_400Regular',
  sansMedium: 'PlusJakartaSans_500Medium',
  sansSemiBold: 'PlusJakartaSans_600SemiBold',
  sansBold: 'PlusJakartaSans_700Bold',
  sansExtraBold: 'PlusJakartaSans_800ExtraBold',
  fallback: 'Inter_400Regular',
  fallbackMedium: 'Inter_500Medium',
  fallbackSemiBold: 'Inter_600SemiBold',
} as const;

const roundness = 12;

/**
 * Paper's MD3 palette has no amber/emerald/blue slots. Rather than bolt them onto
 * the theme object (which would silently diverge from Paper's own type), status
 * colours come from the BRAND palette below at the point of use.
 */
export const buildTheme = (mode: 'light' | 'dark'): MD3Theme => {
  const dark = mode === 'dark';
  const base = dark ? MD3DarkTheme : MD3LightTheme;

  return {
    ...base,
    roundness,
    colors: {
      ...base.colors,
      primary: dark ? BRAND.indigo500 : BRAND.indigo600,
      onPrimary: BRAND.white,
      primaryContainer: dark ? BRAND.indigoDeep : '#E0E7FF',
      onPrimaryContainer: dark ? BRAND.indigo400 : BRAND.indigoDeep,
      secondary: BRAND.emerald500,
      onSecondary: BRAND.white,
      secondaryContainer: dark ? BRAND.emeraldDeep : '#D1FAE5',
      onSecondaryContainer: dark ? BRAND.emerald400 : BRAND.emeraldDeep,
      background: dark ? BRAND.slate900 : BRAND.slate50,
      onBackground: dark ? BRAND.slate50 : BRAND.slate900,
      surface: dark ? BRAND.slate800 : BRAND.white,
      onSurface: dark ? BRAND.slate50 : BRAND.slate900,
      surfaceVariant: dark ? BRAND.slate700 : BRAND.slate100,
      onSurfaceVariant: dark ? BRAND.slate400 : BRAND.slate500,
      outline: dark ? BRAND.slate700 : '#CBD5E1',
      outlineVariant: dark ? BRAND.slate700 : '#E2E8F0',
      error: BRAND.rose500,
      elevation: {
        ...base.colors.elevation,
        level1: dark ? 'rgba(30, 41, 59, 0.9)' : 'rgba(15, 23, 42, 0.04)',
        level3: dark ? 'rgba(15, 23, 42, 0.7)' : 'rgba(15, 23, 42, 0.09)',
      },
    },
  };
};

/** Per-stage pipeline colours, identical to the web `constants/pipeline.js`. */
export const STAGE_COLORS: Record<string, string> = {
  New: '#6366F1',
  Contacted: '#0EA5E9',
  Interested: '#F59E0B',
  'Demo Scheduled': '#8B5CF6',
  'Demo Attended': '#EC4899',
  'Admission Pending': '#14B8A6',
  Admitted: '#22C55E',
  Lost: '#EF4444',
};

export const STAGE_DESCRIPTIONS: Record<string, string> = {
  New: 'Fresh walk-ins and phone enquiries',
  Contacted: 'First call or message attempted',
  Interested: 'Asked about fees, tools or batches',
  'Demo Scheduled': 'Demo class booked',
  'Demo Attended': 'Showed up to the demo class',
  'Admission Pending': 'Deciding, paperwork in flight',
  Admitted: 'Converted into a paying student',
  Lost: 'Closed for now',
};

export const PIPELINE_STAGES = Object.keys(STAGE_COLORS);

export const stageColor = (stage?: string | null) =>
  (stage && STAGE_COLORS[stage]) || BRAND.slate400;

export const ATTENDANCE_COLORS: Record<string, string> = {
  PRESENT: BRAND.emerald500,
  ABSENT: BRAND.rose500,
  LATE: BRAND.amber500,
  EXCUSED: BRAND.blue500,
};

export const INSTALLMENT_COLORS: Record<string, string> = {
  PAID: BRAND.emerald500,
  PENDING: BRAND.amber500,
  OVERDUE: BRAND.rose500,
};

export const SPACING = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
