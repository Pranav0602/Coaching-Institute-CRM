import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert, Box, Button, CircularProgress, Dialog, DialogActions, DialogContent,
  DialogTitle, IconButton, MenuItem, Paper, Snackbar, Stack, Table, TableBody,
  TableCell, TableHead, TablePagination, TableRow, TextField, Tooltip, Typography,
} from '@mui/material';
import { Add, DeleteOutline, PersonOff, Refresh } from '@mui/icons-material';
import api from '../services/api';
import { unwrapList } from '../services/api';
import { useAuth, ROLES } from '../context/AuthContext';
import { TeacherAssignmentsPanel } from '../components/teachers/TeacherAssignmentsPanel';

const STAFF_ROLES = ['TEACHER', 'ADMISSION_COUNSELOR', 'ACCOUNTANT', 'RECEPTIONIST'];
const roleLabel = (role) => role.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
const emptyForm = { first_name: '', last_name: '', username: '', email: '', phone: '', role: '', password: '', branch: '' };
const responseData = (response) => response?.data ?? response;
const errorMessage = (error) => {
  const data = error?.response?.data ?? error ?? {};
  if (typeof data?.message === 'string' && data.message) return data.message;
  const detail = data?.detail || data?.message;
  if (typeof detail === 'string') return detail;
  const firstField = Object.values(data || {})[0];
  return Array.isArray(firstField) ? firstField[0] : 'Unable to complete that request.';
};

