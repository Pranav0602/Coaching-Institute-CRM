/**
 * Shared tab bar.
 *
 * The seven persona shells differ only in which screens they contain, so the tab
 * configuration is data and this component renders it. Each persona's
 * `_layout.tsx` declares its own `Tabs` (that is where Expo Router expects the
 * navigator to live) and delegates the chrome here, which is why the seven
 * layouts stay a handful of lines each instead of drifting apart.
 */
import { Tabs } from 'expo-router';
import {
  BarChart3,
  BookOpen,
  CalendarDays,
  ClipboardCheck,
  CreditCard,
  Gauge,
  GraduationCap,
  IdCard,
  LayoutDashboard,
  ListChecks,
  LogOut,
  MoreHorizontal,
  PhoneCall,
  Receipt,
  School,
  UserCog,
  UserPlus,
  Users,
  Wallet,
} from 'lucide-react-native';
import React from 'react';
import { StyleSheet } from 'react-native';
import { useTheme } from 'react-native-paper';

import { personaFor } from '@/constants/navigation';
import type { Persona, Role } from '@/constants/roles';

type IconComponent = React.ComponentType<{ size?: number | string; color?: string; strokeWidth?: number }>;

export interface TabConfig {
  name: string;
  title: string;
  icon: IconComponent;
}

const ICONS = {
  pipeline: PhoneCall,
  leads: UserPlus,
  followups: CalendarDays,
  syllabi: BookOpen,
  today: ListChecks,
  batches: School,
  mark: ClipboardCheck,
  home: LayoutDashboard,
  schedule: CalendarDays,
  attendance: Gauge,
  fees: Wallet,
  overview: BarChart3,
  users: UserCog,
  staff: Users,
  collection: CreditCard,
  dues: Receipt,
  refunds: Wallet,
  desk: GraduationCap,
  visitors: Users,
  idcards: IdCard,
  more: MoreHorizontal,
  signout: LogOut,
} satisfies Record<string, IconComponent>;

export const PERSONA_TABS: Record<Persona, TabConfig[]> = {
  counsellor: [
    { name: 'index', title: 'Pipeline', icon: ICONS.pipeline },
    { name: 'leads', title: 'Leads', icon: ICONS.leads },
    { name: 'followups', title: 'Follow-ups', icon: ICONS.followups },
    { name: 'syllabi', title: 'Syllabi', icon: ICONS.syllabi },
    { name: 'more', title: 'More', icon: ICONS.more },
  ],
  teacher: [
    { name: 'index', title: 'Today', icon: ICONS.today },
    { name: 'batches', title: 'Batches', icon: ICONS.batches },
    { name: 'mark', title: 'Mark', icon: ICONS.mark },
    { name: 'more', title: 'More', icon: ICONS.more },
  ],
  student: [
    { name: 'index', title: 'Home', icon: ICONS.home },
    { name: 'schedule', title: 'Schedule', icon: ICONS.schedule },
    { name: 'attendance', title: 'Attendance', icon: ICONS.attendance },
    { name: 'fees', title: 'Fees', icon: ICONS.fees },
    { name: 'more', title: 'More', icon: ICONS.more },
  ],
  parent: [
    { name: 'index', title: 'Children', icon: ICONS.home },
    { name: 'notifications', title: 'Notices', icon: ICONS.followups },
    { name: 'more', title: 'More', icon: ICONS.more },
  ],
  admin: [
    { name: 'index', title: 'Overview', icon: ICONS.overview },
    { name: 'batches', title: 'Batches', icon: ICONS.batches },
    { name: 'users', title: 'People', icon: ICONS.users },
    { name: 'more', title: 'More', icon: ICONS.more },
  ],
  accountant: [
    { name: 'index', title: 'Collection', icon: ICONS.collection },
    { name: 'dues', title: 'Dues', icon: ICONS.dues },
    { name: 'refunds', title: 'Refunds', icon: ICONS.refunds },
    { name: 'more', title: 'More', icon: ICONS.more },
  ],
  reception: [
    { name: 'index', title: 'Desk', icon: ICONS.desk },
    { name: 'visitors', title: 'Visitors', icon: ICONS.visitors },
    { name: 'idcards', title: 'ID Cards', icon: ICONS.idcards },
    { name: 'more', title: 'More', icon: ICONS.more },
  ],
};

/**
 * The "More" tab always points at the shared settings screen, so it is rendered
 * as a redirect rather than a duplicate per persona.
 */
export const PersonaTabs = ({ role }: { role: Role | null }) => {
  const theme = useTheme();
  const tabs = PERSONA_TABS[personaFor(role)];

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: theme.colors.surface },
        headerTitleStyle: { fontWeight: '800' },
        headerShadowVisible: false,
        tabBarStyle: {
          backgroundColor: theme.colors.surface,
          borderTopColor: theme.colors.outlineVariant,
          height: 62,
          paddingBottom: 8,
          paddingTop: 6,
        },
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.onSurfaceVariant,
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        sceneStyle: { backgroundColor: theme.colors.background },
        lazy: true,
      }}
    >
      {tabs.map(tab => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{
            title: tab.title,
            tabBarIcon: ({ color, size, focused }) => (
              <tab.icon
                size={focused ? size + 1 : size}
                // Paper hands the tab bar a `ColorValue`, which may be an opaque
                // symbol. Lucide needs a real colour string.
                color={typeof color === 'string' ? color : theme.colors.onSurface}
                strokeWidth={focused ? 2.4 : 1.9}
              />
            ),
            tabBarHideOnKeyboard: true,
          }}
        />
      ))}
    </Tabs>
  );
};

export const tabIcon = (key: keyof typeof ICONS): IconComponent => ICONS[key];

export const tabStyles = StyleSheet.create({
  headerTitle: { fontWeight: '800' },
});
