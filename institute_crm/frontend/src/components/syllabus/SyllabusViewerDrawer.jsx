import React, { useMemo, useState } from 'react';
import {
  Drawer, Box, Typography, Chip, Stack, Button, Divider,
  IconButton, Alert, CircularProgress, Link,
} from '@mui/material';
import { Close, ContentCopy, OpenInNew, Check } from '@mui/icons-material';

/**
 * Slide-out syllabus viewer for counselors (read-only).
 * Props: open, onClose, course {id,code,title,duration_months,total_fee,field_of_engineering,description},
 *        syllabus {title,content,source_url,metadata_json} | null, loading
 */
export const SyllabusViewerDrawer = ({ open, onClose, course, syllabus, loading }) => {
  const [copied, setCopied] = useState(false);

  const tools = useMemo(() => {
    const fromMeta = syllabus?.metadata_json?.tools;
    if (Array.isArray(fromMeta) && fromMeta.length) return fromMeta;
    return [];
  }, [syllabus]);

  const sections = useMemo(() => {
    const content = syllabus?.content || '';
    // Split markdown by ## headings for structured display
    const parts = content.split(/^##\s+/m).map((s) => s.trim()).filter(Boolean);
    // First chunk is header block (title + bullets) if content starts with # 
    return parts;
  }, [syllabus]);

  const handleCopy = async () => {
    if (!course) return;
    const fee = course.total_fee !== null && course.total_fee !== undefined
      ? `Rs.${Number(course.total_fee).toLocaleString('en-IN')}` : 'Contact branch';
    const duration = course.duration_months ? `${course.duration_months} months` : '—';
    const toolsText = tools.length ? tools.join(', ') : 'industry tools';
    const msg = [
      `*${course.title} (${course.code})*`,
      `Discipline: ${course.field_of_engineering || '—'}`,
      `Duration: ${duration} | Fee: ${fee}`,
      `Tools: ${toolsText}`,
      syllabus?.content
        ? `Highlights: ${syllabus.content.slice(0, 400).replace(/[#*`>-]/g, '').trim()}...`
        : (course.description || ''),
      `— Graphix Techno Services, Counselling Desk`,
    ].filter(Boolean).join('\n');
    try {
      await navigator.clipboard.writeText(msg);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard unavailable (non-secure context) — fallback
      const ta = document.createElement('textarea');
      ta.value = msg;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch {}
      document.body.removeChild(ta);
    }
  };

  return (
    <Drawer anchor="right" open={!!open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 560 } } }}>
      <Box sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 2, height: '100%', overflowY: 'auto' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2 }}>
          <Box>
            <Typography variant="overline" color="text.secondary">Course Syllabus</Typography>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              {course?.title || syllabus?.title || 'Syllabus'}
            </Typography>
            {course && (
              <Typography variant="body2" color="text.secondary">
                {course.code} • {course.field_of_engineering || 'General'} • {course.duration_months ? `${course.duration_months} months` : ''} • {course.total_fee ? `Rs.${Number(course.total_fee).toLocaleString('en-IN')}` : ''}
              </Typography>
            )}
          </Box>
          <IconButton onClick={onClose} size="small"><Close /></IconButton>
        </Box>

        {tools.length > 0 && (
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>Software & Tools</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {tools.map((t) => <Chip key={t} label={t} size="small" color="secondary" variant="outlined" />)}
            </Stack>
          </Box>
        )}

        <Divider />

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}><CircularProgress /></Box>
        ) : !syllabus ? (
          <Alert severity="warning">No syllabus uploaded for this course yet. Please check with Branch Admin.</Alert>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {sections.map((sec, i) => (
              <Box key={i}>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{(i > 0 ? '## ' : '') + sec.slice(0, 4000)}</Typography>
                {i < sections.length - 1 && <Divider sx={{ mt: 2 }} />}
              </Box>
            ))}
          </Box>
        )}

        <Divider />

        <Stack direction="row" spacing={1.5}>
          <Button variant="contained" startIcon={copied ? <Check /> : <ContentCopy />} onClick={handleCopy} disabled={!course}>
            {copied ? 'Copied!' : 'Copy Prospect Summary'}
          </Button>
          {syllabus?.source_url && (
            <Button variant="outlined" startIcon={<OpenInNew />} component={Link} href={syllabus.source_url} target="_blank" rel="noreferrer">
              Source / PDF
            </Button>
          )}
          <Box sx={{ flex: 1 }} />
          <Button onClick={onClose}>Close</Button>
        </Stack>
        <Typography variant="caption" color="text.secondary">
          Read-only preview. Counselors cannot edit syllabi — contact Branch Admin for corrections.
        </Typography>
      </Box>
    </Drawer>
  );
};

export default SyllabusViewerDrawer;
