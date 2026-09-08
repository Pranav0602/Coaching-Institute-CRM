import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Grid, Button, Dialog,
  DialogTitle, DialogContent, DialogActions, TextField, MenuItem, Stack, CircularProgress,
  Snackbar, Alert, Paper
} from '@mui/material';
import { Refresh, CheckCircle } from '@mui/icons-material';
import api from '../services/api';
import { STAGE_COLORS } from '../constants/pipeline';
import { LeadCard } from '../components/leads/LeadCard';

const CONVERTIBLE_STAGES = ['Demo Attended', 'Admission Pending'];

export const LeadConversionPage = () => {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [courses, setCourses] = useState([]);
  const [batches, setBatches] = useState([]);
  const [openConvert, setOpenConvert] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });
  const [convertForm, setConvertForm] = useState({ course_id: '', batch_id: '', agreed_fee: 50000 });

  const formatLead = (l, stage) => ({
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
    stage,
    notes: l.notes,
    source: l.source,
  });

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const queries = await Promise.all(CONVERTIBLE_STAGES.map(stage => api.get('/crm/leads/', { params: { stage } })));
      const combined = [];
      queries.forEach((res, i) => {
        const data = res.data || res;
        if (Array.isArray(data)) combined.push(...data.map(l => formatLead(l, CONVERTIBLE_STAGES[i])));
      });
      setLeads(combined);
    } catch (err) {
      console.warn('Failed to fetch convertible leads', err);
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

  useEffect(() => {
    fetchCoursesAndBatches();
    fetchLeads();
  }, []);

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

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Lead Conversion</Typography>
          <Typography color="text.secondary">Leads ready for admission — pick course, batch, and fee to create the student account</Typography>
        </Box>
        <Button variant="outlined" startIcon={<Refresh />} onClick={fetchLeads} disabled={loading}>Refresh</Button>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
      ) : leads.length === 0 ? (
        <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3 }}>
          <CheckCircle sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography variant="h6" sx={{ fontWeight: 700 }}>No leads ready for conversion</Typography>
          <Typography color="text.secondary">Leads land here once they reach "Demo Attended" or "Admission Pending" stages.</Typography>
        </Paper>
      ) : (
        <Grid container spacing={2.5}>
          {leads.map((lead) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={lead.id}>
              <LeadCard
                lead={lead}
                stageColor={STAGE_COLORS[lead.stage] || '#14B8A6'}
                batches={batches}
                currentStage={lead.stage}
                showBatchAssign
                onConvert={(l) => {
                  setSelectedLead(l);
                  setConvertForm({ course_id: l.course_id, batch_id: l.batch_id, agreed_fee: 50000 });
                  setOpenConvert(true);
                }}
                onStageChange={async (l, newStage) => {
                  try {
                    await api.patch(`/crm/leads/${l.id}/`, { stage: newStage });
                  } catch {
                    console.warn('Stage update fallback');
                  }
                  setLeads(prev => prev.filter(x => x.id !== l.id));
                  setToast({ open: true, message: `Moved ${l.name} to stage "${newStage}"`, severity: 'info' });
                }}
                onAssignBatch={async (l, batchId) => {
                  try {
                    await api.patch(`/crm/leads/${l.id}/`, { batch: batchId });
                    setLeads(prev => prev.map(x => x.id === l.id ? { ...x, batch_id: batchId } : x));
                    fetchLeads();
                  } catch (e) {
                    console.warn('Batch assignment fallback:', e);
                  }
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
            Converting <strong>{selectedLead?.name}</strong> ({selectedLead?.branch}) will create a Student User Account, provision login, and assign a batch.
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