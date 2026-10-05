import React, { useEffect, useMemo, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography,
  Box, Chip, Table, TableBody, TableCell, TableHead, TableRow, CircularProgress,
  ToggleButton, ToggleButtonGroup, Alert
} from '@mui/material';
import api, { unwrapList } from '../../services/api';

const STATUS_COLORS = {
  PENDING: 'default', QUEUED: 'default', SUBMITTED: 'info', SENT: 'info',
  DELIVERED: 'success', READ: 'success', FAILED: 'error', SKIPPED: 'warning', OPTED_OUT: 'warning',
};

export const DeliveryFunnelDialog = ({ open, campaignId, campaignTitle, onClose, onRetry }) => {
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('ALL');
  const [retrying, setRetrying] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    if (!open || !campaignId) return;
    setLoading(true);
    api.get(`/communications/notifications/campaign-deliveries/?campaign_id=${campaignId}`)
      .then((res) => setDeliveries(unwrapList(res) || res.data?.results || []))
      .catch(() => setDeliveries([]))
      .finally(() => setLoading(false));
  }, [open, campaignId]);

  const funnel = useMemo(() => {
    const counts = { QUEUED: 0, SUBMITTED: 0, SENT: 0, DELIVERED: 0, READ: 0, FAILED: 0, SKIPPED: 0, PENDING: 0 };
    deliveries.forEach((d) => { counts[d.status] = (counts[d.status] || 0) + 1; });
    return counts;
  }, [deliveries]);

  const filtered = filter === 'ALL' ? deliveries : deliveries.filter((d) => d.status === filter);

  const retryFailed = async () => {
    setRetrying(true);
    setMessage(null);
    try {
      const res = await api.post('/communications/notifications/retry-failed/', { campaign_id: campaignId });
      setMessage(`Re-queued ${res?.data?.requeued ?? res?.requeued ?? 0} deliveries.`);
      setLoading(true);
      const refreshed = await api.get(`/communications/notifications/campaign-deliveries/?campaign_id=${campaignId}`);
      setDeliveries(unwrapList(refreshed) || []);
    } catch {
      setMessage('Retry failed.');
    } finally {
      setRetrying(false);
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Delivery funnel {campaignTitle ? `— ${campaignTitle}` : ''}</DialogTitle>
      <DialogContent>
        {message && <Alert severity="info" sx={{ mb: 2 }}>{message}</Alert>}
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          {Object.entries(funnel).map(([status, count]) => (
            <Chip key={status} label={`${status}: ${count}`} color={STATUS_COLORS[status] || 'default'} variant="outlined" />
          ))}
        </Box>
        <ToggleButtonGroup size="small" exclusive value={filter} onChange={(_, v) => v && setFilter(v)} sx={{ mb: 2 }}>
          <ToggleButton value="ALL">All</ToggleButton>
          <ToggleButton value="FAILED">Failed</ToggleButton>
          <ToggleButton value="SKIPPED">Skipped</ToggleButton>
          <ToggleButton value="READ">Read</ToggleButton>
          <ToggleButton value="DELIVERED">Delivered</ToggleButton>
        </ToggleButtonGroup>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Recipient</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Phone</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Reason</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filtered.map((d) => (
                <TableRow key={d.id}>
                  <TableCell>{d.recipient_name}</TableCell>
                  <TableCell>{d.recipient_role}</TableCell>
                  <TableCell>{d.phone_snapshot ? `+${'*'.repeat(Math.max(d.phone_snapshot.length - 4, 0))}${d.phone_snapshot.slice(-4)}` : '—'}</TableCell>
                  <TableCell><Chip size="small" label={d.status} color={STATUS_COLORS[d.status] || 'default'} /></TableCell>
                  <TableCell>{d.error_message || '—'}</TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow><TableCell colSpan={5} align="center">No deliveries</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={retryFailed} disabled={retrying}>{retrying ? 'Retrying…' : 'Retry failed'}</Button>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};
