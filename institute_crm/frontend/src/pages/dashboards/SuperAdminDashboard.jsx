import React, { useState, useEffect } from 'react';
import {
  Grid, Card, CardContent, Typography, Box, Button, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, LinearProgress
} from '@mui/material';
import {
  People, School, AttachMoney, TrendingUp, Group, ArrowUpward
} from '@mui/icons-material';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend
} from 'chart.js';
import api, { unwrapData } from '../../services/api';
import { Alert } from '@mui/material';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend);

export const SuperAdminDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboard = () => {
    setLoading(true);
    setError(null);
    api.get('/analytics/dashboard/')
      .then((res) => setData(unwrapData(res)))
      .catch((err) => {
        setError(err?.detail || 'Could not load dashboard analytics. Please make sure the API is running.');
        setData(null);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchDashboard(); }, []);

  if (loading) {
    return (
      <Box sx={{ py: 4 }}>
        <LinearProgress />
        <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
          Loading dashboard data…
        </Typography>
      </Box>
    );
  }

  const cards = data?.cards || {};
  const branchPerformance = data?.charts?.branch_performance || [];

  const lineChartData = {
    labels: data?.charts?.growth_and_revenue?.map((d) => d.month) || [],
    datasets: [
      {
        label: 'Admissions Growth',
        data: data?.charts?.growth_and_revenue?.map((d) => d.admissions) || [],
        borderColor: '#6366F1',
        backgroundColor: 'rgba(99, 102, 241, 0.15)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const barChartData = {
    labels: branchPerformance.map((d) => d.branch) || [],
    datasets: [
      {
        label: 'Revenue (INR)',
        data: branchPerformance.map((d) => Number(d.revenue || 0)),
        backgroundColor: '#10B981',
        borderRadius: 8,
      },
    ],
  };

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Super Admin Enterprise Dashboard</Typography>
          <Typography color="text.secondary">Multi-branch operations, revenue analytics, and system performance</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Button size="small" variant="outlined" onClick={fetchDashboard} disabled={loading}>Refresh</Button>
          <Chip icon={<ArrowUpward />} label="System Status: Healthy (AWS US-EAST-1)" color="success" variant="outlined" />
        </Box>
      </Box>
      {error && <Alert severity="error" sx={{ mb: 2 }} action={<Button color="inherit" size="small" onClick={fetchDashboard}>Retry</Button>}>{error}</Alert>}

      {/* KPI Cards */}
      <Grid container spacing={2.5} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(99,102,241,0.05) 100%)' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Total Students</Typography>
                <People color="primary" />
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>{cards.total_students ?? 0}</Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700 }}>
                {cards.total_students ? 'Live count from database' : 'No students enrolled yet'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(16,185,129,0.05) 100%)' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Total Revenue</Typography>
                <AttachMoney color="secondary" />
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>₹{(cards.total_fee_collection ?? 0).toLocaleString()}</Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700 }}>
                {cards.total_fee_collection ? 'All-time collection' : 'No payments recorded yet'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(245,158,11,0.15) 0%, rgba(245,158,11,0.05) 100%)' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Today Attendance</Typography>
                <TrendingUp color="warning" />
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>
                {cards.todays_attendance_pct === null || cards.todays_attendance_pct === undefined
                  ? '—'
                  : `${cards.todays_attendance_pct}%`}
              </Typography>
              <Typography variant="caption" sx={{ color: cards.todays_attendance_pct === null ? 'text.secondary' : 'text.secondary', fontWeight: 700 }}>
                {cards.todays_attendance_pct === null ? 'No data yet' : 'Across ' + (branchPerformance.length || 0) + ' branches'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.15) 0%, rgba(59,130,246,0.05) 100%)' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Active Batches</Typography>
                <School color="info" />
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>{cards.active_batches ?? 0}</Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700 }}>
                {cards.active_batches ? `${cards.active_courses ?? 0} courses active` : 'No running batches yet'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Analytics Charts */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={7}>
          <Card sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Monthly Student Admissions Trend</Typography>
            <Box sx={{ height: 300 }}>
              {lineChartData.labels.length > 0 ? (
                <Line data={lineChartData} options={{ responsive: true, maintainAspectRatio: false }} />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No admissions recorded in the last 6 months yet.
                </Typography>
              )}
            </Box>
          </Card>
        </Grid>

        <Grid item xs={12} md={5}>
          <Card sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Revenue by Branch Campus</Typography>
            <Box sx={{ height: 300 }}>
              {branchPerformance.length > 0 ? (
                <Bar data={barChartData} options={{ responsive: true, maintainAspectRatio: false }} />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No branch revenue recorded yet.
                </Typography>
              )}
            </Box>
          </Card>
        </Grid>
      </Grid>

      {/* Multi-branch Table */}
      <Card sx={{ p: 2.5 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Branch Campus Performance Matrix</Typography>
        <TableContainer component={Paper} elevation={0}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Branch Name</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Students</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Active Enrolments</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Revenue</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {branchPerformance.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} style={{ textAlign: 'center', color: 'text.secondary' }}>
                    No data yet
                  </TableCell>
                </TableRow>
              ) : (
                branchPerformance.map((row) => (
                  <TableRow key={row.branch_id}>
                    <TableCell>{row.branch}</TableCell>
                    <TableCell>{row.students ?? 0}</TableCell>
                    <TableCell>{row.active_enrolments ?? 0}</TableCell>
                    <TableCell>₹{Number(row.revenue || 0).toLocaleString()}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </Box>
  );
};