import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Avatar, Box, Button, Card, Chip, CircularProgress, Grid, IconButton, MenuItem,
  Paper, Snackbar, Alert, Stack, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, TextField, Typography,
} from '@mui/material';
import { Visibility, Refresh, PersonAdd } from '@mui/icons-material';
import { useSearchParams } from 'react-router-dom';
import { PageHeader, MetricCards } from './PageLayout';
import { AddStudentModal } from '../components/students/AddStudentModal';
import { StudentProfileDialog } from '../components/students/StudentProfileDialog';
import api, { unwrapList } from '../services/api';
import { useAuth } from '../context/AuthContext';

const formatDate = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString(undefined, { dateStyle: 'medium' });
  } catch {
    return value;
  }
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

  const [filters, setFilters] = useState({ search: '', branch: '', course: '', batch: '', status: '' });

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    setErrorDetail('');
    Promise.all([
      api.get('/accounts/users/', { params: { role: 'STUDENT' } }),
      api.get('/profiles/students/').catch(() => ({ data: [] })),
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
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

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
        admission_date: student.date_joined,
        status: student.is_active === false ? 'INACTIVE' : 'ACTIVE',
      };
    });
  }, [students, profiles, batches]);

  const filteredRows = useMemo(() => {
    const term = filters.search.trim().toLowerCase();
    return rows.filter((row) => {
      if (filters.branch && row.branch_id !== filters.branch) return false;
      if (filters.course && row.course_id !== filters.course && row.profile?.course !== filters.course) return false;
      if (filters.batch && row.batch_id !== filters.batch) return false;
      if (filters.status && row.status !== filters.status) return false;
      if (term) {
        const haystack = [
          row.full_name, row.reg_no, row.user?.username, row.user?.email,
          row.user?.phone, row.course_title, row.batch_name,
        ].filter(Boolean).join(' ').toLowerCase();
        if (!haystack.includes(term)) return false;
      }
      return true;
    });
  }, [rows, filters]);

  const metrics = useMemo(() => [
    { label: 'Active Students', value: rows.filter((r) => r.status === 'ACTIVE').length },
    { label: 'Branches', value: new Set(rows.map((r) => r.branch_name).filter((b) => b && b !== '—')).size },
    { label: 'Recently Enrolled', value: rows.filter((r) => withinDays(r.admission_date, 30)).length, note: 'Last 30 days', color: 'success.main' },
    { label: 'Inactive Accounts', value: rows.filter((r) => r.status === 'INACTIVE').length },
  ], [rows]);

  const filterBatches = useMemo(
    () => batches.filter((b) => (!filters.branch || b.branch === filters.branch) && (!filters.course || b.course === filters.course)),
    [batches, filters.branch, filters.course],
  );

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

  const clearFilters = () => setFilters({ search: '', branch: '', course: '', batch: '', status: '' });

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
            <TextField select fullWidth size="small" label="Branch" value={filters.branch} onChange={(e) => setFilters({ ...filters, branch: e.target.value })}>
              <MenuItem value="">All</MenuItem>
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
        {(filters.search || filters.branch || filters.course || filters.batch || filters.status) && (
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
                  <TableCell sx={{ fontWeight: 700 }}>Student Name</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Roll / ID</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Course / Batch</TableCell>
                  <TableCell sx={{ fontWeight: 700, display: { xs: 'none', md: 'table-cell' } }}>Contact Info</TableCell>
                  <TableCell sx={{ fontWeight: 700, display: { xs: 'none', sm: 'table-cell' } }}>Admission Date</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>View</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredRows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography color="text.secondary" sx={{ py: 4 }}>
                        {rows.length === 0 ? 'No students yet. Use “Add New Student” to enrol the first one.' : 'No students match the current filters.'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : filteredRows.map((row) => (
                  <TableRow
                    key={row.id}
                    hover
                    onClick={() => setSelectedRow(row)}
                    sx={{ cursor: 'pointer' }}
                  >
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
                    <TableCell>{row.reg_no}</TableCell>
                    <TableCell>
                      <Typography variant="body2">{row.course_title}</Typography>
                      <Typography variant="caption" color="text.secondary">{row.batch_name}</Typography>
                    </TableCell>
                    <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>
                      <Typography variant="body2">{row.user?.phone || '—'}</Typography>
                      <Typography variant="caption" color="text.secondary">{row.user?.email || ''}</Typography>
                    </TableCell>
                    <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>{formatDate(row.admission_date)}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={row.status === 'ACTIVE' ? 'Active' : 'Inactive'}
                        color={row.status === 'ACTIVE' ? 'success' : 'default'}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={(e) => { e.stopPropagation(); setSelectedRow(row); }}>
                        <Visibility fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
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
