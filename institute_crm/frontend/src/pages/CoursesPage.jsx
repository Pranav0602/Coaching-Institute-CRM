import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Button, Card, Chip, Table, TableHead, TableBody, TableRow, TableCell, Typography,
} from '@mui/material';
import { Visibility } from '@mui/icons-material';
import { PageHeader, MetricCards } from './PageLayout';
import { AddRecordModal } from '../components/modals/AddRecordModal';
import { SyllabusViewerDrawer } from '../components/syllabus/SyllabusViewerDrawer';
import api, { unwrapList } from '../services/api';

export const CoursesPage = () => {
  const [courses, setCourses] = useState([]);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [syllabus, setSyllabus] = useState(null);
  const [syllabusLoading, setSyllabusLoading] = useState(false);

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

  const handleViewSyllabus = async (course) => {
    setSelectedCourse(course);
    setSyllabus(null);
    setDrawerOpen(true);
    setSyllabusLoading(true);
    try {
      const res = await api.get(`/academics/courses/${course.id}/syllabus/`);
      const data = res?.data ?? res;
      if (data && data.id) setSyllabus(data);
    } catch {
      setSyllabus(null);
    } finally {
      setSyllabusLoading(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Academic Courses"
        subtitle="Course catalogue, capacity, and current enrolments."
        action="Add Course"
        onAction={() => setShowModal(true)}
      />
      {!loading && !error && <MetricCards items={metrics} />}

      <Card sx={{ overflow: 'hidden' }}>
        <Box sx={{ p: 2.5, pb: 1.5 }}>
          <Typography variant="h6" fontWeight={700}>Course catalogue</Typography>
        </Box>
        <Box sx={{ overflowX: 'auto' }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Code</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Course</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Field of Engineering</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Duration</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Total Fee</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Syllabus</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {courses.map((c) => (
                <TableRow key={c.id} hover>
                  <TableCell>{c.code}</TableCell>
                  <TableCell><Typography variant="body2" fontWeight={600}>{c.title}</Typography></TableCell>
                  <TableCell>{c.field_of_engineering || '—'}</TableCell>
                  <TableCell>{c.duration_months ? `${c.duration_months} months` : '—'}</TableCell>
                  <TableCell>{c.total_fee !== null && c.total_fee !== undefined ? `Rs.${Number(c.total_fee).toLocaleString('en-IN')}` : '—'}</TableCell>
                  <TableCell>
                    <Button size="small" variant="outlined" startIcon={<Visibility />} onClick={() => handleViewSyllabus(c)}>
                      View Syllabus
                    </Button>
                  </TableCell>
                  <TableCell align="right">
                    <Button size="small" color="error" onClick={() => handleDelete(c)}>Delete</Button>
                  </TableCell>
                </TableRow>
              ))}
              {courses.length === 0 && !loading && (
                <TableRow><TableCell colSpan={7} align="center"><Typography color="text.secondary" sx={{ py: 3 }}>No courses yet. Use “Add Course” to create the first one.</Typography></TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </Box>
      </Card>

      {summary.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Enrolment summary: {liveBatches} live batches • {totalEnrolments} active enrolments • {summary.filter((s) => summaryFor(s.course_id || s.id)).length} courses tracked.
          </Typography>
        </Box>
      )}

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
      <SyllabusViewerDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        course={selectedCourse}
        syllabus={syllabus}
        loading={syllabusLoading}
      />
      {error && (
        <Box sx={{ mt: 2 }}>
          <Chip label={error} color="error" />
          {errorDetail && <Typography variant="caption" display="block">{errorDetail}</Typography>}
          <Button size="small" onClick={fetchCourses}>Retry</Button>
        </Box>
      )}
    </>
  );
};
