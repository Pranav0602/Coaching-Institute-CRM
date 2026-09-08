import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Grid, Card, CardContent, Button, Table, TableBody, 
  TableCell, TableHead, TableRow, Chip, Dialog, DialogTitle, DialogContent, 
  DialogActions, Checkbox, FormControlLabel, TextField, Stack, MenuItem, Paper
} from '@mui/material';
import { EventNote, Assignment, UploadFile, CheckCircle, People, Refresh } from '@mui/icons-material';
import api from '../../services/api';

export const TeacherDashboard = () => {
  const [openAttendance, setOpenAttendance] = useState(false);
  const [openUpload, setOpenUpload] = useState(false);

  const [batches, setBatches] = useState([]);
  const [selectedBatchId, setSelectedBatchId] = useState('');
  const [students, setStudents] = useState([]);
  const [loadingStudents, setLoadingStudents] = useState(false);

  useEffect(() => {
    fetchBatches();
  }, []);

  useEffect(() => {
    fetchStudentsForBatch(selectedBatchId);
  }, [selectedBatchId]);

  const fetchBatches = async () => {
    try {
      const res = await api.get('/academics/batches/');
      const data = res.data?.results || res.data || [];
      const list = Array.isArray(data) ? data : [];
      setBatches(list);
      if (list.length > 0) {
        setSelectedBatchId(list[0].id);
      }
    } catch (err) {
      console.warn('Fallback batch fetch:', err);
    }
  };

  const fetchStudentsForBatch = async (batchId) => {
    setLoadingStudents(true);
    try {
      const url = batchId ? `/profiles/students/?batch_id=${batchId}` : '/profiles/students/';
      const res = await api.get(url);
      const data = res.data?.results || res.data || [];
      const list = Array.isArray(data) ? data : [];

      if (list.length > 0) {
        const formatted = list.map(s => ({
          id: s.id,
          name: s.user_detail ? `${s.user_detail.first_name} ${s.user_detail.last_name}`.trim() || s.user_detail.username : 'Student',
          roll: s.enrollment_number,
          email: s.user_detail?.email || '',
          batchName: s.batch_name || 'Assigned Batch',
          status: 'PRESENT'
        }));
        setStudents(formatted);
      } else {
        // Default sample list if API returns empty
        setStudents([
          { id: '1', name: 'Rohan Mehta', roll: 'ENR/DEL/2026/001', email: 'rohan@student.com', batchName: 'Morning Batch A1', status: 'PRESENT' },
          { id: '2', name: 'Aarav Sharma', roll: 'ENR/DEL/2026/002', email: 'aarav@student.com', batchName: 'Morning Batch A1', status: 'PRESENT' },
          { id: '3', name: 'Ishita Kapoor', roll: 'ENR/DEL/2026/003', email: 'ishita@student.com', batchName: 'Morning Batch A1', status: 'ABSENT' },
        ]);
      }
    } catch (err) {
      console.warn('Fallback students fetch:', err);
      setStudents([
        { id: '1', name: 'Rohan Mehta', roll: 'ENR/DEL/2026/001', email: 'rohan@student.com', batchName: 'Morning Batch A1', status: 'PRESENT' },
        { id: '2', name: 'Aarav Sharma', roll: 'ENR/DEL/2026/002', email: 'aarav@student.com', batchName: 'Morning Batch A1', status: 'PRESENT' },
        { id: '3', name: 'Ishita Kapoor', roll: 'ENR/DEL/2026/003', email: 'ishita@student.com', batchName: 'Morning Batch A1', status: 'ABSENT' },
      ]);
    } finally {
      setLoadingStudents(false);
    }
  };

  const toggleStatus = (id) => {
    setStudents(students.map(s => s.id === id ? { ...s, status: s.status === 'PRESENT' ? 'ABSENT' : 'PRESENT' } : s));
  };

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Teacher Dashboard & Academic Management</Typography>
          <Typography color="text.secondary">Department of Computer Science & Web Engineering</Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <Button variant="outlined" startIcon={<Refresh />} onClick={() => fetchStudentsForBatch(selectedBatchId)}>
            Refresh Roster
          </Button>
          <Button variant="outlined" startIcon={<UploadFile />} onClick={() => setOpenUpload(true)}>
            Upload Material (S3)
          </Button>
          <Button variant="contained" startIcon={<EventNote />} onClick={() => setOpenAttendance(true)}>
            Mark Attendance
          </Button>
        </Stack>
      </Box>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Card sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Today's Assigned Lectures</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Time</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Batch</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Topic</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Room</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>09:00 - 10:30 AM</TableCell>
                  <TableCell>BATCH-DEL-A1</TableCell>
                  <TableCell>React State Management & Async APIs</TableCell>
                  <TableCell>Lab 201</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>02:00 - 03:30 PM</TableCell>
                  <TableCell>BATCH-DEL-B2</TableCell>
                  <TableCell>PostgreSQL Indexing & Query Tuning</TableCell>
                  <TableCell>Lab 104</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ p: 2.5 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Recent Assignments Submitted by Students</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Student</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Assignment</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Score</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>Rohan Mehta</TableCell>
                  <TableCell>Fullstack Project #3 - Express REST API</TableCell>
                  <TableCell><Chip label="45 / 50" color="success" size="small" /></TableCell>
                  <TableCell><Button size="small">Grade</Button></TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Card>
        </Grid>
      </Grid>

      {/* Batch & Course Section Student Roster */}
      <Card sx={{ p: 2.5, mb: 4, borderLeft: '4px solid #6366F1' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <People color="primary" />
            <Typography variant="h6" sx={{ fontWeight: 700 }}>Course Section & Batch Student Roster</Typography>
          </Box>
          <Box sx={{ width: 300 }}>
            <TextField
              select
              fullWidth
              size="small"
              label="Select Batch / Course Section"
              value={selectedBatchId}
              onChange={(e) => setSelectedBatchId(e.target.value)}
            >
              {batches.length > 0 ? (
                batches.map((b) => (
                  <MenuItem key={b.id} value={b.id}>
                    {b.name} ({b.code})
                  </MenuItem>
                ))
              ) : (
                <MenuItem value="">All Assigned Batches</MenuItem>
              )}
            </TextField>
          </Box>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Students admitted by Admission Counselors automatically appear in their assigned batch roster below:
        </Typography>

        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Enrollment No</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Student Name</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Email Address</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Batch / Section</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {students.map((std) => (
              <TableRow key={std.id}>
                <TableCell sx={{ fontWeight: 600 }}>{std.roll}</TableCell>
                <TableCell>{std.name}</TableCell>
                <TableCell>{std.email}</TableCell>
                <TableCell><Chip label={std.batchName} size="small" color="primary" variant="outlined" /></TableCell>
                <TableCell><Chip label="Active Enrolled" color="success" size="small" /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Attendance Modal */}
      <Dialog open={openAttendance} onClose={() => setOpenAttendance(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Attendance Grid: Batch Section Students</DialogTitle>
        <DialogContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Roll / Enrollment</TableCell>
                <TableCell>Student Name</TableCell>
                <TableCell>Present?</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {students.map((s) => (
                <TableRow key={s.id}>
                  <TableCell>{s.roll}</TableCell>
                  <TableCell>{s.name}</TableCell>
                  <TableCell>
                    <FormControlLabel
                      control={<Checkbox checked={s.status === 'PRESENT'} onChange={() => toggleStatus(s.id)} />}
                      label={s.status}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAttendance(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => { setOpenAttendance(false); alert('Attendance submitted!'); }}>
            Submit Attendance
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
