import { Component, input } from '@angular/core';
import { NotaRechazo } from '../../../../shared/types/models';
import { formatearFecha } from '../../../../shared/utils/format';

/**
 * Rejection note (T-050, RF-16, case 13).
 *
 * When the expert rejected the idea, shows the comment with who rejected it
 * (name) and when. Rendered in the idea detail so the proponent can read the
 * decision and act on it. UI copy in Spanish (RNF-4).
 */
@Component({
  selector: 'app-reject-note',
  templateUrl: './reject-note.html',
})
export class RejectNote {
  /** The expert's rejection note. */
  readonly nota = input.required<NotaRechazo>();

  protected readonly formatearFecha = formatearFecha;
}
