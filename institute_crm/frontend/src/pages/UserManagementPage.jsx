import React, { useState, useEffect, useCallback } from 'react';
import { SimplePage } from './PageLayout';
import { AddRecordModal } from '../components/modals/AddRecordModal';
import api, { unwrapList } from '../services/api';

export const UserManagementPage = () => {
  const [users, setUsers] = useState([]);
  const [branches, setBranches] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState('');
  const [showModal, setShowModal] = useState(false);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    setErrorDetail('');
    Promise.all([
      api.get('/accounts/users/'),
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
  }, []);

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
      <SimplePage
        title="User Access & Roles"
        subtitle="Manage staff accounts and their system access."
        action="Invite User"
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
        emptyMessage="No users yet. Use “Invite User” to create the first account."
      />
      <AddRecordModal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="Invite User"
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
