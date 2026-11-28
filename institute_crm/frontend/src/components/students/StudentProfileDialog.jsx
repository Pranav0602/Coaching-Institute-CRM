import React, { useEffect, useState } from 'react';
import {
  Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogTitle, Divider, Grid, MenuItem, Stack, TextField, Typography,
} from '@mui/material';
import { Edit, Print, Save, Close, GroupAdd } from '@mui/icons-material';
import api from '../../services/api';
import { useAuth, ROLES } from '../../context/AuthContext';

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

const errMsg = (err, fallback) => {
  const data = err?.response?.data ?? err ?? {};
  return data?.message || data?.detail || err?.message || fallback;
};

const GENDERS = ['MALE', 'FEMALE', 'OTHER'];
const EDIT_ROLES = [ROLES.RECEPTIONIST, ROLES.ADMISSION_COUNSELOR, ROLES.BRANCH_ADMIN, ROLES.SUPER_ADMIN];

// Fields edited in "Edit Student Profile". System-managed fields (id, reg_no,
// created_at, audit, admission_status, is_deleted...) are intentionally omitted.
const emptyProfileForm = {
  dob: '', gender: 'MALE', blood_group: '', address: '', emergency_contact: '',
  secondary_phone: '', course: '', academic_branch: '', source_course_label: '',
  source_softwares: '', documents_url: '', guardian_name: '', guardian_phone: '',
  guardian_relationship: '', agreed_fee: 0, discount_amount: 0, concession_amount: 0,
  scholarship_amount: 0, fee_notes: '',
};

