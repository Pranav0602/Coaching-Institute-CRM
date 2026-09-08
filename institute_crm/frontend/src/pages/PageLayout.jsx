import React from 'react';
import {
  Box, Button, Card, CardContent, Chip, Grid, Table, TableBody,
  TableCell, TableHead, TableRow, Typography, IconButton, Skeleton,
} from '@mui/material';
import { Add, DeleteOutline } from '@mui/icons-material';

export const PageHeader = ({ title, subtitle, action, onAction }) => (
  <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
    <Box>
      <Typography variant="h4" sx={{ fontWeight: 800 }}>{title}</Typography>
      <Typography color="text.secondary">{subtitle}</Typography>
    </Box>
    {action && <Button variant="contained" startIcon={<Add />} onClick={onAction}>{action}</Button>}
  </Box>
);

export const MetricCards = ({ items }) => (
  <Grid container spacing={2.5} sx={{ mb: 3 }}>
    {items.map((item) => (
      <Grid item xs={12} sm={6} md={12 / items.length} key={item.label}>
        <Card><CardContent>
          <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>{item.label}</Typography>
          <Typography variant="h4" sx={{ fontWeight: 800, my: 0.5 }}>
            {item.value === null || item.value === undefined || item.value === '' ? '—' : item.value}
          </Typography>
          {item.note && <Typography variant="caption" color={item.color || 'text.secondary'}>{item.note}</Typography>}
        </CardContent></Card>
      </Grid>
    ))}
  </Grid>
);

export const DataTable = ({
  title, columns, rows = [], actionLabel, onAction, onDelete, loading,
  emptyMessage = 'No records yet.',
}) => {
  const showDelete = typeof onDelete === 'function';
  return (
    <Card sx={{ overflow: 'hidden' }}>
      {(title || actionLabel) && (
        <Box sx={{ p: 2.5, pb: 1.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {title && <Typography variant="h6" sx={{ fontWeight: 700 }}>{title}</Typography>}
          {actionLabel && <Button size="small" onClick={onAction}>{actionLabel}</Button>}
        </Box>
      )}
      <Table size="small">
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell key={column.key} sx={{ fontWeight: 700 }}>{column.label}</TableCell>
            ))}
            {showDelete && <TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {loading ? (
            Array.from({ length: 5 }).map((_, rowIndex) => (
              <TableRow key={`skeleton-${rowIndex}`}>
                {columns.map((column) => (
                  <TableCell key={column.key}><Skeleton height={24} /></TableCell>
                ))}
                {showDelete && <TableCell align="right"><Skeleton height={24} width={40} sx={{ ml: 'auto' }} /></TableCell>}
              </TableRow>
            ))
          ) : rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length + (showDelete ? 1 : 0)} align="center">
                <Typography color="text.secondary" sx={{ py: 3 }}>{emptyMessage}</Typography>
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row, index) => (
              <TableRow key={row.id ?? index} hover>
                {columns.map((column) => {
                  const value = row[column.key];
                  return (
                    <TableCell key={column.key}>
                      {value === null || value === undefined || value === ''
                        ? '—'
                        : column.chip
                          ? <Chip label={value} size="small" color={column.chip(value)} />
                          : value}
                    </TableCell>
                  );
                })}
                {showDelete && (
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => onDelete(row)} aria-label="delete">
                      <DeleteOutline fontSize="small" color="error" />
                    </IconButton>
                  </TableCell>
                )}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </Card>
  );
};

export const SimplePage = ({
  title, subtitle, metrics, tableTitle, columns, rows, action, onAction,
  loading, onDelete, emptyMessage, error, errorDetail, onRetry, children,
}) => (
  <Box>
    <PageHeader title={title} subtitle={subtitle} action={action} onAction={onAction} />
    {error && (
      <Card sx={{ mb: 2, p: 2, borderLeft: '4px solid', borderLeftColor: 'error.main', bgcolor: 'error.50' }}>
        <Typography color="error" variant="body2" sx={{ fontWeight: 700 }}>
          {typeof error === 'string' ? error : 'Could not load data from the server.'}
        </Typography>
        {errorDetail && (
          <Typography color="error" variant="caption" sx={{ display: 'block', mt: 0.5 }}>
            {errorDetail}
          </Typography>
        )}
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
          Please make sure the API is running at {import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'} and you are logged in.
        </Typography>
        {onRetry && <Button size="small" variant="outlined" color="error" sx={{ mt: 1 }} onClick={onRetry}>Retry</Button>}
      </Card>
    )}
    {metrics && !loading && !error && <MetricCards items={metrics} />}
    {metrics && loading && <MetricCards items={metrics.map((m) => ({ ...m, value: '—' }))} />}
    {children !== undefined ? (
      children
    ) : (
      <DataTable
        title={tableTitle}
        columns={columns || []}
        rows={rows || []}
        actionLabel={typeof action === 'string' && tableTitle ? 'View all' : undefined}
        onAction={onAction}
        onDelete={onDelete}
        loading={loading}
        emptyMessage={error ? 'No data available due to load error. Fix the error and retry.' : emptyMessage}
      />
    )}
  </Box>
);
