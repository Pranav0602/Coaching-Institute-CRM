import React, { useState, useEffect, useCallback } from 'react';
import { SimplePage } from './PageLayout';
import { AddRecordModal } from '../components/modals/AddRecordModal';
import api, { unwrapList } from '../services/api';

const FIELDS = [
  { name: 'code', label: 'Code', required: true },
  { name: 'name', label: 'Branch Name', required: true },
  { name: 'city', label: 'City' },
  { name: 'address', label: 'Address', type: 'textarea' },
  { name: 'phone', label: 'Phone' },
  { name: 'email', label: 'Email', type: 'email' },
];

export const BranchManagementPage = () => {
  const [branches, setBranches] = useState([]);
  const [stats, setStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState('');
  const [showModal, setShowModal] = useState(false);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    setErrorDetail('');
    Promise.all([
      api.get('/accounts/branches/'),
      api.get('/accounts/branches/statistics/').catch(() => ({ data: [] })),
    ])
      .then(([branchRes, statsRes]) => {
        setBranches(unwrapList(branchRes));
        setStats(unwrapList(statsRes));
      })
      .catch((err) => {
        setBranches([]);
        setStats([]);
        setError(err?.detail || 'Could not load branches.');
        setErrorDetail(err?.message || '');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const totalStudents = stats.reduce((sum, s) => sum + (s.student_count || 0), 0);

  const metrics = [
    { label: 'Active Branches', value: branches.length },
    { label: 'Total Students', value: totalStudents.toLocaleString() },
    { label: 'Total Teachers', value: stats.reduce((sum, s) => sum + (s.teacher_count || 0), 0) },
  ];

  const handleSubmit = async (data) => {
    await api.post('/accounts/branches/', data);
    setShowModal(false);
    fetchData();
  };

  const handleDelete = async (branch) => {
    if (!window.confirm(`Delete branch "${branch.name}"? This is a soft delete.`)) return;
    await api.delete(`/accounts/branches/${branch.id}/`);
    fetchData();
  };

  return (
    <>
      <SimplePage
        title="Branch Management"
        subtitle="Monitor and manage every institute branch."
        action="Add Branch"
        onAction={() => setShowModal(true)}
        metrics={metrics}
        loading={loading}
        error={error}
        errorDetail={errorDetail}
        onRetry={fetchData}
        tableTitle="Branch directory"
        columns={[
          { key: 'code', label: 'Code' },
          { key: 'name', label: 'Branch' },
          { key: 'city', label: 'Location' },
          { key: 'phone', label: 'Phone' },
          { key: 'email', label: 'Email' },
        ]}
        rows={branches}
        onDelete={handleDelete}
        emptyMessage="No branches yet. Use “Add Branch” to create the first one."
      />
      <AddRecordModal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="Add Branch"
        fields={FIELDS}
        onSubmit={handleSubmit}
      />
    </>
  );
};
