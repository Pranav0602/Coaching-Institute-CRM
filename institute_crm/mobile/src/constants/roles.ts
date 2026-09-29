/**
 * Role vocabulary, kept byte-identical to `accounts.models.Role` on the server.
 *
 * The server is the only authority on what a role may do - this map exists purely
 * to pick a layout and label. Never gate an action on a check made here.
 */
export const ROLES = {
  SUPER_ADMIN: 'SUPER_ADMIN',
  BRANCH_ADMIN: 'BRANCH_ADMIN',
  ADMISSION_COUNSELOR: 'ADMISSION_COUNSELOR',
  TEACHER: 'TEACHER',
  STUDENT: 'STUDENT',
  PARENT: 'PARENT',
  ACCOUNTANT: 'ACCOUNTANT',
  RECEPTIONIST: 'RECEPTIONIST',
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];

export const ALL_ROLES: Role[] = Object.values(ROLES);

export const ROLE_LABELS: Record<Role, string> = {
  [ROLES.SUPER_ADMIN]: 'Super Admin',
  [ROLES.BRANCH_ADMIN]: 'Branch Admin',
  [ROLES.ADMISSION_COUNSELOR]: 'Admission Counselor',
  [ROLES.TEACHER]: 'Teacher',
  [ROLES.STUDENT]: 'Student',
  [ROLES.PARENT]: 'Parent',
  [ROLES.ACCOUNTANT]: 'Accountant',
  [ROLES.RECEPTIONIST]: 'Receptionist',
};

/**
 * Which persona shell a role lands in. Five shells rather than eight: Super
 * Admin and Branch Admin see the same screens, as do none of the rest, so
 * splitting them would only duplicate navigation code.
 */
export type Persona = 'admin' | 'counsellor' | 'teacher' | 'student' | 'parent' | 'accountant' | 'reception';

export const ROLE_PERSONA: Record<Role, Persona> = {
  [ROLES.SUPER_ADMIN]: 'admin',
  [ROLES.BRANCH_ADMIN]: 'admin',
  [ROLES.ADMISSION_COUNSELOR]: 'counsellor',
  [ROLES.TEACHER]: 'teacher',
  [ROLES.STUDENT]: 'student',
  [ROLES.PARENT]: 'parent',
  [ROLES.ACCOUNTANT]: 'accountant',
  [ROLES.RECEPTIONIST]: 'reception',
};

export const isKnownRole = (value: unknown): value is Role =>
  typeof value === 'string' && (ALL_ROLES as string[]).includes(value);

export const roleLabel = (value: string | null | undefined): string =>
  (isKnownRole(value) ? ROLE_LABELS[value] : undefined) ?? (value ?? 'Unknown');
