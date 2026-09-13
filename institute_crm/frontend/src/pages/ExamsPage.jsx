import React, { useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, Chip, MenuItem, Snackbar, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, TextField, Typography,
} from '@mui/material';
import { Refresh } from '@mui/icons-material';
import api, { unwrapList, unwrapData } from '../services/api';
import { PageHeader, MetricCards } from './PageLayout';

export const ExamsPage = () => {
  const [batches, setBatches] = useState([]);
  const [batchId, setBatchId] = useState('');
  const [report, setReport] = useState(null);
  const [examIdx, setExamIdx] = useState(0);
  const [loading, setLoading] = useState(false);
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
      const res = await api.get(`/assignments/exams/batch-report/?batch_id=${bid}`);
      setReport(unwrapData(res));
      setExamIdx(0);
    } catch (e) {
      setToast({ open: true, message: e?.detail || 'Could not load exam report.', severity: 'error' });
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadBatches(); }, []);
  useEffect(() => { if (batchId) loadReport(batchId); }, [batchId]);

  const current = report?.exams?.[examIdx];
  const metrics = report ? [
    { label: 'Exams', value: report.total_exams },
    { label: 'Pass Rate', value: report.pass_rate_pct === null ? '—' : `${report.pass_rate_pct}%` },
    { label: 'Average Score', value: report.average_score_pct === null ? '—' : `${report.average_score_pct}%` },
    { label: 'Top / Lowest', value: report.top_score_pct === null ? '—' : `${report.top_score_pct}% / ${report.lowest_score_pct}%` },
  ] : [
    { label: 'Upcoming Exams', value: '—' },
    { label: 'Results Pending', value: '—' },
    { label: 'Average Score', value: '—' },
  ];

  return (
    <Box>
      <PageHeader title="Exams & Performance" subtitle="Real exam monitoring per batch — pass rate, scores and grade distribution." />
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <TextField select fullWidth label="Select Batch" value={batchId} onChange={(e) => setBatchId(e.target.value)}>
          <MenuItem value="">— Select —</MenuItem>
          {batches.map((b) => <MenuItem key={b.id} value={b.id}>{b.name} ({b.code})</MenuItem>)}
        </TextField>
        <Button variant="outlined" startIcon={<Refresh />} onClick={() => batchId && loadReport(batchId)}>Refresh</Button>
      </Stack>
      <MetricCards items={metrics} />
      {!batchId && <Alert severity="info">Select a batch to view its exams and results.</Alert>}
      {report && (
        <>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Grade distribution: {JSON.stringify(report.grade_distribution)}
          </Typography>
          <TextField select fullWidth label="Exam" value={examIdx} onChange={(e) => setExamIdx(Number(e.target.value))} sx={{ mb: 2 }}>
            {(report.exams || []).map((a, i) => <MenuItem key={a.id} value={i}>{a.title} — {a.exam_date}</MenuItem>)}
          </TextField>
          {current && (
            <Card sx={{ overflow: 'hidden' }}>
              <Box sx={{ p: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>{current.title}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {current.exam_date} · Pass {current.passing_marks}/{current.total_marks} · Pass rate {current.pass_rate_pct ?? '—'}% · Avg {current.average_score_pct ?? '—'}%
                </Typography>
              </Box>
              <Table size="small"><TableHead><TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Student</TableCell><TableCell sx={{ fontWeight: 700 }}>Marks</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Grade</TableCell><TableCell sx={{ fontWeight: 700 }}>Result</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Remarks</TableCell>
              </TableRow></TableHead><TableBody>
                {(current.students || []).map((s) => (
                  <TableRow key={s.student_id}>
                    <TableCell>{s.student_name}</TableCell>
                    <TableCell>{s.marks_obtained ?? 'Absent'} {s.percentage != null ? `(${s.percentage}%)` : ''}</TableCell>
                    <TableCell>{s.grade || '—'}</TableCell>
                    <TableCell>{s.status === 'ABSENT' ? <Chip size="small" label="Absent" /> : <Chip size="small" label={s.passed ? 'Pass' : 'Fail'} color={s.passed ? 'success' : 'error'} />}</TableCell>
                    <TableCell>{s.remarks || '—'}</TableCell>
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
