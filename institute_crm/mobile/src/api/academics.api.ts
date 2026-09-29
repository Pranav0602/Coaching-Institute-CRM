import { api, type QueryParams } from './client';
import type {
  Assignment,
  Attendance,
  AttendanceSummary,
  Batch,
  BatchProgressSummary,
  BatchSummary,
  BulkAttendanceResult,
  Course,
  CourseSummary,
  KnowledgeDocument,
  Lecture,
  LectureRegister,
  LowAttendanceReport,
  Result,
  StudentIdCard,
  StudentProfile,
  Submission,
  TimetableEntry,
  WeekTimetable,
  Exam,
} from '@/types';

export const coursesApi = {
  list: (params?: QueryParams) => api.getList<Course>('/academics/courses/', params),
  summary: () => api.getList<CourseSummary>('/academics/courses/summary/'),
  syllabus: (courseId: string) => api.get<KnowledgeDocument>(`/academics/courses/${courseId}/syllabus/`),
  /**
   * The master catalogue is a `COURSE_CATALOGUE` document with no course behind
   * it, so it comes from the knowledge base rather than a course detail route.
   */
  masterCatalogue: () =>
    api.getList<KnowledgeDocument>('/rag/documents/', { category: 'COURSE_CATALOGUE' }),
};

export const batchesApi = {
  list: () => api.getList<Batch>('/academics/batches/'),
  summary: () => api.getList<BatchSummary>('/academics/batches/summary/'),
  progress: () => api.getList<BatchProgressSummary>('/academics/batches/progress-summary/'),
  roster: (batchId: string) => api.getList<unknown>(`/academics/batches/${batchId}/roster/`),
};

export const timetableApi = {
  weekly: (params?: QueryParams) => api.get<WeekTimetable>('/academics/timetables/weekly/', params),
};

export const lecturesApi = {
  list: (params?: QueryParams) => api.getList<Lecture>('/academics/lectures/', params),
  register: (lectureId: string) =>
    api.get<LectureRegister>(`/academics/lectures/${lectureId}/register/`),
  bulkAttendance: (lectureId: string, records: unknown[], completeLecture = true) =>
    api.post<BulkAttendanceResult>(`/academics/lectures/${lectureId}/bulk-attendance/`, {
      records,
      complete_lecture: completeLecture,
    }),
};

export const attendanceApi = {
  list: (params?: QueryParams) => api.getList<Attendance>('/academics/attendances/', params),
  /**
   * Always answers with a list. A parent gets one row per linked child from a
   * single call, which is why the student screens take `.find()` rather than
   * treating the response as a single object.
   */
  summary: (params?: QueryParams) =>
    api.getList<AttendanceSummary>('/academics/attendances/summary/', params),
  lowAttendance: (params?: QueryParams) =>
    api.get<LowAttendanceReport>('/academics/attendances/low-attendance/', params),
  batchReport: (params: QueryParams) =>
    api.getList<Record<string, unknown>>('/academics/attendances/batch-report/', params),
};

export const studentsApi = {
  list: (params?: QueryParams) => api.getList<StudentProfile>('/profiles/students/', params),
  idCard: (profileId: string) => api.get<StudentIdCard>(`/profiles/students/${profileId}/id-card/`),
  resolveQr: (qrPayload: string) =>
    api.post<{ matched: boolean; student?: StudentProfile; detail?: string }>(
      '/profiles/students/resolve-qr/',
      { qr_payload: qrPayload },
    ),
};

export const academicsApi = {
  courses: coursesApi,
  batches: batchesApi,
  timetable: timetableApi,
  lectures: lecturesApi,
  attendance: attendanceApi,
  students: studentsApi,
};

export const examsApi = {
  assignments: (params?: QueryParams) => api.getList<Assignment>('/exams/assignments/', params),
  submissions: (params?: QueryParams) => api.getList<Submission>('/exams/submissions/', params),
  submit: (body: { assignment: string; file_url: string }) =>
    api.post<Submission>('/exams/submissions/', body),
  evaluate: (submissionId: string, marks: number, feedback?: string) =>
    api.post<Submission>(`/exams/submissions/${submissionId}/evaluate/`, {
      marks_obtained: marks,
      feedback,
    }),
  exams: (params?: QueryParams) => api.getList<Exam>('/exams/exams/', params),
  results: (params?: QueryParams) => api.getList<Result>('/exams/results/', params),
  batchReport: (batchId: string) =>
    api.get<Record<string, unknown>>('/exams/exams/batch-report/', { batch_id: batchId }),
  assignmentBatchReport: (batchId: string) =>
    api.get<Record<string, unknown>>('/exams/assignments/batch-report/', { batch_id: batchId }),
};

export type { TimetableEntry };
