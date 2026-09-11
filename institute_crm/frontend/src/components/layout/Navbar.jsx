import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AppBar, Toolbar, Typography, IconButton, Box, Avatar, Menu, MenuItem,
  Chip, Tooltip, Divider
} from '@mui/material';
import {
  Menu as MenuIcon, Brightness4, Brightness7, Notifications,
  ExitToApp, Person
} from '@mui/icons-material';
import { useAuth, ROLES } from '../../context/AuthContext';

export const Navbar = ({ onToggleSidebar }) => {
  const { user, activeRole, logout, themeMode, toggleTheme } = useAuth();
  const [anchorEl, setAnchorEl] = useState(null);
  const navigate = useNavigate();

  const handleMenuOpen = (e) => setAnchorEl(e.currentTarget);
  const handleMenuClose = () => setAnchorEl(null);

  const handleNavigateProfile = () => {
    handleMenuClose();
    navigate('/profile');
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
  // Production role display: always the server-assigned role, never switchable.
  const displayRole = user?.role_code || activeRole;

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

          <IconButton color="inherit">
            <Notifications />
          </IconButton>

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
    </AppBar>
  );
};
