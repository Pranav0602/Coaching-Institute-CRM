import React, { useEffect, useMemo, useState, useCallback } from 'react';
import {
  Box, Typography, TextField, MenuItem, Card, CardContent, Grid,
  Chip, Button, Tabs, Tab, InputAdornment, CircularProgress, Alert, Stack,
} from '@mui/material';
import { Search, MenuBook, Visibility } from '@mui/icons-material';
import api, { unwrapList } from '../services/api';
import { SyllabusViewerDrawer } from '../components/syllabus/SyllabusViewerDrawer';

const CourseSyllabiPage = () => {
  const [courses, setCourses] = useState([]);
  const [docs, setDocs] = useState([]);
  const [masterDoc, setMasterDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [discipline, setDiscipline] = useState('ALL');
  const [tab, setTab] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [syllabus, setSyllabus] = useState(null);
  const [syllabusLoading, setSyllabusLoading] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [courseRes, docRes, masterRes] = await Promise.all([
        api.get('/academics/courses/'),
        api.get('/rag/documents/', { params: { category: 'STUDY_GUIDE' } }).catch(() => ({ data: [] })),
        api.get('/rag/documents/', { params: { category: 'COURSE_CATALOGUE' } }).catch(() => ({ data: [] })),
      ]);
      setCourses(unwrapList(courseRes));
      setDocs(unwrapList(docRes));
      const masters = unwrapList(masterRes);
      setMasterDoc(masters.find((d) => d?.metadata_json?.doc_type === 'MASTER_CATALOGUE') || masters[0] || null);
    } catch (e) {
      setError(e?.detail || e?.message || 'Could not load syllabi.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const disciplines = useMemo(() => {
    const set = new Set(courses.map((c) => c.field_of_engineering).filter(Boolean));
    return ['ALL', ...Array.from(set)];
  }, [courses]);

  const docByCourseId = useMemo(() => {
    const map = {};
    docs.forEach((d) => {
      const cid = d?.metadata_json?.course_id || d?.metadata_json?.courseId;
      if (cid) map[String(cid)] = d;
    });
    return map;
  }, [docs]);

  const filtered = useMemo(() => courses.filter((c) => {
    if (discipline !== 'ALL' && c.field_of_engineering !== discipline) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const doc = docByCourseId[String(c.id)];
      const tools = (doc?.metadata_json?.tools || []).join(' ').toLowerCase();
      return (
        c.title?.toLowerCase().includes(q) ||
        c.code?.toLowerCase().includes(q) ||
        tools.includes(q) ||
        doc?.content?.toLowerCase().includes(q) ||
        c.field_of_engineering?.toLowerCase().includes(q)
      );
    }
    return true;
  }), [courses, discipline, search, docByCourseId]);

  const openSyllabus = async (course) => {
    setSelectedCourse(course);
    setSyllabus(docByCourseId[String(course.id)] || null);
    setDrawerOpen(true);
    // Always try the direct syllabus endpoint for freshest content
    setSyllabusLoading(true);
    try {
      const res = await api.get(`/academics/courses/${course.id}/syllabus/`);
      const data = res?.data ?? res;
      if (data && data.id) setSyllabus(data);
    } catch {
      // keep preloaded doc (or null → "no syllabus" message)
    } finally {
      setSyllabusLoading(false);
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 800 }}>Course Syllabi</Typography>
        <Typography color="text.secondary">Read-only syllabus reference for counselling — search by course, code, tool or topic.</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Card sx={{ mb: 2, p: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth size="small" placeholder="Search courses, tools (e.g. Creo, CATIA, Full Stack, Salesforce)..."
              value={search} onChange={(e) => setSearch(e.target.value)}
              InputProps={{ startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> }}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField select fullWidth size="small" label="Discipline" value={discipline} onChange={(e) => setDiscipline(e.target.value)}>
              {disciplines.map((d) => <MenuItem key={d} value={d}>{d === 'ALL' ? 'All Disciplines' : d}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={12} md={3}>
            <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="fullWidth">
              <Tab label="Syllabuses" />
              <Tab label="Master Catalogue" />
            </Tabs>
          </Grid>
        </Grid>
      </Card>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
      ) : tab === 1 ? (
        <Card><CardContent>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
            {masterDoc?.title || 'Master Catalogue'}
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {masterDoc?.content?.slice(0, 12000) || 'Master catalogue not indexed yet. Ask Branch Admin to run Sync Catalogue in Knowledge Base.'}
          </Typography>
        </CardContent></Card>
      ) : filtered.length === 0 ? (
        <Alert severity="info">No courses match. Try a different search or discipline.</Alert>
      ) : (
        <Grid container spacing={2}>
          {filtered.map((c) => {
            const doc = docByCourseId[String(c.id)];
            const tools = doc?.metadata_json?.tools || [];
            return (
              <Grid item xs={12} sm={6} md={4} key={c.id}>
                <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1, flex: 1 }}>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                      <MenuBook color="primary" fontSize="small" />
                      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{c.title}</Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">{c.code} • {c.field_of_engineering || 'General'} • {c.duration_months ? `${c.duration_months} months` : ''}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {c.total_fee ? `Rs.${Number(c.total_fee).toLocaleString('en-IN')}` : ''} {doc ? '• Syllabus attached' : '• Syllabus pending'}
                    </Typography>
                    {tools.length > 0 && (
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                        {tools.slice(0, 5).map((t) => <Chip key={t} label={t} size="small" variant="outlined" />)}
                        {tools.length > 5 && <Chip label={`+${tools.length - 5}`} size="small" />}
                      </Stack>
                    )}
                    <Box sx={{ mt: 'auto', pt: 1 }}>
                      <Button size="small" variant="contained" startIcon={<Visibility />} onClick={() => openSyllabus(c)}>
                        View Full Syllabus
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}

      <SyllabusViewerDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        course={selectedCourse}
        syllabus={syllabus}
        loading={syllabusLoading}
      />
    </Box>
  );
};

export default CourseSyllabiPage;
export { CourseSyllabiPage };
