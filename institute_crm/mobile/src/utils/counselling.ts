/**
 * Counselling message templates.
 *
 * A counselor on a call needs to answer "what software, how long, how much" in
 * seconds. These turn a course record into something they can paste into WhatsApp
 * or read aloud, so nobody is copying course titles by hand mid-conversation.
 */
import type { Course, KnowledgeDocument, Lead } from '@/types';
import { formatINR } from './format';

const bullet = (label: string, value: string) => `• ${label}: ${value}`;

export interface CourseFacts {
  title: string;
  code: string;
  duration?: string | null;
  fee?: number | null;
  discipline?: string | null;
  tools: string[];
}

/** The most reliable facts first: the Course row, then the syllabus metadata. */
export const courseFacts = (course?: Course | null, syllabus?: KnowledgeDocument | null): CourseFacts | null => {
  if (!course && !syllabus) return null;
  const meta = syllabus?.metadata_json ?? {};
  const tools = Array.isArray(meta.tools) ? meta.tools : [];
  const durationMonths =
    course?.duration_months ?? (typeof meta.duration_months === 'number' ? meta.duration_months : null);
  return {
    title: course?.title ?? syllabus?.title?.replace(/^Syllabus:\s*/i, '') ?? 'Course',
    code: course?.code ?? meta.code ?? '',
    duration: durationMonths ? `${durationMonths} months` : null,
    fee:
      course?.total_fee != null
        ? Number(course.total_fee)
        : typeof meta.total_fee === 'number'
          ? meta.total_fee
          : null,
    discipline: course?.field_of_engineering ?? meta.field ?? null,
    tools,
  };
};

export const prospectSummary = (facts: CourseFacts, institute = 'Graphix Techno Services'): string =>
  [
    `Hello, thank you for your interest in ${facts.title}.`,
    '',
    `Here are the highlights from ${institute}:`,
    bullet('Course', facts.title + (facts.code ? ` (${facts.code})` : '')),
    facts.discipline ? bullet('Domain', facts.discipline) : null,
    facts.duration ? bullet('Duration', facts.duration) : null,
    facts.fee != null ? bullet('Course fee', formatINR(facts.fee)) : null,
    facts.tools.length ? bullet('Software covered', facts.tools.join(', ')) : null,
    '',
    'We run live, hands-on batches with industry-standard projects and placement support.',
    'Happy to book a free demo class for you - just let me know a convenient time.',
  ]
    .filter((line): line is string => line !== null)
    .join('\n');

export const leadFollowUpMessage = (lead: Lead, facts?: CourseFacts | null): string => {
  const parts = [
    `Hello ${lead.name.split(' ')[0]}, this is from Graphix Techno Services.`,
    facts
      ? `Following up on your enquiry about ${facts.title}${facts.duration ? ` (${facts.duration})` : ''}.`
      : 'Following up on your enquiry.',
  ];
  if (lead.demo_schedule_date) {
    parts.push(`Your demo is scheduled for ${new Date(lead.demo_schedule_date).toLocaleString('en-IN')}.`);
  }
  parts.push('Would a quick 10-minute call today work for you?');
  return parts.join(' ');
};

export const whatsappReplyFor = (lead: Lead, facts?: CourseFacts | null): string =>
  facts ? prospectSummary(facts) : leadFollowUpMessage(lead, facts);

export const reminderMessage = (title: string, body: string, batchName?: string | null): string =>
  [title, body, batchName ? `Batch: ${batchName}` : null, '— Graphix Techno Services']
    .filter(Boolean)
    .join('\n');
