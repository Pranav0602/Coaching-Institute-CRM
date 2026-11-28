import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Divider,
  Grid, LinearProgress, Paper, Stack, Table, TableBody, TableCell, TableHead,
  TableRow, Tab, Tabs, Typography,
} from '@mui/material';
import {
  EventNote, Assignment, School, People, Refresh, NotificationsActive,
  CheckCircle, Event, LocalLibrary,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import api, { unwrapData } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const fmtPct = (v) => (v === null || v === undefined ? '—' : `${v}%`);
const DAY_ORDER = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'];

const Metric = ({ label, value, icon }) => (
  <Grid item xs={12} sm={6} md={3}>
    <Card><CardContent>
      <Stack direction="row" spacing={1} alignItems="center">
        {icon}
        <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>{label}</Typography>
      </Stack>
      <Typography variant="h4" sx={{ fontWeight: 800, my: 0.5 }}>{value ?? '—'}</Typography>
    </CardContent></Card>
  </Grid>
);

export const TeacherDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get('/academics/teacher-dashboard/');
      setData(unwrapData(res));
    } catch (err) {
      setError(err?.message || err?.detail || 'Could not load your teacher dashboard.');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}><CircularProgress /></Box>;
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
        <Button variant="outlined" startIcon={<Refresh />} onClick={load}>Retry</Button>
      </Box>
    );
  }

  const summary = data?.summary || {};
  const assignedCourses = data?.assigned_courses || [];
  const schedule = data?.schedule || [];
  const notices = data?.notices || [];
  const notifications = data?.notifications || [];
  const upcoming = data?.upcoming_activities || [];
  const tasks = data?.tasks || [];
  const today = data?.today_schedule || [];

  const scheduleByDay = DAY_ORDER.map((day) => ({
    day,
    slots: schedule.filter((s) => s.day_of_week === day).sort((a, b) => (a.start_time || '').localeCompare(b.start_time || '')),
  }));

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Teacher Dashboard</Typography>
          <Typography color="text.secondary">
            {data?.teacher?.name || user?.username}
            {data?.assigned_branch ? ` · ${data.assigned_branch}` : ''}
            {' · '}your assigned courses, classes and progress
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" startIcon={<Refresh />} onClick={load}>Refresh</Button>
          <Button variant="contained" startIcon={<EventNote />} onClick={() => navigate('/attendance')}>Mark Attendance</Button>
        </Stack>
      </Box>

      {/* Summary metrics */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Metric label="Assigned Courses" value={summary.assigned_courses ?? assignedCourses.length} icon={<LocalLibrary color="primary" />} />
        <Metric label="Assigned Batches" value={summary.assigned_batches ?? 0} icon={<School color="primary" />} />
        <Metric label="Students" value={summary.total_students ?? 0} icon={<People color="primary" />} />
        <Metric label="Pending Tasks" value={summary.pending_tasks ?? tasks.length} icon={<Assignment color="primary" />} />
      </Grid>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }} variant="scrollable" scrollButtons="auto">
        <Tab label="Assigned Courses" />
        <Tab label="Schedule" />
        <Tab label="Students" />
        <Tab label="Attendance & Progress" />
        <Tab label="Notices & Tasks" />
      </Tabs>

      {/* TAB: Assigned courses */}
      {tab === 0 && (
        assignedCourses.length === 0 ? (
          <Alert severity="info">
            No courses are assigned to you yet. A branch admin can assign you to a branch and select the courses you teach.
          </Alert>
        ) : (
          <Grid container spacing={2.5}>
            {assignedCourses.map((c) => (
              <Grid item xs={12} md={6} key={c.course_id}>
                <Card sx={{ p: 2.5, height: '100%' }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={1}>
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>{c.course_title}</Typography>
                      <Typography variant="body2" color="text.secondary">{c.course_code}</Typography>
                    </Box>
                    <Stack direction="row" spacing={0.5} flexWrap="wrap">
                      {(c.branch_names || []).map((b) => <Chip key={b} label={b} size="small" variant="outlined" />)}
                    </Stack>
                  </Stack>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Branch: {data?.assigned_branch || (c.branch_names || []).join(', ') || '—'}
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap' }}>
                    <Chip size="small" icon={<People />} label={`${c.student_count} student(s)`} />
                    <Chip size="small" label={`${(c.batches || []).length} batch(es)`} />
                    {c.has_course_assignment && <Chip size="small" color="success" label="Assigned" />}
                  </Stack>
                  <Divider sx={{ my: 1.5 }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>Batches</Typography>
                  {(c.batches || []).length === 0 ? (
                    <Typography variant="body2" color="text.secondary">No batches yet.</Typography>
                  ) : (
                    (c.batches || []).map((b) => (
                      <Box key={b.id} sx={{ mb: 0.5 }}>
                        <Typography variant="body2">{b.name} ({b.code})</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {b.enrolled_count}/{b.max_capacity} enrolled · Att {fmtPct(b.attendance_pct)} · Syllabus {fmtPct(b.syllabus_progress_pct)}
                        </Typography>
                      </Box>
                    ))
                  )}
                </Card>
              </Grid>
            ))}
          </Grid>
        )
      )}

      {/* TAB: Schedule */}
      {tab === 1 && (
        <Box>
          {/* Today */}
          <Card sx={{ p: 2.5, mb: 2 }}>
            <Typography variant="h6" sx={{ mb: 1, fontWeight: 700 }}>Today&apos;s classes</Typography>
            {today.length === 0 ? <Typography color="text.secondary">No classes scheduled today.</Typography> : (
              <Stack spacing={1}>
                {today.map((s) => (
                  <Box key={s.id} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                    <Typography sx={{ fontWeight: 600 }}>{s.start_time}–{s.end_time} · {s.subject}</Typography>
                    <Typography variant="body2" color="text.secondary">{s.batch_name} · {s.branch_name} · {s.room_number}</Typography>
                  </Box>
                ))}
              </Stack>
            )}
          </Card>

          {schedule.length === 0 ? <Alert severity="info">No schedule slots for your assigned courses.</Alert> : (
            <Grid container spacing={2}>
              {scheduleByDay.filter((d) => d.slots.length).map(({ day, slots }) => (
                <Grid item xs={12} md={6} key={day}>
                  <Card sx={{ p: 2.5 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>{day.charAt(0) + day.slice(1).toLowerCase()}</Typography>
                    <Table size="small"><TableBody>
                      {slots.map((s) => (
                        <TableRow key={s.id}>
                          <TableCell sx={{ fontWeight: 600 }}>{s.start_time}–{s.end_time}</TableCell>
                          <TableCell>{s.subject}</TableCell>
                          <TableCell>{s.batch_name}</TableCell>
                          <TableCell>{s.room_number}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody></Table>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}

          {/* Upcoming activities */}
          <Card sx={{ p: 2.5, mt: 2 }}>
            <Typography variant="h6" sx={{ mb: 1, fontWeight: 700 }}><Event sx={{ verticalAlign: 'middle', mr: 1 }} />Upcoming activities</Typography>
            {upcoming.length === 0 ? <Typography color="text.secondary">No upcoming lectures or exams.</Typography> : (
              <Stack spacing={1}>
                {upcoming.map((u, i) => (
                  <Box key={`${u.type}-${u.id}-${i}`} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                    <Chip size="small" label={u.type} color={u.type === 'EXAM' ? 'warning' : 'info'} sx={{ mr: 1 }} />
                    <Typography component="span" sx={{ fontWeight: 600 }}>{u.title}</Typography>
                    <Typography variant="body2" color="text.secondary">{u.date}{u.batch_name ? ` · ${u.batch_name}` : ''}{u.subject ? ` · ${u.subject}` : ''}</Typography>
                  </Box>
                ))}
              </Stack>
            )}
          </Card>
        </Box>
      )}

      {/* TAB: Students */}
      {tab === 2 && (
        <Box>
          {assignedCourses.length === 0 ? <Alert severity="info">No assigned courses.</Alert> : assignedCourses.map((c) => (
            <Card key={c.course_id} sx={{ p: 2.5, mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>{c.course_title}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{c.student_count} student(s) enrolled</Typography>
              {(c.students || []).length === 0 ? <Typography color="text.secondary">No students enrolled in this course yet.</Typography> : (
                <Paper variant="outlined" sx={{ overflowX: 'auto' }}>
                  <Table size="small"><TableHead><TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>REG NO</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Name</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Email</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Phone</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Batch</TableCell>
                  </TableRow></TableHead><TableBody>
                    {c.students.map((s) => (
                      <TableRow key={s.student_id} hover>
                        <TableCell sx={{ fontWeight: 600 }}>{s.reg_no || '—'}</TableCell>
                        <TableCell>{s.name}</TableCell>
                        <TableCell>{s.email || '—'}</TableCell>
                        <TableCell>{s.phone || '—'}</TableCell>
                        <TableCell>{s.batch || '—'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody></Table>
                </Paper>
              )}
            </Card>
          ))}
        </Box>
      )}

      {/* TAB: Attendance & progress */}
      {tab === 3 && (
        <Box>
          {assignedCourses.length === 0 ? <Alert severity="info">No assigned courses.</Alert> : assignedCourses.map((c) => (
            <Card key={c.course_id} sx={{ p: 2.5, mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>{c.course_title}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Attendance {fmtPct(c.attendance?.overall_pct)} · Low attendance (&lt;{c.attendance?.threshold ?? 75}%): {c.attendance?.low_attendance_count ?? 0}
              </Typography>
              {(c.batches || []).map((b) => (
                <Box key={b.id} sx={{ mb: 1.5 }}>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography variant="body2">{b.name}</Typography>
                    <Typography variant="body2" color="text.secondary">{fmtPct(b.syllabus_progress_pct)} syllabus · {fmtPct(b.attendance_pct)} attendance</Typography>
                  </Stack>
                  <LinearProgress variant="determinate" value={Number(b.syllabus_progress_pct || 0)} sx={{ height: 8, borderRadius: 2 }} />
                </Box>
              ))}
              <Button size="small" sx={{ mt: 1 }} onClick={() => navigate('/attendance')}>Open attendance</Button>
            </Card>
          ))}
        </Box>
      )}

      {/* TAB: Notices & tasks */}
      {tab === 4 && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Card sx={{ p: 2.5 }}>
              <Typography variant="h6" sx={{ mb: 1, fontWeight: 700 }}><NotificationsActive sx={{ verticalAlign: 'middle', mr: 1 }} />Notices</Typography>
              {notices.length === 0 ? <Typography color="text.secondary">No notices.</Typography> : (
                <Stack spacing={1.5}>
                  {notices.map((n) => (
                    <Box key={n.id} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                      <Typography sx={{ fontWeight: 700 }}>{n.title}</Typography>
                      <Typography variant="body2" color="text.secondary">{n.content}</Typography>
                      {n.published_by && <Typography variant="caption" color="text.secondary">— {n.published_by}</Typography>}
                    </Box>
                  ))}
                </Stack>
              )}
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card sx={{ p: 2.5, mb: 2 }}>
              <Typography variant="h6" sx={{ mb: 1, fontWeight: 700 }}><Assignment sx={{ verticalAlign: 'middle', mr: 1 }} />Tasks</Typography>
              {tasks.length === 0 ? <Typography color="text.secondary">No pending tasks. You&apos;re all caught up.</Typography> : (
                <Stack spacing={1}>
                  {tasks.map((t, i) => (
                    <Box key={`${t.assignment_id}-${t.student_id}-${i}`} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                      <Chip size="small" icon={<CheckCircle />} label="Grade" color="warning" sx={{ mr: 1 }} />
                      <Typography component="span" sx={{ fontWeight: 600 }}>{t.assignment_title}</Typography>
                      <Typography variant="body2" color="text.secondary">Submission from {t.student}</Typography>
                    </Box>
                  ))}
                </Stack>
              )}
              <Button size="small" sx={{ mt: 1 }} onClick={() => navigate('/assignments')}>Go to assignments</Button>
            </Card>

            <Card sx={{ p: 2.5 }}>
              <Typography variant="h6" sx={{ mb: 1, fontWeight: 700 }}>Notifications</Typography>
              {notifications.length === 0 ? <Typography color="text.secondary">No notifications.</Typography> : (
                <Stack spacing={1}>
                  {notifications.map((n) => (
                    <Box key={n.id} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                      <Typography sx={{ fontWeight: 600 }}>{n.title}</Typography>
                      <Typography variant="body2" color="text.secondary">{n.message}</Typography>
                    </Box>
                  ))}
                </Stack>
              )}
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};
