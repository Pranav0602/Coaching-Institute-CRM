import React, { useEffect, useState } from 'react';
import {
  Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogTitle, Divider, Grid, Stack, TextField, Typography,
} from '@mui/material';
import { Edit, Print, Save, Close } from '@mui/icons-material';
import api from '../../services/api';

const money = (value) => {
  if (value === null || value === undefined || value === '') return '—';
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  return `₹${num.toLocaleString('en-IN')}`;
};

const formatDate = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString(undefined, { dateStyle: 'medium' });
  } catch {
    return value;
  }
};

const InfoRow = ({ label, value }) => (
  <Grid item xs={12} sm={6}>
    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.4 }}>
      {label}
    </Typography>
    <Typography variant="body2" sx={{ fontWeight: 500 }}>{value || '—'}</Typography>
  </Grid>
);

const SectionTitle = ({ children }) => (
  <Typography variant="subtitle2" sx={{ fontWeight: 800, mt: 2, mb: 1 }}>{children}</Typography>
);

export const StudentProfileDialog = ({ open, row, onClose, onUpdated }) => {
  const [attendance, setAttendance] = useState(null);
  const [loadingAttendance, setLoadingAttendance] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [contact, setContact] = useState({ first_name: '', last_name: '', email: '', phone: '' });

  const user = row?.user || {};
  const profile = row?.profile || {};

  useEffect(() => {
    if (!open || !user?.id) return undefined;
    setEditing(false);
    setError(null);
    setContact({
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      email: user.email || '',
      phone: user.phone || '',
    });
    let cancelled = false;
    setLoadingAttendance(true);
    api.get('/academics/attendances/summary/', { params: { student_id: user.id } })
      .then((res) => { if (!cancelled) setAttendance(res?.data ?? res ?? null); })
      .catch(() => { if (!cancelled) setAttendance(null); })
      .finally(() => { if (!cancelled) setLoadingAttendance(false); });
    return () => { cancelled = true; };
  }, [open, user?.id]);

  const handleSaveContact = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.patch(`/accounts/users/${user.id}/`, contact);
      setEditing(false);
      onUpdated?.();
    } catch (err) {
      setError(err?.detail || err?.message || 'Could not update contact details.');
    } finally {
      setSaving(false);
    }
  };

  const handlePrint = async () => {
    let card = null;
    if (profile?.id) {
      try {
        const res = await api.get(`/profiles/students/${profile.id}/id-card/`);
        card = res?.data ?? res;
      } catch {
        card = null;
      }
    }
    const data = card || {
      full_name: row?.full_name,
      reg_no: profile?.reg_no,
      course_title: profile?.course_title,
      batch_name: profile?.batch_name,
      branch_name: profile?.branch_name,
      phone: user?.phone,
    };
    const win = window.open('', '_blank', 'width=420,height=640');
    if (!win) {
      setError('Allow pop-ups to print the student ID card.');
      return;
    }
    win.document.write(`
      <html><head><title>Student ID Card</title>
      <style>
        body{font-family:Arial,Helvetica,sans-serif;margin:0;padding:24px;background:#fff;}
        .card{width:320px;margin:0 auto;border:3px solid #6366F1;border-radius:16px;padding:22px;text-align:center;}
        .avatar{width:64px;height:64px;border-radius:50%;background:#6366F1;color:#fff;display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:800;margin:0 auto 10px;}
        h2{margin:6px 0;} .muted{color:#64748b;font-size:12px;} .chip{display:inline-block;background:#EEF2FF;color:#4338CA;border-radius:999px;padding:4px 12px;font-size:12px;margin:8px 0;}
        .row{font-size:13px;margin:4px 0;} .sig{margin-top:18px;color:#94a3b8;font-size:11px;border-top:1px dashed #cbd5e1;padding-top:8px;}
      </style></head><body>
        <div class="card">
          <div class="avatar">${(data.full_name || 'S').charAt(0)}</div>
          <h2>${data.full_name || 'Student'}</h2>
          <div class="muted">${data.reg_no || '—'}</div>
          <div class="chip">${data.course_title || 'Course'}</div>
          <div class="row">Batch: ${data.batch_name || '—'}</div>
          <div class="row">Branch: ${data.branch_name || '—'}</div>
          <div class="row">Phone: ${data.phone || '—'}</div>
          <div class="sig">Authorized Signature</div>
        </div>
        <script>window.onload = function(){ window.print(); };</script>
      </body></html>`);
    win.document.close();
  };

  const fee = profile?.fee_summary || {};
  const guardianName = profile?.guardian_name || profile?.guardian?.name;
  const guardianPhone = profile?.guardian_phone || profile?.guardian?.phone || profile?.emergency_contact;
  const guardianRelation = profile?.guardian_relationship || profile?.guardian?.relationship;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
        <Box>
          {row?.full_name || 'Student Profile'}
          <Chip
            size="small"
            label={user?.is_active === false ? 'Inactive' : 'Active'}
            color={user?.is_active === false ? 'default' : 'success'}
            sx={{ ml: 1.5 }}
          />
        </Box>
        <Stack direction="row" spacing={1}>
          <Button size="small" startIcon={<Print />} onClick={handlePrint}>ID Card</Button>
          {editing ? (
            <Button size="small" startIcon={<Close />} onClick={() => setEditing(false)}>Cancel</Button>
          ) : (
            <Button size="small" startIcon={<Edit />} onClick={() => setEditing(true)}>Edit Contact</Button>
          )}
        </Stack>
      </DialogTitle>
      <DialogContent dividers>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {editing ? (
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}><TextField label="First Name" fullWidth value={contact.first_name} onChange={(e) => setContact({ ...contact, first_name: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField label="Last Name" fullWidth value={contact.last_name} onChange={(e) => setContact({ ...contact, last_name: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField label="Email" type="email" fullWidth value={contact.email} onChange={(e) => setContact({ ...contact, email: e.target.value })} /></Grid>
            <Grid item xs={12} sm={6}><TextField label="Phone" fullWidth value={contact.phone} onChange={(e) => setContact({ ...contact, phone: e.target.value })} /></Grid>
          </Grid>
        ) : (
          <>
            <SectionTitle>Personal information</SectionTitle>
            <Grid container spacing={1.5}>
              <InfoRow label="Full Name" value={row?.full_name} />
              <InfoRow label="Roll / Enrollment No." value={profile?.reg_no} />
              <InfoRow label="Email" value={user?.email} />
              <InfoRow label="Phone" value={[user?.phone, profile?.secondary_phone].filter(Boolean).join(' / ')} />
              <InfoRow label="Date of Birth" value={formatDate(profile?.dob)} />
              <InfoRow label="Gender" value={profile?.gender} />
              <InfoRow label="Blood Group" value={profile?.blood_group} />
              <InfoRow label="Address" value={profile?.address} />
            </Grid>

            <SectionTitle>Guardian / parent contact</SectionTitle>
            <Grid container spacing={1.5}>
              <InfoRow label="Guardian Name" value={guardianName} />
              <InfoRow label="Guardian Contact" value={guardianPhone} />
              <InfoRow label="Relationship" value={guardianRelation} />
            </Grid>

            <Divider sx={{ my: 2 }} />
            <SectionTitle>Academic enrollment</SectionTitle>
            <Grid container spacing={1.5}>
              <InfoRow label="Course" value={profile?.course_title} />
              <InfoRow label="Batch" value={profile?.batch_name || 'Not assigned'} />
              <InfoRow label="Branch" value={row?.branch_name || profile?.branch_name} />
              <InfoRow label="Admission Date" value={formatDate(user?.date_joined || profile?.created_at)} />
              <InfoRow label="Account Status" value={user?.is_active === false ? 'Inactive' : 'Active'} />
              <InfoRow
                label="Attendance"
                value={loadingAttendance ? 'Loading…' : (
                  attendance?.percentage !== null && attendance?.percentage !== undefined
                    ? `${attendance.percentage}% (${attendance.present || 0}/${attendance.total_sessions || 0} present)`
                    : 'No attendance recorded'
                )}
              />
            </Grid>

            <Divider sx={{ my: 2 }} />
            <SectionTitle>Financial summary (read-only)</SectionTitle>
            <Grid container spacing={1.5}>
              <InfoRow label="Net Fee" value={money(profile?.net_fee ?? fee.net_fee)} />
              <InfoRow label="Total Paid" value={money(profile?.total_paid ?? fee.total_paid)} />
              <InfoRow label="Outstanding Balance" value={money(profile?.outstanding_balance ?? fee.outstanding_balance)} />
              <InfoRow label="Next Due Date" value={formatDate(profile?.next_due_date ?? fee.next_due_date)} />
              <InfoRow label="Fee Status" value={profile?.fee_status ?? fee.fee_status} />
            </Grid>
          </>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        {editing ? (
          <>
            <Button onClick={() => setEditing(false)} disabled={saving}>Cancel</Button>
            <Button variant="contained" startIcon={saving ? <CircularProgress size={16} color="inherit" /> : <Save />} onClick={handleSaveContact} disabled={saving}>
              {saving ? 'Saving…' : 'Save Contact'}
            </Button>
          </>
        ) : (
          <Button onClick={onClose}>Close</Button>
        )}
      </DialogActions>
    </Dialog>
  );
};
