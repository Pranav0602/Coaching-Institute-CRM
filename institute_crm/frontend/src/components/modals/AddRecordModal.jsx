import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, MenuItem, Button, Stack, Alert,
} from '@mui/material';

const toOption = (opt) =>
  typeof opt === 'object' && opt !== null ? opt : { value: opt, label: String(opt) };

export const AddRecordModal = ({ open, onClose, title, fields = [], onSubmit }) => {
  const [formData, setFormData] = useState({});
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      const initial = {};
      fields.forEach((f) => {
        initial[f.name] = f.default ?? '';
      });
      setFormData(initial);
      setError(null);
      setSubmitting(false);
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async () => {
    const missing = fields
      .filter((f) => f.required)
      .find((f) => !String(formData[f.name] ?? '').trim());
    if (missing) {
      setError(`${missing.label || missing.name} is required.`);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(formData);
    } catch (err) {
      setError(
        err?.detail ||
          err?.message ||
          'Could not save the record. Please check the values and try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ fontWeight: 700 }}>{title}</DialogTitle>
      <DialogContent dividers>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Stack spacing={2}>
          {fields.map((field) =>
            field.type === 'select' ? (
              <TextField
                key={field.name}
                select
                label={field.label}
                name={field.name}
                value={formData[field.name] ?? ''}
                onChange={handleChange}
                fullWidth
                required={field.required}
              >
                {!field.required && <MenuItem value="">— None —</MenuItem>}
                {(field.options || []).map((opt) => {
                  const { value, label } = toOption(opt);
                  return (
                    <MenuItem key={String(value)} value={value}>
                      {label}
                    </MenuItem>
                  );
                })}
              </TextField>
            ) : (
              <TextField
                key={field.name}
                label={field.label}
                name={field.name}
                type={field.type === 'number' ? 'number' : field.type === 'password' ? 'password' : field.type === 'email' ? 'email' : 'text'}
                multiline={field.type === 'textarea'}
                minRows={field.type === 'textarea' ? 3 : undefined}
                value={formData[field.name] ?? ''}
                onChange={handleChange}
                fullWidth
                required={field.required}
              />
            )
          )}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
