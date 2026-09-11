import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AppBar, Toolbar, Typography, IconButton, Box, Avatar, Menu, MenuItem,
  Chip, Tooltip, Divider, Badge, Popover, List, ListItem, ListItemText,
  Button, CircularProgress
} from '@mui/material';
import {
  Menu as MenuIcon, Brightness4, Brightness7, Notifications,
  ExitToApp, Person, Send
} from '@mui/icons-material';
import { useAuth, ROLES } from '../../context/AuthContext';
import api, { unwrapList, unwrapData } from '../../services/api';
import { SendBatchNotificationModal } from '../notifications/SendBatchNotificationModal';

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

export const Navbar = ({ onToggleSidebar }) => {
  const { user, activeRole, logout, themeMode, toggleTheme } = useAuth();
  const [anchorEl, setAnchorEl] = useState(null);
  const [notifAnchor, setNotifAnchor] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loadingNotifs, setLoadingNotifs] = useState(false);
  const [sendOpen, setSendOpen] = useState(false);
  const navigate = useNavigate();

  const canSend = [ROLES.SUPER_ADMIN, ROLES.BRANCH_ADMIN, ROLES.TEACHER].includes(activeRole);

  const fetchNotifications = useCallback(async () => {
    setLoadingNotifs(true);
    try {
      const [countRes, listRes] = await Promise.all([
        api.get('/communications/notifications/unread-count/').catch(() => null),
        api.get('/communications/notifications/').catch(() => null),
      ]);
      if (countRes) {
        const d = unwrapData(countRes) || countRes;
        setUnreadCount(d?.unread_count ?? 0);
      }
      if (listRes) {
        setNotifications(unwrapList(listRes).slice(0, 20));
        // Fallback: derive count from list if count endpoint unavailable
        if (!countRes) {
          setUnreadCount(unwrapList(listRes).filter((n) => !n.is_read).length);
        }
      }
    } catch { /* keep silent in navbar */ }
    finally {
      setLoadingNotifs(false);
    }
  }, []);

  useEffect(() => {
    if (!user) return;
    fetchNotifications();
    const id = setInterval(fetchNotifications, 60000);
    return () => clearInterval(id);
  }, [user, fetchNotifications]);

  const handleMenuOpen = (e) => setAnchorEl(e.currentTarget);
  const handleMenuClose = () => setAnchorEl(null);

  const handleNavigateProfile = () => {
    handleMenuClose();
    navigate('/profile');
  };

  const handleNotifOpen = (e) => {
    setNotifAnchor(e.currentTarget);
    fetchNotifications();
  };
  const handleNotifClose = () => setNotifAnchor(null);

  const handleMarkAllRead = async () => {
    try {
      await api.post('/communications/notifications/mark-all-read/');
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch { /* silent */ }
  };

  const handleNotifClick = async (notif) => {
    if (!notif.is_read) {
      try {
        await api.post(`/communications/notifications/${notif.id}/mark-read/`);
        setNotifications((prev) => prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n)));
        setUnreadCount((c) => Math.max(0, c - 1));
      } catch { /* silent */ }
    }
  };

  const roleLabels = {
    [ROLES.SUPER_ADMIN]: 'Super Admin',
    [ROLES.BRANCH_ADMIN]: 'Branch Admin',
    [ROLES.ADMISSION_COUNSELOR]: 'Admission Counselor',
    [ROLES.TEACHER]: 'Teacher',
    [ROLES.STUDENT]: 'Student',
    [ROLES.PARENT]: 'Parent',
    [ROLES.ACCOUNTANT]: 'Accountant',
    [ROLES.RECEPTIONIST]: 'Receptionist',
  };

  const avatarUrl = user?.profile_photo_url || user?.profile_picture;
  const displayRole = user?.role_code || activeRole;
  const notifOpen = Boolean(notifAnchor);

  return (
    <AppBar position="sticky" elevation={0} sx={{ borderBottom: '1px solid rgba(255,255,255,0.08)', backdropFilter: 'blur(10px)', backgroundColor: 'background.paper' }}>
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton edge="start" onClick={onToggleSidebar} color="inherit">
            <MenuIcon />
          </IconButton>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'pointer' }} onClick={() => navigate('/')}>
            <Box sx={{ width: 36, height: 36, borderRadius: 2, background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800 }}>
              GT
            </Box>
            <Typography variant="h6" sx={{ fontWeight: 800, background: 'linear-gradient(135deg, #6366F1 0%, #34D399 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', display: { xs: 'none', sm: 'block' } }}>
              GRAPHICS TECHNOLOGY CRM
            </Typography>
          </Box>
          <Chip label={user?.branch_name || "Main Branch"} color="primary" variant="outlined" size="small" sx={{ borderRadius: 2, ml: 1 }} />
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Tooltip title="Toggle Dark/Light Mode">
            <IconButton onClick={toggleTheme} color="inherit">
              {themeMode === 'dark' ? <Brightness7 /> : <Brightness4 />}
            </IconButton>
          </Tooltip>

          <IconButton color="inherit" onClick={handleNotifOpen}>
            <Badge badgeContent={unreadCount} color="error">
              <Notifications />
            </Badge>
          </IconButton>
          <Popover
            open={notifOpen}
            anchorEl={notifAnchor}
            onClose={handleNotifClose}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
            PaperProps={{ sx: { width: 380, maxHeight: 520 } }}
          >
            <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                Notifications {unreadCount > 0 && `(${unreadCount})`}
              </Typography>
              <Button size="small" onClick={handleMarkAllRead} disabled={unreadCount === 0}>
                Mark all as read
              </Button>
            </Box>
            {canSend && (
              <Box sx={{ px: 2, pb: 1 }}>
                <Button
                  fullWidth
                  variant="contained"
                  startIcon={<Send />}
                  onClick={() => { handleNotifClose(); setSendOpen(true); }}
                >
                  Send Batch Notification
                </Button>
              </Box>
            )}
            <Divider />
            {loadingNotifs ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress size={24} /></Box>
            ) : notifications.length === 0 ? (
              <Typography color="text.secondary" sx={{ p: 3, textAlign: 'center' }}>
                You&apos;re all caught up — no notifications.
              </Typography>
            ) : (
              <List sx={{ maxHeight: 340, overflow: 'auto' }}>
                {notifications.map((n) => (
                  <ListItem
                    key={n.id}
                    divider
                    button
                    onClick={() => handleNotifClick(n)}
                    sx={{ bgcolor: n.is_read ? 'transparent' : 'action.hover' }}
                  >
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                          {!n.is_read && <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'error.main' }} />}
                          <Typography variant="body2" sx={{ fontWeight: n.is_read ? 400 : 700 }}>
                            {n.title}
                          </Typography>
                          {n.batch_name && <Chip size="small" label={n.batch_name} variant="outlined" sx={{ height: 20 }} />}
                        </Box>
                      }
                      secondary={
                        <Typography variant="caption" color="text.secondary">
                          {[n.sender_name, timeAgo(n.created_at)].filter(Boolean).join(' • ')}
                        </Typography>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            )}
            <Box sx={{ p: 1, textAlign: 'center' }}>
              <Button size="small" onClick={() => { handleNotifClose(); navigate('/notifications'); }}>
                View all
              </Button>
            </Box>
          </Popover>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, cursor: 'pointer' }} onClick={handleMenuOpen}>
            <Avatar
              src={avatarUrl}
              sx={{
                bgcolor: 'primary.main',
                width: 36,
                height: 36,
                border: '2px solid',
                borderColor: 'primary.light',
                fontWeight: 700,
              }}
            >
              {user?.first_name ? user.first_name[0] : 'U'}
            </Avatar>
            <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
              <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
                {user?.first_name || 'User'} {user?.last_name || ''}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {roleLabels[displayRole] || 'Staff'}
              </Typography>
            </Box>
          </Box>

          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleMenuClose} sx={{ mt: 1 }}>
            <MenuItem onClick={handleNavigateProfile}>
              <Person sx={{ mr: 1.5, fontSize: 20 }} /> My Profile
            </MenuItem>
            <Divider />
            <MenuItem onClick={logout} sx={{ color: 'error.main' }}>
              <ExitToApp sx={{ mr: 1.5, fontSize: 20 }} /> Logout
            </MenuItem>
          </Menu>
        </Box>
      </Toolbar>
      <SendBatchNotificationModal
        open={sendOpen}
        onClose={() => setSendOpen(false)}
        onSent={fetchNotifications}
      />
    </AppBar>
  );
};
