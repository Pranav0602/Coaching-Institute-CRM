import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Button, Card, CardContent, Chip, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, MenuItem, Stack, Typography, Grid, IconButton, Alert, Tabs, Tab, Tooltip,
  Table, TableHead, TableBody, TableRow, TableCell, Skeleton, InputAdornment, Divider
} from '@mui/material';
import {
  Add, DeleteOutline, EditOutlined, CloudUpload, Article, MenuBook,
  Quiz, Policy, History, Sync, Visibility, VisibilityOff, Search
} from '@mui/icons-material';
import api from '../services/api';
import { PageHeader, MetricCards } from './PageLayout';

const CATEGORY_OPTIONS = [
  { value: 'ADMISSION_POLICY', label: 'Admission Policy', icon: <Policy fontSize="small" /> },
  { value: 'FAQ', label: 'FAQ', icon: <Quiz fontSize="small" /> },
  { value: 'STUDY_GUIDE', label: 'Course Syllabus / Study Guide', icon: <MenuBook fontSize="small" /> },
  { value: 'COURSE_CATALOGUE', label: 'Course Catalogue', icon: <Article fontSize="small" /> },
  { value: 'BATCH_SCHEDULE', label: 'Batch Schedule', icon: <History fontSize="small" /> },
  { value: 'GENERAL', label: 'General Information', icon: <Article fontSize="small" /> },
];

const CATEGORY_LABELS = Object.fromEntries(CATEGORY_OPTIONS.map(o => [o.value, o.label]));

const CATEGORY_COLOR = {
  ADMISSION_POLICY: 'primary',
  FAQ: 'info',
  STUDY_GUIDE: 'success',
  COURSE_CATALOGUE: 'secondary',
  BATCH_SCHEDULE: 'warning',
  GENERAL: 'default',
};

function TabPanel({ children, value, index }) {
  return value === index ? <Box sx={{ pt: 2 }}>{children}</Box> : null;
}

