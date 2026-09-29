/**
 * Role -> navigation group.
 *
 * The persona directories under `app/(app)/` are the source of truth for what
 * each role can reach; this map only decides which one a session lands in.
 * Enforced navigation is not an authorisation control - the API is - but it keeps
 * a user from navigating into a shell that has nothing for them.
 */
import { ROLES, ROLE_PERSONA, type Persona, type Role } from './roles';

export const PERSONA_GROUP: Record<Persona, string> = {
  admin: 'admin',
  counsellor: 'counsellor',
  teacher: 'teacher',
  student: 'student',
  parent: 'parent',
  accountant: 'accountant',
  reception: 'reception',
};

export const personaFor = (role: Role | null | undefined): Persona =>
  (role && ROLE_PERSONA[role]) || 'student';

export const homeFor = (role: Role | null | undefined): string => `/(app)/${PERSONA_GROUP[personaFor(role)]}`;

export const IS_ADMIN = (role: Role | null | undefined): boolean =>
  role === ROLES.SUPER_ADMIN || role === ROLES.BRANCH_ADMIN;
