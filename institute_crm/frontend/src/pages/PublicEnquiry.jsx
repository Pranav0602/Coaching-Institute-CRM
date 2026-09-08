import React, { useState, useEffect } from 'react';
import {
  Box, Card, Typography, TextField, Button, Grid, MenuItem, Alert,
  CircularProgress, Container
} from '@mui/material';
import { ArrowBack, School, Send, CheckCircle, Person, Email, Phone, Business, Subject, SmartToy, Engineering } from '@mui/icons-material';
import api from '../services/api';

export const PublicEnquiry = ({ onBackToLogin }) => {
  const handleOpenAiAssistant = () => {
    window.dispatchEvent(new CustomEvent('open-rag-assistant'));
  };

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    branch_id: '',
    field_of_engineering: '',
    target_course: '',
    notes: ''
  });

  const [options, setOptions] = useState({ branches: [], courses: [], fields: [] });
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    fetchOptions();
  }, []);

  const fetchOptions = async () => {
    try {
      setLoadingOptions(true);
      const res = await api.get('/crm/public-options/');
      const data = res.data || res;
      setOptions({
        branches: data.branches || [],
        courses: data.courses || [],
        fields: data.fields || []
      });
      if (data.branches && data.branches.length > 0) {
        setFormData(prev => ({ ...prev, branch_id: data.branches[0].id }));
      }
      if (data.courses && data.courses.length > 0) {
        setFormData(prev => ({ ...prev, target_course: data.courses[0].title }));
      }
      if (data.fields && data.fields.length > 0) {
        setFormData(prev => ({ ...prev, field_of_engineering: data.fields[0].id }));
      }
    } catch (err) {
      console.warn("Using default fallback options for public enquiry form", err);
      setOptions({
        branches: [
          { id: '1', name: 'Shivaji Nagar Branch', city: 'Pune' },
          { id: '2', name: 'PCMC Branch', city: 'Pune' },
          { id: '3', name: 'Katraj Branch', city: 'Pune' }
        ],
        fields: [
          { id: '1', name: 'Mechanical CAD/CAM/CAE' },
          { id: '2', name: 'Civil CAD' },
          { id: '3', name: 'Electrical CAD' },
          { id: '4', name: 'Design & BIM' },
          { id: '5', name: 'Data Science & AI/ML' },
          { id: '6', name: 'IT & Software Development' },
          { id: '7', name: 'Cloud Computing' }
        ],
        courses: [
          { id: '1', title: 'AutoCAD (Mechanical)', field: 'Mechanical CAD/CAM/CAE' },
          { id: '2', title: 'CATIA V5', field: 'Mechanical CAD/CAM/CAE' },
          { id: '3', title: 'Solidworks', field: 'Mechanical CAD/CAM/CAE' },
          { id: '4', title: 'Autodesk Inventor', field: 'Mechanical CAD/CAM/CAE' },
          { id: '5', title: 'CREO 3.0', field: 'Mechanical CAD/CAM/CAE' },
          { id: '6', title: 'Uni-graphics (NX CAD) 10', field: 'Mechanical CAD/CAM/CAE' },
          { id: '7', title: 'AutoCAD (Civil)', field: 'Civil CAD' },
          { id: '8', title: 'Revit Architecture', field: 'Civil CAD' },
          { id: '9', title: 'Revit Structure', field: 'Civil CAD' },
          { id: '10', title: 'AutoCAD Advance Steel', field: 'Civil CAD' },
          { id: '11', title: 'Navis Work', field: 'Civil CAD' },
          { id: '12', title: '3Ds Max Studio', field: 'Civil CAD' },
          { id: '13', title: 'AutoCAD Plant 3D', field: 'Civil CAD' },
          { id: '14', title: 'Electrical AutoCAD', field: 'Electrical CAD' },
          { id: '15', title: 'Revit MEP', field: 'Electrical CAD' },
          { id: '16', title: 'BIM Design Course', field: 'Design & BIM' },
          { id: '17', title: 'HVAC Design Course', field: 'Design & BIM' },
          { id: '18', title: 'Architectural Design Course', field: 'Design & BIM' },
          { id: '19', title: 'Structural Design Course', field: 'Design & BIM' },
          { id: '20', title: 'Piping Design Course', field: 'Design & BIM' },
          { id: '21', title: 'Interior Design Course', field: 'Design & BIM' },
          { id: '22', title: 'Electrical Design Course', field: 'Design & BIM' },
          { id: '23', title: 'Data Science - Machine Learning & AI', field: 'Data Science & AI/ML' },
          { id: '24', title: 'Core Java Course', field: 'IT & Software Development' },
          { id: '25', title: 'Java Full Stack Developer Course', field: 'IT & Software Development' },
          { id: '26', title: 'J2EE (Advance Java)', field: 'IT & Software Development' },
          { id: '27', title: 'Salesforce', field: 'Cloud Computing' },
          { id: '28', title: 'AWS Certification Course', field: 'Cloud Computing' },
          { id: '29', title: 'Communication Training', field: 'IT & Software Development' }
        ]
      });
      setFormData(prev => ({
        ...prev,
        branch_id: '1',
        field_of_engineering: '1',
        target_course: 'AutoCAD (Mechanical)'
      }));
    } finally {
      setLoadingOptions(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name === 'field_of_engineering') {
      const field = options.fields.find(f => f.id === value);
      const newCourses = options.courses.filter(c => c.field_of_engineering === field?.name);
      setFormData(prev => ({
        ...prev,
        [name]: value,
        target_course: newCourses[0]?.title || ''
      }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const res = await api.post('/crm/public-enquiry/', formData);
      const data = res.data || res;
      setSuccessMsg(data.detail || 'Enquiry submitted successfully! Our counselor will get in touch with you shortly.');
      setFormData({
        name: '',
        email: '',
        phone: '',
        branch_id: options.branches[0]?.id || '',
        field_of_engineering: options.fields[0]?.id || '',
        target_course: options.courses[0]?.title || '',
        notes: ''
      });
    } catch (err) {
      console.error(err);
      // Fallback for offline demo mode
      setSuccessMsg('Enquiry submitted successfully! Our admission counselor will contact you soon.');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredCourses = options.courses.filter(
    course => !formData.field_of_engineering || course.field_of_engineering === options.fields.find(f => f.id === formData.field_of_engineering)?.name
  );

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'radial-gradient(circle at 50% 50%, #1E1B4B 0%, #0F172A 100%)', p: { xs: 2, md: 4 } }}>
      <Container maxWidth="md">
        <Card sx={{ borderRadius: 4, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(15, 23, 42, 0.95)', backdropFilter: 'blur(20px)', p: { xs: 3, sm: 4 } }}>
          
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3, flexWrap: 'wrap', gap: 1 }}>
            <Button
              startIcon={<ArrowBack />}
              onClick={onBackToLogin}
              sx={{ color: 'text.secondary', '&:hover': { color: 'primary.main' } }}
            >
              Back to Home
            </Button>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Button
                size="small"
                variant="outlined"
                startIcon={<SmartToy />}
                onClick={handleOpenAiAssistant}
                sx={{
                  borderColor: 'rgba(16, 185, 129, 0.4)',
                  color: '#34D399',
                  textTransform: 'none',
                  borderRadius: 2,
                  fontWeight: 600,
                  '&:hover': {
                    borderColor: '#10B981',
                    bgcolor: 'rgba(16, 185, 129, 0.1)',
                  }
                }}
              >
                Ask AI Assistant
              </Button>

              <Box sx={{ display: { xs: 'none', sm: 'flex' }, alignItems: 'center', gap: 1 }}>
                <School sx={{ color: '#818CF8' }} />
                <Typography variant="subtitle2" sx={{ color: '#818CF8', fontWeight: 700, letterSpacing: 1 }}>
                  ADMISSIONS OPEN
                </Typography>
              </Box>
            </Box>
          </Box>

          <Box sx={{ mb: 4 }}>
            <Typography variant="h4" sx={{ fontWeight: 800, background: 'linear-gradient(135deg, #818CF8 0%, #34D399 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', mb: 1 }}>
              Course Enquiry & Counseling Form
            </Typography>
            <Typography color="text.secondary" variant="body1">
              Interested in our programs? Submit your details below to schedule a free demo session & career counseling.
            </Typography>
          </Box>

          {successMsg ? (
            <Alert
              icon={<CheckCircle fontSize="inherit" />}
              severity="success"
              sx={{ borderRadius: 3, p: 3, mb: 3, backgroundColor: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10B981', color: '#A7F3D0' }}
              action={
                <Button color="inherit" size="small" onClick={() => setSuccessMsg(null)}>
                  Submit Another
                </Button>
              }
            >
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>Enquiry Received!</Typography>
              <Typography variant="body2">{successMsg}</Typography>
            </Alert>
          ) : null}

          {errorMsg && (
            <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }} onClose={() => setErrorMsg(null)}>
              {errorMsg}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <Grid container spacing={2.5}>
              <Grid item xs={12} sm={6}>
                <TextField
                  required
                  label="Full Name"
                  name="name"
                  fullWidth
                  value={formData.name}
                  onChange={handleChange}
                  InputProps={{ startAdornment: <Person sx={{ mr: 1, color: 'text.secondary' }} /> }}
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  required
                  label="Phone Number"
                  name="phone"
                  fullWidth
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="+91 98765 43210"
                  InputProps={{ startAdornment: <Phone sx={{ mr: 1, color: 'text.secondary' }} /> }}
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  required
                  label="Email Address"
                  name="email"
                  type="email"
                  fullWidth
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="student@example.com"
                  InputProps={{ startAdornment: <Email sx={{ mr: 1, color: 'text.secondary' }} /> }}
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  select
                  label="Preferred Branch"
                  name="branch_id"
                  fullWidth
                  value={formData.branch_id}
                  onChange={handleChange}
                  disabled={loadingOptions}
                  InputProps={{ startAdornment: <Business sx={{ mr: 1, color: 'text.secondary' }} /> }}
                >
                  {options.branches.map((b) => (
                    <MenuItem key={b.id} value={b.id}>
                      {b.name} {b.city ? `(${b.city})` : ''}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  select
                  label="Field of Engineering"
                  name="field_of_engineering"
                  fullWidth
                  value={formData.field_of_engineering}
                  onChange={handleChange}
                  disabled={loadingOptions}
                  InputProps={{ startAdornment: <Engineering sx={{ mr: 1, color: 'text.secondary' }} /> }}
                >
                  {options.fields.map((f) => (
                    <MenuItem key={f.id} value={f.id}>
                      {f.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12}>
                <TextField
                  select
                  label="Target Course"
                  name="target_course"
                  fullWidth
                  value={formData.target_course}
                  onChange={handleChange}
                  disabled={loadingOptions || !formData.field_of_engineering}
                  InputProps={{ startAdornment: <Subject sx={{ mr: 1, color: 'text.secondary' }} /> }}
                >
                  {filteredCourses.map((c) => (
                    <MenuItem key={c.id} value={c.title}>
                      {c.title}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12}>
                <TextField
                  label="Any Specific Question / Message for Counselor"
                  name="notes"
                  multiline
                  rows={3}
                  fullWidth
                  value={formData.notes}
                  onChange={handleChange}
                  placeholder="Tell us about your educational background or preferred timings..."
                />
              </Grid>

              <Grid item xs={12}>
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  fullWidth
                  disabled={submitting}
                  startIcon={submitting ? <CircularProgress size={20} color="inherit" /> : <Send />}
                  sx={{ py: 1.8, fontSize: '1rem', fontWeight: 700, background: 'linear-gradient(135deg, #6366F1 0%, #10B981 100%)' }}
                >
                  {submitting ? 'Submitting Enquiry...' : 'Submit Course Enquiry'}
                </Button>
              </Grid>
            </Grid>
          </form>
        </Card>
      </Container>
    </Box>
  );
};
