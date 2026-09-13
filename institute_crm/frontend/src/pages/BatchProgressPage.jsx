import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog,
  DialogActions, DialogContent, DialogTitle, Drawer, Grid, LinearProgress,
  MenuItem, Snackbar, Stack, Tab, Table, TableBody, TableCell, TableHead,
  TableRow, Tabs, TextField, Typography,
} from '@mui/material';
import { Refresh } from '@mui/icons-material';
import { useAuth, ROLES } from '../context/AuthContext';
import api, { unwrapList, unwrapData } from '../services/api';

const listOf = (res) => unwrapList(res);
const dataOf = (res) => unwrapData(res);
const fmtPct = (v) => (v === null || v === undefined ? '—' : `${v}%`);
const healthColor = (h) => (h === 'AT_RISK' ? 'error' : h === 'NEEDS_ATTENTION' ? 'warning' : 'success');
const healthLabel = (h) => (h === 'AT_RISK' ? 'At Risk' : h === 'NEEDS_ATTENTION' ? 'Needs Attention' : 'On Track');

export const BatchProgressPage = () => {
  const { activeRole } = useAuth();
  const isSuperAdmin = activeRole === ROLES.SUPER_ADMIN;
  const [batches, setBatches] = useState([]);
  const [branches, setBranches] = useState([]);
  const [courses, setCourses] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [filters, setFilters] = useState({ branch_id: '', course_id: '', status: '', search: '' });
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [tab, setTab] = useState(0);
  const [assignOpen, setAssignOpen] = useState(false);
  const [assignIds, setAssignIds] = useState([]);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });
  const [showAtRiskOnly, setShowAtRiskOnly] = useState(false);
  const [assignmentIdx, setAssignmentIdx] = useState(0);
  const [examIdx, setExamIdx] = useState(0);
  const [assignmentReport, setAssignmentReport] = useState(null);
  const [examReport, setExamReport] = useState(null);

  const loadAll = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.branch_id) params.set('branch_id', filters.branch_id);
      if (filters.course_id) params.set('course_id', filters.course_id);
      if (filters.status) params.set('status', filters.status);
      if (filters.search) params.set('search', filters.search);
      const qs = params.toString() ? `?${params.toString()}` : '';
      const [summaryRes, branchRes, courseRes, teacherRes] = await Promise.all([
        api.get(`/academics/batches/progress-summary/${qs}`).catch(() => ({ data: [] })),
        isSuperAdmin ? api.get('/accounts/branches/').catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
        api.get('/academics/courses/').catch(() => ({ data: [] })),
        api.get('/accounts/users/?role=TEACHER').catch(() => ({ data: [] })),
      ]);
      const summary = dataOf(summaryRes);
      setBatches(Array.isArray(summary) ? summary : []);
      setBranches(listOf(branchRes));
      setCourses(listOf(courseRes));
      setTeachers(listOf(teacherRes));
    } catch (e) {
      setToast({ open: true, message: 'Could not load batch progress.', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps

  const applyFilters = () => loadAll();
  const updateFilter = (f) => (e) => setFilters((c) => ({ ...c, [f]: e.target.value }));

  const kpis = useMemo(() => {
    const active = batches.filter((b) => b.status === 'RUNNING');
    const totalStudents = batches.reduce((s, b) => s + (b.enrolled_count || 0), 0);
    const attVals = batches.map((b) => b.attendance_pct).filter((v) => v !== null && v !== undefined);
    const avgAtt = attVals.length ? Math.round((attVals.reduce((a, b) => a + b, 0) / attVals.length) * 100) / 100 : null;
    const healthVals = batches.map((b) => b.syllabus_progress_pct).filter((v) => v !== null && v !== undefined);
    const avgHealth = healthVals.length ? Math.round((healthVals.reduce((a, b) => a + b, 0) / healthVals.length) * 100) / 100 : null;
    return { active: active.length, total: batches.length, students: totalStudents, avgAtt, avgHealth };
  }, [batches]);

  const openDeepDive = async (batch) => {
    setSelected(batch);
    setTab(0);
    setAssignmentIdx(0);
    setExamIdx(0);
    setDetailLoading(true);
    try {
      const [progressRes, assignRes, examRes] = await Promise.all([
        api.get(`/academics/batches/${batch.id}/progress/`),
        api.get(`/assignments/assignments/batch-report/?batch_id=${batch.id}`).catch(() => null),
        api.get(`/assignments/exams/batch-report/?batch_id=${batch.id}`).catch(() => null),
      ]);
      setDetail(dataOf(progressRes));
      setAssignmentReport(assignRes ? dataOf(assignRes) : null);
      setExamReport(examRes ? dataOf(examRes) : null);
    } catch (e) {
      setToast({ open: true, message: 'Could not load batch detail.', severity: 'error' });
    } finally {
      setDetailLoading(false);
    }
  };

  const openAssign = () => {
    setAssignIds((detail?.teachers || []).map((t) => t.id));
    setAssignOpen(true);
  };

  const saveAssign = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await api.post(`/academics/batches/${selected.id}/assign-teachers/`, { teacher_ids: assignIds });
      setToast({ open: true, message: 'Teachers assigned.', severity: 'success' });
      setAssignOpen(false);
      openDeepDive(selected);
      loadAll();
    } catch (e) {
      setToast({ open: true, message: e?.detail || 'Could not assign teachers.', severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const students = useMemo(() => {
    const list = detail?.students || [];
    return showAtRiskOnly ? list.filter((s) => s.health === 'AT_RISK') : list;
  }, [detail, showAtRiskOnly]);

  const currentAssignment = assignmentReport?.assignments?.[assignmentIdx];
  const currentExam = examReport?.exams?.[examIdx];

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Batches Progress Hub</Typography>
          <Typography color="text.secondary">Timeline, faculty, attendance, assignments and exam performance per batch.</Typography>
        </Box>
        <Button variant="outlined" startIcon={<Refresh />} onClick={loadAll} disabled={loading}>Refresh</Button>
      </Box>

      <Card sx={{ p: 2, mb: 3 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          {isSuperAdmin && (
            <TextField select fullWidth label="Branch" value={filters.branch_id} onChange={updateFilter('branch_id')}>
              <MenuItem value="">All Branches</MenuItem>
              {branches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}
            </TextField>
          )}
          <TextField select fullWidth label="Course" value={filters.course_id} onChange={updateFilter('course_id')}>
            <MenuItem value="">All Courses</MenuItem>
            {courses.map((c) => <MenuItem key={c.id} value={c.id}>{c.title}</MenuItem>)}
          </TextField>
          <TextField select fullWidth label="Status" value={filters.status} onChange={updateFilter('status')}>
            <MenuItem value="">All</MenuItem>
            <MenuItem value="running">Running</MenuItem>
            <MenuItem value="upcoming">Upcoming</MenuItem>
            <MenuItem value="finished">Finished</MenuItem>
          </TextField>
          <TextField fullWidth label="Search batch" value={filters.search} onChange={updateFilter('search')} placeholder="Name or code" />
          <Button variant="contained" onClick={applyFilters} sx={{ minWidth: 120 }}>Apply</Button>
        </Stack>
      </Card>

      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        {[
          { label: 'Total Batches', value: kpis.total },
          { label: 'Active Batches', value: kpis.active },
          { label: 'Total Enrolled', value: kpis.students },
          { label: 'Avg Attendance', value: kpis.avgAtt === null ? '—' : `${kpis.avgAtt}%` },
          { label: 'Avg Syllabus Progress', value: kpis.avgHealth === null ? '—' : `${kpis.avgHealth}%` },
        ].map((k) => (
          <Grid item xs={12} sm={6} md={2.4} key={k.label}>
            <Card><CardContent>
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>{k.label}</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>{k.value ?? '—'}</Typography>
            </CardContent></Card>
          </Grid>
        ))}
      </Grid>

      {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box> : (
        <Grid container spacing={2.5}>
          {batches.map((b) => (
            <Grid item xs={12} md={6} lg={4} key={b.id}>
              <Card sx={{ p: 2.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap' }}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>{b.name}</Typography>
                  <Chip label={b.status} size="small" color={b.status === 'RUNNING' ? 'success' : b.status === 'UPCOMING' ? 'info' : 'default'} />
                </Box>
                <Typography variant="body2" color="text.secondary">{b.code} · {b.course_title} · {b.branch_name}</Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap' }}>
                  {(b.teachers || []).map((t) => <Chip key={t.id} label={t.name} size="small" variant="outlined" />)}
                  {(b.teachers || []).length === 0 && <Chip label="No teacher assigned" size="small" color="warning" />}
                </Stack>
                <Box sx={{ mt: 2 }}>
                  <Typography variant="caption" color="text.secondary">Timeline {b.timeline_pct ?? 0}%</Typography>
                  <LinearProgress variant="determinate" value={Number(b.timeline_pct || 0)} sx={{ height: 8, borderRadius: 2 }} />
                </Box>
                <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: 'wrap' }}>
                  <Chip label={`Att ${fmtPct(b.attendance_pct)}`} size="small" />
                  <Chip label={`Assign ${fmtPct(b.assignment_submission_pct)}`} size="small" color="info" />
                  <Chip label={`Pass ${fmtPct(b.exam_pass_rate_pct)}`} size="small" color="success" />
                  <Chip label={`${b.enrolled_count}/${b.max_capacity} seats`} size="small" variant="outlined" />
                  {(b.at_risk_count || 0) > 0 && <Chip label={`${b.at_risk_count} at risk`} size="small" color="error" />}
                </Stack>
                <Button fullWidth variant="contained" sx={{ mt: 2 }} onClick={() => openDeepDive(b)}>Deep-Dive</Button>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
      {!loading && batches.length === 0 && <Alert severity="info" sx={{ mt: 2 }}>No batches match the current filters.</Alert>}

      <Drawer anchor="right" open={Boolean(selected)} onClose={() => setSelected(null)} PaperProps={{ sx: { width: { xs: '100%', md: 900 } } }}>
        <Box sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>{selected?.name} — Deep Dive</Typography>
            <Button onClick={() => setSelected(null)}>Close</Button>
          </Box>
          {detailLoading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box> : detail && (
            <>
              <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                <Tab label="Overview & Faculty" />
                <Tab label="Student 360" />
                <Tab label="Assignments" />
                <Tab label="Exams" />
                <Tab label="Attendance" />
              </Tabs>
              {tab === 0 && (
                <Box>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}><Card sx={{ p: 2 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Timeline & Capacity</Typography>
                      <Typography variant="body2">Status: {detail.timeline.status} · {detail.timeline.progress_pct}% elapsed</Typography>
                      <Typography variant="body2">{detail.timeline.start_date} → {detail.timeline.end_date} ({detail.timeline.remaining_days} days left)</Typography>
                      <Typography variant="body2">Enrolled: {detail.batch.enrolled_count}/{detail.batch.max_capacity} · Seats left: {detail.batch.seats_remaining}</Typography>
                      <Typography variant="body2">Lectures: {detail.lectures.completed}/{detail.lectures.total} completed · {detail.lectures.cancelled} cancelled · Syllabus {detail.lectures.syllabus_progress_pct}%</Typography>
                      <Typography variant="body2" sx={{ mt: 1 }}>Topics: {(detail.lectures.topics_taught || []).join(', ') || '—'}</Typography>
                    </Card></Grid>
                    <Grid item xs={12} md={6}><Card sx={{ p: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Assigned Faculty</Typography>
                        <Button size="small" variant="outlined" onClick={openAssign}>+ Assign / Edit Teachers</Button>
                      </Box>
                      <Stack spacing={1} sx={{ mt: 1 }}>
                        {(detail.teachers || []).map((t) => <Chip key={t.id} label={`${t.name} (${t.email})`} />)}
                        {(detail.teachers || []).length === 0 && <Typography variant="body2" color="text.secondary">No teachers assigned yet.</Typography>}
                      </Stack>
                    </Card></Grid>
                  </Grid>
                </Box>
              )}
              {tab === 1 && (
                <Box>
                  <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                    <Button size="small" variant={showAtRiskOnly ? 'contained' : 'outlined'} color="error" onClick={() => setShowAtRiskOnly((v) => !v)}>
                      {showAtRiskOnly ? 'Showing At-Risk Only (click to clear)' : 'Show Only At-Risk Students'}
                    </Button>
                  </Stack>
                  <Table size="small"><TableHead><TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>Student</TableCell><TableCell sx={{ fontWeight: 700 }}>Attendance</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Assignments</TableCell><TableCell sx={{ fontWeight: 700 }}>Exam Avg</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Health</TableCell>
                  </TableRow></TableHead><TableBody>
                    {students.map((s) => (
                      <TableRow key={s.student_id}>
                        <TableCell>{s.student_name}</TableCell>
                        <TableCell>{fmtPct(s.attendance_pct)}</TableCell>
                        <TableCell>{s.assignments_submitted}/{s.assignments_total} ({fmtPct(s.assignment_completion_pct)})</TableCell>
                        <TableCell>{fmtPct(s.exam_avg_pct)}</TableCell>
                        <TableCell><Chip label={healthLabel(s.health)} size="small" color={healthColor(s.health)} /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody></Table>
                  {students.length === 0 && <Typography color="text.secondary" sx={{ mt: 2 }}>No students in this view.</Typography>}
                </Box>
              )}
              {tab === 2 && (
                <Box>
                  {!assignmentReport ? <Alert severity="info">No assignment data.</Alert> : (
                    <>
                      <TextField select fullWidth label="Assignment" value={assignmentIdx} onChange={(e) => setAssignmentIdx(Number(e.target.value))} sx={{ mb: 2 }}>
                        {(assignmentReport.assignments || []).map((a, i) => <MenuItem key={a.id} value={i}>{a.title}</MenuItem>)}
                      </TextField>
                      {currentAssignment && (
                        <>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            Due {currentAssignment.due_date} · {currentAssignment.total_marks} marks · Submission {currentAssignment.submission_rate_pct}% · Pending review {currentAssignment.pending_evaluations}
                          </Typography>
                          <Table size="small"><TableHead><TableRow>
                            <TableCell sx={{ fontWeight: 700 }}>Student</TableCell><TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                            <TableCell sx={{ fontWeight: 700 }}>File</TableCell><TableCell sx={{ fontWeight: 700 }}>Marks</TableCell><TableCell sx={{ fontWeight: 700 }}>Feedback</TableCell>
                          </TableRow></TableHead><TableBody>
                            {(currentAssignment.students || []).map((s) => (
                              <TableRow key={s.student_id}>
                                <TableCell>{s.student_name}</TableCell>
                                <TableCell><Chip size="small" label={`${s.status}${s.timeliness && s.timeliness !== s.status ? ` · ${s.timeliness}` : ''}`} color={s.status === 'SUBMITTED' ? 'success' : 'warning'} /></TableCell>
                                <TableCell>{s.file_url ? <a href={s.file_url} target="_blank" rel="noreferrer">Open</a> : '—'}</TableCell>
                                <TableCell>{s.marks_obtained ?? '—'}</TableCell>
                                <TableCell>{s.feedback || '—'}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody></Table>
                        </>
                      )}
                    </>
                  )}
                </Box>
              )}
              {tab === 3 && (
                <Box>
                  {!examReport ? <Alert severity="info">No exam data.</Alert> : (
                    <>
                      <TextField select fullWidth label="Exam" value={examIdx} onChange={(e) => setExamIdx(Number(e.target.value))} sx={{ mb: 2 }}>
                        {(examReport.exams || []).map((a, i) => <MenuItem key={a.id} value={i}>{a.title}</MenuItem>)}
                      </TextField>
                      {currentExam && (
                        <>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            {currentExam.exam_date} · Pass {currentExam.passing_marks}/{currentExam.total_marks} · Pass rate {fmtPct(currentExam.pass_rate_pct)} · Avg {fmtPct(currentExam.average_score_pct)}
                          </Typography>
                          <Table size="small"><TableHead><TableRow>
                            <TableCell sx={{ fontWeight: 700 }}>Student</TableCell><TableCell sx={{ fontWeight: 700 }}>Marks</TableCell>
                            <TableCell sx={{ fontWeight: 700 }}>Grade</TableCell><TableCell sx={{ fontWeight: 700 }}>Result</TableCell><TableCell sx={{ fontWeight: 700 }}>Remarks</TableCell>
                          </TableRow></TableHead><TableBody>
                            {(currentExam.students || []).map((s) => (
                              <TableRow key={s.student_id}>
                                <TableCell>{s.student_name}</TableCell>
                                <TableCell>{s.marks_obtained ?? 'Absent'} {s.percentage !== null && s.percentage !== undefined ? `(${s.percentage}%)` : ''}</TableCell>
                                <TableCell>{s.grade || '—'}</TableCell>
                                <TableCell>{s.status === 'ABSENT' ? <Chip size="small" label="Absent" color="default" /> : <Chip size="small" label={s.passed ? 'Pass' : 'Fail'} color={s.passed ? 'success' : 'error'} />}</TableCell>
                                <TableCell>{s.remarks || '—'}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody></Table>
                        </>
                      )}
                      <Typography variant="body2" sx={{ mt: 2 }}>Grade distribution: {JSON.stringify(examReport.grade_distribution)}</Typography>
                    </>
                  )}
                </Box>
              )}
              {tab === 4 && (
                <Box>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    Overall {fmtPct(detail.attendance.overall_pct)} · Low attendance (&lt;75%): {detail.attendance.low_attendance_count}
                  </Typography>
                  <Table size="small"><TableHead><TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>Student</TableCell><TableCell sx={{ fontWeight: 700 }}>Attendance</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Health</TableCell>
                  </TableRow></TableHead><TableBody>
                    {(detail.students || []).map((s) => (
                      <TableRow key={s.student_id}>
                        <TableCell>{s.student_name}</TableCell>
                        <TableCell>{fmtPct(s.attendance_pct)}</TableCell>
                        <TableCell><Chip size="small" label={healthLabel(s.health)} color={healthColor(s.health)} /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody></Table>
                </Box>
              )}
            </>
          )}
        </Box>
      </Drawer>

      <Dialog open={assignOpen} onClose={() => !saving && setAssignOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Assign Teachers — {selected?.name}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Multiple teachers can be assigned so co-teachers or substitutes can conduct lectures and mark attendance.
          </Typography>
          <TextField select fullWidth SelectProps={{ multiple: true }} label="Assigned Teachers" value={assignIds} onChange={(e) => setAssignIds(e.target.value)}>
            {teachers.map((t) => <MenuItem key={t.id} value={t.id}>{`${t.first_name} ${t.last_name}`.trim() || t.username} ({t.email})</MenuItem>)}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAssignOpen(false)} disabled={saving}>Cancel</Button>
          <Button variant="contained" onClick={saveAssign} disabled={saving}>{saving ? 'Saving…' : 'Save'}</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={toast.open} autoHideDuration={4500} onClose={() => setToast((c) => ({ ...c, open: false }))}>
        <Alert severity={toast.severity} onClose={() => setToast((c) => ({ ...c, open: false }))}>{toast.message}</Alert>
      </Snackbar>
    </Box>
  );
};
