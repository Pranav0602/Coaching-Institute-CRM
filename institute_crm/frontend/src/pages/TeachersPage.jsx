import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert, Box, Button, CircularProgress, Dialog, DialogActions, DialogContent,
  DialogTitle, IconButton, MenuItem, Paper, Snackbar, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, TextField, Tooltip, Typography,
} from '@mui/material';
import { Add, DeleteOutline, PersonOff, Refresh } from '@mui/icons-material';
import api from '../services/api';

const STAFF_ROLES = ['TEACHER', 'ADMISSION_COUNSELOR', 'ACCOUNTANT', 'RECEPTIONIST'];
const roleLabel = (role) => role.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
const emptyForm = { first_name: '', last_name: '', username: '', email: '', phone: '', role: '', password: '' };
const responseData = (response) => response?.data ?? response;
const errorMessage = (error) => {
  const detail = error?.detail || error?.message;
  if (typeof detail === 'string') return detail;
  const firstField = Object.values(error || {})[0];
  return Array.isArray(firstField) ? firstField[0] : 'Unable to complete that request.';
};

export const TeachersPage = () => {
  const [staff, setStaff] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [addOpen, setAddOpen] = useState(false);
  const [removing, setRemoving] = useState(null);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });

  const loadStaff = async () => {
    setLoading(true);
    try {
      const [usersResponse, rolesResponse] = await Promise.all([
        api.get('/accounts/users/'), api.get('/accounts/roles/'),
      ]);
      const users = responseData(usersResponse);
      const allRoles = responseData(rolesResponse);
      setStaff((Array.isArray(users) ? users : users.results || []).filter((user) => STAFF_ROLES.includes(user.role_code)));
      setRoles((Array.isArray(allRoles) ? allRoles : allRoles.results || []).filter((role) => STAFF_ROLES.includes(role.code)));
    } catch (error) {
      setToast({ open: true, message: errorMessage(error), severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadStaff(); }, []);

  const teacherCount = useMemo(() => staff.filter((user) => user.role_code === 'TEACHER').length, [staff]);

  const updateForm = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));
  const closeAddDialog = () => { if (!saving) { setAddOpen(false); setForm(emptyForm); } };

  const addStaff = async () => {
    if (!form.first_name || !form.last_name || !form.username || !form.email || !form.role || !form.password) {
      setToast({ open: true, message: 'Complete all required fields before saving.', severity: 'warning' });
      return;
    }
    setSaving(true);
    try {
      const created = responseData(await api.post('/accounts/users/', form));
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

  return <Box>
    <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
      <Box><Typography variant="h4" sx={{ fontWeight: 800 }}>Teachers & Staff</Typography><Typography color="text.secondary">Add and manage staff accounts for your branch.</Typography></Box>
      <Stack direction="row" spacing={1}><Button variant="outlined" startIcon={<Refresh />} onClick={loadStaff} disabled={loading}>Refresh</Button><Button variant="contained" startIcon={<Add />} onClick={() => setAddOpen(true)}>Add staff member</Button></Stack>
    </Box>
    <Paper sx={{ overflow: 'hidden' }}>
      {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box> : staff.length === 0 ?
        <Box sx={{ textAlign: 'center', py: 7 }}><PersonOff sx={{ fontSize: 44, color: 'text.disabled' }} /><Typography variant="h6" sx={{ mt: 1 }}>No staff members yet</Typography><Typography color="text.secondary">Use “Add staff member” to create the first account.</Typography></Box> :
        <Table><TableHead><TableRow><TableCell sx={{ fontWeight: 700 }}>Name</TableCell><TableCell sx={{ fontWeight: 700 }}>Role</TableCell><TableCell sx={{ fontWeight: 700 }}>Email</TableCell><TableCell sx={{ fontWeight: 700 }}>Phone</TableCell><TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell></TableRow></TableHead><TableBody>
          {staff.map((user) => <TableRow hover key={user.id}><TableCell>{`${user.first_name} ${user.last_name}`.trim() || user.username}</TableCell><TableCell>{user.role_name || roleLabel(user.role_code)}</TableCell><TableCell>{user.email}</TableCell><TableCell>{user.phone || '—'}</TableCell><TableCell align="right"><Tooltip title="Delete staff member"><IconButton color="error" onClick={() => setRemoving(user)} aria-label={`Delete ${user.username}`}><DeleteOutline /></IconButton></Tooltip></TableCell></TableRow>)}
        </TableBody></Table>}
    </Paper>
    <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>{teacherCount} teacher{teacherCount === 1 ? '' : 's'} · {staff.length - teacherCount} support staff</Typography>

    <Dialog open={addOpen} onClose={closeAddDialog} maxWidth="sm" fullWidth><DialogTitle sx={{ fontWeight: 700 }}>Add staff member</DialogTitle><DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}><TextField required fullWidth label="First name" value={form.first_name} onChange={updateForm('first_name')} /><TextField required fullWidth label="Last name" value={form.last_name} onChange={updateForm('last_name')} /></Stack>
      <TextField required fullWidth label="Username" value={form.username} onChange={updateForm('username')} helperText="Used by this staff member to sign in." />
      <TextField required fullWidth type="email" label="Email" value={form.email} onChange={updateForm('email')} />
      <TextField fullWidth label="Phone" value={form.phone} onChange={updateForm('phone')} />
      <TextField required select fullWidth label="Role" value={form.role} onChange={updateForm('role')}>{roles.map((role) => <MenuItem key={role.id} value={role.id}>{role.name}</MenuItem>)}</TextField>
      <TextField required fullWidth type="password" label="Temporary password" value={form.password} onChange={updateForm('password')} helperText="At least 8 characters." />
    </Stack></DialogContent><DialogActions><Button onClick={closeAddDialog} disabled={saving}>Cancel</Button><Button variant="contained" onClick={addStaff} disabled={saving}>{saving ? 'Adding…' : 'Add staff'}</Button></DialogActions></Dialog>

    <Dialog open={Boolean(removing)} onClose={() => !saving && setRemoving(null)} maxWidth="xs" fullWidth><DialogTitle>Delete staff member?</DialogTitle><DialogContent><Typography>This will deactivate and remove {removing?.first_name || removing?.username} from this staff directory. Their historical records are retained.</Typography></DialogContent><DialogActions><Button onClick={() => setRemoving(null)} disabled={saving}>Cancel</Button><Button color="error" variant="contained" onClick={deleteStaff} disabled={saving}>{saving ? 'Deleting…' : 'Delete'}</Button></DialogActions></Dialog>
    <Snackbar open={toast.open} autoHideDuration={4500} onClose={() => setToast((current) => ({ ...current, open: false }))}><Alert severity={toast.severity} onClose={() => setToast((current) => ({ ...current, open: false }))}>{toast.message}</Alert></Snackbar>
  </Box>;
};
