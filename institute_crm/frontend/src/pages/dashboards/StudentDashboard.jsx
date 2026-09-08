import React, { useState } from 'react';
import {
  Box, Typography, Grid, Card, CardContent, Button, Chip, LinearProgress, 
  Table, TableBody, TableCell, TableHead, TableRow, Dialog, DialogTitle, 
  DialogContent, DialogActions, TextField, Stack
} from '@mui/material';
import { School, EventNote, Assignment, ReceiptLong, CheckCircle } from '@mui/icons-material';

export const StudentDashboard = () => {
  const [openSubmit, setOpenSubmit] = useState(false);

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 800 }}>Student Portal & Academic Overview</Typography>
        <Typography color="text.secondary">Welcome back, Rohan Mehta | Enrollment No: ENR-DEL-2026-001</Typography>
      </Box>

      {/* KPI Cards */}
      <Grid container spacing={2.5} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(16,185,129,0.05) 100%)' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Attendance Percentage</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>94.0%</Typography>
              <Box sx={{ mt: 1 }}>
                <LinearProgress variant="determinate" value={94} color="success" sx={{ height: 8, borderRadius: 4 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(99,102,241,0.05) 100%)' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Enrolled Course</Typography>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>Fullstack Web Dev</Typography>
              <Typography variant="caption" color="text.secondary">Batch: BATCH-DEL-A1</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(245,158,11,0.15) 0%, rgba(245,158,11,0.05) 100%)' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Pending Dues</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>₹40,000</Typography>
              <Typography variant="caption" color="warning.main">Due on 30th Aug 2026</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.15) 0%, rgba(59,130,246,0.05) 100%)' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Latest Test Score</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>88.5 / 100</Typography>
              <Typography variant="caption" color="success.main">Grade A+ (Web Dev Assessment)</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Grid */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <Card sx={{ p: 2.5, mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Today's Class Timetable</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Time</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Subject</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Teacher</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Room</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>09:00 - 10:30 AM</TableCell>
                  <TableCell>Frontend Web Engineering</TableCell>
                  <TableCell>Dr. Alok Gupta</TableCell>
                  <TableCell>Lab 201</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>11:00 - 12:30 PM</TableCell>
                  <TableCell>Database Systems & SQL</TableCell>
                  <TableCell>Prof. S. N. Sharma</TableCell>
                  <TableCell>Lab 102</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Card>
        </Grid>

        <Grid item xs={12} md={5}>
          <Card sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Assignments & Submissions</Typography>
            <Box sx={{ mb: 2, p: 2, border: '1px solid rgba(255,255,255,0.1)', borderRadius: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Fullstack Project #3 - Node & Express API</Typography>
              <Typography variant="caption" color="text.secondary" display="block">Due: 5th Aug 2026 | Total Marks: 50</Typography>
              <Box sx={{ mt: 1.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Chip label="Submitted (45/50)" color="success" size="small" />
                <Button size="small" variant="outlined" onClick={() => setOpenSubmit(true)}>Resubmit</Button>
              </Box>
            </Box>
          </Card>
        </Grid>
      </Grid>

      {/* Assignment Submit Modal */}
      <Dialog open={openSubmit} onClose={() => setOpenSubmit(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Submit Assignment File</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography variant="body2">Select solution PDF to upload securely to AWS S3:</Typography>
            <Button variant="outlined" component="label">
              Upload PDF File
              <input type="file" hidden />
            </Button>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenSubmit(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => { setOpenSubmit(false); alert('Assignment uploaded to S3 successfully!'); }}>
            Submit to Teacher
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
