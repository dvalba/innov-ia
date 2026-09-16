/**
 * Idea state helpers (T-009, RNF-2): Spanish labels for the three states of
 * plan §2.2/§4.6. The visual mapping (badge) lives in `badge-state`.
 */

import { IdeaState } from '../types/models';

/** Spanish label for an idea state (RNF-4). */
export function estadoLabel(state: IdeaState): string {
  switch (state) {
    case 'EN_DESARROLLO':
      return 'En desarrollo';
    case 'SOLICITANDO_PUBLICACION':
      return 'Solicitando publicación';
    case 'VALIDADA_PUBLICA':
      return 'Validada pública';
  }
}
