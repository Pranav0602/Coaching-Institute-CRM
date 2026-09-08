import React, { useState, useEffect, useCallback } from 'react';
import { SimplePage } from './PageLayout';
import api, { unwrapList } from '../services/api';

const fmtMoney = (value) =>
  value === null || value === undefined || value === ''
    ? '—'
    : `₹${Number(value).toLocaleString()}`;

export const FinancePage = () => {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState('');

  const fetchPayments = useCallback(() => {
    setLoading(true);
    setError(null);
    setErrorDetail('');
    api
      .get('/finance/payments/')
      .then((res) => setPayments(unwrapList(res)))
      .catch((err) => {
        setPayments([]);
        setError(err?.detail || 'Could not load payments.');
        setErrorDetail(err?.message || '');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  const now = new Date();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const collectedThisMonth = payments
    .filter((p) => p.payment_date && new Date(p.payment_date) >= monthStart)
    .reduce((sum, p) => sum + Number(p.amount || 0), 0);
  const totalCollected = payments.reduce((sum, p) => sum + Number(p.amount || 0), 0);

  const metrics = [
    { label: 'Collected This Month', value: fmtMoney(collectedThisMonth), color: 'success.main' },
    { label: 'Total Collected', value: fmtMoney(totalCollected) },
    { label: 'Payment Records', value: payments.length },
  ];

  return (
    <SimplePage
      title="Financial Accounts"
      subtitle="Fee collection and recent transactions (read-only — payments are recorded through the installment flow)."
      metrics={metrics}
      loading={loading}
      error={error}
      errorDetail={errorDetail}
      onRetry={fetchPayments}
      tableTitle="Recent payments"
      columns={[
        { key: 'student_name', label: 'Student' },
        { key: 'amount', label: 'Amount' },
        { key: 'payment_mode', label: 'Mode' },
        { key: 'reference_number', label: 'Reference' },
        {
          key: 'receipt',
          label: 'Receipt',
          // receipt is a nested object; flatten it for display
        },
        { key: 'payment_date', label: 'Date' },
      ]}
      rows={payments.map((p) => ({
        ...p,
        amount: fmtMoney(p.amount),
        reference_number: p.reference_number || '—',
        receipt: p.receipt?.receipt_number || '—',
        payment_date: p.payment_date ? new Date(p.payment_date).toLocaleDateString() : '—',
      }))}
      emptyMessage="No payments recorded yet."
    />
  );
};
