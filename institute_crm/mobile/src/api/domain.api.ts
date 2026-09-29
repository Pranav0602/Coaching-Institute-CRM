import { api, type QueryParams } from './client';
import type {
  Announcement,
  Branch,
  DashboardAnalytics,
  DeviceToken,
  FollowUp,
  Installment,
  KnowledgeDocument,
  Lead,
  Notification,
  Payment,
  PublicOptions,
  RagAnswer,
  Receipt,
  Refund,
  StageCounts,
  User,
  Visitor,
} from '@/types';

export interface LeadFilters extends QueryParams {
  stage?: string;
  branch_id?: string;
  course_id?: string;
}

export interface LeadDraft {
  name: string;
  email: string;
  phone: string;
  branch: string;
  course?: string | null;
  target_course?: string;
  source?: string;
  stage?: string;
  notes?: string;
  demo_schedule_date?: string | null;
}

export interface LeadConversion {
  lead_id: string;
  student_user_id: string;
  username: string;
  enrollment_number: string;
  admission_number: string;
  temporary_password: string;
}

export const leadsApi = {
  list: (filters: LeadFilters = {}) => api.getList<Lead>('/crm/leads/', filters),
  stageCounts: () => api.get<StageCounts>('/crm/leads/stage-counts/'),
  create: (body: LeadDraft) => api.post<Lead>('/crm/leads/', body),
  update: (id: string, body: Partial<LeadDraft> & { stage?: string }) =>
    api.patch<Lead>(`/crm/leads/${id}/`, body),
  remove: (id: string) => api.del<void>(`/crm/leads/${id}/`),
  convert: (id: string, body: { course_id: string; batch_id: string; agreed_fee: number }) =>
    api.post<LeadConversion>(`/crm/leads/${id}/convert/`, body),
  followUps: () => api.getList<FollowUp>('/crm/follow-ups/'),
  updateFollowUp: (id: string, body: Partial<Pick<FollowUp, 'status' | 'remarks' | 'scheduled_date'>>) =>
    api.patch<FollowUp>(`/crm/follow-ups/${id}/`, body),
  visitors: () => api.getList<Visitor>('/crm/visitors/'),
  logVisitor: (body: { visitor_name: string; phone: string; purpose: string; branch: string }) =>
    api.post<Visitor>('/crm/visitors/', body),
  publicOptions: () => api.get<PublicOptions>('/crm/public-options/'),
};

export const financeApi = {
  installments: (params?: QueryParams) => api.getList<Installment>('/finance/installments/', params),
  payments: (params?: QueryParams) => api.getList<Payment>('/finance/payments/', params),
  receipts: () => api.getList<Receipt>('/finance/receipts/'),
  refunds: () => api.getList<Refund>('/finance/refunds/'),
  recordPayment: (body: {
    student_id: string;
    installment_id?: string | null;
    amount: number;
    payment_mode: string;
  }) => api.post<Payment>('/finance/payments/record-payment/', body),
};

export const commsApi = {
  notifications: (params?: QueryParams) =>
    api.getList<Notification>('/communications/notifications/', params),
  unreadCount: () => api.get<{ unread_count: number }>('/communications/notifications/unread-count/'),
  markRead: (id: string) => api.post<Notification>(`/communications/notifications/${id}/mark-read/`),
  markAllRead: () => api.post<{ updated: number }>('/communications/notifications/mark-all-read/'),
  announcements: () => api.getList<Announcement>('/communications/announcements/'),
};

export const devicesApi = {
  list: () => api.getList<DeviceToken>('/communications/devices/'),
  register: (body: {
    expo_push_token: string;
    platform: 'ios' | 'android' | 'web';
    device_name?: string;
    app_version?: string;
  }) => api.post<DeviceToken>('/communications/devices/register/', body),
  unregister: (id: string) => api.post<DeviceToken>(`/communications/devices/${id}/unregister/`),
  unregisterAll: () => api.post<{ retired: number }>('/communications/devices/unregister-all/'),
};

export const ragApi = {
  ask: (query: string, sessionId?: string) =>
    api.post<RagAnswer>('/rag/query/', { query, session_id: sessionId }),
  documents: (params: { category: string; search?: string }) =>
    api.getList<KnowledgeDocument>('/rag/documents/', params),
};

export const accountsApi = {
  me: () => api.get<User>('/accounts/auth/me/'),
  profile: () => api.get<User>('/accounts/auth/profile/'),
  updateProfile: (body: { first_name?: string; last_name?: string; email?: string; phone?: string }) =>
    api.patch<User>('/accounts/auth/profile/', body),
  branches: () => api.getList<Branch>('/accounts/branches/'),
  users: (params?: QueryParams) => api.getList<User>('/accounts/users/', params),
};

export const analyticsApi = {
  dashboard: (months = 6) => api.get<DashboardAnalytics>('/analytics/dashboard/', { months }),
};

/**
 * Re-exported so a screen imports every endpoint it needs from one place; the
 * split into `academics.api` / `domain.api` is an implementation detail.
 */
export {
  academicsApi,
  attendanceApi,
  batchesApi,
  coursesApi,
  examsApi,
  lecturesApi,
  studentsApi,
  timetableApi,
} from './academics.api';
