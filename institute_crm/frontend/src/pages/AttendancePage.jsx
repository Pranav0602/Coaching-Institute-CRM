import React, { useState } from 'react';
import { Box, Button, Card, Checkbox, FormControlLabel, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material';
import { PageHeader } from './PageLayout';
const initialStudents = [{ name: 'Rohan Mehta', roll: 'ENR/2026/001' }, { name: 'Aarav Sharma', roll: 'ENR/2026/002' }, { name: 'Ishita Kapoor', roll: 'ENR/2026/003' }];
export const AttendancePage = () => {
  const [present, setPresent] = useState(initialStudents.map(() => true));
  const [saved, setSaved] = useState(false);
  return <Box><PageHeader title="Attendance" subtitle="Mark attendance for Morning Batch A1 — React Fundamentals." />
    <Card sx={{ p: 2.5 }}><Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Student roster</Typography><Table><TableHead><TableRow><TableCell sx={{ fontWeight: 700 }}>Enrollment</TableCell><TableCell sx={{ fontWeight: 700 }}>Student</TableCell><TableCell sx={{ fontWeight: 700 }}>Present</TableCell></TableRow></TableHead><TableBody>{initialStudents.map((student, index) => <TableRow key={student.roll}><TableCell>{student.roll}</TableCell><TableCell>{student.name}</TableCell><TableCell><FormControlLabel control={<Checkbox checked={present[index]} onChange={() => setPresent(present.map((value, i) => i === index ? !value : value))} />} label={present[index] ? 'Present' : 'Absent'} /></TableCell></TableRow>)}</TableBody></Table><Button variant="contained" sx={{ mt: 2 }} onClick={() => setSaved(true)}>Save attendance</Button>{saved && <Typography color="success.main" sx={{ mt: 1 }}>Attendance saved for this session.</Typography>}</Card></Box>;
};
