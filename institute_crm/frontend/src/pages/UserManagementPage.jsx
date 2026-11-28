import React, { useState, useEffect, useCallback } from 'react';
import { Button, Chip, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow, TextField, Typography, Box } from '@mui/material';
import { PageHeader, MetricCards } from './PageLayout';
import { AddRecordModal } from '../components/modals/AddRecordModal';
import api, { unwrapList } from '../services/api';
import { useAuth, ROLES } from '../context/AuthContext';

const emptyFilters = { name: '', email: '', reg_no: '', course: '', batch: '', branch: '' };

export const UserManagementPage = () => {
  const { user } = useAuth();
  const isSuperAdmin = user?.role_code === ROLES.SUPER_ADMIN;
  const [users, setUsers] = useState([]);
  const [branches, setBranches] = useState([]);
  const [roles, setRoles] = useState([]);
  const [courses, setCourses] = useState([]);
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState('');
  const [showModal, setShowModal] = useState(false);

  // Combined filters. `branch` kept as `branchFilter` name in params too.
  const [filters, setFilters] = useState(emptyFilters);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    setErrorDetail('');
    const params = {};
    if (filters.name.trim()) params.name = filters.name.trim();
    if (filters.email.trim()) params.email = filters.email.trim();
    if (filters.reg_no.trim()) params.reg_no = filters.reg_no.trim();
    if (filters.course) params.course_id = filters.course;
    if (filters.batch) params.batch_id = filters.batch;
    if (filters.branch) params.branch_id = filters.branch;
    Promise.all([
      api.get('/accounts/users/', { params }),
      api.get('/accounts/branches/').catch(() => ({ data: [] })),
      api.get('/accounts/roles/').catch(() => ({ data: [] })),
      api.get('/academics/courses/').catch(() => ({ data: [] })),
      api.get('/academics/batches/').catch(() => ({ data: [] })),
    ])
      .then(([userRes, branchRes, roleRes, courseRes, batchRes]) => {
        setUsers(unwrapList(userRes));
        setBranches(unwrapList(branchRes));
        setRoles(unwrapList(roleRes));
        setCourses(unwrapList(courseRes));
        setBatches(unwrapList(batchRes));
      })
      .catch((err) => {
        setUsers([]);
        setError(err?.detail || 'Could not load users.');
        setErrorDetail(err?.message || '');
      })
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { setPage(0); }, [filters]);

  const metrics = [
    { label: 'Total Users', value: users.length },
    { label: 'Active', value: users.filter((u) => u.is_active).length },
    { label: 'Inactive', value: users.filter((u) => u.is_active === false).length },
  ];

  const handleSubmit = async (data) => {
    await api.post('/accounts/users/', data);
    setShowModal(false);
    fetchData();
  };

  const handleDelete = async (user) => {
    if (!window.confirm(`Soft-delete user "${user.full_name || user.username}"?`)) return;
    await api.delete(`/accounts/users/${user.id}/`);
    fetchData();
  };

  const updateFilter = (field) => (e) => setFilters((c) => ({ ...c, [field]: e.target.value }));
  const clearFilters = () => setFilters(emptyFilters);
  const hasActiveFilters = Object.values(filters).some((v) => v);

  // Batches filtered to the chosen branch/course where applicable.
  const filterBatches = batches.filter((b) =>
    (!filters.branch || b.branch === filters.branch) && (!filters.course || b.course === filters.course));

  const pagedUsers = users.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  return (
    <Box>
      <PageHeader title="User Access & Roles" subtitle="Manage staff accounts and their system access." action="Add User" onAction={() => setShowModal(true)} />
      <MetricCards items={metrics} />

      {/* Filters (Super Admin; server re-applies scope). Combined. */}
      <Paper sx={{ p: 2, mb: 2, borderRadius: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} flexWrap="wrap" useFlexGap>
          <TextField size="small" label="Name" value={filters.name} onChange={updateFilter('name')} sx={{ minWidth: 160 }} />
          <TextField size="small" label="Email" value={filters.email} onChange={updateFilter('email')} sx={{ minWidth: 180 }} />
          <TextField size="small" label="Registration number" value={filters.reg_no} onChange={updateFilter('reg_no')} sx={{ minWidth: 180 }} />
          <TextField select size="small" label="Course" value={filters.course} onChange={updateFilter('course')} sx={{ minWidth: 160 }}>
            <MenuItem value="">All courses</MenuItem>
            {courses.map((c) => <MenuItem key={c.id} value={c.id}>{c.title}</MenuItem>)}
          </TextField>
          <TextField select size="small" label="Batch" value={filters.batch} onChange={updateFilter('batch')} sx={{ minWidth: 160 }}>
            <MenuItem value="">All batches</MenuItem>
            {filterBatches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}
          </TextField>
          <TextField select size="small" label="Branch" value={filters.branch} onChange={updateFilter('branch')} sx={{ minWidth: 160 }}>
            <MenuItem value="">All branches</MenuItem>
            {branches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}
          </TextField>
          <Button onClick={clearFilters} disabled={!hasActiveFilters}>Clear filters</Button>
        </Stack>
      </Paper>

      {error && <Paper sx={{ p: 2, mb: 2, borderLeft: '4px solid', borderLeftColor: 'error.main' }}><Typography color="error" variant="body2">{error}</Typography></Paper>}

      <Paper sx={{ borderRadius: 3, overflow: 'hidden' }}>
        <Box sx={{ p: 2 }}><Typography variant="h6" sx={{ fontWeight: 700 }}>User directory · {users.length} user{users.length === 1 ? '' : 's'}</Typography></Box>
        <TableContainer sx={{ overflowX: 'auto' }}>
          <Table size="small">
            <TableHead><TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Name</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Username</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Email</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Role</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Branch</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell>
            </TableRow></TableHead>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={7} align="center"><Typography color="text.secondary" sx={{ py: 3 }}>Loading…</Typography></TableCell></TableRow>
              ) : pagedUsers.length === 0 ? (
                <TableRow><TableCell colSpan={7} align="center"><Typography color="text.secondary" sx={{ py: 3 }}>No users match the current filters.</Typography></TableCell></TableRow>
              ) : pagedUsers.map((u) => (
                <TableRow hover key={u.id}>
                  <TableCell>{u.full_name || `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.username}</TableCell>
                  <TableCell>{u.username}</TableCell>
                  <TableCell>{u.email}</TableCell>
                  <TableCell>{u.role_name}</TableCell>
                  <TableCell>{u.branch_name || '—'}</TableCell>
                  <TableCell><Chip size="small" label={u.is_active ? 'Active' : 'Inactive'} color={u.is_active ? 'success' : 'default'} /></TableCell>
                  <TableCell align="right"><Button size="small" color="error" onClick={() => handleDelete(u)}>Delete</Button></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        {!loading && users.length > 0 && (
          <TablePagination
            component="div"
            count={users.length}
            page={page}
            onPageChange={(_, p) => setPage(p)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
            rowsPerPageOptions={[10, 25, 50, 100]}
          />
        )}
      </Paper>

      <AddRecordModal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="Add User"
        fields={[
          { name: 'username', label: 'Username', required: true },
          { name: 'email', label: 'Email', type: 'email', required: true },
          { name: 'first_name', label: 'First Name', required: true },
          { name: 'last_name', label: 'Last Name' },
          { name: 'role', label: 'Role', type: 'select', required: true, options: roles.map((r) => ({ value: r.id, label: r.name })) },
          { name: 'branch', label: 'Branch', type: 'select', options: branches.map((b) => ({ value: b.id, label: b.name })) },
          { name: 'password', label: 'Initial Password', type: 'password', required: true },
        ]}
        onSubmit={handleSubmit}
      />
    </Box>
  );
};
