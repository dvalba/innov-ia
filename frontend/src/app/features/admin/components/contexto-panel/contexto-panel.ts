import { Component, computed, inject, signal } from '@angular/core';
import { ContextoForm } from '../contexto-form/contexto-form';
import { ContextoSubida } from '../contexto-subida/contexto-subida';
import { ContextoService } from '../../services/contexto.service';

/**
 * Company-context administration section (T-076, RF-21, RNF-12, D13).
 *
 * Combines the three administrative operations over the single document:
 * downloading the `text/plain` template, the online editor (profile + guide
 * text) and the file upload that replaces the whole document. It also shows
 * the visible notice when the document is blank (case 24, RNF-12) and the
 * loading state while the read settles.
 */
@Component({
  selector: 'app-contexto-panel',
  imports: [ContextoForm, ContextoSubida],
  templateUrl: './contexto-panel.html',
})
export class ContextoPanel {
  private readonly contexto = inject(ContextoService);

  /** The reactive read of the current document. */
  protected readonly documento = this.contexto.documento;

  protected readonly cargando = this.documento.isLoading;
  protected readonly descargando = signal(false);

  /**
   * True when the stored document is blank (case 24, RNF-12): a blank profile
   * (no name/sector/description/mission and no strategic objectives) AND a
   * blank guide text — mirrors the backend `CompanyContext.is_empty`.
   */
  protected readonly vacio = computed(() => {
    const doc = this.documento.value();
    if (!doc) return false;
    const p = doc.profile ?? {};
    const perfilVacio =
      !p.name && !p.sector && !p.description && !p.mission && !(p.strategicObjectives ?? []).length;
    return perfilVacio && !String(doc.guideText ?? '').trim();
  });

  protected async onDescargarPlantilla(): Promise<void> {
    if (this.descargando()) return;
    this.descargando.set(true);
    try {
      await this.contexto.descargarPlantilla();
    } finally {
      this.descargando.set(false);
    }
  }
}
