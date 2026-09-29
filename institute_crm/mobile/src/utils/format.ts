/** Presentation helpers shared across every screen. */

const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const compactCurrency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  notation: 'compact',
  maximumFractionDigits: 1,
});

/** Rupees, Indian digit grouping, no decimals. Matches the web CRM's `Rs.` format. */
export const formatINR = (value: number | string | null | undefined): string => {
  const amount = typeof value === 'string' ? Number(value) : value;
  if (amount === null || amount === undefined || Number.isNaN(amount)) return 'Rs.0';
  return currency.format(amount);
};

export const formatCompactINR = (value: number | string | null | undefined): string => {
  const amount = typeof value === 'string' ? Number(value) : value;
  if (amount === null || amount === undefined || Number.isNaN(amount)) return 'Rs.0';
  return compactCurrency.format(amount);
};

export const formatNumber = (value: number | null | undefined): string =>
  value === null || value === undefined || Number.isNaN(value) ? '0' : new Intl.NumberFormat('en-IN').format(value);

const parseDate = (value: string | Date | null | undefined): Date | null => {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
};

export const formatDate = (value: string | Date | null | undefined): string => {
  const date = parseDate(value);
  return date ? date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
};

export const formatDateTime = (value: string | Date | null | undefined): string => {
  const date = parseDate(value);
  return date
    ? date.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      })
    : '—';
};

export const formatTime = (value: string | Date | null | undefined): string => {
  const date = parseDate(value);
  return date
    ? date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })
    : '—';
};

/** "2 hours ago" / "in 3 days" - the format people actually scan a list for. */
export const formatRelative = (value: string | Date | null | undefined): string => {
  const date = parseDate(value);
  if (!date) return '—';
  const deltaMs = date.getTime() - Date.now();
  const abs = Math.abs(deltaMs);
  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['year', 31_536_000_000],
    ['month', 2_592_000_000],
    ['day', 86_400_000],
    ['hour', 3_600_000],
    ['minute', 60_000],
  ];
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  for (const [unit, ms] of units) {
    if (abs >= ms) return rtf.format(Math.round(deltaMs / ms), unit);
  }
  return 'just now';
};

export const isOverdue = (dueDate: string | null | undefined): boolean => {
  const date = parseDate(dueDate);
  return date !== null && date.getTime() < Date.now();
};

export const initials = (name?: string | null): string => {
  if (!name) return '?';
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
};

export const DAY_ORDER = [
  'MONDAY',
  'TUESDAY',
  'WEDNESDAY',
  'THURSDAY',
  'FRIDAY',
  'SATURDAY',
  'SUNDAY',
] as const;

export const dayLabel = (code: string | null | undefined): string =>
  code ? code.charAt(0) + code.slice(1).toLowerCase() : '—';

export const currentDayCode = (): string => {
  const names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  return names[new Date().getDay()].toUpperCase();
};

/** Indian mobile numbers are stored inconsistently; normalise before dialling. */
export const normalisePhone = (phone: string | null | undefined): string => {
  if (!phone) return '';
  const digits = phone.replace(/\D/g, '');
  if (digits.length === 10) return `+91${digits}`;
  if (digits.length === 12 && digits.startsWith('91')) return `+${digits}`;
  return phone.trim();
};

export const maskPhone = (phone: string | null | undefined): string => {
  const normalised = normalisePhone(phone);
  if (normalised.length < 6) return normalised || '—';
  return `${normalised.slice(0, 4)}••••${normalised.slice(-3)}`;
};
