import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, Card, Grid, MenuItem, TextField } from '@mui/material';
import { PageHeader } from './PageLayout';
import api from '../services/api';

export const CreateBatchPage = () => {
  const [courses, setCourses] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [form, setForm] = useState({ name: '', code: '', course: '', max_capacity: 30, start_date: '', end_date: '', teacher_ids: [] });
  const [notice, setNotice] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get('/academics/courses/')
      .then((response) => {
        const list = response.data?.results || response.data?.data || response.data || [];
        setCourses(Array.isArray(list) ? list : (list.results || []));
      })
      .catch(() => setNotice({ severity: 'error', text: 'Unable to load courses. Please refresh and try again.' }));
    api.get('/accounts/users/?role=TEACHER')
      .then((response) => {
        const d = response.data ?? response;
        const list = Array.isArray(d) ? d : (d.results || d.data || []);
        setTeachers(Array.isArray(list) ? list : []);
      })
      .catch(() => {});
  }, []);

  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    try {
      await api.post('/academics/batches/', { ...form, max_capacity: Number(form.max_capacity) });
      setNotice({ severity: 'success', text: 'Batch created successfully. It is now available to admission counsellors.' });
      setForm({ name: '', code: '', course: '', max_capacity: 30, start_date: '', end_date: '', teacher_ids: [] });
    } catch (error) {
      const fieldErrors = error?.errors || error;
      const message = Object.entries(fieldErrors || {})
        .filter(([, messages]) => Array.isArray(messages))
        .map(([field, messages]) => `${field.replace('_', ' ')}: ${messages.join(', ')}`)
        .join(' ');
      setNotice({ severity: 'error', text: message || error?.detail || 'Unable to create the batch. Please check the details and try again.' });
    } finally {
      setSaving(false);
    }
  };

  return <Box><PageHeader title="Create Batch" subtitle="Create a course batch for your branch. It will be available for admissions immediately." /><Card component="form" onSubmit={submit} sx={{ p: 3, maxWidth: 850 }}><Grid container spacing={2}><Grid item xs={12} md={6}><TextField required fullWidth label="Batch name" placeholder="Morning A1" value={form.name} onChange={update('name')} /></Grid><Grid item xs={12} md={6}><TextField required fullWidth label="Batch code" placeholder="FSD-A1-26" value={form.code} onChange={update('code')} /></Grid><Grid item xs={12} md={6}><TextField required select fullWidth label="Course" value={form.course} onChange={update('course')}><MenuItem value="" disabled>Select course</MenuItem>{courses.map((course) => <MenuItem key={course.id} value={course.id}>{course.title} ({course.code})</MenuItem>)}</TextField></Grid><Grid item xs={12} md={6}><TextField required fullWidth type="number" label="Maximum students" value={form.max_capacity} onChange={update('max_capacity')} inputProps={{ min: 1 }} /></Grid><Grid item xs={12} md={6}><TextField required fullWidth label="Start date" type="date" value={form.start_date} onChange={update('start_date')} InputLabelProps={{ shrink: true }} /></Grid><Grid item xs={12} md={6}><TextField required fullWidth label="End date" type="date" value={form.end_date} onChange={update('end_date')} InputLabelProps={{ shrink: true }} /></Grid><Grid item xs={12}><TextField select fullWidth SelectProps={{ multiple: true }} label="Assigned Teachers" value={form.teacher_ids} onChange={update('teacher_ids')} helperText="Multiple teachers can be assigned so co-teachers or substitutes can conduct lectures and mark attendance.">{teachers.map((t) => <MenuItem key={t.id} value={t.id}>{`${t.first_name} ${t.last_name}`.trim() || t.username} ({t.email})</MenuItem>)}</TextField></Grid></Grid>{notice && <Alert severity={notice.severity} sx={{ mt: 2 }}>{notice.text}</Alert>}<Button type="submit" variant="contained" sx={{ mt: 3 }} disabled={saving}>{saving ? 'Creating batch...' : 'Create batch'}</Button></Card></Box>;
};
