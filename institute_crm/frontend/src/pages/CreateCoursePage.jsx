import React, { useState } from 'react';
import { Alert, Box, Button, Card, Grid, MenuItem, TextField } from '@mui/material';
import { PageHeader } from './PageLayout';
import api from '../services/api';

const FIELD_OPTIONS = [
  'Mechanical CAD/CAM/CAE',
  'Civil CAD',
  'Electrical CAD',
  'Design & BIM',
  'Data Science & AI/ML',
  'IT & Software Development',
  'Cloud Computing',
];

export const CreateCoursePage = () => {
  const [form, setForm] = useState({ title: '', code: '', duration_months: '', total_fee: '', description: '', field_of_engineering: '' });
  const [notice, setNotice] = useState(null);
  const [saving, setSaving] = useState(false);

  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    try {
      await api.post('/academics/courses/', {
        ...form,
        duration_months: Number(form.duration_months),
        total_fee: Number(form.total_fee),
        field_of_engineering: form.field_of_engineering || null,
      });
      setNotice({ severity: 'success', text: 'Course created successfully. It is now available when creating a batch.' });
      setForm({ title: '', code: '', duration_months: '', total_fee: '', description: '', field_of_engineering: '' });
    } catch (error) {
      const fieldErrors = error?.errors || error;
      const message = Object.entries(fieldErrors || {})
        .filter(([, messages]) => Array.isArray(messages))
        .map(([field, messages]) => `${field.replace('_', ' ')}: ${messages.join(', ')}`)
        .join(' ');
      setNotice({ severity: 'error', text: message || error?.detail || 'Unable to create the course. Please check the details and try again.' });
    } finally {
      setSaving(false);
    }
  };

  return <Box><PageHeader title="Create Course" subtitle="Create a course that can be selected while creating a batch. Link it to its field of engineering." /><Card component="form" onSubmit={submit} sx={{ p: 3, maxWidth: 850 }}><Grid container spacing={2}><Grid item xs={12} md={6}><TextField required fullWidth label="Course name" value={form.title} onChange={update('title')} /></Grid><Grid item xs={12} md={6}><TextField required fullWidth label="Course code" placeholder="FSD-101" value={form.code} onChange={update('code')} /></Grid><Grid item xs={12} md={6}><TextField required select fullWidth label="Duration" value={form.duration_months} onChange={update('duration_months')}><MenuItem value="" disabled>Select duration</MenuItem><MenuItem value={3}>3 months</MenuItem><MenuItem value={6}>6 months</MenuItem><MenuItem value={12}>12 months</MenuItem></TextField></Grid><Grid item xs={12} md={6}><TextField required fullWidth type="number" label="Course fee (₹)" value={form.total_fee} onChange={update('total_fee')} inputProps={{ min: 0 }} /></Grid><Grid item xs={12}><TextField select fullWidth label="Field of Engineering" value={form.field_of_engineering} onChange={update('field_of_engineering')} helperText="Each course is linked to its engineering discipline for filtering and reporting."><MenuItem value="">— No field (general) —</MenuItem>{FIELD_OPTIONS.map((opt) => <MenuItem key={opt} value={opt}>{opt}</MenuItem>)}</TextField></Grid><Grid item xs={12}><TextField fullWidth multiline minRows={3} label="Course description" value={form.description} onChange={update('description')} /></Grid></Grid>{notice && <Alert severity={notice.severity} sx={{ mt: 2 }}>{notice.text}</Alert>}<Button type="submit" variant="contained" sx={{ mt: 3 }} disabled={saving}>{saving ? 'Creating course...' : 'Create course'}</Button></Card></Box>;
};
