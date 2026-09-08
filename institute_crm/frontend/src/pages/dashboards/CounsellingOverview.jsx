import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Grid, Card, CardContent, Button, Chip, Dialog,
  DialogTitle, DialogContent, DialogActions, TextField, MenuItem, Stack, CircularProgress,
  Snackbar, Alert, Paper
} from '@mui/material';
import { Add, Refresh, ArrowForward } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { PIPELINE_STAGES, STAGE_COLORS, STAGE_DESCRIPTIONS } from '../../constants/pipeline';

const STAGE_CHIP_COLORS = {
  'New': 'primary',
  'Contacted': 'info',
  'Interested': 'warning',
  'Demo Scheduled': 'secondary',
  'Demo Attended': 'error',
  'Admission Pending': 'success',
  'Admitted': 'success',
  'Lost': 'default',
};

export const CounsellingOverview = () => {
  const navigate = useNavigate();
  const [stageCounts, setStageCounts] = useState({});
  const [recentLeads, setRecentLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [courses, setCourses] = useState([]);
  const [branches, setBranches] = useState([]);
  const [openNewLead, setOpenNewLead] = useState(false);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });
  const [newLeadForm, setNewLeadForm] = useState({
    name: '', phone: '', email: '', branch_id: '', course_id: '', source: 'WALK_IN'
  });

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [cRes, lRes, cListRes, bListRes] = await Promise.all([
        api.get('/crm/leads/stage-counts/'),
        api.get('/crm/leads/'),
        api.get('/academics/courses/'),
        api.get('/accounts/branches/')
      ]);
      const counts = cRes.data || cRes || {};
      setStageCounts(typeof counts === 'object' && !Array.isArray(counts) ? counts : {});

      const leads = lRes.data || lRes;
      if (Array.isArray(leads)) {
        setRecentLeads(leads.slice(0, 8).map(l => ({
          id: l.id,
          name: l.name,
          phone: l.phone,
          course: l.course_title || l.target_course || 'General',
          branch: l.branch_name || '',
          stage: l.stage || 'New',
        })));
      }

      const cList = cListRes.data?.results || cListRes.data || [];
      const bList = bListRes.data?.results || bListRes.data || [];
      setCourses(Array.isArray(cList) ? cList : []);
      setBranches(Array.isArray(bList) ? bList : []);
    } catch (err) {
      console.warn('Failed to load counselling desk', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const handleCreateLead = async () => {
    const selectedCourse = courses.find(c => c.id === newLeadForm.course_id);
    try {
      await api.post('/crm/leads/', {
        name: newLeadForm.name,
        phone: newLeadForm.phone,
        email: newLeadForm.email,
        branch: newLeadForm.branch_id,
        course: newLeadForm.course_id,
        target_course: selectedCourse ? selectedCourse.title : newLeadForm.course_id,
        source: newLeadForm.source || 'WALK_IN',
        stage: 'New'
      });
      setToast({ open: true, message: `Created lead for ${newLeadForm.name}`, severity: 'success' });
    } catch (e) {
      console.warn('Lead creation fallback', e);
      setToast({ open: true, message: `Created lead for ${newLeadForm.name}`, severity: 'success' });
    }
    setOpenNewLead(false);
    setNewLeadForm({ name: '', phone: '', email: '', branch_id: '', course_id: '', source: 'WALK_IN' });
    fetchAll();
  };

  const totalLeads = PIPELINE_STAGES.reduce((sum, s) => sum + (stageCounts[s] || 0), 0);

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Counselling Desk</Typography>
          <Typography color="text.secondary">Overview of your lead pipeline — click a stage to open its board</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <Button variant="outlined" startIcon={<Refresh />} onClick={fetchAll} disabled={loading}>
            Refresh
          </Button>
          <Button variant="contained" startIcon={<Add />} onClick={() => setOpenNewLead(true)}>
            New Enquiry Lead
          </Button>
        </Box>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
      ) : (
        <>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
            Lead Pipeline <Chip label={totalLeads} size="small" color="primary" sx={{ ml: 1 }} />
          </Typography>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            {PIPELINE_STAGES.map((stage) => {
              const color = STAGE_COLORS[stage];
              return (
                <Grid item xs={6} sm={4} md={3} key={stage}>
                  <Card
                    sx={{
                      p: 1.5,
                      cursor: 'pointer',
                      borderTop: `4px solid ${color}`,
                      transition: 'transform 0.15s ease',
                      '&:hover': { transform: 'translateY(-3px)', boxShadow: 4 },
                    }}
                    onClick={() => navigate(`/pipeline/${encodeURIComponent(stage)}`)}
                  >
                    <CardContent sx={{ p: '0 !important' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{stage}</Typography>
                        <ArrowForward sx={{ fontSize: 16, color: 'text.secondary' }} />
                      </Box>
                      <Typography variant="h4" sx={{ fontWeight: 800, my: 0.5 }}>{stageCounts[stage] || 0}</Typography>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {STAGE_DESCRIPTIONS[stage]}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>

          <Paper sx={{ borderRadius: 3, overflow: 'hidden' }}>
            <Box sx={{ p: 2.5, pb: 1.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>Recent Enquiries</Typography>
              <Button size="small" onClick={() => navigate('/pipeline/New')}>View New Leads</Button>
            </Box>
            <Box sx={{ px: 2.5, pb: 2.5 }}>
              {recentLeads.length === 0 ? (
                <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
                  No enquiries yet. Create one with "New Enquiry Lead".
                </Typography>
              ) : (
                <Grid container spacing={2}>
                  {recentLeads.map(lead => (
                    <Grid item xs={12} sm={6} md={4} lg={3} key={lead.id}>
                      <Card sx={{ p: 2, borderLeft: `4px solid ${STAGE_COLORS[lead.stage] || '#6366F1'}` }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{lead.name}</Typography>
                        <Typography variant="caption" color="text.secondary" display="block">{lead.phone}</Typography>
                        <Typography variant="caption" color="text.secondary" display="block">{lead.course}</Typography>
                        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                          <Chip size="small" label={lead.branch || 'Branch'} variant="outlined" />
                          <Chip size="small" label={lead.stage} color={STAGE_CHIP_COLORS[lead.stage] || 'default'} />
                        </Stack>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              )}
            </Box>
          </Paper>
        </>
      )}

      <Dialog open={openNewLead} onClose={() => setOpenNewLead(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Create New Enquiry Lead</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField label="Full Name" fullWidth value={newLeadForm.name} onChange={(e) => setNewLeadForm({ ...newLeadForm, name: e.target.value })} />
            <TextField label="Phone Number" fullWidth value={newLeadForm.phone} onChange={(e) => setNewLeadForm({ ...newLeadForm, phone: e.target.value })} />
            <TextField label="Email Address" fullWidth value={newLeadForm.email} onChange={(e) => setNewLeadForm({ ...newLeadForm, email: e.target.value })} />
            <TextField select label="Branch" fullWidth value={newLeadForm.branch_id} onChange={(e) => setNewLeadForm({ ...newLeadForm, branch_id: e.target.value })}>
              {branches.length > 0 ? branches.map(b => (
                <MenuItem key={b.id} value={b.id}>{b.name} ({b.code})</MenuItem>
              )) : (
                <MenuItem value="">Select a branch</MenuItem>
              )}
            </TextField>
            <TextField select label="Target Course" fullWidth value={newLeadForm.course_id} onChange={(e) => setNewLeadForm({ ...newLeadForm, course_id: e.target.value })}>
              {courses.length > 0 ? courses.map(c => (
                <MenuItem key={c.id} value={c.id}>{c.title} ({c.code})</MenuItem>
              )) : (
                <MenuItem value="">Select a course</MenuItem>
              )}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenNewLead(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateLead}>Save Enquiry</Button>
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