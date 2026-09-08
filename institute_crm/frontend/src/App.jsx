import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { AuthProvider, useAuth, ROLES } from './context/AuthContext';
import { getAppTheme } from './theme/theme';
import { MainLayout } from './components/layout/MainLayout';
import { Login } from './pages/Login';
import { PublicEnquiry } from './pages/PublicEnquiry';
import { LandingPage } from './pages/LandingPage';
import { BranchManagementPage } from './pages/BranchManagementPage';
import { LeadManagementPage } from './pages/LeadManagementPage';
import { CoursesPage } from './pages/CoursesPage';
import { UserManagementPage } from './pages/UserManagementPage';
import { FinancePage } from './pages/FinancePage';
import { ReportsPage } from './pages/ReportsPage';
import { StudentsPage } from './pages/StudentsPage';
import { TeachersPage } from './pages/TeachersPage';
import { TimetablePage } from './pages/TimetablePage';
import { CreateCoursePage } from './pages/CreateCoursePage';
import { CreateBatchPage } from './pages/CreateBatchPage';
import { AttendancePage } from './pages/AttendancePage';
import { AssignmentsPage } from './pages/AssignmentsPage';
import { MaterialsPage } from './pages/MaterialsPage';
import { ExamsPage } from './pages/ExamsPage';
import { PipelineStagePage } from './pages/pipeline/PipelineStagePage';
import { FollowUpsPage } from './pages/FollowUpsPage';
import { LeadConversionPage } from './pages/LeadConversionPage';
import { ProfilePage } from './pages/ProfilePage';
import { KnowledgeBasePage } from './pages/KnowledgeBasePage';
import { RagAssistantWidget } from './components/rag/RagAssistantWidget';

// Dashboards
import { SuperAdminDashboard } from './pages/dashboards/SuperAdminDashboard';
import { BranchAdminDashboard } from './pages/dashboards/BranchAdminDashboard';
import { CounsellingOverview } from './pages/dashboards/CounsellingOverview';
import { TeacherDashboard } from './pages/dashboards/TeacherDashboard';
import { StudentDashboard } from './pages/dashboards/StudentDashboard';
import { ParentDashboard } from './pages/dashboards/ParentDashboard';
import { AccountantDashboard } from './pages/dashboards/AccountantDashboard';
import { ReceptionistDashboard } from './pages/dashboards/ReceptionistDashboard';

const DashboardRouter = () => {
  const { activeRole } = useAuth();

  switch (activeRole) {
    case ROLES.SUPER_ADMIN:
      return <SuperAdminDashboard />;
    case ROLES.BRANCH_ADMIN:
      return <BranchAdminDashboard />;
    case ROLES.ADMISSION_COUNSELOR:
      return <CounsellingOverview />;
    case ROLES.TEACHER:
      return <TeacherDashboard />;
    case ROLES.STUDENT:
      return <StudentDashboard />;
    case ROLES.PARENT:
      return <ParentDashboard />;
    case ROLES.ACCOUNTANT:
      return <AccountantDashboard />;
    case ROLES.RECEPTIONIST:
      return <ReceptionistDashboard />;
    default:
      return <SuperAdminDashboard />;
  }
};

const RequireRole = ({ children, allowed }) => {
  const { activeRole } = useAuth();
  if (!allowed.includes(activeRole)) {
    return <Navigate to="/" replace />;
  }
  return children;
};

const AppContent = () => {
  const { isAuthenticated, themeMode } = useAuth();
  const theme = getAppTheme(themeMode);
  const [authViewMode, setAuthViewMode] = useState('landing'); // 'landing' | 'login' | 'enquiry'

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {!isAuthenticated ? (
        authViewMode === 'enquiry' ? (
          <PublicEnquiry onBackToLogin={() => setAuthViewMode('landing')} />
        ) : authViewMode === 'login' ? (
          <Login onOpenEnquiry={() => setAuthViewMode('enquiry')} onBackToLanding={() => setAuthViewMode('landing')} />
        ) : (
          <LandingPage onOpenLogin={() => setAuthViewMode('login')} onOpenEnquiry={() => setAuthViewMode('enquiry')} />
        )
      ) : (
        <MainLayout>
          <Routes>
            <Route path="/" element={<DashboardRouter />} />
            <Route path="/branches" element={<BranchManagementPage />} />
            <Route path="/leads" element={<LeadManagementPage />} />
            <Route path="/courses" element={<CoursesPage />} />
            <Route path="/users" element={<UserManagementPage />} />
            <Route path="/finance" element={<FinancePage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/students" element={<StudentsPage />} />
            <Route path="/teachers" element={<TeachersPage />} />
            <Route path="/timetable" element={<TimetablePage />} />
            <Route path="/create-course" element={<CreateCoursePage />} />
            <Route path="/create-batch" element={<CreateBatchPage />} />
            <Route path="/attendance" element={<AttendancePage />} />
            <Route path="/assignments" element={<AssignmentsPage />} />
            <Route path="/materials" element={<MaterialsPage />} />
            <Route path="/exams" element={<ExamsPage />} />
            <Route path="/pipeline/:stage" element={<PipelineStagePage />} />
            <Route path="/followups" element={<FollowUpsPage />} />
            <Route path="/convert" element={<LeadConversionPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route
              path="/knowledge-base"
              element={
                <RequireRole allowed={[ROLES.SUPER_ADMIN, ROLES.BRANCH_ADMIN]}>
                  <KnowledgeBasePage />
                </RequireRole>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </MainLayout>
      )}
      <RagAssistantWidget onOpenEnquiry={() => setAuthViewMode('enquiry')} />
    </ThemeProvider>
  );
};

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </BrowserRouter>
  );
}
