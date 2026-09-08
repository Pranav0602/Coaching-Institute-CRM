import React, { useState } from 'react';
import {
  Box, Typography, Grid, Card, CardContent, Button, Table, TableBody, 
  TableCell, TableHead, TableRow, Chip, Dialog, DialogTitle, DialogContent, 
  DialogActions, TextField, Stack
} from '@mui/material';
import { MeetingRoom, Badge, Add, Print, Phone, Person } from '@mui/icons-material';

export const ReceptionistDashboard = () => {
  const [openVisitor, setOpenVisitor] = useState(false);
  const [openIdCard, setOpenIdCard] = useState(false);

  const [visitors, setVisitors] = useState([
    { id: '1', name: 'Sunil Verma', phone: '+91-9899001122', purpose: 'Enquiry for Fullstack Web Development', time: '10:15 AM', status: 'IN' },
    { id: '2', name: 'Meena Saxena', phone: '+91-9877112233', purpose: 'Parent Counseling Meeting', time: '11:30 AM', status: 'OUT' },
  ]);

  const [newVisitor, setNewVisitor] = useState({ name: '', phone: '', purpose: 'Admission Enquiry' });

  const handleAddVisitor = () => {
    setVisitors([...visitors, { id: String(Date.now()), ...newVisitor, time: 'Now', status: 'IN' }]);
    setOpenVisitor(false);
  };

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Reception Desk & Visitor Management</Typography>
          <Typography color="text.secondary">Main Campus Front Desk | Visitor Check-in, Walk-ins & Student ID Cards</Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <Button variant="outlined" startIcon={<Badge />} onClick={() => setOpenIdCard(true)}>
            Print Student ID Card
          </Button>
          <Button variant="contained" startIcon={<Add />} onClick={() => setOpenVisitor(true)}>
            Check-in Walk-in Visitor
          </Button>
        </Stack>
      </Box>

      <Grid container spacing={2.5} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Today Visitors</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>14</Typography>
              <Typography variant="caption" color="success.main">Walk-ins registered</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Currently In Campus</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>3</Typography>
              <Typography variant="caption" color="info.main">Active visitors</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Counselling Scheduled</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>6</Typography>
              <Typography variant="caption" color="text.secondary">For today afternoon</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>ID Cards Printed</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>28</Typography>
              <Typography variant="caption" color="text.secondary">This week</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card sx={{ p: 2.5 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Today Visitor Log</Typography>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Visitor Name</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Phone</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Purpose</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Check-in Time</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {visitors.map((v) => (
              <TableRow key={v.id}>
                <TableCell>{v.name}</TableCell>
                <TableCell>{v.phone}</TableCell>
                <TableCell>{v.purpose}</TableCell>
                <TableCell>{v.time}</TableCell>
                <TableCell>
                  <Chip label={v.status === 'IN' ? 'In Campus' : 'Checked Out'} color={v.status === 'IN' ? 'success' : 'default'} size="small" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Visitor Check-in Modal */}
      <Dialog open={openVisitor} onClose={() => setOpenVisitor(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Walk-in Visitor Check-in</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Visitor Name" fullWidth value={newVisitor.name} onChange={(e) => setNewVisitor({ ...newVisitor, name: e.target.value })} />
            <TextField label="Phone Number" fullWidth value={newVisitor.phone} onChange={(e) => setNewVisitor({ ...newVisitor, phone: e.target.value })} />
            <TextField label="Purpose of Visit" fullWidth value={newVisitor.purpose} onChange={(e) => setNewVisitor({ ...newVisitor, purpose: e.target.value })} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenVisitor(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddVisitor}>Register Check-in</Button>
        </DialogActions>
      </Dialog>

      {/* Student ID Card Print View Modal */}
      <Dialog open={openIdCard} onClose={() => setOpenIdCard(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, textAlign: 'center' }}>Student Identity Card</DialogTitle>
        <DialogContent>
          <Box sx={{ p: 3, border: '2px solid #6366F1', borderRadius: 3, textAlign: 'center', bgcolor: 'background.paper', boxShadow: 3 }}>
            <Box sx={{ width: 60, height: 60, borderRadius: '50%', bgcolor: 'primary.main', color: '#fff', mx: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 800, mb: 1 }}>
              RM
            </Box>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>Rohan Mehta</Typography>
            <Typography variant="caption" color="text.secondary" display="block">ENR-DEL-2026-001</Typography>
            <Chip label="Fullstack Web Development" color="primary" size="small" sx={{ my: 1 }} />
            <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>Batch: BATCH-DEL-A1</Typography>
            <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>Branch: Main Campus - Delhi</Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>Authorized Signature</Typography>
          </Box>
        </DialogContent>
        <DialogActions sx={{ justifyContent: 'center' }}>
          <Button variant="contained" startIcon={<Print />} onClick={() => window.print()}>Print Badge</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
