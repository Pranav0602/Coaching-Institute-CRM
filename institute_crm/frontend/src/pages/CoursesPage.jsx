import React, { useState, useEffect, useCallback } from 'react';
import { SimplePage } from './PageLayout';
import { AddRecordModal } from '../components/modals/AddRecordModal';
import api, { unwrapList } from '../services/api';

export const CoursesPage = () => {
  const [courses, setCourses] = useState([]);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState('');
  const [showModal, setShowModal] = useState(false);

  const fetchCourses = useCallback(() => {
    setLoading(true);
    setError(null);
    setErrorDetail('');
    Promise.all([
      api.get('/academics/courses/'),
      api.get('/academics/courses/summary/').catch(() => ({ data: [] })),
    ])
      .then(([courseRes, summaryRes]) => {
        setCourses(unwrapList(courseRes));
        setSummary(unwrapList(summaryRes));
      })
      .catch((err) => {
        setCourses([]);
        setSummary([]);
        setError(err?.detail || 'Could not load courses.');
        setErrorDetail(err?.message || err?.errors?.detail || '');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchCourses();
  }, [fetchCourses]);

  // summary rows are keyed by course and carry batch/enrolment counts
  const summaryFor = (courseId) =>
    summary.find((s) => s.course_id === courseId || s.id === courseId) || {};

  const activeCourses = courses.length;
  const liveBatches = summary.reduce((sum, s) => sum + (s.batch_count ?? s.batches ?? 0), 0);
  const totalEnrolments = summary.reduce(
    (sum, s) => sum + (s.enrolment_count ?? s.enrolments ?? 0),
    0
  );

  const metrics = [
    { label: 'Active Courses', value: activeCourses },
    { label: 'Live Batches', value: liveBatches },
    { label: 'Total Enrolments', value: totalEnrolments },
  ];

  const handleSubmit = async (data) => {
    await api.post('/academics/courses/', {
      ...data,
      duration_months: data.duration_months ? Number(data.duration_months) : undefined,
      total_fee: data.total_fee ? Number(data.total_fee) : undefined,
    });
    setShowModal(false);
    fetchCourses();
  };

  const handleDelete = async (course) => {
    if (!window.confirm(`Delete course "${course.title}"? This is a soft delete.`)) return;
    await api.delete(`/academics/courses/${course.id}/`);
    fetchCourses();
  };

  return (
    <>
      <SimplePage
        title="Academic Courses"
        subtitle="Course catalogue, capacity, and current enrolments."
        action="Add Course"
        onAction={() => setShowModal(true)}
        metrics={metrics}
        loading={loading}
        error={error}
        errorDetail={errorDetail}
        onRetry={fetchCourses}
        tableTitle="Course catalogue"
        columns={[
          { key: 'code', label: 'Code' },
          { key: 'title', label: 'Course' },
          { key: 'field_of_engineering', label: 'Field of Engineering' },
          { key: 'duration_months', label: 'Duration' },
          { key: 'total_fee', label: 'Total Fee' },
        ]}
        rows={courses.map((c) => ({
          ...c,
          field_of_engineering: c.field_of_engineering || '—',
          duration_months: c.duration_months ? `${c.duration_months} months` : '—',
          total_fee:
            c.total_fee !== null && c.total_fee !== undefined
              ? `₹${Number(c.total_fee).toLocaleString()}`
              : '—',
        }))}
        onDelete={handleDelete}
        emptyMessage="No courses yet. Use “Add Course” to create the first one."
      />
      <AddRecordModal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="Add Course"
        fields={[
          { name: 'code', label: 'Code', required: true },
          { name: 'title', label: 'Title', required: true },
          { name: 'description', label: 'Description', type: 'textarea' },
          { name: 'duration_months', label: 'Duration (months)', type: 'number', required: true },
          { name: 'total_fee', label: 'Total Fee (₹)', type: 'number', required: true },
          {
            name: 'field_of_engineering',
            label: 'Field of Engineering',
            type: 'select',
            required: false,
            options: [
              { value: 'Mechanical CAD/CAM/CAE', label: 'Mechanical CAD/CAM/CAE' },
              { value: 'Civil CAD', label: 'Civil CAD' },
              { value: 'Electrical CAD', label: 'Electrical CAD' },
              { value: 'Design & BIM', label: 'Design & BIM' },
              { value: 'Data Science & AI/ML', label: 'Data Science & AI/ML' },
              { value: 'IT & Software Development', label: 'IT & Software Development' },
              { value: 'Cloud Computing', label: 'Cloud Computing' },
            ],
          },
        ]}
        onSubmit={handleSubmit}
      />
    </>
  );
};
