import { SlicePipe } from '@angular/common';
import { Component, inject, input, output, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CatalogService } from '../../services/catalog.service';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { formatearFecha } from '../../../../shared/utils/format';
import { Debate, MensajeDebate } from '../../../../shared/types/models';

/**
 * Published-idea debate panel (T-077, RF-24/RF-25, cases 18-21; T-085:
 * compact closure + read-only view).
 *
 * Renders the public debate of one published idea and its mutations. The read
 * state (messages, deadline, closure, the AI summary, the pending `@asistant`)
 * is passed in as an input from the parent's reactive resource; the panel
 * performs its own mutated calls (`POST .../debate`, the admin `PUT .../debate/
 * deadline`) through `CatalogService` (guideline §5: mutations never use
 * `httpResource`) and emits `actualizado` so the parent reloads the resources
 * and the server stays the source of truth (RNF-2).
 *
 * Three renderings (T-085, RF-24/RF-29):
 *   - **open** (default): the full thread + the composer + the admin-only
 *     deadline adjustment;
 *   - **closed** (default): a compact box — the AI summary (or a "no debate"
 *     notice) and a link to the read-only thread, with no input at all;
 *   - **read-only** (`soloLectura`): the full thread with no composer and no
 *     deadline control (the `/catalogo/publico/{id}/debate` page).
 *
 * The `@asistant` rule is surfaced, not re-implemented (RNF-3/RNF-4): a text
 * that starts with `@asistant` only asks the assistant when it also links an
 * existing message of the thread (case 19); without a link it posts as a plain
 * message, and a down assistant keeps the request pending (case 20) with the
 * notice shown below. The closure deadline and its admin-only adjustment (with
 * its audit trace) complete the panel (RNF-11).
 */
@Component({
  selector: 'app-debate-panel',
  imports: [SlicePipe, RouterLink],
  templateUrl: './debate-panel.html',
})
export class DebatePanel {
  /** The id of the idea whose debate is shown. */
  readonly ideaId = input.required<string>();
  /** The current debate read state (from the parent resource). */
  readonly debate = input<Debate | null>(null);
  /** `true` for an administrator (may adjust the deadline, RF-24). */
  readonly esAdmin = input(false);
  /**
   * `true` to render the read-only thread (no composer, no deadline control):
   * the `/catalogo/publico/{id}/debate` page (T-085, RF-24).
   */
  readonly soloLectura = input(false);
  /** A mutation finished (post / deadline) so the parent can reload. */
  readonly actualizado = output<void>();

  private readonly catalogo = inject(CatalogService);

  /** The composer text. */
  protected readonly texto = signal('');
  /** The message the `@asistant` invocation links (empty = no link). */
  protected readonly enlazado = signal('');
  /** The admin's draft new deadline (pre-filled with the current one). */
  protected readonly fechaAjuste = signal('');
  /** `true` while the admin's deadline control is revealed. */
  protected readonly ajustando = signal(false);
  /** `true` while a message post is in flight. */
  protected readonly publicando = signal(false);
  /** `true` while the deadline adjustment is in flight. */
  protected readonly ajustandoLimite = signal(false);
  /** The last backend error message to surface (RNF-3). */
  protected readonly error = signal('');

  protected readonly formatearFecha = formatearFecha;

  /** The current deadline in the `datetime-local` format (`YYYY-MM-DDTHH:mm`). */
  protected fechaInputLimite(): string {
    const iso = this.debate()?.deadline;
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  /** `true` when the composer text starts with the `@asistant` token (RF-25). */
  protected esInvocacion(): boolean {
    return this.texto().trimStart().startsWith('@asistant');
  }

  protected publicar(): void {
    const texto = this.texto().trim();
    if (!texto) return;
    this.publicando.set(true);
    this.error.set('');
    void this.catalogo
      .publicarMensaje(this.ideaId(), texto, this.enlazado() || null)
      .then(() => {
        this.texto.set('');
        this.enlazado.set('');
        this.actualizado.emit();
      })
      .catch((err) => this.error.set(errorMessage(err)))
      .finally(() => this.publicando.set(false));
  }

  protected mostrarAjuste(): void {
    this.ajustando.set(true);
    this.fechaAjuste.set(this.fechaInputLimite());
    this.error.set('');
  }

  protected ajustarLimite(): void {
    const nueva = this.fechaAjuste();
    if (!nueva) return;
    this.ajustandoLimite.set(true);
    this.error.set('');
    void this.catalogo
      .ajustarFechaLimite(this.ideaId(), nueva)
      .then(() => {
        this.ajustando.set(false);
        this.actualizado.emit();
      })
      .catch((err) => this.error.set(errorMessage(err)))
      .finally(() => this.ajustandoLimite.set(false));
  }

  protected descartarError(): void {
    this.error.set('');
  }

  /** Whether the given message is the assistant (styling, RNF-4). */
  protected esAsistente(m: MensajeDebate): boolean {
    return m.isAssistant;
  }
}
