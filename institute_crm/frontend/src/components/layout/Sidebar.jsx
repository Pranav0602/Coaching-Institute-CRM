import React, { useState, useEffect } from 'react';
import {
  Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText,
  Box, Typography, Divider, Chip
} from '@mui/material';
import {
  Dashboard, People, School, Assignment, EventNote,
  AttachMoney, Analytics, MeetingRoom, MenuBook, Badge,
  SupportAgent, RecordVoiceOver, Quiz, ReceiptLong, FiberManualRecord, LibraryBooks, AutoStories
} from '@mui/icons-material';
import { useAuth, ROLES } from '../../context/AuthContext';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { PIPELINE_STAGES, STAGE_COLORS } from '../../constants/pipeline';

export const Sidebar = ({ open, onClose }) => {
  const { activeRole } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [stageCounts, setStageCounts] = useState({});

  useEffect(() => {
    if (activeRole !== ROLES.ADMISSION_COUNSELOR) {
      setStageCounts({});
      return;
    }
    let cancelled = false;
    api.get('/crm/leads/stage-counts/')
      .then(res => {
        const d = res.data || res;
        if (!cancelled && d && typeof d === 'object') setStageCounts(d);
      })
      .catch(() => { if (!cancelled) setStageCounts({}); });
    return () => { cancelled = true; };
  }, [activeRole, location.pathname]);

  const getRoleMenuItems = () => {
    switch (activeRole) {
      case ROLES.SUPER_ADMIN:
        return [
          { text: 'Overview Dashboard', icon: <Dashboard />, path: '/' },
          { text: 'Branch Management', icon: <School />, path: '/branches' },
          { text: 'Lead Management CRM', icon: <SupportAgent />, path: '/leads' },
          { text: 'Academic Courses', icon: <MenuBook />, path: '/courses' },
          { text: 'Batches Progress', icon: <School />, path: '/batches' },
          { text: 'Assignments & Submissions', icon: <Assignment />, path: '/assignments' },
          { text: 'Exams & Performance', icon: <Quiz />, path: '/exams' },
          { text: 'Knowledge Base', icon: <LibraryBooks />, path: '/knowledge-base' },
          { text: 'User Access & Roles', icon: <People />, path: '/users' },
          { text: 'Financial Accounts', icon: <AttachMoney />, path: '/finance' },
          { text: 'Reports & Analytics', icon: <Analytics />, path: '/reports' },
        ];
      case ROLES.BRANCH_ADMIN:
        return [
          { text: 'Branch Dashboard', icon: <Dashboard />, path: '/' },
          { text: 'Students & Batches', icon: <People />, path: '/students' },
          { text: 'Teachers & Staff', icon: <Badge />, path: '/teachers' },
          { text: 'Timetables', icon: <EventNote />, path: '/timetable' },
          { text: 'Batches Progress', icon: <School />, path: '/batches' },
          { text: 'Assignments & Submissions', icon: <Assignment />, path: '/assignments' },
          { text: 'Exams & Performance', icon: <Quiz />, path: '/exams' },
          { text: 'Create Course', icon: <MenuBook />, path: '/create-course' },
          { text: 'Create Batch', icon: <School />, path: '/create-batch' },
          { text: 'Knowledge Base', icon: <LibraryBooks />, path: '/knowledge-base' },
          { text: 'Branch Revenue', icon: <AttachMoney />, path: '/finance' },
        ];
      case ROLES.ADMISSION_COUNSELOR:
        return [
          { text: 'Counselling Desk', icon: <Dashboard />, path: '/' },
          { text: 'Scheduled Follow-ups', icon: <EventNote />, path: '/followups' },
          { text: 'Lead Conversion', icon: <School />, path: '/convert' },
        ];
      case ROLES.TEACHER:
        return [
          { text: 'Teacher Portal', icon: <Dashboard />, path: '/' },
          { text: 'Today Lectures & Attendance', icon: <EventNote />, path: '/attendance' },
          { text: 'Assignments & Evaluation', icon: <Assignment />, path: '/assignments' },
          { text: 'Study Materials Upload', icon: <MenuBook />, path: '/materials' },
          { text: 'Exams & Marks', icon: <Quiz />, path: '/exams' },
        ];
      case ROLES.STUDENT:
        return [
          { text: 'Student Portal', icon: <Dashboard />, path: '/' },
          { text: 'Class Timetable', icon: <EventNote />, path: '/timetable' },
          { text: 'My Assignments', icon: <Assignment />, path: '/assignments' },
          { text: 'Exam Performance', icon: <Quiz />, path: '/marks' },
          { text: 'Fee Receipts', icon: <ReceiptLong />, path: '/fees' },
          { text: 'Study Materials', icon: <MenuBook />, path: '/materials' },
        ];
      case ROLES.PARENT:
        return [
          { text: 'Parent Portal', icon: <Dashboard />, path: '/' },
          { text: 'Child Attendance %', icon: <EventNote />, path: '/child-attendance' },
          { text: 'Test Scores', icon: <Quiz />, path: '/child-marks' },
          { text: 'Fee Dues & History', icon: <ReceiptLong />, path: '/child-fees' },
        ];
      case ROLES.ACCOUNTANT:
        return [
          { text: 'Accountant Desk', icon: <Dashboard />, path: '/' },
          { text: 'Fee Collection', icon: <AttachMoney />, path: '/collection' },
          { text: 'Pending Installments', icon: <ReceiptLong />, path: '/installments' },
          { text: 'Record Payment & Receipt', icon: <ReceiptLong />, path: '/receipts' },
          { text: 'Refund Requests', icon: <AttachMoney />, path: '/refunds' },
        ];
      case ROLES.RECEPTIONIST:
        return [
          { text: 'Reception Desk', icon: <Dashboard />, path: '/' },
          { text: 'Walk-in Visitor Entry', icon: <MeetingRoom />, path: '/visitors' },
          { text: 'New Lead Enquiry', icon: <RecordVoiceOver />, path: '/enquiries' },
          { text: 'Print Student ID Card', icon: <Badge />, path: '/id-cards' },
        ];
      default:
        return [{ text: 'Dashboard', icon: <Dashboard />, path: '/' }];
    }
  };

  const menuItems = getRoleMenuItems();
  const isCounselor = activeRole === ROLES.ADMISSION_COUNSELOR;

  const pipelineItems = PIPELINE_STAGES.map((stage) => ({
    stage,
    path: `/pipeline/${encodeURIComponent(stage)}`,
    count: stageCounts[stage] || 0,
  }));

  return (
    <Drawer
      variant="persistent"
      open={open}
      onClose={onClose}
      sx={{
        width: 260,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: 260,
          boxSizing: 'border-box',
          borderRight: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: 'background.paper',
        },
      }}
    >
      <Box sx={{ p: 2.5, textAlign: 'center' }}>
        <Chip
          label={`${activeRole.replace('_', ' ')} MODE`}
          color="secondary"
          size="small"
          sx={{ fontWeight: 700, borderRadius: 2 }}
        />
      </Box>
      <Divider />
      <List sx={{ px: 1.5, py: 1 }}>
        {menuItems.map((item) => (
          <ListItem key={item.path} disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton
              component={NavLink}
              to={item.path}
              end={item.path === '/'}
              selected={item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path)}
              sx={{
                borderRadius: 2,
                '&.Mui-selected': {
                  backgroundColor: 'primary.main',
                  color: '#fff',
                  '& .MuiListItemIcon-root': { color: '#fff' },
                },
                '&:hover': {
                  backgroundColor: 'rgba(99, 102, 241, 0.12)',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 40, color: 'text.secondary' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText
                primary={item.text}
                primaryTypographyProps={{ fontSize: '0.9rem', fontWeight: 600 }}
              />
            </ListItemButton>
          </ListItem>
        ))}

        {isCounselor && (
          <>
            <ListItem disablePadding sx={{ pl: 1.5, pt: 1, pb: 0.5 }}>
              <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 700, fontSize: '0.68rem', letterSpacing: 1.2 }}>
                Lead Pipeline
              </Typography>
            </ListItem>
            {pipelineItems.map(({ stage, path, count }) => (
              <ListItem key={stage} disablePadding sx={{ mb: 0.5 }}>
                <ListItemButton
                  selected={location.pathname === path}
                  onClick={() => navigate(path)}
                  sx={{
                    borderRadius: 2,
                    '&.Mui-selected': {
                      backgroundColor: 'primary.main',
                      color: '#fff',
                      '& .MuiListItemIcon-root': { color: '#fff' },
                    },
                    '&:hover': {
                      backgroundColor: 'rgba(99, 102, 241, 0.12)',
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 40, color: 'text.secondary' }}>
                    <FiberManualRecord sx={{ color: STAGE_COLORS[stage], fontSize: 12 }} />
                  </ListItemIcon>
                  <ListItemText
                    primary={stage}
                    primaryTypographyProps={{ fontSize: '0.85rem', fontWeight: 500 }}
                  />
                  <Chip
                    label={count}
                    size="small"
                    sx={{
                      height: 20,
                      minWidth: 20,
                      fontSize: '0.68rem',
                      bgcolor: STAGE_COLORS[stage],
                      color: '#fff',
                    }}
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </>
        )}
      </List>
    </Drawer>
  );
};