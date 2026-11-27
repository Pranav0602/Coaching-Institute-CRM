import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert, Button, CircularProgress, Dialog, DialogActions, DialogContent,
  DialogTitle, Grid, MenuItem, Stack, TextField, Typography,
} from '@mui/material';
import api from '../../services/api';
import { useAuth, ROLES } from '../../context/AuthContext';

const EMPTY_FORM = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  secondary_phone: '',
  softwares: '',
  dob: '',
  gender: 'MALE',
  branch: '',
  course: '',
  batch: '',
  reg_no: '',
  guardian_name: '',
  guardian_phone: '',
  guardian_relationship: '',
  agreed_fee: '',
  discount_amount: '',
  concession_amount: '',
  scholarship_amount: '',
  fee_notes: '',
  username: '',
  password: 'Welcome@123',
};

const errorMessage = (err) => {
  if (!err) return 'Could not add the student. Please try again.';
  if (typeof err === 'string') return err;
  if (err.detail) return err.detail;
  if (err.message) return err.message;
  const errors = err.errors || err;
  if (errors && typeof errors === 'object') {
    const first = Object.entries(errors).find(([, value]) => value);
    if (first) {
      const [field, value] = first;
      const text = Array.isArray(value) ? value[0] : value;
      return `${field.replace(/_/g, ' ')}: ${text}`;
    }
  }
  return 'Could not add the student. Please check the details and try again.';
};

