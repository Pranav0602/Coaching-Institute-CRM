import React, { useState, useEffect, useCallback } from 'react';
import { Button, MenuItem, Paper, Stack, TextField } from '@mui/material';
import { SimplePage } from './PageLayout';
import { AddRecordModal } from '../components/modals/AddRecordModal';
import api, { unwrapList } from '../services/api';
import { useAuth, ROLES } from '../context/AuthContext';

export const UserManagementPage = () => {
  const { user } = useAuth();
  const isSuperAdmin = user?.role_code === ROLES.SUPER_ADMIN;
  const [users, setUsers] = useState([]);
  const [branches, setBranches] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [branchFilter, setBranchFilter] = useState('');

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    setErrorDetail('');
    const params = {};
    if (branchFilter) params.branch_id = branchFilter;
    Promise.all([
      api.get('/accounts/users/', { params }),
      api.get('/accounts/branches/').catch(() => ({ data: [] })),
      api.get('/accounts/roles/').catch(() => ({ data: [] })),
    ])
      .then(([userRes, branchRes, roleRes]) => {
        setUsers(unwrapList(userRes));
        setBranches(unwrapList(branchRes));
        setRoles(unwrapList(roleRes));
      })
      .catch((err) => {
        setUsers([]);
        setError(err?.detail || 'Could not load users.');
        setErrorDetail(err?.message || '');
      })
      .finally(() => setLoading(false));
  }, [branchFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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

  return (
    <>
      {isSuperAdmin && (
        <Paper sx={{ p: 2, mb: 2, borderRadius: 3 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center">
            <TextField select size="small" label="Filter by branch" value={branchFilter} onChange={(e) => setBranchFilter(e.target.value)} sx={{ minWidth: 240 }}>
              <MenuItem value="">All branches</MenuItem>
              {branches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}
            </TextField>
            <Button onClick={() => setBranchFilter('')}>Clear filters</Button>
          </Stack>
        </Paper>
      )}
      <SimplePage
        title="User Access & Roles"
        subtitle="Manage staff accounts and their system access."
        action="Add User"
        onAction={() => setShowModal(true)}
        metrics={metrics}
        loading={loading}
        error={error}
        errorDetail={errorDetail}
        onRetry={fetchData}
        tableTitle="User directory"
        columns={[
          { key: 'full_name', label: 'Name' },
          { key: 'username', label: 'Username' },
          { key: 'role_name', label: 'Role' },
          { key: 'branch_name', label: 'Branch' },
          {
            key: 'is_active',
            label: 'Status',
            chip: (value) => (value ? 'success' : 'default'),
          },
        ]}
        rows={users.map((u) => ({
          ...u,
          is_active: u.is_active ? 'Active' : 'Inactive',
        }))}
        onDelete={handleDelete}
        emptyMessage="No users yet. Use “Add User” to create the first account."
      />
      <AddRecordModal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="Add User"
        fields={[
          { name: 'username', label: 'Username', required: true },
          { name: 'email', label: 'Email', type: 'email', required: true },
          { name: 'first_name', label: 'First Name', required: true },
          { name: 'last_name', label: 'Last Name' },
          {
            name: 'role',
            label: 'Role',
            type: 'select',
            required: true,
            options: roles.map((r) => ({ value: r.id, label: r.name })),
          },
          {
            name: 'branch',
            label: 'Branch',
            type: 'select',
            options: branches.map((b) => ({ value: b.id, label: b.name })),
          },
          { name: 'password', label: 'Initial Password', type: 'password', required: true },
        ]}
        onSubmit={handleSubmit}
      />
    </>
  );
};
