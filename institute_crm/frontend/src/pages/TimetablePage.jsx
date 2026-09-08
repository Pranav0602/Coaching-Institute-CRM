import React, { useEffect, useState } from 'react';
import {
  Alert, Box, Button, CircularProgress, Dialog, DialogActions, DialogContent,
  DialogTitle, IconButton, MenuItem, Paper, Snackbar, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, TextField, Tooltip, Typography,
} from '@mui/material';
import { Add, DeleteOutline, EventBusy, Refresh } from '@mui/icons-material';
import api from '../services/api';

const DAYS = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'];
const initialForm = { batch: '', subject: '', teacher: '', day_of_week: 'MONDAY', start_time: '', end_time: '', room_number: '' };
const dataOf = (response) => response?.data ?? response;
const listOf = (response) => { const data = dataOf(response); return Array.isArray(data) ? data : data.results || []; };
const dayLabel = (day) => day.charAt(0) + day.slice(1).toLowerCase();
const errorMessage = (error) => typeof error?.detail === 'string' ? error.detail : (Array.isArray(Object.values(error || {})[0]) ? Object.values(error)[0][0] : 'Unable to complete that request.');

export const TimetablePage = () => {
  const [sessions, setSessions] = useState([]);
  const [batches, setBatches] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });

  const loadData = async () => {
    setLoading(true);
    try {
      const [sessionRes, batchRes, subjectRes, teacherRes] = await Promise.all([
        api.get('/academics/timetables/'), api.get('/academics/batches/'), api.get('/academics/subjects/'), api.get('/accounts/users/?role=TEACHER'),
      ]);
      setSessions(listOf(sessionRes)); setBatches(listOf(batchRes)); setSubjects(listOf(subjectRes)); setTeachers(listOf(teacherRes));
    } catch (error) {
      setToast({ open: true, message: errorMessage(error), severity: 'error' });
    } finally { setLoading(false); }
  };
  useEffect(() => { loadData(); }, []);
  const updateForm = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));
  const closeAdd = () => { if (!saving) { setAddOpen(false); setForm(initialForm); } };
  const addSession = async () => {
    if (!form.batch || !form.subject || !form.teacher || !form.start_time || !form.end_time || !form.room_number) { setToast({ open: true, message: 'Complete all session fields before saving.', severity: 'warning' }); return; }
    if (form.end_time <= form.start_time) { setToast({ open: true, message: 'End time must be after start time.', severity: 'warning' }); return; }
    setSaving(true);
    try {
      const created = dataOf(await api.post('/academics/timetables/', form));
      setSessions((current) => [...current, created]); setForm(initialForm); setAddOpen(false);
      setToast({ open: true, message: 'Session added to the timetable.', severity: 'success' });
    } catch (error) { setToast({ open: true, message: errorMessage(error), severity: 'error' }); }
    finally { setSaving(false); }
  };
  const deleteSession = async () => {
    if (!deleting) return; setSaving(true);
    try { await api.delete(`/academics/timetables/${deleting.id}/`); setSessions((current) => current.filter((session) => session.id !== deleting.id)); setDeleting(null); setToast({ open: true, message: 'Session deleted.', severity: 'success' }); }
    catch (error) { setToast({ open: true, message: errorMessage(error), severity: 'error' }); }
    finally { setSaving(false); }
  };
  return <Box>
    <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}><Box><Typography variant="h4" sx={{ fontWeight: 800 }}>Timetable</Typography><Typography color="text.secondary">Schedule and manage recurring class sessions for your branch.</Typography></Box><Stack direction="row" spacing={1}><Button variant="outlined" startIcon={<Refresh />} onClick={loadData} disabled={loading}>Refresh</Button>
    <Button variant="contained" startIcon={<Add />} onClick={() => setAddOpen(true)}>Add session</Button></Stack></Box>
    <Paper sx={{ overflow: 'hidden' }}>{loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box> : sessions.length === 0 ? <Box sx={{ textAlign: 'center', py: 7 }}><EventBusy sx={{ fontSize: 44, color: 'text.disabled' }} /><Typography variant="h6" sx={{ mt: 1 }}>No sessions scheduled</Typography><Typography color="text.secondary">Use “Add session” to create the first timetable entry.</Typography></Box> : <Table><TableHead><TableRow><TableCell sx={{ fontWeight: 700 }}>Day & time</TableCell><TableCell sx={{ fontWeight: 700 }}>Batch</TableCell><TableCell sx={{ fontWeight: 700 }}>Subject</TableCell><TableCell sx={{ fontWeight: 700 }}>Teacher</TableCell><TableCell sx={{ fontWeight: 700 }}>Room</TableCell><TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell></TableRow></TableHead><TableBody>{sessions.map((session) => <TableRow hover key={session.id}><TableCell>{dayLabel(session.day_of_week)} · {session.start_time?.slice(0, 5)} – {session.end_time?.slice(0, 5)}</TableCell><TableCell>{session.batch_name}</TableCell><TableCell>{session.subject_title}</TableCell><TableCell>{session.teacher_name}</TableCell><TableCell>{session.room_number}</TableCell><TableCell align="right"><Tooltip title="Delete session"><IconButton color="error" onClick={() => setDeleting(session)} aria-label="Delete session"><DeleteOutline /></IconButton></Tooltip></TableCell></TableRow>)}</TableBody></Table>}</Paper>
    <Dialog open={addOpen} onClose={closeAdd} maxWidth="sm" fullWidth><DialogTitle sx={{ fontWeight: 700 }}>Add timetable session</DialogTitle><DialogContent><Stack spacing={2} sx={{ mt: 1 }}><TextField required select fullWidth label="Batch" value={form.batch} onChange={updateForm('batch')}>{batches.map((batch) => <MenuItem key={batch.id} value={batch.id}>{batch.name}</MenuItem>)}</TextField>
    <TextField required select fullWidth label="Subject" value={form.subject} onChange={updateForm('subject')}>{subjects.map((subject) => <MenuItem key={subject.id} value={subject.id}>{subject.title}</MenuItem>)}</TextField><TextField required select fullWidth label="Teacher" value={form.teacher} onChange={updateForm('teacher')}>{teachers.map((teacher) => <MenuItem key={teacher.id} value={teacher.id}>{`${teacher.first_name} ${teacher.last_name}`.trim() || teacher.username}</MenuItem>)}</TextField>
    <TextField required select fullWidth label="Day" value={form.day_of_week} onChange={updateForm('day_of_week')}>{DAYS.map((day) => <MenuItem key={day} value={day}>{dayLabel(day)}</MenuItem>)}</TextField><Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}><TextField required fullWidth type="time" label="Start time" InputLabelProps={{ shrink: true }} value={form.start_time} onChange={updateForm('start_time')} /><TextField required fullWidth type="time" label="End time" InputLabelProps={{ shrink: true }} value={form.end_time} onChange={updateForm('end_time')} /></Stack><TextField required fullWidth label="Room" value={form.room_number} onChange={updateForm('room_number')} placeholder="e.g. Room 101" /></Stack></DialogContent><DialogActions><Button onClick={closeAdd} disabled={saving}>Cancel</Button><Button variant="contained" onClick={addSession} disabled={saving}>{saving ? 'Adding…' : 'Add session'}</Button></DialogActions></Dialog>
    <Dialog open={Boolean(deleting)} onClose={() => !saving && setDeleting(null)} maxWidth="xs" fullWidth><DialogTitle>Delete session?</DialogTitle><DialogContent><Typography>This will remove the {deleting?.subject_title} session from the timetable.</Typography></DialogContent><DialogActions>
    <Button onClick={() => setDeleting(null)} disabled={saving}>Cancel</Button><Button color="error" variant="contained" onClick={deleteSession} disabled={saving}>{saving ? 'Deleting…' : 'Delete'}</Button></DialogActions></Dialog>
    <Snackbar open={toast.open} autoHideDuration={4500} onClose={() => setToast((current) => ({ ...current, open: false }))}><Alert severity={toast.severity} onClose={() => setToast((current) => ({ ...current, open: false }))}>{toast.message}</Alert></Snackbar>
  </Box>;
};
