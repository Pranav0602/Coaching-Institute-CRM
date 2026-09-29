/**
 * Shared response shapes from the DRF backend.
 *
 * Every successful 2xx is wrapped by `StandardResponseRenderer` as
 * `{ success, message, data }`; every failure is `{ success, message, errors,
 * status_code }`. Both are modelled here so call sites never reach into `any`.
 */

export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface ApiErrorBody {
  success: false;
  message: string;
  errors?: Record<string, string | string[]> | { detail?: string };
  code?: string;
  status_code?: number;
}

export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string | null;
  role: string | null;
  role_name: string | null;
  role_code: string | null;
  branch: string | null;
  branch_name: string | null;
  branch_code: string | null;
  profile_photo_url: string | null;
  is_active: boolean;
  date_joined: string;
  last_login: string | null;
  password_changed_at: string | null;
  password_age_days?: number | null;
}

export type SessionUser = User;

export interface Branch {
  id: string;
  code: string;
  name: string;
  city: string;
  address: string;
  phone: string;
  email: string;
  created_at?: string;
}

export interface Course {
  id: string;
  code: string;
  title: string;
  description: string | null;
  duration_months: number;
  total_fee: string;
  field_of_engineering: string | null;
  subjects: Subject[];
  subject_count: number;
  batch_count: number;
}

export interface Subject {
  id: string;
  course: string;
  course_title: string;
  code: string;
  title: string;
  description: string | null;
}

export interface CourseSummary {
  id: string;
  code: string;
  title: string;
  total_fee: string;
  field_of_engineering: string | null;
  subject_count: number;
  batch_count: number;
  enrolment_count: number;
}

export interface Batch {
  id: string;
  course: string;
  course_title: string;
  branch: string | null;
  branch_name: string | null;
  code: string;
  name: string;
  start_date: string;
  end_date: string;
  max_capacity: number;
  enrolled_count: number;
  seats_available: number;
  teachers: string[];
  teacher_details: Array<{ id: string; username: string; full_name: string }>;
}

export interface BatchSummary {
  id: string;
  code: string;
  name: string;
  start_date: string;
  end_date: string;
  max_capacity: number;
  course__title: string;
  branch__name: string;
  enrolled_count: number;
  session_count: number;
}

export interface BatchProgressSummary {
  id: string;
  name: string;
  code: string;
  course_title: string;
  branch_name: string;
  status: string;
  timeline_pct: number;
  enrolled_count: number;
  max_capacity: number;
  capacity_filled_pct: number;
  teachers: string[];
  attendance_pct: number;
  assignment_submission_pct: number;
  exam_pass_rate_pct: number;
  syllabus_progress_pct: number;
  at_risk_count: number;
}

export type AttendanceStatus = 'PRESENT' | 'ABSENT' | 'LATE' | 'EXCUSED';

export interface Attendance {
  id: string;
  lecture: string;
  lecture_date: string;
  subject_title: string | null;
  student: string;
  student_name: string;
  status: AttendanceStatus;
  remarks: string | null;
}

/**
 * One entry per student. The endpoint always answers with a list, even for a
 * single student, because a parent gets one row per linked child in the same call.
 */
export interface AttendanceSummary {
  student_id: string;
  total_sessions: number;
  present: number;
  absent: number;
  late: number;
  excused: number;
  percentage: number | null;
  below_threshold: boolean;
  threshold: number;
}

export interface LowAttendanceReport {
  threshold: number;
  count: number;
  students: Array<{
    student_id: string;
    student_name: string;
    total: number;
    present: number;
    percentage: number;
  }>;
}

export interface TimetableEntry {
  id: string;
  batch: string;
  batch_name: string;
  subject: string;
  subject_title: string;
  teacher: string;
  teacher_name: string;
  branch_name: string | null;
  day_of_week: string;
  start_time: string;
  end_time: string;
  room_number: string | null;
}

export type WeekTimetable = Record<string, TimetableEntry[]>;

