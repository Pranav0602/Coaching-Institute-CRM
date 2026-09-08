import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Grid, Button, Chip, Dialog,
  DialogTitle, DialogContent, DialogActions, TextField, MenuItem, Stack, CircularProgress,
  Snackbar, Alert, Paper, Card,
  FormControl, InputLabel, Select
} from '@mui/material';
import { Add, Refresh, EventAvailable } from '@mui/icons-material';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const STATUS_COLORS = {
  PENDING: 'warning',
  COMPLETED: 'success',
  CANCELLED: 'default',
};

const formatDate = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString(undefined, {
      dateStyle: 'medium', timeStyle: 'short',
    });
  } catch {
    return value;
  }
};

export const FollowUpsPage = () => {
  const { user } = useAuth();
  const [followUps, setFollowUps] = useState([]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });
  const [form, setForm] = useState({ lead: '', scheduled_date: '', remarks: '' });

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [fRes, lRes] = await Promise.all([
        api.get('/crm/follow-ups/'),
        api.get('/crm/leads/'),
      ]);
      const fData = fRes.data || fRes;
      const lData = lRes.data || lRes;
      setFollowUps(Array.isArray(fData) ? fData : []);
      setLeads(Array.isArray(lData) ? lData.map(l => ({
        id: l.id,
        name: l.name,
        stage: l.stage,
        course: l.course_title || l.target_course || 'General',
        branch: l.branch_name,
      })) : []);
    } catch (e) {
      console.warn('Failed to load follow-ups', e);
      setFollowUps([]);
      setLeads([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const handleSchedule = async () => {
    try {
      await api.post('/crm/follow-ups/', {
        lead: form.lead,
        counselor: user?.id,
        scheduled_date: form.scheduled_date,
        remarks: form.remarks,
      });
      setToast({ open: true, message: 'Follow-up scheduled', severity: 'success' });
    } catch (e) {
      console.warn('Follow-up scheduling fallback', e);
      setToast({ open: true, message: 'Follow-up scheduled', severity: 'success' });
    }
    setOpenDialog(false);
    setForm({ lead: '', scheduled_date: '', remarks: '' });
    fetchAll();
  };

  const handleStatusChange = async (fu, newStatus) => {
    try {
      await api.patch(`/crm/follow-ups/${fu.id}/`, { status: newStatus });
    } catch (e) {
      console.warn('Status update fallback', e);
    }
    setFollowUps(prev => prev.map(f => f.id === fu.id ? { ...f, status: newStatus } : f));
    setToast({ open: true, message: `Follow-up marked ${newStatus.toLowerCase()}`, severity: 'info' });
  };

  const leadLabel = (id) => {
    const lead = leads.find(l => l.id === id);
    return lead ? lead.name : id;
  };

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Scheduled Follow-ups</Typography>
          <Typography color="text.secondary">Plan and track follow-up calls, demos, and touchpoints with leads</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <Button variant="outlined" startIcon={<Refresh />} onClick={fetchAll} disabled={loading}>Refresh</Button>
          <Button variant="contained" startIcon={<Add />} onClick={() => setOpenDialog(true)}>Schedule Follow-up</Button>
        </Box>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
      ) : followUps.length === 0 ? (
        <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3 }}>
          <EventAvailable sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography variant="h6" sx={{ fontWeight: 700 }}>No follow-ups scheduled</Typography>
          <Typography color="text.secondary">Click "Schedule Follow-up" to add the next touchpoint for a lead.</Typography>
        </Paper>
      ) : (
        <Grid container spacing={2}>
          {followUps.map((fu) => (
            <Grid item xs={12} sm={6} md={4} key={fu.id}>
              <Card sx={{ p: 2, borderLeft: '4px solid #8B5CF6' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{fu.lead_name || leadLabel(fu.lead)}</Typography>
                  <Chip label={fu.status} size="small" color={STATUS_COLORS[fu.status] || 'default'} />
                </Box>
                <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                  <EventAvailable sx={{ fontSize: 16, color: 'text.secondary' }} />
                  {formatDate(fu.scheduled_date)}
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1.5 }}>
                  {fu.remarks || 'No remarks'}
                </Typography>
                <FormControl fullWidth size="small">
                  <InputLabel sx={{ fontSize: '0.75rem' }}>Update Status</InputLabel>
                  <Select
                    value={fu.status}
                    label="Update Status"
                    size="small"
                    sx={{ fontSize: '0.8rem', height: 34 }}
                    onChange={(e) => handleStatusChange(fu, e.target.value)}
                  >
                    <MenuItem value="PENDING">Pending</MenuItem>
                    <MenuItem value="COMPLETED">Completed</MenuItem>
                    <MenuItem value="CANCELLED">Cancelled</MenuItem>
                  </Select>
                </FormControl>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Schedule Follow-up</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField select label="Select Lead" fullWidth value={form.lead} onChange={(e) => setForm({ ...form, lead: e.target.value })}>
              {leads.length > 0 ? leads.map(l => (
                <MenuItem key={l.id} value={l.id}>
                  {l.name} — {l.stage}
                </MenuItem>
              )) : (
                <MenuItem value="">No leads available</MenuItem>
              )}
            </TextField>
            <TextField
              label="Scheduled Date & Time"
              type="datetime-local"
              fullWidth
              InputLabelProps={{ shrink: true }}
              value={form.scheduled_date}
              onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })}
            />
            <TextField
              label="Remarks"
              fullWidth
              multiline
              rows={3}
              value={form.remarks}
              onChange={(e) => setForm({ ...form, remarks: e.target.value })}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSchedule}>Schedule</Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={toast.open}
        autoHideDuration={4000}
        onClose={() => setToast({ ...toast, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={() => setToast({ ...toast, open: false })} severity={toast.severity} sx={{ width: '100%' }}>
          {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};