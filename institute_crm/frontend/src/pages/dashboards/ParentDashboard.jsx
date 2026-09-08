import React from 'react';
import { Box, Typography, Grid, Card, CardContent, Chip, Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material';

export const ParentDashboard = () => {
  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 800 }}>Parent Monitoring Portal</Typography>
        <Typography color="text.secondary">Parent Guardian: Suresh Mehta | Child: Rohan Mehta (Fullstack Web Dev Batch A1)</Typography>
      </Box>

      <Grid container spacing={2.5} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Overall Attendance</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>94%</Typography>
              <Typography variant="caption" color="success.main">Present 47 / 50 Days</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Average Test Rank</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>3rd / 40</Typography>
              <Typography variant="caption" color="success.main">Top 5% in Batch</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Paid Fee Total</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>₹80,000</Typography>
              <Typography variant="caption" color="text.secondary">Receipts available</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Upcoming Dues</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>₹40,000</Typography>
              <Typography variant="caption" color="warning.main">Next Installment</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card sx={{ p: 2.5, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Teacher Remarks & Subject Performance</Typography>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Subject</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Teacher</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Latest Test Score</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Teacher Remark</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell>Web Development</TableCell>
              <TableCell>Dr. Alok Gupta</TableCell>
              <TableCell>88.5 / 100</TableCell>
              <TableCell>Excellent problem-solving speed in React architecture & REST APIs.</TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Database Engineering</TableCell>
              <TableCell>Prof. S. N. Sharma</TableCell>
              <TableCell>82.0 / 100</TableCell>
              <TableCell>Good grasp of PostgreSQL schema design; focus on complex SQL join queries.</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>
    </Box>
  );
};