export const TeachersPage = () => {
  const { user } = useAuth();
  const isSuperAdmin = user?.role_code === ROLES.SUPER_ADMIN;
  const canManage = [ROLES.SUPER_ADMIN, ROLES.BRANCH_ADMIN].includes(user?.role_code);

  const [staff, setStaff] = useState([]);
  const [roles, setRoles] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [addOpen, setAddOpen] = useState(false);
  const [removing, setRemoving] = useState(null);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  // Staff filters. Branch is a list (multi for Super Admin); server scopes the rest.
  const [filters, setFilters] = useState({ search: '', branch: [] });

  const selectedBranches = Array.isArray(filters.branch) ? filters.branch : (filters.branch ? [filters.branch] : []);

  const loadStaff = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (selectedBranches.length === 1) params.branch_id = selectedBranches[0];
      else if (selectedBranches.length > 1) params.branch_ids = selectedBranches;
      const [usersResponse, rolesResponse, branchesResponse] = await Promise.all([
        api.get('/accounts/users/', { params }),
        api.get('/accounts/roles/'),
        api.get('/accounts/branches/').catch(() => ({ data: [] })),
      ]);
      const users = responseData(usersResponse);
      const allRoles = responseData(rolesResponse);
      setStaff((Array.isArray(users) ? users : users.results || []).filter((u) => STAFF_ROLES.includes(u.role_code)));
      setRoles((Array.isArray(allRoles) ? allRoles : allRoles.results || []).filter((role) => STAFF_ROLES.includes(role.code)));
      setBranches(unwrapList(branchesResponse));
    } catch (error) {
      setToast({ open: true, message: errorMessage(error), severity: 'error' });
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBranches.join(',')]);

  useEffect(() => { loadStaff(); }, [loadStaff]);

  const filteredStaff = useMemo(() => {
    const term = filters.search.trim().toLowerCase();
    const branchSel = selectedBranches;
    return staff.filter((u) => {
      if (branchSel.length && !branchSel.includes(u.branch)) return false;
      if (!term) return true;
      const haystack = [u.first_name, u.last_name, u.username, u.email, u.phone, u.role_name, u.branch_name].filter(Boolean).join(' ').toLowerCase();
      return haystack.includes(term);
    });
  }, [staff, filters.search, selectedBranches.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  const teacherCount = useMemo(() => filteredStaff.filter((u) => u.role_code === 'TEACHER').length, [filteredStaff]);
  const pagedStaff = useMemo(() => filteredStaff.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage), [filteredStaff, page, rowsPerPage]);
  useEffect(() => { setPage(0); }, [filters.search, selectedBranches.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  const updateForm = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));
  const closeAddDialog = () => { if (!saving) { setAddOpen(false); setForm(emptyForm); } };

  const addStaff = async () => {
    if (!form.first_name || !form.last_name || !form.username || !form.email || !form.role || !form.password) {
      setToast({ open: true, message: 'Complete all required fields before saving.', severity: 'warning' });
      return;
    }
    setSaving(true);
    try {
      const payload = { ...form };
      if (!payload.branch) delete payload.branch;
      const created = responseData(await api.post('/accounts/users/', payload));
      setStaff((current) => [...current, created]);
      setToast({ open: true, message: 'Staff member added.', severity: 'success' });
      setForm(emptyForm);
      setAddOpen(false);
    } catch (error) {
      setToast({ open: true, message: errorMessage(error), severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const deleteStaff = async () => {
    if (!removing) return;
    setSaving(true);
    try {
      await api.delete(`/accounts/users/${removing.id}/`);
      setStaff((current) => current.filter((user) => user.id !== removing.id));
      setToast({ open: true, message: 'Staff member removed.', severity: 'success' });
      setRemoving(null);
    } catch (error) {
      setToast({ open: true, message: errorMessage(error), severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const clearFilters = () => setFilters({ search: '', branch: [] });

  return <Box>
    <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
      <Box><Typography variant="h4" sx={{ fontWeight: 800 }}>Teachers & Staff</Typography><Typography color="text.secondary">Add and manage staff accounts{isSuperAdmin ? ' across branches' : ' for your branch'}.</Typography></Box>
      <Stack direction="row" spacing={1}><Button variant="outlined" startIcon={<Refresh />} onClick={loadStaff} disabled={loading}>Refresh</Button><Button variant="contained" startIcon={<Add />} onClick={() => setAddOpen(true)}>Add staff member</Button></Stack>
    </Box>

    {/* Staff filters */}
    <Paper sx={{ p: 2, mb: 2, borderRadius: 3 }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <TextField fullWidth size="small" label="Search name, email, role or branch" value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })} />
        <TextField
          select
          size="small"
          label="Branch"
          value={selectedBranches}
          SelectProps={{
            multiple: isSuperAdmin,
            renderValue: (selected) => {
              const sel = Array.isArray(selected) ? selected : [selected];
              if (!sel.length) return 'All branches';
              return sel.map((id) => branches.find((b) => b.id === id)?.name || id).join(', ');
            },
          }}
          onChange={(e) => {
            const value = e.target.value;
            const list = typeof value === 'string' ? value.split(',') : value;
            setFilters({ ...filters, branch: isSuperAdmin ? list : list.slice(0, 1) });
          }}
          sx={{ minWidth: 240 }}
        >
          {branches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}
        </TextField>
        <Button onClick={clearFilters}>Clear filters</Button>
      </Stack>
    </Paper>

    <Paper sx={{ overflow: 'hidden' }}>
      {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box> : filteredStaff.length === 0 ?
        <Box sx={{ textAlign: 'center', py: 7 }}><PersonOff sx={{ fontSize: 44, color: 'text.disabled' }} /><Typography variant="h6" sx={{ mt: 1 }}>No staff members found</Typography><Typography color="text.secondary">Adjust filters or use “Add staff member”.</Typography></Box> :
        <Table><TableHead><TableRow><TableCell sx={{ fontWeight: 700 }}>Name</TableCell><TableCell sx={{ fontWeight: 700 }}>Role</TableCell><TableCell sx={{ fontWeight: 700 }}>Branch</TableCell><TableCell sx={{ fontWeight: 700 }}>Email</TableCell><TableCell sx={{ fontWeight: 700 }}>Phone</TableCell><TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell></TableRow></TableHead><TableBody>
          {pagedStaff.map((user) => <TableRow hover key={user.id}><TableCell>{`${user.first_name} ${user.last_name}`.trim() || user.username}</TableCell><TableCell>{user.role_name || roleLabel(user.role_code)}</TableCell><TableCell>{user.branch_name || '—'}</TableCell><TableCell>{user.email}</TableCell><TableCell>{user.phone || '—'}</TableCell><TableCell align="right">{canManage && <Tooltip title="Delete staff member"><IconButton color="error" onClick={() => setRemoving(user)} aria-label={`Delete ${user.username}`}><DeleteOutline /></IconButton></Tooltip>}</TableCell></TableRow>)}
        </TableBody></Table>}
      {!loading && filteredStaff.length > 0 && (
        <TablePagination
          component="div"
          count={filteredStaff.length}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      )}
    </Paper>
    <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>{teacherCount} teacher{teacherCount === 1 ? '' : 's'} · {filteredStaff.length - teacherCount} support staff{filteredStaff.length !== staff.length ? ` · ${filteredStaff.length} of ${staff.length} shown` : ''}</Typography>

    {/* Teacher assignment flow */}
    {canManage && <Box sx={{ mt: 3 }}><TeacherAssignmentsPanel /></Box>}

    <Dialog open={addOpen} onClose={closeAddDialog} maxWidth="sm" fullWidth><DialogTitle sx={{ fontWeight: 700 }}>Add staff member</DialogTitle><DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}><TextField required fullWidth label="First name" value={form.first_name} onChange={updateForm('first_name')} /><TextField required fullWidth label="Last name" value={form.last_name} onChange={updateForm('last_name')} /></Stack>
      <TextField required fullWidth label="Username" value={form.username} onChange={updateForm('username')} helperText="Used by this staff member to sign in." />
      <TextField required fullWidth type="email" label="Email" value={form.email} onChange={updateForm('email')} />
      <TextField fullWidth label="Phone" value={form.phone} onChange={updateForm('phone')} />
      <TextField required select fullWidth label="Role" value={form.role} onChange={updateForm('role')}>{roles.map((role) => <MenuItem key={role.id} value={role.id}>{role.name}</MenuItem>)}</TextField>
      {isSuperAdmin && <TextField select fullWidth label="Branch" value={form.branch} onChange={updateForm('branch')}><MenuItem value="">No branch</MenuItem>{branches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}</TextField>}
      <TextField required fullWidth type="password" label="Temporary password" value={form.password} onChange={updateForm('password')} helperText="At least 8 characters." />
    </Stack></DialogContent><DialogActions><Button onClick={closeAddDialog} disabled={saving}>Cancel</Button><Button variant="contained" onClick={addStaff} disabled={saving}>{saving ? 'Adding…' : 'Add staff'}</Button></DialogActions></Dialog>

    <Dialog open={Boolean(removing)} onClose={() => !saving && setRemoving(null)} maxWidth="xs" fullWidth><DialogTitle>Delete staff member?</DialogTitle><DialogContent><Typography>This will deactivate and remove {removing?.first_name || removing?.username} from this staff directory. Their historical records are retained.</Typography></DialogContent><DialogActions><Button onClick={() => setRemoving(null)} disabled={saving}>Cancel</Button><Button color="error" variant="contained" onClick={deleteStaff} disabled={saving}>{saving ? 'Deleting…' : 'Delete'}</Button></DialogActions></Dialog>
    <Snackbar open={toast.open} autoHideDuration={4500} onClose={() => setToast((current) => ({ ...current, open: false }))}><Alert severity={toast.severity} onClose={() => setToast((current) => ({ ...current, open: false }))}>{toast.message}</Alert></Snackbar>
  </Box>;
};
