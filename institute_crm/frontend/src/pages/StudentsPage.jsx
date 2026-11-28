import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Avatar, Box, Button, Card, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogTitle, Grid, IconButton, MenuItem,
  Paper, Snackbar, Alert, Stack, Table, TableBody, TableCell, TableContainer,
  TableHead, TablePagination, TableRow, TextField, Tooltip, Typography,
} from '@mui/material';
import { Visibility, Refresh, PersonAdd, DeleteOutline, Block } from '@mui/icons-material';
import { useSearchParams } from 'react-router-dom';
import { PageHeader, MetricCards } from './PageLayout';
import { AddStudentModal } from '../components/students/AddStudentModal';
import { StudentProfileDialog } from '../components/students/StudentProfileDialog';
import api, { unwrapList } from '../services/api';
import { useAuth, ROLES } from '../context/AuthContext';

const formatDate = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString(undefined, { dateStyle: 'medium' });
  } catch {
    return value;
  }
};

const extractError = (err, fallback) => {
  const data = err?.response?.data ?? err ?? {};
  if (typeof data?.message === 'string' && data.message) return data.message;
  if (typeof data?.detail === 'string' && data.detail) return data.detail;
  const errors = data?.errors;
  if (errors) {
    const first = Array.isArray(errors) ? errors[0] : Object.values(errors)[0];
    if (typeof first === 'string') return first;
    if (Array.isArray(first) && first.length) return first[0];
  }
  return err?.message || fallback;
};

const withinDays = (value, days) => {
  if (!value) return false;
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return false;
  return Date.now() - then <= days * 24 * 60 * 60 * 1000;
};

