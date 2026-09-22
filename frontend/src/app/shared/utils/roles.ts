import { ROLE_PROPOSER, ROLE_VALIDATOR, ROLE_ADMIN } from '../types/models';

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
