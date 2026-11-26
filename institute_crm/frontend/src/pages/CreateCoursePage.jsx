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

// Accept free-text durations such as "6", "6 months" or "12 mo" and keep the
// numeric part the API expects. Returns null when no positive integer is present.
const parseMonths = (value) => {
  const match = String(value ?? '').match(/\d+/);
  if (!match) return null;
  const months = Number.parseInt(match[0], 10);
  return Number.isFinite(months) && months > 0 ? months : null;
};

export const CreateCoursePage = () => {
  const [form, setForm] = useState({ title: '', code: '', duration_months: '', total_fee: '', description: '', field_of_engineering: '' });
  const [notice, setNotice] = useState(null);
  const [saving, setSaving] = useState(false);

  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setNotice(null);

    const durationMonths = parseMonths(form.duration_months);
    if (durationMonths === null) {
      setNotice({ severity: 'error', text: 'Duration must include a whole number of months, e.g. 6 or 6 months.' });
      return;
    }
    const totalFee = Number(form.total_fee);
    if (!Number.isFinite(totalFee) || totalFee < 0) {
      setNotice({ severity: 'error', text: 'Course fee must be a valid non-negative amount.' });
      return;
    }

    setSaving(true);
    try {
      await api.post('/academics/courses/', {
        ...form,
        duration_months: durationMonths,
        total_fee: totalFee,
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

  return <Box><PageHeader title="Create Course" subtitle="Create a course that can be selected while creating a batch. Link it to its field of engineering." /><Card component="form" onSubmit={submit} sx={{ p: 3, maxWidth: 850 }}><Grid container spacing={2}><Grid item xs={12} md={6}><TextField required fullWidth label="Course name" value={form.title} onChange={update('title')} /></Grid><Grid item xs={12} md={6}><TextField required fullWidth label="Course code" placeholder="FSD-101" value={form.code} onChange={update('code')} /></Grid><Grid item xs={12} md={6}><TextField required fullWidth label="Duration" placeholder="e.g. 6 or 6 months" helperText="Enter the duration; the number of months is detected automatically." value={form.duration_months} onChange={update('duration_months')} /></Grid><Grid item xs={12} md={6}><TextField required fullWidth type="number" label="Course fee (₹)" value={form.total_fee} onChange={update('total_fee')} inputProps={{ min: 0 }} /></Grid><Grid item xs={12}><TextField select fullWidth label="Field of Engineering" value={form.field_of_engineering} onChange={update('field_of_engineering')} helperText="Each course is linked to its engineering discipline for filtering and reporting."><MenuItem value="">— No field (general) —</MenuItem>{FIELD_OPTIONS.map((opt) => <MenuItem key={opt} value={opt}>{opt}</MenuItem>)}</TextField></Grid><Grid item xs={12}><TextField fullWidth multiline minRows={3} label="Course description" value={form.description} onChange={update('description')} /></Grid></Grid>{notice && <Alert severity={notice.severity} sx={{ mt: 2 }}>{notice.text}</Alert>}<Button type="submit" variant="contained" sx={{ mt: 3 }} disabled={saving}>{saving ? 'Creating course...' : 'Create course'}</Button></Card></Box>;
};