export interface Lecture {
  id: string;
  timetable: string;
  batch: string;
  batch_name: string;
  subject_title: string;
  teacher_name: string;
  day_of_week: string;
  date: string;
  topic: string;
  status: 'SCHEDULED' | 'COMPLETED' | 'CANCELLED';
  conducted_by: string | null;
  conducted_by_name: string | null;
}

export interface LectureRegister {
  lecture_id: string;
  lecture_status: string;
  date: string;
  batch: string;
  subject: string;
  students: Array<{
    student_id: string;
    student_name: string;
    enrolment_id: string;
    status: AttendanceStatus;
    remarks: string | null;
    attendance_id: string | null;
  }>;
}

export interface BulkAttendanceResult {
  lecture_id: string;
  lecture_status: string;
  count: number;
  created: number;
  updated: number;
  tally: Record<string, number>;
  records: Attendance[];
}

export interface BulkAttendanceEntry {
  student_id: string;
  status: AttendanceStatus;
  remarks?: string;
}

export interface StudentProfile {
  id: string;
  user: string;
  user_detail: User;
  enrollment_number: string;
  dob: string | null;
  gender: string;
  blood_group: string | null;
  address: string | null;
  emergency_contact: string | null;
  batch: string | null;
  batch_name: string | null;
  documents_url: string[];
  qr_payload: string;
  created_at: string;
}

export interface StudentIdCard {
  student_id: string;
  user_id: string;
  full_name: string;
  username: string;
  phone: string | null;
  email: string;
  enrollment_number: string;
  qr_payload: string;
  dob: string | null;
  gender: string;
  blood_group: string | null;
  address: string | null;
  emergency_contact: string | null;
  batch: string | null;
  batch_name: string | null;
  batch_code: string | null;
  course_title: string | null;
  branch_name: string | null;
  branch_code: string | null;
  profile_photo_url: string | null;
}

export interface Lead {
  id: string;
  name: string;
  email: string;
  phone: string;
  branch: string;
  branch_name: string;
  course: string | null;
  course_title: string | null;
  course_code: string | null;
  batch: string | null;
  batch_name: string | null;
  batch_code: string | null;
  target_course: string;
  source: string;
  stage: string;
  lead_owner: string | null;
  lead_owner_name: string | null;
  notes: string;
  demo_schedule_date: string | null;
  created_at: string;
  updated_at: string;
}

export type StageCounts = Record<string, number>;

/**
 * The `FollowUp` serializer only carries the lead's primary key, never their name
 * or phone. Screens join against `Lead[]` rather than the backend widening this
 * payload - a follow-up list is small, and re-fetching every lead on each render
 * would be worse than one extra query.
 */
export interface FollowUp {
  id: string;
  lead: string;
  counselor: string | null;
  counselor_name: string | null;
  scheduled_date: string;
  status: 'PENDING' | 'COMPLETED' | 'CANCELLED';
  remarks: string;
  created_at: string;
}

export interface Visitor {
  id: string;
  visitor_name: string;
  phone: string;
  purpose: string;
  branch: string;
  branch_name: string;
  host_staff: string | null;
  host_staff_name: string | null;
  check_in: string;
  check_out: string | null;
}

export interface Installment {
  id: string;
  student: string;
  student_name: string;
  fee_structure: string;
  installment_number: number;
  due_date: string;
  amount: string;
  status: 'PENDING' | 'PAID' | 'OVERDUE';
}

export interface Receipt {
  id: string;
  receipt_number: string;
  payment: string;
  issue_date: string;
  pdf_url: string | null;
}

export interface Payment {
  id: string;
  student: string;
  student_name: string;
  installment: string | null;
  amount: string;
  payment_mode: 'CASH' | 'CARD' | 'UPI' | 'BANK_TRANSFER';
  reference_number: string;
  payment_date: string;
  recorded_by: string | null;
  receipt: Receipt | null;
}

export interface Refund {
  id: string;
  student: string;
  student_name: string;
  amount: string;
  reason: string;
  status: 'REQUESTED' | 'APPROVED' | 'REJECTED';
  processed_by: string | null;
  created_at: string;
}