export const StudentsPage = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const isReceptionDesk = [ROLES.RECEPTIONIST, ROLES.ADMISSION_COUNSELOR].includes(user?.role_code);
  const isSuperAdmin = user?.role_code === ROLES.SUPER_ADMIN;
  const canManageAdmissions = [ROLES.RECEPTIONIST, ROLES.BRANCH_ADMIN, ROLES.SUPER_ADMIN].includes(user?.role_code);

  const [students, setStudents] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [branches, setBranches] = useState([]);
  const [courses, setCourses] = useState([]);
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState('');

  const [showAdd, setShowAdd] = useState(false);
  const [selectedRow, setSelectedRow] = useState(null);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });

  // `branch` is a list for Super Admin (multi-branch filter); single value otherwise.
  const [filters, setFilters] = useState({ search: '', branch: [], course: '', batch: '', status: '' });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  // Admission cancellation + removal dialogs.
  const [cancelTarget, setCancelTarget] = useState(null);
  const [cancelReason, setCancelReason] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [actionBusy, setActionBusy] = useState(false);

  const selectedBranches = Array.isArray(filters.branch) ? filters.branch : (filters.branch ? [filters.branch] : []);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    setErrorDetail('');
    const branchParams = {};
    if (selectedBranches.length === 1) branchParams.branch_id = selectedBranches[0];
    else if (selectedBranches.length > 1) branchParams.branch_ids = selectedBranches;
    Promise.all([
      api.get('/accounts/users/', { params: { role: 'STUDENT', ...branchParams } }),
      api.get('/profiles/students/', { params: branchParams }).catch(() => ({ data: [] })),
      api.get('/accounts/branches/').catch(() => ({ data: [] })),
      api.get('/academics/courses/').catch(() => ({ data: [] })),
      api.get('/academics/batches/').catch(() => ({ data: [] })),
    ])
      .then(([studentRes, profileRes, branchRes, courseRes, batchRes]) => {
        setStudents(unwrapList(studentRes));
        setProfiles(unwrapList(profileRes));
        setBranches(unwrapList(branchRes));
        setCourses(unwrapList(courseRes));
        setBatches(unwrapList(batchRes));
      })
      .catch((err) => {
        setStudents([]);
        setProfiles([]);
        setError(err?.detail || 'Could not load students.');
        setErrorDetail(err?.message || '');
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBranches.join(',')]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (isReceptionDesk && user?.branch) {
      setFilters((prev) => {
        const cur = Array.isArray(prev.branch) ? prev.branch : [];
        return cur.includes(user.branch) && cur.length === 1 ? prev : { ...prev, branch: [user.branch] };
      });
    }
  }, [isReceptionDesk, user?.branch]);

  useEffect(() => {
    if (searchParams.get('add') === '1') {
      setShowAdd(true);
      const next = new URLSearchParams(searchParams);
      next.delete('add');
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const rows = useMemo(() => {
    const profileByUser = new Map(profiles.map((p) => [p.user, p]));
    const batchById = new Map(batches.map((b) => [b.id, b]));
    return students.map((student) => {
      const profile = profileByUser.get(student.id) || {};
      const branchName = student.branch_name || profile.branch_name;
      const batch = batchById.get(profile.batch);
      return {
        id: student.id,
        user: student,
        profile,
        full_name: student.full_name || `${student.first_name || ''} ${student.last_name || ''}`.trim() || student.username,
        reg_no: profile.reg_no || '—',
        course_id: profile.course || batch?.course || '',
        course_title: profile.course_title || '—',
        batch_id: profile.batch || '',
        batch_name: profile.batch_name || 'Not assigned',
        branch_id: student.branch || profile.branch || '',
        branch_name: branchName || '—',
        contact: [student.phone, student.email].filter(Boolean).join(' · '),
        mobile: student.phone || '',
        secondary_phone: profile.secondary_phone || '',
        softwares: Array.isArray(profile.softwares) ? profile.softwares : [],
        admission_date: student.date_joined,
        status: student.is_active === false ? 'INACTIVE' : 'ACTIVE',
        admission_status: profile.admission_status || 'PENDING',
        cancellation_reason: profile.cancellation_reason || '',
        is_enrolled: Boolean(profile.is_enrolled),
        deletion_eligible: Boolean(profile.deletion_eligible),
        profile_id: profile.id || profile.reg_no || '',
      };
    }).sort((a, b) => {
      const aRegNo = a.reg_no === '—' ? '' : a.reg_no;
      const bRegNo = b.reg_no === '—' ? '' : b.reg_no;
      if (!aRegNo && !bRegNo) return a.full_name.localeCompare(b.full_name);
      if (!aRegNo) return 1;
      if (!bRegNo) return -1;
      return aRegNo.localeCompare(bRegNo, undefined, { numeric: true, sensitivity: 'base' });
    });
  }, [students, profiles, batches]);

  const filteredRows = useMemo(() => {
    const term = filters.search.trim().toLowerCase();
    const branchSel = Array.isArray(filters.branch) ? filters.branch : (filters.branch ? [filters.branch] : []);
    return rows.filter((row) => {
      if (branchSel.length && !branchSel.includes(row.branch_id)) return false;
      if (filters.course && row.course_id !== filters.course && row.profile?.course !== filters.course) return false;
      if (filters.batch && row.batch_id !== filters.batch) return false;
      if (filters.status && row.status !== filters.status) return false;
      if (term) {
        const haystack = [
          row.full_name, row.reg_no, row.user?.username, row.user?.email,
          row.user?.phone, row.secondary_phone, row.course_title, row.batch_name,
          ...(row.softwares || []),
        ].filter(Boolean).join(' ').toLowerCase();
        if (!haystack.includes(term)) return false;
      }
      return true;
    });
  }, [rows, filters]);

  // Summary counts reflect the current filters (branch/search/etc.), not just totals.
  const metrics = useMemo(() => [
    { label: 'Active Students', value: filteredRows.filter((r) => r.status === 'ACTIVE').length },
    { label: 'Branches', value: new Set(filteredRows.map((r) => r.branch_name).filter((b) => b && b !== '—')).size },
    { label: 'Recently Enrolled', value: filteredRows.filter((r) => withinDays(r.admission_date, 30)).length, note: 'Last 30 days', color: 'success.main' },
    { label: 'Cancelled Admissions', value: filteredRows.filter((r) => r.admission_status === 'CANCELLED').length },
  ], [filteredRows]);

  const filterBatches = useMemo(
    () => batches.filter((b) => {
      const branchSel = Array.isArray(filters.branch) ? filters.branch : (filters.branch ? [filters.branch] : []);
      return (!branchSel.length || branchSel.includes(b.branch)) && (!filters.course || b.course === filters.course);
    }),
    [batches, filters.branch, filters.course],
  );

  const pagedRows = useMemo(
    () => filteredRows.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage),
    [filteredRows, page, rowsPerPage],
  );

  useEffect(() => { setPage(0); }, [filters, selectedBranches.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleCreated = (data) => {
    const temp = data?.temporary_password;
    setToast({
      open: true,
      message: temp
        ? `Student created. Temporary password: ${temp}`
        : 'Student created successfully.',
      severity: 'success',
    });
    fetchData();
  };

  const clearFilters = () => setFilters({
    search: '',
    branch: isReceptionDesk ? [(user?.branch || '')].filter(Boolean) : [],
    course: '',
    batch: '',
    status: '',
  });

  const showToast = (message, severity = 'success') => setToast({ open: true, message, severity });

  // ---- Student cancellation & removal ------------------------------------
  const canCancelAdmission = (row) =>
    canManageAdmissions &&
    row.profile_id &&
    !row.is_enrolled &&
    row.admission_status !== 'CANCELLED';

  const canDeleteStudent = (row) =>
    canManageAdmissions && row.profile_id && row.deletion_eligible && row.admission_status === 'CANCELLED';

  const handleCancelAdmission = async () => {
    if (!cancelTarget) return;
    setActionBusy(true);
    try {
      await api.post(`/profiles/students/${encodeURIComponent(cancelTarget.profile_id)}/cancel-admission/`, {
        reason: cancelReason.trim() || undefined,
      });
      showToast(`Admission cancelled for ${cancelTarget.full_name}.`, 'success');
      setCancelTarget(null);
      setCancelReason('');
      fetchData();
    } catch (err) {
      showToast(extractError(err, 'Could not cancel admission.'), 'error');
    } finally {
      setActionBusy(false);
    }
  };

  const handleDeleteStudent = async () => {
    if (!deleteTarget) return;
    setActionBusy(true);
    try {
      await api.delete(`/profiles/students/${encodeURIComponent(deleteTarget.profile_id)}/`, {
        data: { confirm: true, reason: deleteReason.trim() || undefined },
      });
      showToast(`${deleteTarget.full_name} removed from the directory. History is retained for audit.`, 'success');
      setDeleteTarget(null);
      setDeleteReason('');
      fetchData();
    } catch (err) {
      showToast(extractError(err, 'Could not remove student.'), 'error');
    } finally {
      setActionBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Students Directory"
        subtitle="Search, filter and open complete student profiles across your branch."
      />
      <Stack direction="row" spacing={1.5} sx={{ mb: 2, flexWrap: 'wrap' }}>
        <Button variant="contained" startIcon={<PersonAdd />} onClick={() => setShowAdd(true)}>
          Add New Student
        </Button>
        <Button variant="outlined" startIcon={<Refresh />} onClick={fetchData} disabled={loading}>
          Refresh
        </Button>
      </Stack>

      {error && (
        <Card sx={{ mb: 2, p: 2, borderLeft: '4px solid', borderLeftColor: 'error.main' }}>
          <Typography color="error" variant="body2" sx={{ fontWeight: 700 }}>{error}</Typography>
          {errorDetail && <Typography color="error" variant="caption">{errorDetail}</Typography>}
          <Box sx={{ mt: 1 }}><Button size="small" variant="outlined" color="error" onClick={fetchData}>Retry</Button></Box>
        </Card>
      )}

      {!error && <MetricCards items={loading ? metrics.map((m) => ({ ...m, value: '—' })) : metrics} />}

      <Paper sx={{ p: 2, mb: 2, borderRadius: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              size="small"
              label="Search name, roll no, email or phone"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            />
          </Grid>
          <Grid item xs={6} sm={3} md={2}>
            <TextField
              select
              fullWidth
              size="small"
              label="Branch"
              value={selectedBranches}
              SelectProps={{
                multiple: isSuperAdmin,
                renderValue: (selected) => {
                  const sel = Array.isArray(selected) ? selected : [selected];
                  if (sel.length === 0) return 'All branches';
                  return sel.map((id) => branches.find((b) => b.id === id)?.name || id).join(', ');
                },
              }}
              onChange={(e) => {
                const value = e.target.value;
                const list = typeof value === 'string' ? value.split(',') : value;
                setFilters({ ...filters, branch: isSuperAdmin ? list : list.slice(0, 1) });
              }}
              disabled={isReceptionDesk}
              helperText={isReceptionDesk ? 'Assigned branch' : (isSuperAdmin ? 'All branches, or pick one/more' : 'Limited to your branch')}
            >
              {branches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={6} sm={3} md={2}>
            <TextField select fullWidth size="small" label="Course" value={filters.course} onChange={(e) => setFilters({ ...filters, course: e.target.value })}>
              <MenuItem value="">All</MenuItem>
              {courses.map((c) => <MenuItem key={c.id} value={c.id}>{c.title}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={6} sm={3} md={2}>
            <TextField select fullWidth size="small" label="Batch" value={filters.batch} onChange={(e) => setFilters({ ...filters, batch: e.target.value })}>
              <MenuItem value="">All</MenuItem>
              {filterBatches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={6} sm={3} md={2}>
            <TextField select fullWidth size="small" label="Status" value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <MenuItem value="">All</MenuItem>
              <MenuItem value="ACTIVE">Active</MenuItem>
              <MenuItem value="INACTIVE">Inactive</MenuItem>
            </TextField>
          </Grid>
        </Grid>
        {(filters.search || selectedBranches.length > (isReceptionDesk ? 1 : 0) || filters.course || filters.batch || filters.status) && (
          <Box sx={{ mt: 1 }}>
            <Button size="small" onClick={clearFilters}>Clear filters</Button>
          </Box>
        )}
      </Paper>

      <Card sx={{ borderRadius: 3, overflow: 'hidden' }}>
        <Box sx={{ p: 2.5, pb: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Student roster</Typography>
          <Typography variant="body2" color="text.secondary">{filteredRows.length} student(s)</Typography>
        </Box>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}><CircularProgress /></Box>
        ) : (
          <TableContainer sx={{ overflowX: 'auto' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>BRANCH</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>REG NO</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>STUDENT NAME</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>MOB.NO</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>COURSE</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>SOFTWARES</TableCell>
                  <TableCell sx={{ fontWeight: 700, display: { xs: 'none', sm: 'table-cell' } }}>Admission Date</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>{canManageAdmissions ? 'Actions' : 'View'}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredRows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} align="center">
                      <Typography color="text.secondary" sx={{ py: 4 }}>
                        {rows.length === 0 ? 'No students yet. Use “Add New Student” to enrol the first one.' : 'No students match the current filters.'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : pagedRows.map((row) => (
                  <TableRow
                    key={row.id}
                    hover
                    onClick={() => setSelectedRow(row)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>{row.branch_name}</Typography>
                    </TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{row.reg_no}</TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={1.5} alignItems="center">
                        <Avatar sx={{ width: 34, height: 34, bgcolor: 'primary.main', fontSize: 14 }}>
                          {(row.full_name || 'S').charAt(0)}
                        </Avatar>
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>{row.full_name}</Typography>
                          <Typography variant="caption" color="text.secondary">{row.user?.username}</Typography>
                        </Box>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{row.mobile || '—'}</Typography>
                      {row.secondary_phone && (
                        <Typography variant="caption" color="text.secondary" display="block">Alt: {row.secondary_phone}</Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{row.course_title}</Typography>
                      <Typography variant="caption" color="text.secondary">{row.batch_name}</Typography>
                    </TableCell>
                    <TableCell>
                      {row.softwares && row.softwares.length > 0 ? (
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ maxWidth: 220 }}>
                          {row.softwares.map((sw, idx) => (
                            <Chip key={idx} label={sw} size="small" sx={{ fontSize: '0.72rem', height: 20 }} />
                          ))}
                        </Stack>
                      ) : (
                        <Typography variant="caption" color="text.secondary">—</Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>{formatDate(row.admission_date)}</TableCell>
                    <TableCell>
                      <Stack spacing={0.5} alignItems="flex-start">
                        <Chip
                          size="small"
                          label={row.status === 'ACTIVE' ? 'Active' : 'Inactive'}
                          color={row.status === 'ACTIVE' ? 'success' : 'default'}
                        />
                        {row.admission_status === 'CANCELLED' && (
                          <Chip size="small" color="error" variant="outlined" label="Admission cancelled" />
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                        <Tooltip title="View profile">
                          <IconButton size="small" onClick={(e) => { e.stopPropagation(); setSelectedRow(row); }}>
                            <Visibility fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        {canManageAdmissions && canCancelAdmission(row) && (
                          <Tooltip title="Cancel admission">
                            <IconButton
                              size="small"
                              color="warning"
                              onClick={(e) => { e.stopPropagation(); setCancelTarget(row); setCancelReason(''); }}
                            >
                              <Block fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {canManageAdmissions && canDeleteStudent(row) && (
                          <Tooltip title="Remove cancelled-admission student">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={(e) => { e.stopPropagation(); setDeleteTarget(row); setDeleteReason(''); }}
                            >
                              <DeleteOutline fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        {!loading && filteredRows.length > 0 && (
          <TablePagination
            component="div"
            count={filteredRows.length}
            page={page}
            onPageChange={(_, p) => setPage(p)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
            rowsPerPageOptions={[10, 25, 50, 100]}
          />
        )}
      </Card>

      <AddStudentModal
        open={showAdd}
        onClose={() => setShowAdd(false)}
        onCreated={handleCreated}
        branches={branches}
        courses={courses}
        batches={batches}
        defaultBranchId={user?.branch || ''}
      />

      <StudentProfileDialog
        open={Boolean(selectedRow)}
        row={selectedRow}
        onClose={() => setSelectedRow(null)}
        onUpdated={fetchData}
      />

      {/* Cancel admission confirmation */}
      <Dialog open={Boolean(cancelTarget)} onClose={() => !actionBusy && setCancelTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 800 }}>Cancel admission?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Cancel admission for <strong>{cancelTarget?.full_name}</strong>? They will no longer count as
            active/enrolled. Records and history are retained. A cancelled-admission student with no live
            enrolment can then be removed from active views.
          </Typography>
          <TextField
            fullWidth
            multiline
            minRows={2}
            label="Cancellation reason (optional)"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelTarget(null)} disabled={actionBusy}>Keep student</Button>
          <Button variant="contained" color="warning" onClick={handleCancelAdmission} disabled={actionBusy}>
            {actionBusy ? 'Cancelling…' : 'Cancel admission'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete cancelled-admission student confirmation */}
      <Dialog open={Boolean(deleteTarget)} onClose={() => !actionBusy && setDeleteTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 800 }}>Remove student?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 1 }}>
            Remove <strong>{deleteTarget?.full_name}</strong> from active views? Only eligible cancelled-admission
            records can be removed. The student is not permanently erased - history, related records and the
            audit trail are retained.
          </Typography>
          {deleteTarget?.cancellation_reason && (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
              Cancellation reason: {deleteTarget.cancellation_reason}
            </Typography>
          )}
          <TextField
            fullWidth
            multiline
            minRows={2}
            label="Deletion reason (optional)"
            value={deleteReason}
            onChange={(e) => setDeleteReason(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)} disabled={actionBusy}>Keep student</Button>
          <Button variant="contained" color="error" onClick={handleDeleteStudent} disabled={actionBusy}>
            {actionBusy ? 'Removing…' : 'Remove student'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={toast.open}
        autoHideDuration={5000}
        onClose={() => setToast({ ...toast, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={() => setToast({ ...toast, open: false })} severity={toast.severity} sx={{ width: '100%' }}>
          {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};
