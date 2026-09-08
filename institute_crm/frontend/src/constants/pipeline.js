export const PIPELINE_STAGES = [
  'New',
  'Contacted',
  'Interested',
  'Demo Scheduled',
  'Demo Attended',
  'Admission Pending',
  'Admitted',
  'Lost',
];

export const STAGE_COLORS = {
  'New': '#6366F1',
  'Contacted': '#0EA5E9',
  'Interested': '#F59E0B',
  'Demo Scheduled': '#8B5CF6',
  'Demo Attended': '#EC4899',
  'Admission Pending': '#14B8A6',
  'Admitted': '#22C55E',
  'Lost': '#EF4444',
};

export const STAGE_DESCRIPTIONS = {
  'New': 'Fresh enquiries awaiting first contact',
  'Contacted': 'Counselor has reached out to the lead',
  'Interested': 'Lead showed concrete interest in a course',
  'Demo Scheduled': 'A demo class has been scheduled',
  'Demo Attended': 'Lead attended the demo session',
  'Admission Pending': 'Documents and fees under finalization',
  'Admitted': 'Lead converted to a student account',
  'Lost': 'Lead disengaged or chose not to join',
};