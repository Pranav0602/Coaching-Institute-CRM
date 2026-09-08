import React from 'react';
import {
  Card, Typography, Chip, Stack, Box, Button,
  FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import { Phone, Storefront, Groups, BookmarkAdded } from '@mui/icons-material';
import { PIPELINE_STAGES } from '../../constants/pipeline';

export const LeadCard = ({
  lead,
  stageColor = '#6366F1',
  batches = [],
  showBatchAssign = false,
  currentStage,
  onStageChange = () => {},
  onAssignBatch = () => {},
  onConvert = () => {},
}) => (
  <Card sx={{ p: 2, borderLeft: `4px solid ${stageColor}`, height: '100%', display: 'flex', flexDirection: 'column', gap: 1.5 }}>
    <Box>
      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{lead.name}</Typography>
      <Typography variant="caption" color="text.secondary">{lead.email}</Typography>
    </Box>

    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      <Chip size="small" icon={<BookmarkAdded sx={{ fontSize: 14 }} />} label={lead.course} title={lead.course} />
      {lead.batch_id ? (
        <Chip size="small" icon={<Groups sx={{ fontSize: 14 }} />} label={`Batch: ${lead.batch}`} title={`${lead.batch} (${lead.batch_code})`} />
      ) : (
        <Chip size="small" variant="outlined" label="Batch: Unassigned" />
      )}
      <Chip size="small" variant="outlined" icon={<Storefront sx={{ fontSize: 14 }} />} label={lead.branch || 'Branch'} />
    </Stack>

    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'text.secondary', fontSize: '0.75rem' }}>
      <Phone sx={{ fontSize: 14 }} /> {lead.phone}
    </Box>

    {showBatchAssign && (
      <FormControl fullWidth size="small">
        <InputLabel sx={{ fontSize: '0.75rem' }}>Assign Batch</InputLabel>
        <Select
          value={lead.batch_id || ''}
          label="Assign Batch"
          size="small"
          sx={{ fontSize: '0.8rem', height: 34 }}
          onChange={(e) => onAssignBatch(lead, e.target.value)}
        >
          <MenuItem value=""><em>Unassigned</em></MenuItem>
          {batches.map(b => (
            <MenuItem key={b.id} value={b.id}>{b.name} ({b.code})</MenuItem>
          ))}
        </Select>
      </FormControl>
    )}

    <Box sx={{ mt: 'auto', display: 'flex', gap: 1 }}>
      <FormControl fullWidth size="small">
        <InputLabel sx={{ fontSize: '0.75rem' }}>Move Stage</InputLabel>
        <Select
          value={currentStage}
          label="Move Stage"
          size="small"
          sx={{ fontSize: '0.8rem', height: 34 }}
          onChange={(e) => onStageChange(lead, e.target.value)}
        >
          {PIPELINE_STAGES.map(s => (
            <MenuItem key={s} value={s} sx={{ fontSize: '0.8rem' }}>{s}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <Button
        size="small"
        variant={currentStage === 'Admitted' ? 'contained' : 'outlined'}
        color={currentStage === 'Admitted' ? 'success' : 'primary'}
        disabled={currentStage === 'Admitted'}
        onClick={() => onConvert(lead)}
      >
        {currentStage === 'Admitted' ? 'Admitted' : 'Convert'}
      </Button>
    </Box>
  </Card>
);