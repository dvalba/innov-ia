import { ROLE_PROPOSER, ROLE_VALIDATOR, ROLE_ADMIN, Usuario } from '../types/models';

/** Role options in the platform's fixed order (UI labels in Spanish, RNF-4). */
export const ROLE_OPCIONES: { code: string; label: string }[] = [
  { code: ROLE_PROPOSER, label: 'Proponente' },
  { code: ROLE_VALIDATOR, label: 'Especialista' },
  { code: ROLE_ADMIN, label: 'Administrador' },
];

/** Spanish label for a role code; unknown codes render as-is. */
export function roleLabel(rol: string): string {
  return ROLE_OPCIONES.find((option) => option.code === rol)?.label ?? rol;
}

/**
 * Last-administrator rule applied in the UI (mirrors `role_rules.py`, RF-17).
 *
 * An operation that would leave the system without an active administrator
 * is blocked: the backend answers 409 and the change is not applied, so the
 * UI pre-blocks the action as an affordance.
 */
export function isLastActiveAdmin(all: Usuario[], target: Usuario): boolean {
  if (!target.active || !target.roles.includes(ROLE_ADMIN)) return false;
  return all.every(
    (user) => user.id === target.id || !user.active || !user.roles.includes(ROLE_ADMIN),
  );
}
