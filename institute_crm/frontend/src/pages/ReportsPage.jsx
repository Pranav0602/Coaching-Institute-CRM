import React, { useState, useEffect } from 'react';
import {
  Box, Card, CardContent, Grid, Typography, Table, TableBody, TableCell,
  TableHead, TableRow, Skeleton,
} from '@mui/material';
import { PageHeader } from './PageLayout';
import api, { unwrapData } from '../services/api';
import { Alert, Button } from '@mui/material';

const fmtMoney = (value) =>
  value === null || value === undefined || Number(value) === 0
    ? '₹0'
    : `₹${Number(value).toLocaleString()}`;

const REPORT_LINKS = [
  { report: 'Admissions funnel', period: 'Monthly', metricKey: 'open_leads' },
  { report: 'Branch revenue', period: 'Monthly', metricKey: 'total_fee_collection' },
  { report: 'Student attendance', period: 'Weekly', metricKey: 'todays_attendance_pct' },
];

export const ReportsPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState('');

  const fetchReport = () => {
    setLoading(true);
    setError(null);
    setErrorDetail('');
    api
      .get('/analytics/dashboard/')
      .then((res) => setData(unwrapData(res) ?? null))
      .catch((err) => {
        setError(err?.detail || 'Could not reach the analytics service.');
        setErrorDetail(err?.message || '');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchReport(); }, []);

  const cards = data?.cards || {};

  const metrics = loading
    ? []
    : [
        {
          label: 'Open Leads',
          value: cards.open_leads ?? '—',
        },
        {
          label: 'Admissions This Month',
          value: cards.admissions_this_month ?? '—',
          color: 'success.main',
        },
        {
          label: "Today's Attendance",
          value:
            cards.todays_attendance_pct === null || cards.todays_attendance_pct === undefined
              ? 'No data yet'
              : `${cards.todays_attendance_pct}%`,
        },
      ];

  return (
    <Box>
      <PageHeader
        title="Reports & Analytics"
        subtitle="A concise view of institute performance and operational trends."
      />
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} action={<Button size="small" color="inherit" onClick={fetchReport}>Retry</Button>}>
          {error} {errorDetail && `— ${errorDetail}`} Please make sure the API is running at {import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'}.
        </Alert>
      )}

      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        {metrics.map((item) => (
          <Grid item xs={12} sm={4} key={item.label}>
            <Card><CardContent>
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>{item.label}</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800, my: 0.5 }}>{item.value}</Typography>
            </CardContent></Card>
          </Grid>
        ))}
        {loading && [1, 2, 3].map((n) => (
          <Grid item xs={12} sm={4} key={n}>
            <Card><CardContent><Skeleton height={48} /></CardContent></Card>
          </Grid>
        ))}
      </Grid>

      <Card sx={{ overflow: 'hidden' }}>
        <Box sx={{ p: 2.5, pb: 1.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Available reports</Typography>
        </Box>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Report</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Period</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Latest Value</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {REPORT_LINKS.map(({ report, period, metricKey }) => (
              <TableRow key={report} hover>
                <TableCell>{report}</TableCell>
                <TableCell>{period}</TableCell>
                <TableCell>
                  {metricKey === 'todays_attendance_pct'
                    ? (cards[metricKey] === null || cards[metricKey] === undefined
                        ? 'No data yet'
                        : `${cards[metricKey]}%`)
                    : (cards[metricKey] ?? 'No data yet')}
                </TableCell>
                <TableCell>{loading ? 'Loading…' : data ? 'Ready' : 'Unavailable'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </Box>
  );
};