export const AddStudentModal = ({
  open, onClose, onCreated, branches = [], courses = [], batches = [], defaultBranchId = '',
}) => {
  const { user } = useAuth();
  const isReceptionDesk = [ROLES.RECEPTIONIST, ROLES.ADMISSION_COUNSELOR].includes(user?.role_code);
  const lockedBranchId = isReceptionDesk ? (user?.branch || defaultBranchId || '') : (defaultBranchId || '');
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setForm({ ...EMPTY_FORM, branch: lockedBranchId });
      setError(null);
      setSubmitting(false);
    }
  }, [open, lockedBranchId]);

  const setField = (name) => (event) => {
    setForm((prev) => ({ ...prev, [name]: event.target.value }));
  };

  const effectiveBranch = isReceptionDesk ? lockedBranchId : form.branch;
  const availableCourses = useMemo(() => courses, [courses]);
  const availableBatches = useMemo(
    () => batches.filter((b) => {
      if (effectiveBranch && b.branch && b.branch !== effectiveBranch) return false;
      if (form.course) return b.course === form.course;
      return true;
    }),
    [batches, effectiveBranch, form.course],
  );

  const handleSubmit = async () => {
    if (!form.first_name.trim()) {
      setError('First name is required.');
      return;
    }
    if (!form.email.trim()) {
      setError('Email is required.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = Object.fromEntries(
        Object.entries({ ...form, branch: effectiveBranch || form.branch }).filter(([, value]) => value !== '' && value !== null && value !== undefined),
      );
      if (typeof payload.softwares === 'string') {
        payload.softwares = payload.softwares
          .split(/[,+]/)
          .map((item) => item.trim())
          .filter(Boolean);
      }
      const res = await api.post('/accounts/users/create-student/', payload);
      const data = res?.data ?? res;
      onCreated?.(data);
      onClose?.();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ fontWeight: 800 }}>Add New Student</DialogTitle>
      <DialogContent dividers>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 700 }}>
          Basic details
        </Typography>
        <Grid container spacing={2} sx={{ mt: 0.5, mb: 2 }}>
          <Grid item xs={12} sm={6}><TextField label="First Name" fullWidth required value={form.first_name} onChange={setField('first_name')} /></Grid>
          <Grid item xs={12} sm={6}><TextField label="Last Name" fullWidth value={form.last_name} onChange={setField('last_name')} /></Grid>
          <Grid item xs={12} sm={6}><TextField label="Email" type="email" fullWidth required value={form.email} onChange={setField('email')} /></Grid>
          <Grid item xs={12} sm={6}><TextField label="Phone Number" fullWidth value={form.phone} onChange={setField('phone')} /></Grid>
          <Grid item xs={12} sm={6}><TextField label="Alternate Mobile Number" fullWidth value={form.secondary_phone} onChange={setField('secondary_phone')} /></Grid>
          <Grid item xs={12} sm={6}>
            <TextField label="Date of Birth" type="date" fullWidth InputLabelProps={{ shrink: true }} value={form.dob} onChange={setField('dob')} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField select label="Gender" fullWidth value={form.gender} onChange={setField('gender')}>
              <MenuItem value="MALE">Male</MenuItem>
              <MenuItem value="FEMALE">Female</MenuItem>
              <MenuItem value="OTHER">Other</MenuItem>
            </TextField>
          </Grid>
        </Grid>

        <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 700 }}>
          Academic &amp; enrollment
        </Typography>
        <Grid container spacing={2} sx={{ mt: 0.5, mb: 2 }}>
          <Grid item xs={12} sm={6}>
            <TextField
              select
              label="Enrolled Branch"
              fullWidth
              value={effectiveBranch}
              onChange={setField('branch')}
              disabled={isReceptionDesk}
              helperText={isReceptionDesk ? 'Assigned to your branch' : undefined}
            >
              {!isReceptionDesk && <MenuItem value="">— Select branch —</MenuItem>}
              {branches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name} ({b.code})</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              select
              label="Target Course"
              fullWidth
              value={form.course}
              onChange={(e) => setForm((prev) => ({ ...prev, course: e.target.value, batch: '' }))}
            >
              <MenuItem value="">— Assign later —</MenuItem>
              {availableCourses.map((c) => <MenuItem key={c.id} value={c.id}>{c.title} ({c.code})</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              select
              label="Batch Assignment"
              fullWidth
              value={form.batch}
              onChange={setField('batch')}
              helperText={form.course ? 'Optional — assign the cohort now or later.' : 'Choose a course first to narrow batches.'}
            >
              <MenuItem value="">— Assign later —</MenuItem>
              {availableBatches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name} ({b.code})</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label="REG NO" fullWidth value={form.reg_no} onChange={setField('reg_no')} helperText="Leave blank to auto-generate." />
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="Softwares"
              fullWidth
              value={form.softwares}
              onChange={setField('softwares')}
              helperText="Software(s) for this course enrolment, separated by commas or + (e.g. AutoCAD, SolidWorks)."
            />
          </Grid>
        </Grid>

        <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 700 }}>
          Parent / guardian
        </Typography>
        <Grid container spacing={2} sx={{ mt: 0.5, mb: 2 }}>
          <Grid item xs={12} sm={4}><TextField label="Guardian Name" fullWidth value={form.guardian_name} onChange={setField('guardian_name')} /></Grid>
          <Grid item xs={12} sm={4}><TextField label="Guardian Contact" fullWidth value={form.guardian_phone} onChange={setField('guardian_phone')} /></Grid>
          <Grid item xs={12} sm={4}>
            <TextField select label="Relationship" fullWidth value={form.guardian_relationship} onChange={setField('guardian_relationship')}>
              <MenuItem value="">—</MenuItem>
              <MenuItem value="FATHER">Father</MenuItem>
              <MenuItem value="MOTHER">Mother</MenuItem>
              <MenuItem value="GUARDIAN">Guardian</MenuItem>
              <MenuItem value="OTHER">Other</MenuItem>
            </TextField>
          </Grid>
        </Grid>

        <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 700 }}>
          Fee terms (INR)
        </Typography>
        <Grid container spacing={2} sx={{ mt: 0.5, mb: 2 }}>
          <Grid item xs={12} sm={6}>
            <TextField label="Agreed Fee (₹)" type="number" fullWidth value={form.agreed_fee} onChange={setField('agreed_fee')} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label="Discount Amount (₹)" type="number" fullWidth value={form.discount_amount} onChange={setField('discount_amount')} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label="Concession Amount (₹)" type="number" fullWidth value={form.concession_amount} onChange={setField('concession_amount')} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label="Scholarship Amount (₹)" type="number" fullWidth value={form.scholarship_amount} onChange={setField('scholarship_amount')} />
          </Grid>
          <Grid item xs={12}>
            <TextField label="Fee Notes / Conditions" fullWidth value={form.fee_notes} onChange={setField('fee_notes')} helperText="Optional rationale for custom fees or payment conditions." />
          </Grid>
        </Grid>

        <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 700 }}>
          Initial system access
        </Typography>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={12} sm={6}><TextField label="Username" fullWidth value={form.username} onChange={setField('username')} helperText="Leave blank to auto-generate." /></Grid>
          <Grid item xs={12} sm={6}><TextField label="Temporary Password" fullWidth value={form.password} onChange={setField('password')} /></Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={submitting}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting} startIcon={submitting ? <CircularProgress size={16} color="inherit" /> : null}>
          {submitting ? 'Creating…' : 'Create Student'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
