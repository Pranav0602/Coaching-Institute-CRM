import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert, Box, Button, Card, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogTitle, Divider, IconButton, MenuItem, Paper, Snackbar,
  Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField,
  Tooltip, Typography,
} from '@mui/material';
import { Add, DeleteOutline, Refresh, School } from '@mui/icons-material';
import api, { unwrapList } from '../../services/api';
import { useAuth, ROLES } from '../../context/AuthContext';

const errorMessage = (error, fallback = 'Something went wrong.') => {
  const data = error?.response?.data ?? error ?? {};
  if (typeof data?.message === 'string' && data.message) return data.message;
  if (typeof data?.detail === 'string' && data.detail) return data.detail;
  const errors = data?.errors;
  if (errors) {
    const first = Array.isArray(errors) ? errors[0] : Object.values(errors)[0];
    if (typeof first === 'string') return first;
    if (Array.isArray(first) && first.length) return first[0];
  }
  return error?.message || fallback;
};

/**
 * Branch Admin (own branch) / Super Admin (any branch) assign a teacher to a
 * branch and pick the courses they teach. Server re-validates everything.
 */
export const TeacherAssignmentsPanel = () => {
  const { user } = useAuth();
  const isSuperAdmin = user?.role_code === ROLES.SUPER_ADMIN;

  const [assignments, setAssignments] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });

  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [branchFilter, setBranchFilter] = useState('');
  const [form, setForm] = useState({ teacher: '', branch: '', course_ids: [], notes: '' });
  const [branchCourses, setBranchCourses] = useState([]);
  const [loadingCourses, setLoadingCourses] = useState(false);

  const ownBranch = user?.branch || '';

  const showToast = (message, severity = 'success') => setToast({ open: true, message, severity });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const branchParams = {};
      if (branchFilter) branchParams.branch_id = branchFilter;
      const [assignRes, teacherRes, branchRes] = await Promise.all([
        api.get('/academics/teacher-assignments/', { params: branchParams }).catch(() => ({ data: [] })),
        api.get('/accounts/users/', { params: { role: 'TEACHER' } }).catch(() => ({ data: [] })),
        api.get('/accounts/branches/').catch(() => ({ data: [] })),
      ]);
      setAssignments(unwrapList(assignRes));
      setTeachers(unwrapList(teacherRes));
      setBranches(unwrapList(branchRes));
    } catch (err) {
      showToast(errorMessage(err, 'Could not load teacher assignments.'), 'error');
    } finally {
      setLoading(false);
    }
  }, [branchFilter]);

  useEffect(() => { load(); }, [load]);

  // Courses that belong to the chosen branch.
  useEffect(() => {
    const branchId = form.branch || ownBranch;
    if (!branchId) { setBranchCourses([]); return undefined; }
    let cancelled = false;
    setLoadingCourses(true);
    api.get('/academics/teacher-assignments/available-courses/', { params: { branch_id: branchId } })
      .then((res) => { if (!cancelled) setBranchCourses(unwrapList(res)); })
      .catch(() => { if (!cancelled) setBranchCourses([]); })
      .finally(() => { if (!cancelled) setLoadingCourses(false); });
    return () => { cancelled = true; };
  }, [form.branch, ownBranch]);

  const effectiveBranch = form.branch || ownBranch;

  // Client-side guard: don't offer already-assigned courses for this teacher+branch.
  const existingKeys = useMemo(() => {
    const set = new Set();
    assignments.forEach((a) => {
      if (a.teacher === form.teacher && a.branch === effectiveBranch) set.add(a.course);
    });
    return set;
  }, [assignments, form.teacher, effectiveBranch]);

  const availableCourses = useMemo(
    () => branchCourses.filter((c) => !existingKeys.has(c.id)),
    [branchCourses, existingKeys],
  );

  const openDialog = () => {
    setForm({ teacher: '', branch: isSuperAdmin ? '' : ownBranch, course_ids: [], notes: '' });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.teacher) { showToast('Select a teacher.', 'warning'); return; }
    if (!effectiveBranch) { showToast('Select a branch.', 'warning'); return; }
    if (!form.course_ids.length) { showToast('Select at least one course.', 'warning'); return; }
    setSaving(true);
    try {
      await api.post('/academics/teacher-assignments/', {
        teacher: form.teacher,
        branch: effectiveBranch,
        course_ids: form.course_ids,
        notes: form.notes?.trim() || undefined,
      });
      showToast('Teacher assignment saved.', 'success');
      setOpen(false);
      await load();
    } catch (err) {
      showToast(errorMessage(err, 'Could not save assignment.'), 'error');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (assignment) => {
    try {
      await api.delete(`/academics/teacher-assignments/${assignment.id}/`);
      showToast('Assignment removed.', 'success');
      await load();
    } catch (err) {
      showToast(errorMessage(err, 'Could not remove assignment.'), 'error');
    }
  };

  return (
    <Card sx={{ p: 2.5, borderRadius: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }} flexWrap="wrap" gap={1}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <School color="primary" />
          <Typography variant="h6" sx={{ fontWeight: 800 }}>Teacher assignments</Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" size="small" startIcon={<Refresh />} onClick={load} disabled={loading}>Refresh</Button>
          <Button variant="contained" size="small" startIcon={<Add />} onClick={openDialog}>Assign teacher</Button>
        </Stack>
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Assign a teacher to {isSuperAdmin ? 'a branch' : 'your branch'} and choose the courses they teach.
        Courses are validated to belong to that branch; duplicate assignments are rejected.
      </Typography>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
        {isSuperAdmin && (
          <TextField select size="small" label="Filter by branch" value={branchFilter} onChange={(e) => setBranchFilter(e.target.value)} sx={{ minWidth: 220 }}>
            <MenuItem value="">All branches</MenuItem>
            {branches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}
          </TextField>
        )}
      </Stack>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
      ) : assignments.length === 0 ? (
        <Alert severity="info">No teacher assignments yet. Use “Assign teacher” to add one.</Alert>
      ) : (
        <Paper variant="outlined" sx={{ overflowX: 'auto' }}>
          <Table size="small">
            <TableHead><TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Teacher</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Branch</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Course</TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell>
            </TableRow></TableHead>
            <TableBody>
              {assignments.map((a) => (
                <TableRow key={a.id} hover>
                  <TableCell>{a.teacher_name || a.teacher_username}</TableCell>
                  <TableCell>{a.branch_name}</TableCell>
                  <TableCell><Chip size="small" label={`${a.course_title} (${a.course_code})`} /></TableCell>
                  <TableCell align="right">
                    <Tooltip title="Remove assignment">
                      <IconButton size="small" color="error" onClick={() => remove(a)} aria-label={`Remove ${a.course_title}`}>
                        <DeleteOutline fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      <Divider sx={{ my: 2 }} />

      <Dialog open={open} onClose={() => !saving && setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 800 }}>Assign teacher</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField select required fullWidth label="Teacher" value={form.teacher} onChange={(e) => setForm({ ...form, teacher: e.target.value })}>
              {teachers.map((t) => <MenuItem key={t.id} value={t.id}>{`${t.first_name} ${t.last_name}`.trim() || t.username} ({t.email})</MenuItem>)}
            </TextField>

            {isSuperAdmin ? (
              <TextField select required fullWidth label="Branch" value={form.branch} onChange={(e) => setForm({ ...form, branch: e.target.value, course_ids: [] })}>
                {branches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}
              </TextField>
            ) : (
              <TextField fullWidth label="Branch" value={branches.find((b) => b.id === effectiveBranch)?.name || ownBranch} disabled />
            )}

            <TextField
              select
              required
              fullWidth
              label="Courses taught"
              SelectProps={{ multiple: true }}
              value={form.course_ids}
              onChange={(e) => {
                const value = typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value;
                setForm({ ...form, course_ids: value });
              }}
              helperText={loadingCourses ? 'Loading courses…' : (availableCourses.length === 0 ? 'No courses available in this branch' : `${availableCourses.length} course(s) in this branch`)}
              disabled={!effectiveBranch || loadingCourses}
            >
              {availableCourses.map((c) => <MenuItem key={c.id} value={c.id}>{c.title} ({c.code})</MenuItem>)}
            </TextField>

            <TextField fullWidth label="Notes (optional)" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)} disabled={saving}>Cancel</Button>
          <Button variant="contained" onClick={submit} disabled={saving}>{saving ? 'Saving…' : 'Assign'}</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={toast.open} autoHideDuration={4500} onClose={() => setToast((c) => ({ ...c, open: false }))}>
        <Alert severity={toast.severity} onClose={() => setToast((c) => ({ ...c, open: false }))}>{toast.message}</Alert>
      </Snackbar>
    </Card>
  );
};
