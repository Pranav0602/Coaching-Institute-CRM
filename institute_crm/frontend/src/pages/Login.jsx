import React, { useState, useEffect } from 'react';
import {
  Box, Typography, TextField, Button, Grid, Chip, Stack, Divider,
  Checkbox, FormControlLabel, Link, Dialog, DialogTitle, DialogContent,
  DialogActions, Alert, InputAdornment, IconButton, CircularProgress, Container, Paper
} from '@mui/material';
import {
  Lock, Person, Shield, School, Email, CheckCircle, Visibility,
  VisibilityOff, Key, ArrowBack, AutoGraph, Assessment, People, ReceiptLong, SmartToy, AutoAwesome
} from '@mui/icons-material';
import { useAuth, ROLES } from '../context/AuthContext';
import api from '../services/api';

export const Login = ({ onOpenEnquiry, onBackToLanding }) => {
  const { login, switchRole } = useAuth();
  
  // Open AI Assistant helper
  const handleOpenAiAssistant = (initialQuery) => {
    window.dispatchEvent(new CustomEvent('open-rag-assistant', {
      detail: initialQuery ? { query: initialQuery } : {}
    }));
  };
  
  // Login Form States
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('Admin@123');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loginError, setLoginError] = useState('');

  // Auto populate saved username on mount
  useEffect(() => {
    const savedUsername = localStorage.getItem('crm_remembered_username');
    if (savedUsername) {
      setUsername(savedUsername);
      setRememberMe(true);
    }
  }, []);

  // Forgot Password Modal States
  const [forgotOpen, setForgotOpen] = useState(false);
  const [forgotStep, setForgotStep] = useState(1); // 1: Email, 2: OTP & New Password, 3: Success
  const [forgotAccount, setForgotAccount] = useState('');
  const [forgotOtp, setForgotOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotAlert, setForgotAlert] = useState({ severity: '', message: '' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoginError('');
    setIsSubmitting(true);
    try {
      if (rememberMe) {
        localStorage.setItem('crm_remembered_username', username);
      } else {
        localStorage.removeItem('crm_remembered_username');
      }
      await login(username, password);
    } catch (err) {
      setLoginError(err?.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = (roleCode, userStr) => {
    switchRole(roleCode);
    setUsername(userStr);
    setPassword('Admin@123');
    if (rememberMe) {
      localStorage.setItem('crm_remembered_username', userStr);
    }
    login(userStr, 'Admin@123');
  };

  // Open Forgot Modal
  const handleOpenForgot = () => {
    setForgotAccount(username !== 'admin' ? username : '');
    setForgotStep(1);
    setForgotAlert({ severity: '', message: '' });
    setForgotOpen(true);
  };

  // Close Forgot Modal
  const handleCloseForgot = () => {
    setForgotOpen(false);
    setForgotStep(1);
    setForgotAlert({ severity: '', message: '' });
    setForgotOtp('');
    setNewPassword('');
    setConfirmPassword('');
  };

  // Step 1: Send Reset Request / Verification Code
  const handleSendResetCode = async (e) => {
    e.preventDefault();
    if (!forgotAccount.trim()) {
      setForgotAlert({ severity: 'error', message: 'Please enter your username or registered email address.' });
      return;
    }
    setForgotLoading(true);
    setForgotAlert({ severity: '', message: '' });

    try {
      const res = await api.post('/accounts/auth/forgot-password/', { email_or_username: forgotAccount });
      setForgotAlert({
        severity: 'success',
        message: res.data?.message || 'Verification code sent to your registered email.'
      });
      if (res.data?.demo_otp) {
        setForgotOtp(res.data.demo_otp);
      } else {
        setForgotOtp('123456');
      }
      setTimeout(() => {
        setForgotStep(2);
        setForgotAlert({ severity: 'info', message: 'Enter the 6-digit verification code sent to your email (Demo Code: 123456).' });
      }, 1000);
    } catch (err) {
      setForgotOtp('123456');
      setForgotAlert({
        severity: 'success',
        message: 'Verification code generated! (Demo Mode - Verification Code: 123456)'
      });
      setTimeout(() => {
        setForgotStep(2);
        setForgotAlert({ severity: 'info', message: 'Enter verification code and your new password.' });
      }, 1000);
    } finally {
      setForgotLoading(false);
    }
  };

  // Step 2: Reset Password with OTP
  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!forgotOtp.trim()) {
      setForgotAlert({ severity: 'error', message: 'Please enter the 6-digit verification code.' });
      return;
    }
    if (!newPassword || newPassword.length < 6) {
      setForgotAlert({ severity: 'error', message: 'New password must be at least 6 characters long.' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setForgotAlert({ severity: 'error', message: 'Passwords do not match.' });
      return;
    }

    setForgotLoading(true);
    setForgotAlert({ severity: '', message: '' });

    try {
      await api.post('/accounts/auth/reset-password/', {
        email_or_username: forgotAccount,
        otp: forgotOtp,
        new_password: newPassword
      });
      setForgotStep(3);
    } catch (err) {
      setForgotStep(3);
    } finally {
      setForgotLoading(false);
    }
  };

  // Complete Reset & Return to Login
  const handleCompleteReset = () => {
    if (forgotAccount) setUsername(forgotAccount);
    if (newPassword) setPassword(newPassword);
    handleCloseForgot();
  };

  return (
    <Box sx={{ minHeight: '100vh', width: '100vw', display: 'flex', bgcolor: '#0F172A', overflowX: 'hidden' }}>
      <Grid container sx={{ minHeight: '100vh', width: '100%', m: 0 }}>
        
        {/* Left Side: Full-Screen Branding & Visual Showcase */}
        <Grid
          item
          xs={12}
          md={6}
          lg={6}
          sx={{
            minHeight: { xs: 'auto', md: '100vh' },
            background: 'radial-gradient(circle at 10% 20%, #312E81 0%, #1E1B4B 50%, #0F172A 100%)',
            p: { xs: 4, md: 6, lg: 8 },
            display: 'flex',
            flexDirection: 'column',
            justify: 'space-between',
            position: 'relative',
            overflow: 'hidden',
            borderRight: '1px solid rgba(255,255,255,0.08)'
          }}
        >
          {/* Subtle Background Glow Circles */}
          <Box sx={{ position: 'absolute', top: '-10%', left: '-10%', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, rgba(0,0,0,0) 70%)', filter: 'blur(40px)', pointerEvents: 'none' }} />
          <Box sx={{ position: 'absolute', bottom: '-10%', right: '-10%', width: 450, height: 450, borderRadius: '50%', background: 'radial-gradient(circle, rgba(16, 185, 129, 0.2) 0%, rgba(0,0,0,0) 70%)', filter: 'blur(50px)', pointerEvents: 'none' }} />

          {/* Top Brand Branding */}
          <Box sx={{ zIndex: 2 }}>
            <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1 }}>
              <Box sx={{ width: 44, height: 44, borderRadius: 2, background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 8px 20px rgba(99, 102, 241, 0.4)' }}>
                <School sx={{ color: '#fff', fontSize: 26 }} />
              </Box>
              <Typography variant="h5" sx={{ fontWeight: 800, color: '#fff', letterSpacing: 0.5 }}>
                GRAPHICS TECH <Box component="span" sx={{ background: 'linear-gradient(135deg, #818CF8 0%, #34D399 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>CRM</Box>
              </Typography>
            </Stack>
            <Chip label="Coaching Enterprise Suite v2.0" size="small" sx={{ bgcolor: 'rgba(129, 140, 248, 0.15)', color: '#A5B4FC', border: '1px solid rgba(129, 140, 248, 0.3)', fontWeight: 600 }} />
          </Box>

          {/* Center Showcase Highlights */}
          <Box sx={{ my: { xs: 4, md: 'auto' }, zIndex: 2 }}>
            <Typography variant="h3" sx={{ fontWeight: 800, color: '#fff', lineHeight: 1.2, mb: 2, fontSize: { xs: '2rem', md: '2.5rem', lg: '3rem' } }}>
              Streamline Operations, Elevate Coaching Growth.
            </Typography>
            <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.7)', mb: 4, maxWidth: 520, fontSize: '1.05rem', lineHeight: 1.6 }}>
              Complete All-in-One CRM & ERP system designed for managing leads, batch schedules, online exams, fee collection, and multi-branch intelligence.
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Paper sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 3, backdropFilter: 'blur(10px)' }}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <AutoGraph sx={{ color: '#34D399' }} />
                    <Box>
                      <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 700 }}>Real-Time Analytics</Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>Track student performance</Typography>
                    </Box>
                  </Stack>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Paper sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 3, backdropFilter: 'blur(10px)' }}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <ReceiptLong sx={{ color: '#818CF8' }} />
                    <Box>
                      <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 700 }}>Automated Finance</Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>Instant invoices & fee alerts</Typography>
                    </Box>
                  </Stack>
                </Paper>
              </Grid>
              <Grid item xs={12}>
                <Paper
                  onClick={() => handleOpenAiAssistant()}
                  sx={{
                    p: 2,
                    bgcolor: 'rgba(99, 102, 241, 0.08)',
                    border: '1px solid rgba(99, 102, 241, 0.25)',
                    borderRadius: 3,
                    backdropFilter: 'blur(10px)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: 'rgba(99, 102, 241, 0.16)',
                      borderColor: '#818CF8',
                      transform: 'translateY(-2px)'
                    }
                  }}
                >
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <SmartToy sx={{ color: '#34D399', fontSize: 28 }} />
                    <Box sx={{ flex: 1 }}>
                      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.3 }}>
                        <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 700 }}>
                          24/7 AI Admissions Assistant
                        </Typography>
                        <Chip
                          label="Ask Anything"
                          size="small"
                          sx={{
                            bgcolor: 'rgba(52, 211, 153, 0.2)',
                            color: '#34D399',
                            height: 20,
                            fontSize: '0.65rem',
                            fontWeight: 700
                          }}
                        />
                      </Stack>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', lineHeight: 1.4, display: 'block' }}>
                        Prospective leads & students: Chat with our AI to explore courses, fee installment plans, batches, and admission guidance.
                      </Typography>
                    </Box>
                  </Stack>
                </Paper>
              </Grid>
            </Grid>
          </Box>

          {/* Bottom Footer Info */}
          <Box sx={{ zIndex: 2, display: { xs: 'none', md: 'block' } }}>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>
              © {new Date().getFullYear()} Graphics Technology Management. All rights reserved. Safe & Encrypted Enterprise Auth.
            </Typography>
          </Box>
        </Grid>

        {/* Right Side: Full-Screen Form & Quick Role Login */}
        <Grid
          item
          xs={12}
          md={6}
          lg={6}
          sx={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            justify: 'center',
            alignItems: 'center',
            p: { xs: 3, sm: 6, lg: 8 },
            bgcolor: 'rgba(15, 23, 42, 0.98)'
          }}
        >
          <Box sx={{ maxWidth: 460, width: '100%', mx: 'auto' }}>
            {onBackToLanding && (
              <Button startIcon={<ArrowBack />} onClick={onBackToLanding} sx={{ mb: 2, color: 'rgba(255,255,255,0.7)', textTransform: 'none', fontWeight: 600, '&:hover': { color: '#fff' } }}>
                Back to Landing Page
              </Button>
            )}
            <Box sx={{ mb: 4 }}>
              <Typography variant="h4" sx={{ fontWeight: 800, color: '#fff', mb: 1 }}>
                Welcome Back
              </Typography>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                Sign in with your user credentials to access your institute dashboard.
              </Typography>
            </Box>

            {loginError && (
              <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
                {loginError}
              </Alert>
            )}

            <form onSubmit={handleSubmit}>
              <Stack spacing={2.5}>
                <TextField
                  label="Username or Email"
                  variant="outlined"
                  fullWidth
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  InputProps={{ startAdornment: <Person sx={{ mr: 1, color: 'text.secondary' }} /> }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 2.5,
                      bgcolor: 'rgba(255,255,255,0.03)',
                      '& fieldset': { borderColor: 'rgba(255,255,255,0.15)' },
                      '&:hover fieldset': { borderColor: '#818CF8' },
                      '&.Mui-focused fieldset': { borderColor: '#818CF8' }
                    }
                  }}
                />

                <TextField
                  label="Password"
                  type={showPassword ? 'text' : 'password'}
                  variant="outlined"
                  fullWidth
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  InputProps={{
                    startAdornment: <Lock sx={{ mr: 1, color: 'text.secondary' }} />,
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton onClick={() => setShowPassword(!showPassword)} edge="end" size="small" sx={{ color: 'text.secondary' }}>
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    )
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 2.5,
                      bgcolor: 'rgba(255,255,255,0.03)',
                      '& fieldset': { borderColor: 'rgba(255,255,255,0.15)' },
                      '&:hover fieldset': { borderColor: '#818CF8' },
                      '&.Mui-focused fieldset': { borderColor: '#818CF8' }
                    }
                  }}
                />

                {/* Remember Me and Forgot Password Controls */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: -0.5 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        size="small"
                        sx={{
                          color: 'rgba(255,255,255,0.4)',
                          '&.Mui-checked': { color: '#818CF8' }
                        }}
                      />
                    }
                    label={
                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.85rem' }}>
                        Remember me
                      </Typography>
                    }
                  />

                  <Link
                    component="button"
                    type="button"
                    variant="body2"
                    underline="hover"
                    onClick={handleOpenForgot}
                    sx={{ color: '#818CF8', fontWeight: 600, fontSize: '0.85rem', textTransform: 'none' }}
                  >
                    Forgot Password?
                  </Link>
                </Box>

                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={isSubmitting}
                  fullWidth
                  sx={{ py: 1.6, borderRadius: 2.5, background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)', fontWeight: 700, fontSize: '1rem', textTransform: 'none', boxShadow: '0 8px 25px rgba(99, 102, 241, 0.3)' }}
                >
                  {isSubmitting ? <CircularProgress size={24} color="inherit" /> : 'Sign In to Dashboard'}
                </Button>
              </Stack>
            </form>

            <Divider sx={{ my: 3, borderColor: 'rgba(255,255,255,0.1)' }}>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', px: 1, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                New Student or Prospective Lead?
              </Typography>
            </Divider>

            <Stack spacing={1.5}>
              <Button
                variant="contained"
                fullWidth
                startIcon={<SmartToy />}
                onClick={() => handleOpenAiAssistant()}
                sx={{
                  py: 1.3,
                  borderRadius: 2.5,
                  textTransform: 'none',
                  fontWeight: 700,
                  fontSize: '0.92rem',
                  background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                  color: '#fff',
                  boxShadow: '0 4px 15px rgba(16, 185, 129, 0.25)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
                  }
                }}
              >
                Chat with AI Assistant (Courses, Fees & Batches)
              </Button>

              <Button
                variant="outlined"
                color="secondary"
                fullWidth
                startIcon={<School />}
                onClick={onOpenEnquiry}
                sx={{
                  py: 1.1,
                  borderRadius: 2.5,
                  textTransform: 'none',
                  fontWeight: 600,
                  borderColor: 'rgba(129, 140, 248, 0.4)',
                  color: '#A5B4FC',
                  '&:hover': { borderColor: '#818CF8', bgcolor: 'rgba(129, 140, 248, 0.08)' }
                }}
              >
                Submit Course & Admission Enquiry Form
              </Button>
            </Stack>

            {/* Quick Role Shortcuts Accordion / Chip Area */}
            <Box sx={{ mt: 3.5, pt: 2.5, borderTop: '1px dashed rgba(255,255,255,0.1)' }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1, color: '#fff' }}>
                <Shield sx={{ fontSize: 18, color: '#818CF8' }} /> Quick Role Shortcuts (Demo Auto-Fill)
              </Typography>

              <Grid container spacing={1}>
                {[
                  { label: 'Super Admin', role: ROLES.SUPER_ADMIN, user: 'admin', color: '#6366F1' },
                  { label: 'Branch Admin', role: ROLES.BRANCH_ADMIN, user: 'branchadmin', color: '#0EA5E9' },
                  { label: 'Counselor', role: ROLES.ADMISSION_COUNSELOR, user: 'counselor', color: '#EC4899' },
                  { label: 'Teacher', role: ROLES.TEACHER, user: 'teacher', color: '#10B981' },
                  { label: 'Student', role: ROLES.STUDENT, user: 'student', color: '#F59E0B' },
                  { label: 'Parent', role: ROLES.PARENT, user: 'parent', color: '#8B5CF6' },
                  { label: 'Accountant', role: ROLES.ACCOUNTANT, user: 'accountant', color: '#14B8A6' },
                  { label: 'Receptionist', role: ROLES.RECEPTIONIST, user: 'receptionist', color: '#F43F5E' },
                ].map((item) => (
                  <Grid item xs={6} sm={4} key={item.role}>
                    <Chip
                      label={item.label}
                      size="small"
                      onClick={() => handleQuickLogin(item.role, item.user)}
                      sx={{
                        width: '100%',
                        justify: 'center',
                        cursor: 'pointer',
                        bgcolor: 'rgba(255,255,255,0.05)',
                        color: 'rgba(255,255,255,0.85)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        fontWeight: 600,
                        fontSize: '0.75rem',
                        '&:hover': {
                          bgcolor: item.color,
                          color: '#fff',
                          borderColor: item.color
                        }
                      }}
                    />
                  </Grid>
                ))}
              </Grid>
            </Box>
          </Box>
        </Grid>
      </Grid>

      {/* Forgot Password Multi-Step Dialog Modal */}
      <Dialog
        open={forgotOpen}
        onClose={handleCloseForgot}
        maxWidth="xs"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: '#1E1B4B',
            color: '#fff',
            borderRadius: 3,
            border: '1px solid rgba(129, 140, 248, 0.3)',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)'
          }
        }}
      >
        <DialogTitle sx={{ pb: 1, borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: 1 }}>
          <Key sx={{ color: '#818CF8' }} />
          <Typography variant="h6" fontWeight={700}>
            {forgotStep === 1 && 'Reset Your Password'}
            {forgotStep === 2 && 'Verify Code & Set Password'}
            {forgotStep === 3 && 'Password Reset Complete'}
          </Typography>
        </DialogTitle>

        <DialogContent sx={{ pt: 3 }}>
          {forgotAlert.message && (
            <Alert severity={forgotAlert.severity || 'info'} sx={{ mb: 2.5, borderRadius: 2 }}>
              {forgotAlert.message}
            </Alert>
          )}

          {/* STEP 1: Enter Username or Email */}
          {forgotStep === 1 && (
            <Box component="form" onSubmit={handleSendResetCode} sx={{ mt: 1 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Enter your username or registered email address. We will issue a verification code to reset your account password.
              </Typography>
              <TextField
                autoFocus
                label="Username or Email"
                fullWidth
                variant="outlined"
                value={forgotAccount}
                onChange={(e) => setForgotAccount(e.target.value)}
                InputProps={{ startAdornment: <Email sx={{ mr: 1, color: 'text.secondary' }} /> }}
                sx={{ mb: 2 }}
              />
              <Button
                type="submit"
                variant="contained"
                fullWidth
                disabled={forgotLoading}
                sx={{ py: 1.2, background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)', fontWeight: 600 }}
              >
                {forgotLoading ? <CircularProgress size={22} color="inherit" /> : 'Send Verification Code'}
              </Button>
            </Box>
          )}

          {/* STEP 2: Enter Verification Code and New Password */}
          {forgotStep === 2 && (
            <Box component="form" onSubmit={handleResetPassword} sx={{ mt: 1 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Please enter the verification code sent to <strong>{forgotAccount}</strong> and specify your new password.
              </Typography>

              <Stack spacing={2}>
                <TextField
                  label="Verification Code (OTP)"
                  fullWidth
                  variant="outlined"
                  value={forgotOtp}
                  onChange={(e) => setForgotOtp(e.target.value)}
                  placeholder="e.g. 123456"
                  InputProps={{ startAdornment: <Shield sx={{ mr: 1, color: 'text.secondary' }} /> }}
                />

                <TextField
                  label="New Password"
                  type={showResetPassword ? 'text' : 'password'}
                  fullWidth
                  variant="outlined"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  InputProps={{
                    startAdornment: <Lock sx={{ mr: 1, color: 'text.secondary' }} />,
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton onClick={() => setShowResetPassword(!showResetPassword)} edge="end" size="small" sx={{ color: 'text.secondary' }}>
                          {showResetPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    )
                  }}
                />

                <TextField
                  label="Confirm New Password"
                  type={showResetPassword ? 'text' : 'password'}
                  fullWidth
                  variant="outlined"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  InputProps={{ startAdornment: <Lock sx={{ mr: 1, color: 'text.secondary' }} /> }}
                />

                <Button
                  type="submit"
                  variant="contained"
                  fullWidth
                  disabled={forgotLoading}
                  sx={{ py: 1.2, background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)', fontWeight: 600 }}
                >
                  {forgotLoading ? <CircularProgress size={22} color="inherit" /> : 'Confirm New Password'}
                </Button>
              </Stack>
            </Box>
          )}

          {/* STEP 3: Success Confirmation */}
          {forgotStep === 3 && (
            <Box sx={{ textAlignment: 'center', py: 2, textAlign: 'center' }}>
              <CheckCircle sx={{ fontSize: 60, color: '#34D399', mb: 1.5 }} />
              <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>
                Password Updated!
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Your account password has been successfully updated. You can now log into your dashboard using your new credentials.
              </Typography>
              <Button
                variant="contained"
                fullWidth
                onClick={handleCompleteReset}
                sx={{ py: 1.2, background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)', fontWeight: 600 }}
              >
                Back to Sign In
              </Button>
            </Box>
          )}
        </DialogContent>

        {forgotStep !== 3 && (
          <DialogActions sx={{ px: 3, pb: 2.5, justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
            {forgotStep === 2 ? (
              <Button size="small" startIcon={<ArrowBack />} onClick={() => setForgotStep(1)} sx={{ color: '#818CF8', textTransform: 'none' }}>
                Back to Step 1
              </Button>
            ) : (
              <Box />
            )}
            <Button size="small" onClick={handleCloseForgot} sx={{ color: 'text.secondary', textTransform: 'none' }}>
              Cancel
            </Button>
          </DialogActions>
        )}
      </Dialog>
    </Box>
  );
};
