import React, { useState, useEffect, useCallback } from 'react';
import { SimplePage } from './PageLayout';
import { AddRecordModal } from '../components/modals/AddRecordModal';
import api, { unwrapList } from '../services/api';

const SOURCE_OPTIONS = ['WEBSITE', 'WALK_IN', 'REFERRAL', 'SOCIAL_MEDIA', 'CAMPAIGN'];

export const LeadManagementPage = () => {
  const [leads, setLeads] = useState([]);
  const [branches, setBranches] = useState([]);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState('');
  const [showModal, setShowModal] = useState(false);

  const fetchLeads = useCallback(() => {
    setLoading(true);
    setError(null);
    setErrorDetail('');
    Promise.all([
      api.get('/crm/leads/'),
      api.get('/accounts/branches/').catch(() => ({ data: [] })),
      api.get('/academics/courses/').catch(() => ({ data: [] })),
    ])
      .then(([leadRes, branchRes, courseRes]) => {
        setLeads(unwrapList(leadRes));
        setBranches(unwrapList(branchRes));
        setCourses(unwrapList(courseRes));
      })
      .catch((err) => {
        setLeads([]);
        setError(err?.detail || 'Could not load leads.');
        setErrorDetail(err?.message || '');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  const weekAgo = new Date();
  weekAgo.setDate(weekAgo.getDate() - 7);
  const newThisWeek = leads.filter(
    (l) => l.created_at && new Date(l.created_at) >= weekAgo
  ).length;
  const inFollowUp = leads.filter(
    (l) => !['ADMITTED', 'LOST'].includes(l.stage)
  ).length;
  const converted = leads.filter((l) => l.stage === 'ADMITTED').length;

  const metrics = [
    { label: 'New This Week', value: newThisWeek, color: 'success.main' },
    { label: 'In Follow-up', value: inFollowUp },
    { label: 'Converted', value: converted },
  ];

  const handleSubmit = async (data) => {
    await api.post('/crm/leads/', {
      ...data,
      target_course: data.target_course || 'General',
    });
    setShowModal(false);
    fetchLeads();
  };

  const handleDelete = async (lead) => {
    if (!window.confirm(`Delete lead "${lead.name}"?`)) return;
    await api.delete(`/crm/leads/${lead.id}/`);
    fetchLeads();
  };

  return (
    <>
      <SimplePage
        title="Lead Management CRM"
        subtitle="Track enquiries from first contact through admission."
        action="Add Lead"
        onAction={() => setShowModal(true)}
        metrics={metrics}
        loading={loading}
        error={error}
        errorDetail={errorDetail}
        onRetry={fetchLeads}
        tableTitle="Recent leads"
        columns={[
          { key: 'name', label: 'Lead' },
          { key: 'phone', label: 'Phone' },
          { key: 'target_course', label: 'Interested Course' },
          { key: 'lead_owner_name', label: 'Counselor' },
          { key: 'source', label: 'Source' },
          {
            key: 'stage',
            label: 'Stage',
            chip: (value) =>
              value === 'ADMITTED' ? 'success' : value === 'LOST' ? 'error' : 'warning',
          },
        ]}
        rows={leads}
        onDelete={handleDelete}
        emptyMessage="No leads yet. Use “Add Lead” to record the first enquiry."
      />
      <AddRecordModal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="Add Lead"
        fields={[
          { name: 'name', label: 'Full Name', required: true },
          { name: 'email', label: 'Email', type: 'email' },
          { name: 'phone', label: 'Phone', required: true },
          {
            name: 'branch',
            label: 'Branch',
            type: 'select',
            options: branches.map((b) => ({ value: b.id, label: b.name })),
          },
          {
            name: 'target_course',
            label: 'Target Course',
            type: 'select',
            options: courses.map((c) => ({ value: c.title, label: c.title })),
          },
          {
            name: 'source',
            label: 'Source',
            type: 'select',
            options: SOURCE_OPTIONS,
            default: 'WEBSITE',
          },
          {
            name: 'stage',
            label: 'Stage',
            type: 'select',
            options: ['NEW', 'CONTACTED', 'DEMO_SCHEDULED', 'ADMISSION_PENDING'],
            default: 'NEW',
          },
        ]}
        onSubmit={handleSubmit}
      />
    </>
  );
};
