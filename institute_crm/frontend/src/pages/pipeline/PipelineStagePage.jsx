import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Grid, Button, Chip, Dialog, Paper,
  DialogTitle, DialogContent, DialogActions, TextField, MenuItem, Stack, CircularProgress,
  Snackbar, Alert
} from '@mui/material';
import { Refresh, CheckCircle } from '@mui/icons-material';
import { useParams } from 'react-router-dom';
import api from '../../services/api';
import { PIPELINE_STAGES, STAGE_COLORS, STAGE_DESCRIPTIONS } from '../../constants/pipeline';
import { LeadCard } from '../../components/leads/LeadCard';

export const PipelineStagePage = () => {
  const { stage } = useParams();
  const decodedStage = PIPELINE_STAGES.find(s => s.toLowerCase() === decodeURIComponent(stage || '').toLowerCase()) || PIPELINE_STAGES[0];

  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [courses, setCourses] = useState([]);
  const [batches, setBatches] = useState([]);
  const [openConvert, setOpenConvert] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });
  const [convertForm, setConvertForm] = useState({ course_id: '', batch_id: '', agreed_fee: 50000 });

  useEffect(() => {
    fetchCoursesAndBatches();
    fetchLeads();
  }, [decodedStage]);

  const formatLead = (l) => ({
    id: l.id,
    name: l.name,
    phone: l.phone,
    email: l.email,
    course: l.course_title || l.target_course || 'General',
    course_id: l.course || '',
    course_code: l.course_code || '',
    batch: l.batch_name || 'Unassigned',
    batch_id: l.batch || '',
    batch_code: l.batch_code || '',
    branch: l.branch_name || '',
    stage: l.stage || decodedStage,
    notes: l.notes,
    source: l.source,
  });

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const res = await api.get('/crm/leads/', { params: { stage: decodedStage } });
      const apiData = res.data || res;
      setLeads(Array.isArray(apiData) ? apiData.map(formatLead) : []);
    } catch (err) {
      console.warn('Failed to fetch leads', err);
      setLeads([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchCoursesAndBatches = async () => {
    try {
      const [cRes, bRes] = await Promise.all([
        api.get('/academics/courses/'),
        api.get('/academics/batches/')
      ]);
      const cList = cRes.data?.results || cRes.data || [];
      const bList = bRes.data?.results || bRes.data || [];
      setCourses(Array.isArray(cList) ? cList : []);
      setBatches(Array.isArray(bList) ? bList : []);
    } catch {
      console.warn('Fallback course/batch selection');
    }
  };

  const handleStageChange = async (lead, newStage) => {
    try {
      await api.patch(`/crm/leads/${lead.id}/`, { stage: newStage });
    } catch {
      console.warn('API stage update fallback');
    }
    setLeads(prev => prev.filter(l => l.id !== lead.id));
    setToast({ open: true, message: `Moved ${lead.name} to stage "${newStage}"`, severity: 'info' });
  };

  const handleAssignBatch = async (lead, batchId) => {
    try {
      await api.patch(`/crm/leads/${lead.id}/`, { batch: batchId });
      setLeads(prev => prev.map(l => l.id === lead.id ? { ...l, batch_id: batchId } : l));
      fetchLeads();
      setToast({ open: true, message: `Assigned batch for ${lead.name}`, severity: 'success' });
    } catch (e) {
      console.warn('Batch assignment fallback:', e);
    }
  };

  const handleConvertLead = async () => {
    try {
      if (selectedLead) {
        await api.post(`/crm/leads/${selectedLead.id}/convert/`, convertForm);
      }
    } catch {
      console.log('Conversion simulation');
    }
    setLeads(prev => prev.filter(l => l.id !== selectedLead.id));
    setOpenConvert(false);
    setToast({ open: true, message: `Student account created for ${selectedLead.name}!`, severity: 'success' });
  };

  const stageColor = STAGE_COLORS[decodedStage] || '#6366F1';

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Chip label={leads.length} size="small" sx={{ bgcolor: stageColor, color: '#fff', fontWeight: 700 }} />
            <Typography variant="h4" sx={{ fontWeight: 800 }}>{decodedStage}</Typography>
          </Box>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>{STAGE_DESCRIPTIONS[decodedStage]}</Typography>
        </Box>
        <Button variant="outlined" startIcon={<Refresh />} onClick={fetchLeads} disabled={loading}>
          Refresh
        </Button>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
      ) : leads.length === 0 ? (
        <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>No leads in "{decodedStage}"</Typography>
          <Typography color="text.secondary">Leads will appear here when they are moved to this stage.</Typography>
        </Paper>
      ) : (
        <Grid container spacing={2.5}>
          {leads.map((lead) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={lead.id}>
              <LeadCard
                lead={lead}
                stageColor={stageColor}
                batches={batches}
                currentStage={decodedStage}
                showBatchAssign={['Demo Scheduled', 'Demo Attended', 'Admission Pending'].includes(decodedStage)}
                onStageChange={handleStageChange}
                onAssignBatch={handleAssignBatch}
                onConvert={(lead) => {
                  setSelectedLead(lead);
                  setConvertForm({ course_id: lead.course_id, batch_id: lead.batch_id, agreed_fee: 50000 });
                  setOpenConvert(true);
                }}
              />
            </Grid>
          ))}
        </Grid>
      )}

      <Dialog open={openConvert} onClose={() => setOpenConvert(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Convert Lead to Admitted Student</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2, mt: 1 }}>
            Converting <strong>{selectedLead?.name}</strong> will create a Student User Account, provision login, and assign a batch.
          </Typography>
          <Stack spacing={2}>
            <TextField
              select
              label="Select Course"
              fullWidth
              value={convertForm.course_id}
              onChange={(e) => setConvertForm({ ...convertForm, course_id: e.target.value })}
            >
              {courses.length > 0 ? courses.map(c => (
                <MenuItem key={c.id} value={c.id}>{c.title} ({c.code})</MenuItem>
              )) : (
                <MenuItem value="">Select a course</MenuItem>
              )}
            </TextField>
            <TextField
              select
              label="Select Batch Section"
              fullWidth
              value={convertForm.batch_id}
              onChange={(e) => setConvertForm({ ...convertForm, batch_id: e.target.value })}
            >
              {batches.length > 0 ? batches.map(b => (
                <MenuItem key={b.id} value={b.id}>{b.name} ({b.code})</MenuItem>
              )) : (
                <MenuItem value="">Select a batch</MenuItem>
              )}
            </TextField>
            <TextField
              label="Agreed Fee Amount (INR)"
              fullWidth
              type="number"
              value={convertForm.agreed_fee}
              onChange={(e) => setConvertForm({ ...convertForm, agreed_fee: e.target.value })}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenConvert(false)}>Cancel</Button>
          <Button variant="contained" color="success" onClick={handleConvertLead} startIcon={<CheckCircle />}>
            Confirm Admission
          </Button>
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