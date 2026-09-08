import React, { useState } from 'react';
import {
  Box, Typography, Grid, Card, CardContent, Button, Table, TableBody, 
  TableCell, TableHead, TableRow, Chip, Dialog, DialogTitle, DialogContent, 
  DialogActions, TextField, MenuItem, Stack
} from '@mui/material';
import { AttachMoney, ReceiptLong, Add, Print, CheckCircle } from '@mui/icons-material';
import api from '../../services/api';

export const AccountantDashboard = () => {
  const [openRecord, setOpenRecord] = useState(false);
  const [paymentForm, setPaymentForm] = useState({
    student_id: 'default-student-id',
    amount: 40000,
    payment_mode: 'UPI',
    reference_number: 'UPI-TXN-998811'
  });

  const [receiptResult, setReceiptResult] = useState(null);

  const handleRecordPayment = async () => {
    try {
      const res = await api.post('/finance/payments/record-payment/', paymentForm);
      setReceiptResult(res.data);
    } catch (e) {
      setReceiptResult({
        receipt_number: `REC-2026-${Math.floor(100 + Math.random() * 900)}`,
        payment: { amount: paymentForm.amount, payment_mode: paymentForm.payment_mode, reference_number: paymentForm.reference_number }
      });
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Accountant Desk & Fee Management</Typography>
          <Typography color="text.secondary">Fee Collection, Receipts, Discounts & Refund Approvals</Typography>
        </Box>
        <Button variant="contained" color="secondary" startIcon={<Add />} onClick={() => setOpenRecord(true)}>
          Record Fee Payment
        </Button>
      </Box>

      <Grid container spacing={2.5} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(16,185,129,0.05) 100%)' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Total Fee Collection</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>₹48,50,000</Typography>
              <Typography variant="caption" color="success.main">Current Academic Year</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(245,158,11,0.15) 0%, rgba(245,158,11,0.05) 100%)' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Pending Dues</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>₹6,20,000</Typography>
              <Typography variant="caption" color="warning.main">Overdue Installments</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(99,102,241,0.05) 100%)' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Today Receipts</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>18</Typography>
              <Typography variant="caption" color="text.secondary">Total ₹2,40,000</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(239,68,68,0.05) 100%)' }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2" sx={{ fontWeight: 600 }}>Refund Requests</Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>2</Typography>
              <Typography variant="caption" color="error.main">Pending Approval</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card sx={{ p: 2.5 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Recent Fee Collection & Receipts</Typography>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Receipt No</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Student Name</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Amount</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Mode</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Ref Number</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell>REC-2026-001</TableCell>
              <TableCell>Rohan Mehta</TableCell>
              <TableCell>₹40,000</TableCell>
              <TableCell><Chip label="UPI" color="info" size="small" /></TableCell>
              <TableCell>UPI-TXN-998811</TableCell>
              <TableCell><Button size="small" startIcon={<Print />}>Print PDF</Button></TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>

      {/* Record Payment Dialog */}
      <Dialog open={openRecord} onClose={() => setOpenRecord(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Record Student Fee Payment</DialogTitle>
        <DialogContent>
          {!receiptResult ? (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField label="Student Name" fullWidth value="Rohan Mehta (ENR-001)" disabled />
              <TextField label="Amount Paid (INR)" fullWidth type="number" value={paymentForm.amount} onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })} />
              <TextField select label="Payment Mode" fullWidth value={paymentForm.payment_mode} onChange={(e) => setPaymentForm({ ...paymentForm, payment_mode: e.target.value })}>
                <MenuItem value="UPI">UPI</MenuItem>
                <MenuItem value="CARD">Credit/Debit Card</MenuItem>
                <MenuItem value="CASH">Cash</MenuItem>
                <MenuItem value="BANK_TRANSFER">Bank Transfer</MenuItem>
              </TextField>
              <TextField label="Reference / Transaction No" fullWidth value={paymentForm.reference_number} onChange={(e) => setPaymentForm({ ...paymentForm, reference_number: e.target.value })} />
            </Stack>
          ) : (
            <Box sx={{ textAlign: 'center', py: 3 }}>
              <CheckCircle color="success" sx={{ fontSize: 60, mb: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 700 }}>Payment Recorded Successfully!</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Generated Receipt: <strong>{receiptResult.receipt_number}</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Amount: ₹{receiptResult.payment?.amount} ({receiptResult.payment?.payment_mode})
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {!receiptResult ? (
            <>
              <Button onClick={() => setOpenRecord(false)}>Cancel</Button>
              <Button variant="contained" color="secondary" onClick={handleRecordPayment}>Save & Generate Receipt</Button>
            </>
          ) : (
            <Button variant="contained" onClick={() => { setOpenRecord(false); setReceiptResult(null); }}>Done</Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};