const KnowledgeBasePage = () => {
  const [documents, setDocuments] = useState([]);
  const [courses, setCourses] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterCategory, setFilterCategory] = useState('ALL');
  const [search, setSearch] = useState('');
  const [syncing, setSyncing] = useState(false);

  // dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDoc, setEditingDoc] = useState(null);
  const [formTab, setFormTab] = useState(0); // 0=write, 1=upload
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    title: '',
    category: 'ADMISSION_POLICY',
    content: '',
    source_url: '',
    is_published: true,
    linked_course: '',
  });
  const [fileName, setFileName] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [docRes, courseRes, statsRes] = await Promise.all([
        api.get('/rag/documents/'),
        api.get('/academics/courses/').catch(() => ({ data: [] })),
        api.get('/rag/stats/').catch(() => null),
      ]);
      const docs = Array.isArray(docRes?.data) ? docRes.data : (Array.isArray(docRes) ? docRes : docRes?.data?.results || []);
      // handle paginated response
      const docList = Array.isArray(docs) ? docs : (docs?.results || []);
      // fallback: if docRes is {data: [...]}
      const finalDocs = Array.isArray(docRes?.data) ? docRes.data : docList.length ? docList : [];
      // Another fallback try raw array
      const raw = docRes?.data ?? docRes;
      const normalized = Array.isArray(raw) ? raw : (raw?.results ?? finalDocs ?? []);
      setDocuments(Array.isArray(normalized) ? normalized : []);
      setCourses(Array.isArray(courseRes?.data) ? courseRes.data : []);
      if (statsRes?.data) setStats(statsRes.data);
      else if (statsRes) setStats(statsRes);
    } catch (e) {
      setError(e?.detail || e?.message || 'Could not load knowledge base. Please ensure the API is running.');
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const resetForm = (doc = null, categoryOverride = null) => {
    if (doc) {
      const linkedCourse = doc.metadata_json?.course_id || doc.metadata_json?.courseId || '';
      setForm({
        title: doc.title || '',
        category: doc.category || 'GENERAL',
        content: doc.content || '',
        source_url: doc.source_url || '',
        is_published: doc.is_published ?? true,
        linked_course: linkedCourse,
      });
      setEditingDoc(doc);
    } else {
      setForm({
        title: '',
        category: categoryOverride || 'ADMISSION_POLICY',
        content: '',
        source_url: '',
        is_published: true,
        linked_course: '',
      });
      setEditingDoc(null);
    }
    setFormTab(0);
    setFileName('');
    setFormError(null);
  };

  const handleOpenCreate = (category = 'ADMISSION_POLICY') => {
    resetForm(null, category);
    setDialogOpen(true);
  };

  const handleOpenEdit = (doc) => {
    resetForm(doc);
    setDialogOpen(true);
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const allowedText = ['text/plain', 'text/markdown', 'text/csv'];
    try {
      let text = '';
      if (allowedText.includes(file.type) || file.name.match(/\.(txt|md|csv)$/i)) {
        text = await file.text();
      } else if (file.name.match(/\.(pdf|docx|doc)$/i)) {
        // For PDF/DOCX we read as text fallback and instruct user to paste; real extraction would happen server-side
        // Try to read as text (will be garbled for binary but we still allow)
        try { text = await file.text(); } catch { text = ''; }
        if (!text || text.length < 20 || text.includes('\uFFFD')) {
          setFormError('PDF/DOCX direct parsing is not supported in-browser. Please copy-paste the text into the Write tab, or upload a .txt/.md file.');
          return;
        }
      } else {
        text = await file.text();
      }
      setForm(prev => ({ ...prev, content: text }));
      if (!form.title && file.name) {
        const base = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ');
        setForm(prev => ({ ...prev, title: prev.title || base }));
      }
      setFormError(null);
      setFormTab(0); // switch to write tab to show content
    } catch (err) {
      setFormError('Could not read file. Please try a .txt or .md file.');
    }
  };

  const handleSubmit = async () => {
    if (!form.title.trim()) { setFormError('Title is required.'); return; }
    if (!form.content.trim()) { setFormError('Content is required. The document will be chunked and embedded for retrieval.'); return; }
    if (!form.category) { setFormError('Category is required.'); return; }
    const needsCourse = ['STUDY_GUIDE', 'COURSE_CATALOGUE'].includes(form.category);
    if (needsCourse && !form.linked_course) {
      setFormError('Please select a course to link this syllabus/catalogue entry.');
      return;
    }

    setSubmitting(true);
    setFormError(null);
    try {
      const payload = {
        title: form.title.trim(),
        category: form.category,
        content: form.content.trim(),
        source_url: form.source_url?.trim() || null,
        is_published: !!form.is_published,
      };
      // Store course link in metadata_json via version field? Backend serializer doesn't expose metadata_json but model supports it.
      // We send linked course info inside content prefix + metadata_json if backend accepts it.
      // Check if backend accepts metadata_json: add it if present in API
      if (form.linked_course) {
        payload.metadata_json = { course_id: form.linked_course };
        // Also prefix content with structured header for better retrieval
        const courseTitle = courses.find(c => String(c.id) === String(form.linked_course))?.title || '';
        if (courseTitle && !payload.content.includes(courseTitle)) {
          payload.content = `Course: ${courseTitle}\n${payload.content}`;
        }
      }

      if (editingDoc) {
        await api.patch(`/rag/documents/${editingDoc.id}/`, payload);
      } else {
        await api.post('/rag/documents/', payload);
      }
      setDialogOpen(false);
      setEditingDoc(null);
      await fetchData();
    } catch (err) {
      const detail = err?.detail || err?.message || (err?.errors ? JSON.stringify(err.errors) : null) || 'Could not save document.';
      // Try to extract field errors
      if (err?.errors) {
        const msg = Object.entries(err.errors).map(([k,v]) => `${k}: ${Array.isArray(v)?v.join(', '):v}`).join(' ');
        setFormError(msg);
      } else if (err?.data?.detail) {
        setFormError(err.data.detail);
      } else {
        setFormError(detail);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (doc) => {
    if (!window.confirm(`Delete "${doc.title}" ? Its chunks will be removed from the vector store.`)) return;
    try {
      await api.delete(`/rag/documents/${doc.id}/`);
      fetchData();
    } catch (e) {
      alert(e?.detail || 'Could not delete document.');
    }
  };

  const handleTogglePublish = async (doc) => {
    try {
      await api.patch(`/rag/documents/${doc.id}/`, { is_published: !doc.is_published });
      fetchData();
    } catch (e) {
      alert(e?.detail || 'Could not update publish status.');
    }
  };

  const handleSyncCatalogue = async () => {
    setSyncing(true);
    try {
      await api.post('/rag/ingest/');
      await fetchData();
    } catch (e) {
      alert(e?.detail || 'Catalogue sync failed.');
    } finally {
      setSyncing(false);
    }
  };

  // derived metrics & filtered list
  const filtered = documents.filter(d => {
    if (filterCategory !== 'ALL' && d.category !== filterCategory) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (d.title?.toLowerCase().includes(q) || d.content?.toLowerCase().includes(q) || d.category?.toLowerCase().includes(q));
    }
    return true;
  });

  const metrics = [
    { label: 'Total Documents', value: documents.length },
    { label: 'Chunks Indexed', value: stats?.chunks_count ?? documents.reduce((s,d)=> s+(d.chunks_count||0),0) },
    { label: 'Published', value: documents.filter(d=>d.is_published).length, color: 'success.main' },
    { label: 'Queries Served', value: stats?.queries_served ?? '—' },
  ];

  const needsCourseField = ['STUDY_GUIDE', 'COURSE_CATALOGUE'].includes(form.category);

  return (
    <Box>
      <PageHeader
        title="Knowledge Base"
        subtitle="Manage Admission Policy, Refund Policy, FAQs and Course Syllabi for the RAG assistant. All published documents are automatically chunked and embedded."
        action="Add Document"
        onAction={() => handleOpenCreate('ADMISSION_POLICY')}
      />

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!loading && <MetricCards items={metrics} />}

      {/* Category quick-create cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', borderLeft: '4px solid', borderLeftColor: 'primary.main' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Policy color="primary" /><Typography variant="subtitle2" fontWeight={700}>Admission Policy</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, minHeight: 40 }}>Admissions, eligibility and refund policies shown to prospects.</Typography>
              <Button size="small" variant="outlined" startIcon={<Add />} onClick={() => handleOpenCreate('ADMISSION_POLICY')}>New Admission Policy</Button>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', borderLeft: '4px solid', borderLeftColor: 'info.main' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Article color="info" /><Typography variant="subtitle2" fontWeight={700}>Refund Policy</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, minHeight: 40 }}>Refund windows, deductions and process. Uses Admission Policy category.</Typography>
              <Button size="small" variant="outlined" color="info" startIcon={<Add />} onClick={() => handleOpenCreate('ADMISSION_POLICY')}>New Refund Policy</Button>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', borderLeft: '4px solid', borderLeftColor: 'warning.main' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Quiz color="warning" /><Typography variant="subtitle2" fontWeight={700}>FAQ</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, minHeight: 40 }}>Frequently asked questions answered with citations.</Typography>
              <Button size="small" variant="outlined" color="warning" startIcon={<Add />} onClick={() => handleOpenCreate('FAQ')}>New FAQ</Button>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', borderLeft: '4px solid', borderLeftColor: 'success.main' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <MenuBook color="success" /><Typography variant="subtitle2" fontWeight={700}>Course Syllabus</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, minHeight: 40 }}>Structured syllabus linked to a course. Auto-indexed for course queries.</Typography>
              <Button size="small" variant="outlined" color="success" startIcon={<Add />} onClick={() => handleOpenCreate('STUDY_GUIDE')}>New Syllabus</Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Toolbar */}
      <Card sx={{ mb: 2, p: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={5}>
            <TextField
              fullWidth size="small" placeholder="Search by title or content..."
              value={search} onChange={e=>setSearch(e.target.value)}
              InputProps={{ startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> }}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField select fullWidth size="small" label="Category" value={filterCategory} onChange={e=>setFilterCategory(e.target.value)}>
              <MenuItem value="ALL">All Categories</MenuItem>
              {CATEGORY_OPTIONS.map(o=> <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={12} md={4} sx={{ display: 'flex', gap: 1, justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
            <Tooltip title="Re-index all courses & built-in FAQs into the vector store">
              <Button variant="outlined" startIcon={<Sync />} onClick={handleSyncCatalogue} disabled={syncing}>
                {syncing ? 'Syncing…' : 'Sync Catalogue'}
              </Button>
            </Tooltip>
            <Button variant="contained" startIcon={<Add />} onClick={() => handleOpenCreate()}>Add Document</Button>
          </Grid>
        </Grid>
      </Card>

      {/* Documents table */}
      <Card sx={{ overflow: 'hidden' }}>
        <Box sx={{ p: 2.5, pb: 1.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" fontWeight={700}>Knowledge documents</Typography>
          <Chip label={`${filtered.length} / ${documents.length}`} size="small" variant="outlined" />
        </Box>
        <Box sx={{ overflowX: 'auto' }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Title</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Category</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Course Link</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Chunks</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Published</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Updated</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                Array.from({length:5}).map((_,i)=>(
                  <TableRow key={i}><TableCell colSpan={7}><Skeleton height={30} /></TableCell></TableRow>
                ))
              ) : filtered.length===0 ? (
                <TableRow><TableCell colSpan={7} align="center"><Typography color="text.secondary" sx={{py:3}}>
                  {documents.length===0 ? 'No documents yet. Use the cards above to create Admission Policy, FAQ or a Course Syllabus.' : 'No documents match the current filter.'}
                </Typography></TableCell></TableRow>
              ) : filtered.map(doc=> {
                const linkedCourseId = doc.metadata_json?.course_id;
                const linkedCourseTitle = linkedCourseId ? (courses.find(c=> String(c.id)===String(linkedCourseId))?.title || linkedCourseId) : '—';
                return (
                  <TableRow key={doc.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600} sx={{ maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.title}</Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.content?.slice(0,120)}…</Typography>
                    </TableCell>
                    <TableCell><Chip label={CATEGORY_LABELS[doc.category] || doc.category} size="small" color={CATEGORY_COLOR[doc.category]||'default'} variant="outlined" /></TableCell>
                    <TableCell><Typography variant="body2">{linkedCourseTitle}</Typography></TableCell>
                    <TableCell>{doc.chunks_count ?? '—'}</TableCell>
                    <TableCell>
                      <Chip
                        label={doc.is_published ? 'Published' : 'Draft'}
                        size="small"
                        color={doc.is_published ? 'success' : 'default'}
                        icon={doc.is_published ? <Visibility sx={{fontSize:16}}/> : <VisibilityOff sx={{fontSize:16}}/>}
                      />
                    </TableCell>
                    <TableCell><Typography variant="caption">{doc.updated_at ? new Date(doc.updated_at).toLocaleDateString() : '—'}</Typography></TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                        <Tooltip title={doc.is_published ? 'Unpublish (hide from RAG)' : 'Publish (make available to RAG)'}>
                          <IconButton size="small" onClick={()=>handleTogglePublish(doc)}>
                            {doc.is_published ? <VisibilityOff fontSize="small"/> : <Visibility fontSize="small" color="success"/>}
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Edit"><IconButton size="small" onClick={()=>handleOpenEdit(doc)}><EditOutlined fontSize="small"/></IconButton></Tooltip>
                        <Tooltip title="Delete"><IconButton size="small" onClick={()=>handleDelete(doc)}><DeleteOutline fontSize="small" color="error"/></IconButton></Tooltip>
                      </Stack>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Box>
      </Card>

      <Alert severity="info" sx={{ mt: 2 }}>
        All saves automatically chunk (500 words, 100 overlap), embed and upsert into <code>pgvector</code> via <code>IngestionService.index_document</code>. Use Sync Catalogue to re-index existing courses and built-in FAQs.
      </Alert>

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onClose={()=>setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          {editingDoc ? `Edit: ${editingDoc.title}` : 'Add Knowledge Document'}
        </DialogTitle>
        <DialogContent dividers>
          {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}

          <Stack spacing={2}>
            <TextField
              label="Title" required fullWidth
              value={form.title} onChange={e=>setForm(p=>({...p, title: e.target.value}))}
              placeholder={form.category==='ADMISSION_POLICY' ? 'e.g. Admission Policy – 2026 Batch' : form.category==='FAQ' ? 'e.g. What documents are required for admission?' : 'e.g. Full Stack Development – Syllabus'}
            />
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField select fullWidth required label="Category" value={form.category} onChange={e=>setForm(p=>({...p, category: e.target.value}))}>
                  {CATEGORY_OPTIONS.map(o=> <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>)}
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField select fullWidth label="Published" value={String(form.is_published)} onChange={e=>setForm(p=>({...p, is_published: e.target.value==='true'}))}>
                  <MenuItem value="true">Published – visible to RAG retrieval</MenuItem>
                  <MenuItem value="false">Draft – hidden from RAG</MenuItem>
                </TextField>
              </Grid>
            </Grid>

            {needsCourseField && (
              <TextField
                select fullWidth required label="Linked Course" helperText="Syllabus / catalogue entries must be linked to a course so the assistant can scope answers."
                value={form.linked_course} onChange={e=>setForm(p=>({...p, linked_course: e.target.value}))}
              >
                {courses.length===0 && <MenuItem disabled value="">No courses found – create one at /create-course first</MenuItem>}
                {courses.map(c=> <MenuItem key={c.id} value={c.id}>{c.title} ({c.code})</MenuItem>)}
              </TextField>
            )}

            <TextField fullWidth label="Source URL (optional)" placeholder="https://…" value={form.source_url} onChange={e=>setForm(p=>({...p, source_url: e.target.value}))} />

            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={formTab} onChange={(_,v)=>setFormTab(v)} aria-label="content input tabs">
                <Tab label="Write Content" icon={<EditOutlined />} iconPosition="start" />
                <Tab label="Upload File" icon={<CloudUpload />} iconPosition="start" />
              </Tabs>
            </Box>

            <TabPanel value={formTab} index={0}>
              <TextField
                fullWidth multiline minRows={8} label="Content" required
                value={form.content} onChange={e=>setForm(p=>({...p, content: e.target.value}))}
                placeholder={
                  form.category==='ADMISSION_POLICY'
                    ? 'Admission Policy & Refund Policy:\n1. Eligibility...\n2. Fee structure...\n3. Refund: full within 7 days minus 10% registration…'
                    : form.category==='FAQ'
                    ? 'Q: What documents are needed?\nA: ...\n\nQ: ...'
                    : form.category==='STUDY_GUIDE'
                    ? 'Module 1: HTML/CSS fundamentals...\nModule 2: JavaScript...\nModule 3: ...\nLearning outcomes...\nEligibility...\nDuration...'
                    : 'Enter the knowledge content that will be chunked and embedded.'
                }
                helperText={`${form.content.split(/\s+/).filter(Boolean).length} words • Will be split into ~500-word chunks with 100-word overlap`}
              />
            </TabPanel>

            <TabPanel value={formTab} index={1}>
              <Box sx={{ border: '1px dashed', borderColor: 'divider', borderRadius: 2, p: 3, textAlign: 'center', bgcolor: 'background.default' }}>
                <CloudUpload sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
                <Typography variant="body2" fontWeight={600} gutterBottom>Upload a document</Typography>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                  Supports .txt, .md, .csv directly. For PDF/DOCX, copy-paste text into the Write tab (browser cannot reliably extract PDFs).
                </Typography>
                <Button variant="outlined" component="label" startIcon={<CloudUpload />}>
                  Choose File
                  <input hidden type="file" accept=".txt,.md,.csv,.pdf,.docx,.doc" onChange={handleFileChange} />
                </Button>
                {fileName && <Typography variant="caption" display="block" sx={{ mt: 1.5 }}>Selected: {fileName} — {form.content.split(/\s+/).filter(Boolean).length} words loaded</Typography>}
                {form.content && <Alert severity="success" sx={{ mt: 2, textAlign: 'left' }}>Content loaded. Switch to Write tab to review/edit before saving. The document will be auto-indexed on save.</Alert>}
              </Box>
            </TabPanel>

          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={()=>setDialogOpen(false)} disabled={submitting}>Cancel</Button>
          <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
            {submitting ? 'Saving & Indexing…' : editingDoc ? 'Save & Re-index' : 'Create & Index'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default KnowledgeBasePage;
export { KnowledgeBasePage };
