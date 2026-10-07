import { Component, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SugerenciaTitulo, TituloAction } from '../../../../shared/types/models';

/** A title action emitted by the block (RF-4). */
export interface TituloAccion {
  action: TituloAction;
  manualText?: string;
}

/**
 * Proactive title suggestion (T-042, RF-4).
 *
 * Shows the assistant's suggested title (never a fixed list) with the allowed
 * actions: accept it, ask for another, or type one's own — the manual text is
 * stored unmodified. The block is rendered only when the current turn carries
 * a `titleSuggestion`.
 */
@Component({
  selector: 'app-title-suggestion',
  imports: [FormsModule],
  templateUrl: './title-suggestion.html',
  styleUrl: './title-suggestion.css',
})
export class TitleSuggestion {
  /** The suggestion to present. */
  readonly sugerencia = input.required<SugerenciaTitulo>();
  /** Whether a title call is in flight (RNF-3). */
  readonly cargando = input<boolean>(false);

  /** Emits the chosen action (`accept` / `another` / `manual` + own text). */
  readonly accion = output<TituloAccion>();

  /** The typed manual title. */
  readonly textoManual = signal('');

  protected emitir(action: TituloAction, manualText?: string): void {
    if (this.cargando()) return;
    this.accion.emit({ action, manualText });
    this.textoManual.set('');
  }

  protected onManual(): void {
    const texto = this.textoManual().trim();
    if (!texto) return;
    this.emitir('manual', texto);
  }
}
