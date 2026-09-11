import React, { useEffect, useState } from 'react';
import {
  Box, Tabs, Tab, List, ListItem, ListItemText, Chip, Typography,
  Button, CircularProgress, Alert, Card
} from '@mui/material';
import { PageHeader } from './PageLayout';
import api, { unwrapList, unwrapData } from '../services/api';
import { useAuth, ROLES } from '../context/AuthContext';
import { SendBatchNotificationModal } from '../components/notifications/SendBatchNotificationModal';

const timeAgo = (iso) => {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
};

export const NotificationsPage = () => {
  const { activeRole } = useAuth();
  const [tab, setTab] = useState('all');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);

  const canSend = [ROLES.SUPER_ADMIN, ROLES.BRANCH_ADMIN, ROLES.TEACHER].includes(activeRole);

  const fetchList = async (nextTab = tab) => {
    setLoading(true);
    setError(null);
    try {
      let url = '/communications/notifications/';
      if (nextTab === 'unread') url += '?unread=true';
      if (nextTab === 'sent') url = '/communications/notifications/sent/';
      const res = await api.get(url);
      setItems(unwrapList(res));
    } catch {
      setError('Unable to load notifications.');
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList(tab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const markAllRead = async () => {
    try {
      await api.post('/communications/notifications/mark-all-read/');
      fetchList(tab);
    } catch {
      setError('Unable to mark notifications as read.');
    }
  };

  const markOneRead = async (id) => {
    try {
      await api.post(`/communications/notifications/${id}/mark-read/`);
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    } catch { /* silent */ }
  };

  return (
    <Box>
      <PageHeader
        title="Notifications"
        subtitle="Batch announcements and inbox"
        action={canSend ? <Button variant="contained" onClick={() => setModalOpen(true)}>Send Batch Notification</Button> : null}
      />
      <Card sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Tabs value={tab} onChange={(_, v) => setTab(v)}>
            <Tab value="all" label="All" />
            <Tab value="unread" label="Unread" />
            {canSend && <Tab value="sent" label="Sent by Me" />}
          </Tabs>
          {tab !== 'sent' && <Button size="small" onClick={markAllRead}>Mark all as read</Button>}
        </Box>
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
        ) : items.length === 0 ? (
          <Typography color="text.secondary" sx={{ p: 4, textAlign: 'center' }}>
            You&apos;re all caught up — no notifications here.
          </Typography>
        ) : (
          <List>
            {items.map((n) => (
              <ListItem
                key={n.id}
                divider
                button={tab !== 'sent'}
                onClick={() => tab !== 'sent' && !n.is_read && markOneRead(n.id)}
                sx={{ bgcolor: n.is_read ? 'transparent' : 'action.hover', borderRadius: 1 }}
              >
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: n.is_read ? 400 : 700 }}>
                        {n.title}
                      </Typography>
                      {n.batch_name && <Chip size="small" label={n.batch_name} variant="outlined" />}
                      {!n.is_read && tab !== 'sent' && <Chip size="small" color="error" label="New" sx={{ height: 20 }} />}
                    </Box>
                  }
                  secondary={
                    <>
                      <Typography variant="body2" color="text.primary">{n.message}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {[n.sender_name, timeAgo(n.created_at)].filter(Boolean).join(' • ')}
                      </Typography>
                    </>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </Card>
      <SendBatchNotificationModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSent={() => { setModalOpen(false); fetchList(tab); }}
      />
    </Box>
  );
};