export interface Assignment {
  id: string;
  subject: string;
  subject_title?: string;
  batch: string;
  batch_name?: string;
  title: string;
  description: string;
  total_marks: number;
  due_date: string;
  file_url: string | null;
  created_by: string;
}

export interface Submission {
  id: string;
  assignment: string;
  student: string;
  student_name: string;
  submitted_at: string;
  file_url: string;
  marks_obtained: string | null;
  feedback: string | null;
  evaluated_by: string | null;
}

export interface Exam {
  id: string;
  subject: string;
  subject_title?: string;
  batch: string;
  batch_name?: string;
  title: string;
  total_marks: number;
  passing_marks: number;
  exam_date: string;
}

export interface Result {
  id: string;
  exam: string;
  student: string;
  student_name: string;
  marks_obtained: string;
  grade: string | null;
  remarks: string | null;
}

export interface Notification {
  id: string;
  recipient: string;
  sender: string | null;
  sender_name: string | null;
  batch_id: string | null;
  batch_name: string | null;
  target_audience: string;
  title: string;
  message: string;
  channel: string;
  is_read: boolean;
  created_at: string;
}

export interface Announcement {
  id: string;
  branch: string | null;
  title: string;
  content: string;
  target_role: string | null;
  published_by: string;
  publisher_name: string;
  created_at: string;
}

export interface DeviceToken {
  id: string;
  expo_push_token: string;
  platform: 'ios' | 'android' | 'web';
  device_name: string | null;
  app_version: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  category: string;
  content: string;
  source_url: string | null;
  is_published: boolean;
  version: number;
  metadata_json: {
    course_id?: string;
    code?: string;
    field?: string | null;
    duration_months?: number;
    total_fee?: number;
    tools?: string[];
    doc_type?: string;
    total_courses?: number;
    institute?: string;
  };
  chunks_count: number;
  created_at: string;
  updated_at: string;
}

export interface RagAnswer {
  answer: string;
  sources?: Array<{ title?: string; document_id?: string; score?: number }>;
  confidence?: number;
  session_id?: string;
  [key: string]: unknown;
}

export interface PublicOptions {
  branches: Array<Pick<Branch, 'id' | 'name' | 'city' | 'code'>>;
  courses: Array<Pick<Course, 'id' | 'code' | 'title' | 'total_fee' | 'field_of_engineering'>>;
  fields: Array<{ id: string; name: string }>;
}

/**
 * `/analytics/dashboard/` is role-shaped, not user-shaped: the service omits whole
 * card and chart groups the caller is not entitled to, so everything past the
 * always-present keys is optional by design rather than by accident.
 */
export interface DashboardAnalytics {
  generated_at: string;
  scope: {
    role: string | null;
    branch_id: string | null;
    branch_name: string | null;
    all_branches: boolean;
    visible_batches: number;
    shows_finance: boolean;
  };
  cards: {
    total_students: number;
    total_teachers: number;
    active_batches: number;
    active_courses: number;
    upcoming_exams: number;
    todays_attendance_pct: number | null;
    todays_sessions: number;
    todays_marks_recorded: number;
    open_leads?: number;
    admissions_this_month?: number;
    total_fee_collection?: number;
    collection_this_month?: number;
    pending_fees?: number;
    overdue_fees?: number;
  };
  charts: {
    course_popularity: Array<{ course: string; enrolments: number }>;
    attendance_trend: Array<{
      month: string;
      month_start: string;
      percentage: number | null;
      sessions_marked: number;
    }>;
    lead_funnel?: Array<{ stage: string; count: number }>;
    growth_and_revenue?: Array<{
      month: string;
      month_start: string;
      admissions: number;
      revenue: number;
    }>;
    branch_performance?: Array<{
      branch_id: string;
      branch: string;
      students: number;
      active_enrolments: number;
      revenue: number;
    }>;
    exam_performance?: Array<{
      exam_id: string;
      exam: string;
      total_marks: number;
      exam_date: string;
      candidates: number;
      average_marks: number;
      pass_rate: number;
    }>;
  };
}
