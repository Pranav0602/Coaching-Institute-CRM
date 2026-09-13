import React, { useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, Chip, MenuItem, Snackbar, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, TextField, Typography,
} from '@mui/material';
import { Refresh } from '@mui/icons-material';
import api, { unwrapList, unwrapData } from '../services/api';
import { PageHeader, MetricCards } from './PageLayout';

export const AssignmentsPage = () => {
  const [batches, setBatches] = useState([]);
  const [batchId, setBatchId] = useState('');
  const [report, setReport] = useState(null);
  const [assignmentIdx, setAssignmentIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });

  const loadBatches = async () => {
    try {
      const res = await api.get('/academics/batches/');
      setBatches(unwrapList(res));
    } catch (e) {
      setToast({ open: true, message: 'Could not load batches.', severity: 'error' });
    }
  };

  const loadReport = async (bid) => {
    if (!bid) { setReport(null); return; }
    setLoading(true);
    try {
      const res = await api.get(`/assignments/assignments/batch-report/?batch_id=${bid}`);
      setReport(unwrapData(res));
      setAssignmentIdx(0);
    } catch (e) {
      setToast({ open: true, message: e?.detail || 'Could not load assignment report.', severity: 'error' });
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    (async () => { setLoading(true); await loadBatches(); setLoading(false); })();
  }, []);

  useEffect(() => { if (batchId) loadReport(batchId); }, [batchId]);

  const current = report?.assignments?.[assignmentIdx];
  const metrics = report ? [
    { label: 'Assignments', value: report.total_assignments },
    { label: 'Submission Rate', value: `${report.submission_rate_pct}%`, note: `${report.submissions_received}/${report.expected_submissions} received` },
    { label: 'Pending Review', value: report.pending_evaluations },
    { label: 'Average Score', value: report.average_score_pct === null ? '—' : `${report.average_score_pct}%` },
  ] : [
    { label: 'Open Assignments', value: '—' },
    { label: 'Awaiting Review', value: '—' },
    { label: 'Graded', value: '—' },
  ];

  return (
    <Box>
      <PageHeader title="Assignments & Submissions" subtitle="Real assignment monitoring per batch — submissions, timeliness and evaluation." />
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <TextField select fullWidth label="Select Batch" value={batchId} onChange={(e) => setBatchId(e.target.value)}>
          <MenuItem value="">— Select —</MenuItem>
          {batches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name} ({b.code})</MenuItem>)}
        </TextField>
        <Button variant="outlined" startIcon={<Refresh />} onClick={() => batchId && loadReport(batchId)}>Refresh</Button>
      </Stack>
      <MetricCards items={metrics} />
      {!batchId && <Alert severity="info">Select a batch to view its assignments and submissions.</Alert>}
      {report && (
        <>
          <TextField select fullWidth label="Assignment" value={assignmentIdx} onChange={(e) => setAssignmentIdx(Number(e.target.value))} sx={{ mb: 2 }}>
            {(report.assignments || []).map((a, i) => <MenuItem key={a.id} value={i}>{a.title} — {a.received}/{a.expected}</MenuItem>)}
          </TextField>
          {current && (
            <Card sx={{ overflow: 'hidden' }}>
              <Box sx={{ p: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>{current.title}</Typography>
                <Typography variant="body2" color="text.secondary">
                  Due {current.due_date} · {current.total_marks} marks · Submission {current.submission_rate_pct}% · Pending review {current.pending_evaluations}
                </Typography>
              </Box>
              <Table size="small"><TableHead><TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Student</TableCell><TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Submitted</TableCell><TableCell sx={{ fontWeight: 700 }}>File</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Marks</TableCell><TableCell sx={{ fontWeight: 700 }}>Feedback</TableCell>
              </TableRow></TableHead><TableBody>
                {(current.students || []).map((s) => (
                  <TableRow key={s.student_id}>
                    <TableCell>{s.student_name}</TableCell>
                    <TableCell><Chip size="small" label={s.status === 'SUBMITTED' ? `Submitted ${s.timeliness === 'LATE' ? '(late)' : '(on time)'}` : 'Pending / Not submitted'} color={s.status === 'SUBMITTED' ? (s.timeliness === 'LATE' ? 'warning' : 'success') : 'default'} /></TableCell>
                    <TableCell>{s.submitted_at ? new Date(s.submitted_at).toLocaleString() : '—'}</TableCell>
                    <TableCell>{s.file_url ? <a href={s.file_url} target="_blank" rel="noreferrer">Open</a> : '—'}</TableCell>
                    <TableCell>{s.marks_obtained ?? '—'}</TableCell>
                    <TableCell>{s.feedback || '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody></Table>
            </Card>
          )}
        </>
      )}
      <Snackbar open={toast.open} autoHideDuration={4500} onClose={() => setToast((c) => ({ ...c, open: false }))}>
        <Alert severity={toast.severity} onClose={() => setToast((c) => ({ ...c, open: false }))}>{toast.message}</Alert>
      </Snackbar>
    </Box>
  );
};
