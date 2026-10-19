import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { BadgeState } from '../../../../shared/components/badge-state/badge-state';
import { ConfirmDialog } from '../../../../shared/components/confirm-dialog/confirm-dialog';
import { MyIdeasService } from '../../services/my-ideas.service';
import { FieldEditor } from '../../components/field-editor/field-editor';
import { ImprovePanel } from '../../components/improve-panel/improve-panel';
import { RefineView } from '../../components/refine-view/refine-view';
import { RejectNote } from '../../components/reject-note/reject-note';
import {
  CAMPOS_DEF,
  formatearDetalle,
  origenLabel,
} from '../../services/my-idea-fields';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { formatearFecha, formatearDia } from '../../../../shared/utils/format';
import { Idea, IdeaFields, IdeaVersion } from '../../../../shared/types/models';

/**
 * Idea detail (T-047/T-048/T-049/T-050, RF-9/RF-10/RF-8/RF-16).
 *
 * Shows the 6 fields, origin/state/`reviewedByAI` (RNF-2) and the actions for
 * the current state. When `EN_DESARROLLO` the fields are editable (PUT, RNF-9)
 * with a visual block while a generation is in flight (`generando`), plus
 * "Solicitar mejora a la IA" (T-048), the refinement view for manual ideas
 * (T-049) and the publication request (RF-10, available even if the idea was
 * never seen by the IA). When `SOLICITANDO_PUBLICACION` the request date is
 * shown and no editing is allowed. A rejected idea surfaces the expert's
 * comment (`reject-note`, T-050).
 *
 * The page is lazy-loaded per navigation (its `:id`), so the path param is read
 * once from the snapshot and feeds a per-instance `httpResource`
 * (`MyIdeasService.ideaDetalle`), per guideline §5.
 */
@Component({
  selector: 'app-idea-detail',
  imports: [BadgeState, ConfirmDialog, FieldEditor, ImprovePanel, RefineView, RejectNote],
  templateUrl: './detail.html',
})
export class IdeaDetail {
  private readonly ideas = inject(MyIdeasService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  /** The `:id` route parameter, read once for this lazy-loaded instance. */
  readonly ideaId = this.route.snapshot.paramMap.get('id') as string;

  /** `GET /ideas/{id}` -> `{ idea, versions }`. */
  readonly detalle = this.ideas.ideaDetalle(this.ideaId);

  /** `true` while a decide / edit call is in flight. */
  protected readonly operando = signal(false);
  /** The last backend error message to surface (RNF-3). */
  protected readonly error = signal('');
  /** An informational callout (e.g. the manual-editing fallback for the chat). */
  protected readonly info = signal('');
  /** `true` when the publication request is in flight. */
  protected readonly publicando = signal(false);
  /** Whether the "Solicitar publicación" confirm dialog is open (T-056). */
  protected readonly confirmarPublicar = signal(false);

  protected readonly campos = CAMPOS_DEF;
  protected readonly formatearDetalle = formatearDetalle;
  protected readonly formatearFecha = formatearFecha;
  protected readonly formatearDia = formatearDia;
  protected readonly origenLabel = origenLabel;

  // -- idea / versions (read straight from the reactive resource) ------------
  protected idea(): Idea | null {
    return this.detalle.value()?.idea ?? null;
  }

  protected versiones(): IdeaVersion[] {
    return this.detalle.value()?.versions ?? [];
  }

  /** The pending improvement versions for the panel (refinements are decided
   *  in the refine view, not here). */
  protected pendientes(): IdeaVersion[] {
    return this.versiones().filter(
      (v) => v.status === 'PENDIENTE' && v.requestedBy !== 'refinement',
    );
  }

  protected enDesarrollo(): boolean {
    return this.vida() === 'EN_DESARROLLO';
  }

  protected solicitando(): boolean {
    return this.vida() === 'SOLICITANDO_PUBLICACION';
  }

  protected validada(): boolean {
    return this.vida() === 'VALIDADA_PUBLICA';
  }

  protected ideaGenerando(): boolean {
    return !!this.idea()?.generando;
  }

  protected esManual(): boolean {
    return this.idea()?.origin === 'manual';
  }

  /** The newest pending refinement version (T-049 `refine-view`), when any. */
  protected versionRefinada(): IdeaVersion | null {
    const p = this.versiones().filter(
      (v) => v.status === 'PENDIENTE' && v.requestedBy === 'refinement',
    );
    return p.length ? p[p.length - 1] : null;
  }

  private vida(): string {
    return this.idea()?.state ?? '';
  }

  // -- actions ----------------------------------------------------------------
  protected onGuardar(campos: IdeaFields): void {
    if (this.idea()) this.error.set('');
    void this.mutar(() => this.ideas.actualizar(this.ideaId, campos));
  }

  /** Opens the confirm dialog before requesting publication (T-056). */
  protected abrirPublicar(): void {
    this.confirmarPublicar.set(true);
  }

  /** Confirmation accepted: `POST /ideas/{id}/request-publication` (RF-10). */
  protected onPublicar(): void {
    this.confirmarPublicar.set(false);
    this.publicando.set(true);
    this.error.set('');
    this.ideas
      .solicitarPublicacion(this.ideaId)
      .then(() => this.detalle.reload())
      .catch((err) => this.error.set(errorMessage(err)))
      .finally(() => this.publicando.set(false));
  }

  protected onDecidir(v: IdeaVersion, decision: 'accept' | 'discard'): void {
    void this.mutar(() => this.ideas.decidirVersion(this.ideaId, v.id, decision));
  }

  /**
   * "Ajustar detalles en el chat" (T-049): the precontextualized conversation
   * and its backend (G13) are not part of this vertical, so the manual-editing
   * fallback (RF-9) is what is actually available and is surfaced here.
   */
  protected onAjustar(_v: IdeaVersion): void {
    this.info.set(
      'El ajuste conversacional se habilita con el asistente (pendiente de integración). ' +
        'Mientras tanto puedes editar manualmente los campos de la iniciativa.',
    );
  }

  protected mejorado(): void {
    // The panel already reloaded on success; ensure a fresh load here too so the
    // new pending version (or the case-10 request) is rendered.
    this.detalle.reload();
  }

  protected refrescar(): void {
    this.detalle.reload();
  }

  protected descartarError(): void {
    this.error.set('');
  }

  protected descartarInfo(): void {
    this.info.set('');
  }

  protected irAtras(): void {
    void this.router.navigate(['/mis-ideas']);
  }

  private async mutar(f: () => Promise<unknown>): Promise<void> {
    this.operando.set(true);
    this.error.set('');
    try {
      await f();
      this.detalle.reload();
    } catch (err) {
      this.error.set(errorMessage(err));
    } finally {
      this.operando.set(false);
    }
  }
}
