import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog,
  DialogActions, DialogContent, DialogTitle, Grid, MenuItem, Paper, Snackbar,
  Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography,
} from '@mui/material';
import {
  Add, ArrowForward, MeetingRoom, PersonAdd, RecordVoiceOver, Refresh, School,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import api, { unwrapList } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { PIPELINE_STAGES, STAGE_COLORS, STAGE_DESCRIPTIONS } from '../../constants/pipeline';

const formatDateTime = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return value;
  }
};

export const ReceptionistDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [stageCounts, setStageCounts] = useState({});
  const [recentLeads, setRecentLeads] = useState([]);
  const [students, setStudents] = useState([]);
  const [followUps, setFollowUps] = useState([]);
  const [visitors, setVisitors] = useState([]);
  const [courses, setCourses] = useState([]);
  const [branches, setBranches] = useState([]);

  const [openVisitor, setOpenVisitor] = useState(false);
  const [openLead, setOpenLead] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });

  const [visitorForm, setVisitorForm] = useState({ visitor_name: '', phone: '', purpose: 'Admission Enquiry' });
  const [leadForm, setLeadForm] = useState({ name: '', phone: '', email: '', branch_id: '', course_id: '', source: 'WALK_IN' });

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [countRes, leadRes, studentRes, followRes, visitorRes, courseRes, branchRes] = await Promise.all([
        api.get('/crm/leads/stage-counts/').catch(() => ({ data: {} })),
        api.get('/crm/leads/').catch(() => ({ data: [] })),
        api.get('/accounts/users/', { params: { role: 'STUDENT' } }).catch(() => ({ data: [] })),
        api.get('/crm/follow-ups/').catch(() => ({ data: [] })),
        api.get('/crm/visitors/').catch(() => ({ data: [] })),
        api.get('/academics/courses/').catch(() => ({ data: [] })),
        api.get('/accounts/branches/').catch(() => ({ data: [] })),
      ]);

      const counts = countRes?.data ?? countRes ?? {};
      setStageCounts(counts && typeof counts === 'object' && !Array.isArray(counts) ? counts : {});
      setRecentLeads(unwrapList(leadRes).slice(0, 8));
      setStudents(unwrapList(studentRes));
      setFollowUps(unwrapList(followRes));
      setVisitors(unwrapList(visitorRes).slice(0, 8));
      setCourses(unwrapList(courseRes));
      setBranches(unwrapList(branchRes));
    } catch (err) {
      setToast({ open: true, message: err?.detail || 'Could not load the reception dashboard.', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const defaultBranch = user?.branch || '';
  const pendingFollowUps = followUps.filter((f) => f.status === 'PENDING').length;
  const todayVisitors = visitors.filter((v) => {
    if (!v.check_in) return false;
    return new Date(v.check_in).toDateString() === new Date().toDateString();
  }).length;
  const activeStudents = students.filter((s) => s.is_active !== false).length;
  const totalLeads = PIPELINE_STAGES.reduce((sum, stage) => sum + (stageCounts[stage] || 0), 0);

  const handleCreateVisitor = async () => {
    if (!visitorForm.visitor_name.trim() || !visitorForm.phone.trim()) {
      setToast({ open: true, message: 'Visitor name and phone are required.', severity: 'warning' });
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/crm/visitors/', {
        ...visitorForm,
        branch: defaultBranch || branches[0]?.id,
      });
      setToast({ open: true, message: 'Visitor checked in.', severity: 'success' });
      setOpenVisitor(false);
      setVisitorForm({ visitor_name: '', phone: '', purpose: 'Admission Enquiry' });
      fetchAll();
    } catch (err) {
      setToast({ open: true, message: err?.detail || 'Could not register the visitor.', severity: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateLead = async () => {
    if (!leadForm.name.trim() || !leadForm.phone.trim()) {
      setToast({ open: true, message: 'Name and phone are required.', severity: 'warning' });
      return;
    }
    const course = courses.find((c) => c.id === leadForm.course_id);
    setSubmitting(true);
    try {
      await api.post('/crm/leads/', {
        name: leadForm.name,
        phone: leadForm.phone,
        email: leadForm.email,
        branch: leadForm.branch_id || defaultBranch || branches[0]?.id,
        course: leadForm.course_id || undefined,
        target_course: course ? course.title : 'General',
        source: leadForm.source || 'WALK_IN',
        stage: 'New',
      });
      setToast({ open: true, message: `New enquiry created for ${leadForm.name}.`, severity: 'success' });
      setOpenLead(false);
      setLeadForm({ name: '', phone: '', email: '', branch_id: '', course_id: '', source: 'WALK_IN' });
      fetchAll();
    } catch (err) {
      setToast({ open: true, message: err?.detail || 'Could not create the enquiry.', severity: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Reception Desk</Typography>
          <Typography color="text.secondary">
            Lead pipeline, student onboarding and the student directory in one place.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1.5} sx={{ flexWrap: 'wrap' }}>
          <Button variant="outlined" startIcon={<MeetingRoom />} onClick={() => setOpenVisitor(true)}>
            Check-in Visitor
          </Button>
          <Button variant="outlined" startIcon={<RecordVoiceOver />} onClick={() => setOpenLead(true)}>
            New Lead Enquiry
          </Button>
          <Button variant="contained" startIcon={<PersonAdd />} onClick={() => navigate('/students?add=1')}>
            Add New Student
          </Button>
        </Stack>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
      ) : (
        <>
          <Grid container spacing={2.5} sx={{ mb: 3 }}>
            {[
              { label: 'Active Students', value: activeStudents, note: 'Across your branch', color: 'success.main' },
              { label: 'Open Leads', value: totalLeads, note: 'All pipeline stages', color: 'primary.main' },
              { label: 'Pending Follow-ups', value: pendingFollowUps, note: 'Awaiting contact', color: 'warning.main' },
              { label: "Today's Visitors", value: todayVisitors, note: 'Checked in today', color: 'info.main' },
            ].map((metric) => (
              <Grid item xs={12} sm={6} md={3} key={metric.label}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>{metric.label}</Typography>
                    <Typography variant="h4" sx={{ fontWeight: 800 }}>{metric.value}</Typography>
                    <Typography variant="caption" color={metric.color}>{metric.note}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          <Paper sx={{ p: 2.5, mb: 3, borderRadius: 3, borderLeft: '4px solid', borderLeftColor: 'secondary.main', display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <School color="secondary" />
            <Box sx={{ flex: 1, minWidth: 220 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Student Directory &amp; Profiles</Typography>
              <Typography variant="body2" color="text.secondary">
                Open any student to view personal, guardian, academic, attendance and fee details.
              </Typography>
            </Box>
            <Button variant="contained" color="secondary" onClick={() => navigate('/students')}>
              Open Directory
            </Button>
          </Paper>

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

          <Grid container spacing={2.5}>
            <Grid item xs={12} lg={6}>
              <Paper sx={{ borderRadius: 3, p: 2.5, height: '100%' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>Recent Enquiries</Typography>
                  <Button size="small" onClick={() => navigate('/pipeline/New')}>View New Leads</Button>
                </Box>
                {recentLeads.length === 0 ? (
                  <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
                    No enquiries yet. Use “New Lead Enquiry”.
                  </Typography>
                ) : (
                  <Stack spacing={1.5}>
                    {recentLeads.map((lead) => (
                      <Card key={lead.id} variant="outlined" sx={{ p: 1.5, borderLeft: `4px solid ${STAGE_COLORS[lead.stage] || '#6366F1'}` }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap' }}>
                          <Box>
                            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{lead.name}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {[lead.phone, lead.course_title || lead.target_course, lead.branch_name].filter(Boolean).join(' · ')}
                            </Typography>
                          </Box>
                          <Chip size="small" label={lead.stage} />
                        </Box>
                      </Card>
                    ))}
                  </Stack>
                )}
              </Paper>
            </Grid>

            <Grid item xs={12} lg={6}>
              <Paper sx={{ borderRadius: 3, p: 2.5, height: '100%' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>Today Visitor Log</Typography>
                  <Button size="small" startIcon={<Add />} onClick={() => setOpenVisitor(true)}>Check-in</Button>
                </Box>
                {visitors.length === 0 ? (
                  <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
                    No visitors registered yet.
                  </Typography>
                ) : (
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700 }}>Visitor</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Purpose</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Check-in</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {visitors.map((visitor) => (
                        <TableRow key={visitor.id}>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>{visitor.visitor_name}</Typography>
                            <Typography variant="caption" color="text.secondary">{visitor.phone}</Typography>
                          </TableCell>
                          <TableCell>{visitor.purpose}</TableCell>
                          <TableCell>{formatDateTime(visitor.check_in)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </Paper>
            </Grid>
          </Grid>
        </>
      )}

      <Dialog open={openVisitor} onClose={() => setOpenVisitor(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Walk-in Visitor Check-in</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Visitor Name" fullWidth required value={visitorForm.visitor_name} onChange={(e) => setVisitorForm({ ...visitorForm, visitor_name: e.target.value })} />
            <TextField label="Phone Number" fullWidth required value={visitorForm.phone} onChange={(e) => setVisitorForm({ ...visitorForm, phone: e.target.value })} />
            <TextField label="Purpose of Visit" fullWidth value={visitorForm.purpose} onChange={(e) => setVisitorForm({ ...visitorForm, purpose: e.target.value })} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenVisitor(false)} disabled={submitting}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateVisitor} disabled={submitting}>Register Check-in</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={openLead} onClose={() => setOpenLead(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Create New Enquiry Lead</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField label="Full Name" fullWidth required value={leadForm.name} onChange={(e) => setLeadForm({ ...leadForm, name: e.target.value })} />
            <TextField label="Phone Number" fullWidth required value={leadForm.phone} onChange={(e) => setLeadForm({ ...leadForm, phone: e.target.value })} />
            <TextField label="Email Address" fullWidth value={leadForm.email} onChange={(e) => setLeadForm({ ...leadForm, email: e.target.value })} />
            <TextField select label="Branch" fullWidth value={leadForm.branch_id || defaultBranch} onChange={(e) => setLeadForm({ ...leadForm, branch_id: e.target.value })}>
              {branches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name} ({b.code})</MenuItem>)}
            </TextField>
            <TextField select label="Target Course" fullWidth value={leadForm.course_id} onChange={(e) => setLeadForm({ ...leadForm, course_id: e.target.value })}>
              <MenuItem value="">— General enquiry —</MenuItem>
              {courses.map((c) => <MenuItem key={c.id} value={c.id}>{c.title} ({c.code})</MenuItem>)}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenLead(false)} disabled={submitting}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateLead} disabled={submitting}>Save Enquiry</Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={toast.open}
        autoHideDuration={5000}
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
