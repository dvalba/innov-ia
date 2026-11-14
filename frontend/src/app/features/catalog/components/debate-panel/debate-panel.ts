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
  * performs its own mutated call (`POST .../debate`) through `CatalogService`
  * (guideline §5: mutations never use `httpResource`) and emits `actualizado`
  * so the parent reloads the resources and the server stays the source of
  * truth (RNF-2).
 *
  * Three renderings (T-085, RF-24/RF-29):
  *   - **open** (default): the full thread + the composer + the (read-only)
  *     closure deadline (T-090: the deadline is fixed at opening, so it is no
  *     longer adjusted here);
  *   - **closed** (default): a compact box — the AI summary (or a "no debate"
  *     notice) and a link to the read-only thread, with no input at all;
  *   - **read-only** (`soloLectura`): the full thread with no composer
  *     (the `/catalogo/publico/{id}/debate` page).
  *
  * The `@asistant` rule is surfaced, not re-implemented (RNF-3/RNF-4; v2.5):
  * a text that starts with `@asistant` asks the assistant inline when it also
  * carries a non-blank request after the token; the message link is *optional*
  * context for the answer (the select appears when the token is detected). The
  * token alone posts as a plain message (case 19), a provided link that does
  * not exist is a 400, and a down assistant keeps the request pending
  * (case 20) with the notice shown below.
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
  /** The optional context message of the `@asistant` invocation (empty = none). */
  protected readonly enlazado = signal('');
  /** `true` while a message post is in flight. */
  protected readonly publicando = signal(false);
  /** The last backend error message to surface (RNF-3). */
  protected readonly error = signal('');

  protected readonly formatearFecha = formatearFecha;

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
      .catch((err) => {
        this.error.set(errorMessage(err));
        // A 409 `DEBATE_CLOSED` means the debate closed on the server (the
        // deadline elapsed while this page was open): reload the read state so
        // the panel switches to the compact closed view instead of keeping a
        // stale composer that would block the chat (RF-24, case 18).
        if (err?.error?.code === 'DEBATE_CLOSED') {
          this.actualizado.emit();
        }
      })
      .finally(() => this.publicando.set(false));
  }

  protected descartarError(): void {
    this.error.set('');
  }

  /** Whether the given message is the assistant (styling, RNF-4). */
  protected esAsistente(m: MensajeDebate): boolean {
    return m.isAssistant;
  }
}
