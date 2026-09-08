import React, { useState, useEffect, useCallback } from 'react';
import { SimplePage } from './PageLayout';
import { AddRecordModal } from '../components/modals/AddRecordModal';
import api, { unwrapList } from '../services/api';

export const StudentsPage = () => {
  const [students, setStudents] = useState([]);
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
      api.get('/accounts/users/', { params: { role: 'STUDENT' } }),
      api.get('/accounts/branches/').catch(() => ({ data: [] })),
      api.get('/accounts/roles/').catch(() => ({ data: [] })),
    ])
      .then(([studentRes, branchRes, roleRes]) => {
        setStudents(unwrapList(studentRes));
        setBranches(unwrapList(branchRes));
        setRoles(unwrapList(roleRes));
      })
      .catch((err) => {
        setStudents([]);
        setError(err?.detail || 'Could not load students.');
        setErrorDetail(err?.message || '');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const studentRole = roles.find((r) => r.code === 'STUDENT');

  const metrics = [
    { label: 'Active Students', value: students.length },
    {
      label: 'Unassigned Branch',
      value: students.filter((s) => !s.branch).length,
    },
    {
      label: 'Inactive Accounts',
      value: students.filter((s) => s.is_active === false).length,
    },
  ];

  const handleSubmit = async (data) => {
    await api.post('/accounts/users/', {
      ...data,
      role: studentRole?.id ?? data.role,
      password: data.password || 'Welcome@123',
    });
    setShowModal(false);
    fetchData();
  };

  const handleDelete = async (student) => {
    if (!window.confirm(`Soft-delete student "${student.full_name || student.username}"?`)) return;
    await api.delete(`/accounts/users/${student.id}/`);
    fetchData();
  };

  return (
    <>
      <SimplePage
        title="Students & Batches"
        subtitle="Manage student enrolments and their assigned batches."
        action="Add Student"
        onAction={() => setShowModal(true)}
        metrics={metrics}
        loading={loading}
        error={error}
        errorDetail={errorDetail}
        onRetry={fetchData}
        tableTitle="Student roster"
        columns={[
          { key: 'full_name', label: 'Student' },
          { key: 'username', label: 'Username' },
          { key: 'email', label: 'Email' },
          { key: 'branch_name', label: 'Branch' },
          {
            key: 'is_active',
            label: 'Status',
            chip: (value) => (value ? 'success' : 'default'),
          },
        ]}
        rows={students.map((s) => ({
          ...s,
          is_active: s.is_active ? 'Active' : 'Inactive',
        }))}
        onDelete={handleDelete}
        emptyMessage="No students yet. Use “Add Student” to enrol the first one."
      />
      <AddRecordModal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="Add Student"
        fields={[
          { name: 'username', label: 'Username', required: true },
          { name: 'first_name', label: 'First Name', required: true },
          { name: 'last_name', label: 'Last Name' },
          { name: 'email', label: 'Email', type: 'email', required: true },
          {
            name: 'branch',
            label: 'Branch',
            type: 'select',
            options: branches.map((b) => ({ value: b.id, label: b.name })),
          },
          { name: 'password', label: 'Initial Password', type: 'password' },
        ]}
        onSubmit={handleSubmit}
      />
    </>
  );
};
