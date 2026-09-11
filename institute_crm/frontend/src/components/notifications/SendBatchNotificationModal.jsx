import React, { useEffect, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField,
  MenuItem, FormControl, FormLabel, RadioGroup, FormControlLabel, Radio,
  Alert, CircularProgress, Box, Chip
} from '@mui/material';
import api, { unwrapList, unwrapData } from '../../services/api';

const CHANNELS = [
  { value: 'IN_APP', label: 'In-App Notification' },
  { value: 'EMAIL', label: 'Email' },
  { value: 'SMS', label: 'SMS' },
  { value: 'ALL', label: 'All Channels' },
];

const AUDIENCES = [
  { value: 'STUDENTS', label: 'Students Only' },
  { value: 'PARENTS', label: 'Parents Only' },
  { value: 'ALL', label: 'Students & Parents' },
];

export const SendBatchNotificationModal = ({ open, onClose, onSent }) => {
  const [batches, setBatches] = useState([]);
  const [batchId, setBatchId] = useState('');
  const [targetAudience, setTargetAudience] = useState('STUDENTS');
  const [channel, setChannel] = useState('IN_APP');
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingBatches, setLoadingBatches] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setSuccess(null);
    setLoadingBatches(true);
    api.get('/academics/batches/')
      .then((res) => {
        const list = unwrapList(res);
        setBatches(list);
      })
      .catch(() => setError('Unable to load batches. Please try again.'))
      .finally(() => setLoadingBatches(false));
  }, [open]);

  const reset = () => {
    setBatchId('');
    setTargetAudience('STUDENTS');
    setChannel('IN_APP');
    setTitle('');
    setMessage('');
    setError(null);
    setSuccess(null);
  };

  const handleClose = () => {
    if (loading) return;
    reset();
    onClose?.();
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    setError(null);
    setSuccess(null);
    if (!batchId) {
      setError('Please select a batch.');
      return;
    }
    if (!title.trim() || !message.trim()) {
      setError('Title and message are required.');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/communications/notifications/send-batch/', {
        batch_id: batchId,
        title: title.trim(),
        message: message.trim(),
        channel,
        target_audience: targetAudience,
      });
      const data = unwrapData(res) || res;
      const count = data?.recipient_count ?? data?.data?.recipient_count ?? 0;
      setSuccess(`Notification sent to ${count} recipient(s).`);
      onSent?.(data);
    } catch (err) {
      const fieldErrors = err?.errors;
      const msg = fieldErrors
        ? Object.entries(fieldErrors).map(([f, m]) => `${f}: ${Array.isArray(m) ? m.join(', ') : m}`).join(' ')
        : (err?.detail || err?.message || 'Failed to send notification.');
      setError(typeof msg === 'string' ? msg : 'Failed to send notification.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Send Batch Notification</DialogTitle>
      <Box component="form" onSubmit={handleSubmit}>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          {success && <Alert severity="success">{success}</Alert>}
          <TextField
            select
            required
            fullWidth
            label="Batch"
            value={batchId}
            onChange={(e) => setBatchId(e.target.value)}
            disabled={loadingBatches || loading}
            helperText={loadingBatches ? 'Loading batches…' : 'Only batches visible to you are listed.'}
          >
            <MenuItem value="" disabled>Select batch</MenuItem>
            {batches.map((b) => (
              <MenuItem key={b.id} value={b.id}>
                {b.name} ({b.code}) — {b.branch_name || b.branch?.name || ''}
              </MenuItem>
            ))}
          </TextField>

          <FormControl component="fieldset">
            <FormLabel component="legend">Target audience</FormLabel>
            <RadioGroup row value={targetAudience} onChange={(e) => setTargetAudience(e.target.value)}>
              {AUDIENCES.map((a) => (
                <FormControlLabel key={a.value} value={a.value} control={<Radio />} label={a.label} disabled={loading} />
              ))}
            </RadioGroup>
          </FormControl>

          <FormControl component="fieldset">
            <FormLabel component="legend">Delivery channel</FormLabel>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
              {CHANNELS.map((c) => (
                <Chip
                  key={c.value}
                  label={c.label}
                  clickable
                  color={channel === c.value ? 'primary' : 'default'}
                  onClick={() => setChannel(c.value)}
                />
              ))}
            </Box>
          </FormControl>

          <TextField
            required
            fullWidth
            label="Subject / Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={loading}
            inputProps={{ maxLength: 200 }}
          />
          <TextField
            required
            fullWidth
            multiline
            minRows={4}
            label="Message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={loading}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} disabled={loading}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={loading || !batchId}>
            {loading ? <><CircularProgress size={18} sx={{ mr: 1 }} /> Sending…</> : 'Send'}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
};