export const StudentProfileDialog = ({ open, row, onClose, onUpdated, batches: batchesProp }) => {
  const { user: currentUser } = useAuth();
  const canEdit = EDIT_ROLES.includes(currentUser?.role_code);

  const [attendance, setAttendance] = useState(null);
  const [loadingAttendance, setLoadingAttendance] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [contact, setContact] = useState({ first_name: '', last_name: '', email: '', phone: '' });
  const [profileForm, setProfileForm] = useState(emptyProfileForm);
  const [courses, setCourses] = useState([]);

  // Batch assignment
  const [assignOpen, setAssignOpen] = useState(false);
  const [assignBatchId, setAssignBatchId] = useState('');
  const [assignSaving, setAssignSaving] = useState(false);
  const [batches, setBatches] = useState(batchesProp || []);
  const [assignError, setAssignError] = useState(null);

  const user = row?.user || {};
  const profile = row?.profile || {};
  const profileKey = profile?.id || profile?.reg_no;

  useEffect(() => {
    if (!open || !user?.id) return undefined;
    setEditing(false);
    setError(null);
    setNotice(null);
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

  useEffect(() => {
    if (!open) return;
    setProfileForm({
      dob: profile.dob || '',
      gender: profile.gender || 'MALE',
      blood_group: profile.blood_group || '',
      address: profile.address || '',
      emergency_contact: profile.emergency_contact || '',
      secondary_phone: profile.secondary_phone || '',
      course: profile.course || '',
      academic_branch: profile.academic_branch || '',
      source_course_label: profile.source_course_label || '',
      source_softwares: profile.source_softwares || '',
      documents_url: Array.isArray(profile.documents_url) ? profile.documents_url.join('\n') : (profile.documents_url || ''),
      guardian_name: profile.guardian_name || '',
      guardian_phone: profile.guardian_phone || profile.guardian?.phone || '',
      guardian_relationship: profile.guardian_relationship || profile.guardian?.relationship || '',
      agreed_fee: profile.agreed_fee ?? 0,
      discount_amount: profile.discount_amount ?? 0,
      concession_amount: profile.concession_amount ?? 0,
      scholarship_amount: profile.scholarship_amount ?? 0,
      fee_notes: profile.fee_notes || '',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, profileKey]);

  useEffect(() => {
    if (!open) return;
    api.get('/academics/courses/').then((res) => setCourses(res?.data ?? res ?? [])).catch(() => setCourses([]));
    api.get('/academics/batches/').then((res) => setBatches((res?.data ?? res ?? []))).catch(() => setBatches(batchesProp || []));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const updateProfileField = (field) => (e) => setProfileForm((c) => ({ ...c, [field]: e.target.value }));

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      // Contact (account-level) — authorized staff; reception may correct contact.
      if (user?.id) {
        await api.patch(`/accounts/users/${user.id}/`, {
          first_name: contact.first_name,
          last_name: contact.last_name,
          email: contact.email,
          phone: contact.phone,
        });
      }
      if (profileKey) {
        const profilePayload = { ...profileForm };
        // documents_url -> list; empty strings -> null
        profilePayload.documents_url = profilePayload.documents_url
          ? profilePayload.documents_url.split('\n').map((s) => s.trim()).filter(Boolean)
          : [];
        ['dob', 'blood_group', 'address', 'emergency_contact', 'secondary_phone', 'course', 'academic_branch',
          'source_course_label', 'source_softwares', 'guardian_name', 'guardian_phone', 'guardian_relationship', 'fee_notes']
          .forEach((k) => { if (profilePayload[k] === '') profilePayload[k] = null; });
        ['agreed_fee', 'discount_amount', 'concession_amount', 'scholarship_amount'].forEach((k) => {
          profilePayload[k] = Number(profilePayload[k] || 0);
        });
        await api.patch(`/profiles/students/${encodeURIComponent(profileKey)}/`, profilePayload);
      }
      setEditing(false);
      setNotice('Student profile saved.');
      onUpdated?.();
    } catch (err) {
      setError(errMsg(err, 'Could not save student profile.'));
    } finally {
      setSaving(false);
    }
  };

  // Valid batches for this student: active batch in student's branch + matching course.
  const studentBranchId = user?.branch || profile?.branch_branch || row?.branch_id || '';
  const studentCourseId = profile?.course || '';
  const validBatches = (batches || []).filter((b) => {
    if (b.is_deleted) return false;
    const branchOk = !studentBranchId || b.branch === studentBranchId;
    const courseOk = !studentCourseId || b.course === studentCourseId;
    return branchOk && courseOk;
  });

  const handleAssignBatch = async () => {
    if (!assignBatchId) { setAssignError('Select a batch.'); return; }
    setAssignSaving(true);
    setAssignError(null);
    try {
      await api.post(`/profiles/students/${encodeURIComponent(profileKey)}/assign-batch/`, { batch: assignBatchId });
      setAssignOpen(false);
      setAssignBatchId('');
      onUpdated?.();
    } catch (err) {
      setAssignError(errMsg(err, 'Could not assign batch.'));
    } finally {
      setAssignSaving(false);
    }
  };

  const handlePrint = async () => {
    let card = null;
    if (profile?.id) {
      try {
        const res = await api.get(`/profiles/students/${encodeURIComponent(profile.id)}/id-card/`);
        card = res?.data ?? res;
      } catch {
        card = null;
      }
    }
    const data = card || {
      full_name: row?.full_name, reg_no: profile?.reg_no, course_title: profile?.course_title,
      batch_name: profile?.batch_name, branch_name: profile?.branch_name, phone: user?.phone,
    };
    const win = window.open('', '_blank', 'width=420,height=640');
    if (!win) { setError('Allow pop-ups to print the student ID card.'); return; }
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
          <Chip size="small" label={user?.is_active === false ? 'Inactive' : 'Active'} color={user?.is_active === false ? 'default' : 'success'} sx={{ ml: 1.5 }} />
        </Box>
        <Stack direction="row" spacing={1}>
          <Button size="small" startIcon={<Print />} onClick={handlePrint}>ID Card</Button>
          {canEdit && (editing ? (
            <Button size="small" startIcon={<Close />} onClick={() => { setEditing(false); setError(null); }} disabled={saving}>Cancel</Button>
          ) : (
            <Button size="small" startIcon={<Edit />} onClick={() => { setEditing(true); setNotice(null); }}>Edit Student Profile</Button>
          ))}
        </Stack>
      </DialogTitle>
      <DialogContent dividers>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {notice && <Alert severity="success" sx={{ mb: 2 }}>{notice}</Alert>}

        {editing ? (
          <Box component="form" onSubmit={(e) => { e.preventDefault(); handleSave(); }}>
            <SectionTitle>Contact</SectionTitle>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}><TextField label="First Name" fullWidth value={contact.first_name} onChange={(e) => setContact({ ...contact, first_name: e.target.value })} /></Grid>
              <Grid item xs={12} sm={6}><TextField label="Last Name" fullWidth value={contact.last_name} onChange={(e) => setContact({ ...contact, last_name: e.target.value })} /></Grid>
              <Grid item xs={12} sm={6}><TextField label="Email" type="email" fullWidth value={contact.email} onChange={(e) => setContact({ ...contact, email: e.target.value })} /></Grid>
              <Grid item xs={12} sm={6}><TextField label="Phone" fullWidth value={contact.phone} onChange={(e) => setContact({ ...contact, phone: e.target.value })} /></Grid>
            </Grid>

            <SectionTitle>Personal</SectionTitle>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}><TextField label="Date of Birth" type="date" fullWidth value={profileForm.dob || ''} onChange={updateProfileField('dob')} InputLabelProps={{ shrink: true }} /></Grid>
              <Grid item xs={12} sm={6}><TextField select label="Gender" fullWidth value={profileForm.gender || 'MALE'} onChange={updateProfileField('gender')}>{GENDERS.map((g) => <MenuItem key={g} value={g}>{g}</MenuItem>)}</TextField></Grid>
              <Grid item xs={12} sm={6}><TextField label="Blood Group" fullWidth value={profileForm.blood_group || ''} onChange={updateProfileField('blood_group')} /></Grid>
              <Grid item xs={12} sm={6}><TextField label="Secondary Phone" fullWidth value={profileForm.secondary_phone || ''} onChange={updateProfileField('secondary_phone')} /></Grid>
              <Grid item xs={12}><TextField label="Address" fullWidth multiline minRows={2} value={profileForm.address || ''} onChange={updateProfileField('address')} /></Grid>
              <Grid item xs={12} sm={6}><TextField label="Emergency Contact" fullWidth value={profileForm.emergency_contact || ''} onChange={updateProfileField('emergency_contact')} /></Grid>
            </Grid>

            <SectionTitle>Guardian / parent</SectionTitle>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}><TextField label="Guardian Name" fullWidth value={profileForm.guardian_name || ''} onChange={updateProfileField('guardian_name')} /></Grid>
              <Grid item xs={12} sm={4}><TextField label="Guardian Phone" fullWidth value={profileForm.guardian_phone || ''} onChange={updateProfileField('guardian_phone')} /></Grid>
              <Grid item xs={12} sm={4}><TextField label="Relationship" fullWidth value={profileForm.guardian_relationship || ''} onChange={updateProfileField('guardian_relationship')} /></Grid>
            </Grid>

            <SectionTitle>Academic</SectionTitle>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField select label="Course" fullWidth value={profileForm.course || ''} onChange={updateProfileField('course')}>
                  <MenuItem value="">— None —</MenuItem>
                  {courses.map((c) => <MenuItem key={c.id} value={c.id}>{c.title}</MenuItem>)}
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}><TextField label="Academic Branch" fullWidth value={profileForm.academic_branch || ''} onChange={updateProfileField('academic_branch')} /></Grid>
              <Grid item xs={12} sm={6}><TextField label="Source Course Label" fullWidth value={profileForm.source_course_label || ''} onChange={updateProfileField('source_course_label')} /></Grid>
              <Grid item xs={12} sm={6}><TextField label="Source Softwares" fullWidth value={profileForm.source_softwares || ''} onChange={updateProfileField('source_softwares')} /></Grid>
              <Grid item xs={12}>
                <TextField label="Documents (one URL per line)" fullWidth multiline minRows={2} value={profileForm.documents_url || ''} onChange={updateProfileField('documents_url')} />
              </Grid>
            </Grid>

            <SectionTitle>Fee terms (INR)</SectionTitle>
            <Grid container spacing={2}>
              <Grid item xs={6} sm={3}><TextField label="Agreed Fee" type="number" fullWidth value={profileForm.agreed_fee} onChange={updateProfileField('agreed_fee')} /></Grid>
              <Grid item xs={6} sm={3}><TextField label="Discount" type="number" fullWidth value={profileForm.discount_amount} onChange={updateProfileField('discount_amount')} /></Grid>
              <Grid item xs={6} sm={3}><TextField label="Concession" type="number" fullWidth value={profileForm.concession_amount} onChange={updateProfileField('concession_amount')} /></Grid>
              <Grid item xs={6} sm={3}><TextField label="Scholarship" type="number" fullWidth value={profileForm.scholarship_amount} onChange={updateProfileField('scholarship_amount')} /></Grid>
              <Grid item xs={12}><TextField label="Fee Notes" fullWidth multiline minRows={2} value={profileForm.fee_notes || ''} onChange={updateProfileField('fee_notes')} /></Grid>
            </Grid>

            <Divider sx={{ my: 2 }} />
            <Typography variant="caption" color="text.secondary">
              REG NO, IDs, created/updated timestamps, admission status and audit fields are system-managed and not editable.
            </Typography>
          </Box>
        ) : (
          <>
            <SectionTitle>Personal information</SectionTitle>
            <Grid container spacing={1.5}>
              <InfoRow label="Full Name" value={row?.full_name} />
              <InfoRow label="REG NO" value={profile?.reg_no} />
              <InfoRow label="Email" value={user?.email} />
              <InfoRow label="MOB.NO" value={user?.phone} />
              <InfoRow label="Alternate Mobile" value={profile?.secondary_phone} />
              <InfoRow label="Date of Birth" value={formatDate(profile?.dob)} />
              <InfoRow label="Gender" value={profile?.gender} />
              <InfoRow label="Blood Group" value={profile?.blood_group} />
              <InfoRow label="Address" value={profile?.address} />
              <InfoRow label="Emergency Contact" value={profile?.emergency_contact} />
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
              <InfoRow label="Softwares" value={(profile?.softwares || []).join(', ')} />
              <InfoRow label="Academic Branch" value={profile?.academic_branch} />
              <InfoRow label="Admission Date" value={formatDate(user?.date_joined || profile?.created_at)} />
              <InfoRow label="Account Status" value={user?.is_active === false ? 'Inactive' : 'Active'} />
              <InfoRow label="Admission Status" value={profile?.admission_status} />
              <InfoRow label="Attendance" value={loadingAttendance ? 'Loading…' : (attendance?.percentage !== null && attendance?.percentage !== undefined ? `${attendance.percentage}% (${attendance.present || 0}/${attendance.total_sessions || 0} present)` : 'No attendance recorded')} />
            </Grid>

            {/* Assign batch to unassigned student */}
            {canEdit && !profile?.batch_name && (
              <Box sx={{ mt: 2 }}>
                <Button size="small" variant="outlined" startIcon={<GroupAdd />} onClick={() => { setAssignOpen(true); setAssignError(null); }}>
                  Assign batch
                </Button>
                <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>This student has no batch assigned.</Typography>
              </Box>
            )}

            <Divider sx={{ my: 2 }} />
            <SectionTitle>Fee terms &amp; financial summary (read-only)</SectionTitle>
            <Grid container spacing={1.5}>
              <InfoRow label="Agreed Fee" value={money(profile?.agreed_fee)} />
              <InfoRow label="Discount Amount" value={money(profile?.discount_amount)} />
              <InfoRow label="Concession Amount" value={money(profile?.concession_amount)} />
              <InfoRow label="Scholarship Amount" value={money(profile?.scholarship_amount)} />
              <InfoRow label="Net Fee" value={money(profile?.net_fee ?? fee.net_fee)} />
              <InfoRow label="Total Paid" value={money(profile?.total_paid ?? fee.total_paid)} />
              <InfoRow label="Outstanding Balance" value={money(profile?.outstanding_balance ?? fee.outstanding_balance)} />
              <InfoRow label="Next Due Date" value={formatDate(profile?.next_due_date ?? fee.next_due_date)} />
              <InfoRow label="Fee Status" value={profile?.fee_status ?? fee.fee_status} />
              {profile?.fee_notes && <InfoRow label="Fee Notes" value={profile.fee_notes} />}
            </Grid>
          </>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        {editing ? (
          <>
            <Button onClick={() => setEditing(false)} disabled={saving}>Cancel</Button>
            <Button type="submit" variant="contained" startIcon={saving ? <CircularProgress size={16} color="inherit" /> : <Save />} onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save Profile'}
            </Button>
          </>
        ) : (
          <Button onClick={onClose}>Close</Button>
        )}
      </DialogActions>

      {/* Assign batch dialog */}
      <Dialog open={assignOpen} onClose={() => !assignSaving && setAssignOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 800 }}>Assign batch</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Choose a valid batch for this student’s branch{studentCourseId ? ' and course' : ''}.
          </Typography>
          {assignError && <Alert severity="error" sx={{ mb: 2 }}>{assignError}</Alert>}
          {validBatches.length === 0 ? (
            <Alert severity="info">No valid batches available in this branch{studentCourseId ? '/course' : ''}.</Alert>
          ) : (
            <TextField select fullWidth label="Batch" value={assignBatchId} onChange={(e) => setAssignBatchId(e.target.value)}>
              {validBatches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name} ({b.code})</MenuItem>)}
            </TextField>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAssignOpen(false)} disabled={assignSaving}>Cancel</Button>
          <Button variant="contained" onClick={handleAssignBatch} disabled={assignSaving || !assignBatchId}>
            {assignSaving ? 'Assigning…' : 'Assign'}
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
};
