import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { ContextoService } from '../../services/contexto.service';

const PERFIL_VACIO: {
  name: string;
  sector: string;
  description: string;
  mission: string;
  strategicObjectives: string[];
} = { name: '', sector: '', description: '', mission: '', strategicObjectives: [] };

/**
 * Online company-context editor (T-076, RF-21).
 *
 * Edits the two parts of the single document — the fixed profile (name,
 * sector, description, mission, strategic objectives) and the free guide
 * text. The document read (`httpResource`) is the single source of truth:
 * each field binds straight to it and, on input, updates it in place, so the
 * form, the upload and the panel all stay in sync. On save, the `PUT
 * /admin/contexto` is issued through the dedicated service and the resource
 * is reconciled with the server response (new `updatedAt`). The strategic
 * objectives are edited as a one-per-line textarea (the natural admin
 * affordance) and compiled into the list the backend stores.
 */
@Component({
  selector: 'app-contexto-form',
  imports: [FormsModule],
  templateUrl: './contexto-form.html',
})
export class ContextoForm {
  private readonly contexto = inject(ContextoService);

  /** The reactive read of the current document (single source of truth). */
  protected readonly documento = this.contexto.documento;
  protected readonly cargando = this.documento.isLoading;

  // Projected, blank-safe views of the document for the input bindings.
  protected readonly perfil = computed(() => this.documento.value()?.profile ?? PERFIL_VACIO);
  protected readonly guia = computed(() => this.documento.value()?.guideText ?? '');
  protected readonly updatedAt = computed(() => this.documento.value()?.updatedAt ?? '');
  protected readonly objetivosTexto = computed(
    () => (this.perfil().strategicObjectives ?? []).join('\n'),
  );

  protected readonly guardando = signal(false);
  protected readonly error = signal('');

  /** Updates a profile field in place (blank-safe while the read is pending). */
  protected onPerfilCampo(
    campo: 'name' | 'sector' | 'description' | 'mission',
    valor: string,
  ): void {
    this.documento.update((doc) =>
      doc ? { ...doc, profile: { ...doc.profile, [campo]: valor } } : doc,
    );
  }

  /**
   * Replaces the objectives list from the one-per-line textarea. Stored
   * verbatim (one entry per line) so the textarea round-trips exactly while
   * editing; trims are only applied at save time.
   */
  protected onObjetivos(valor: string): void {
    this.documento.update((doc) =>
      doc
        ? { ...doc, profile: { ...doc.profile, strategicObjectives: valor.split('\n') } }
        : doc,
    );
  }

  /** Updates the free guide text in place. */
  protected onGuia(valor: string): void {
    this.documento.update((doc) => (doc ? { ...doc, guideText: valor } : doc));
  }

  private objetivos(texto: string): string[] {
    return texto
      .split('\n')
      .map((o) => o.trim())
      .filter(Boolean);
  }

  protected async onGuardar(): Promise<void> {
    if (this.guardando()) return;
    this.guardando.set(true);
    this.error.set('');
    try {
      const perfil = this.perfil();
      const guardado = await this.contexto.guardar({
        profile: {
          name: perfil.name.trim(),
          sector: perfil.sector.trim(),
          description: perfil.description.trim(),
          mission: perfil.mission.trim(),
          strategicObjectives: this.objetivos(perfil.strategicObjectives.join('\n')),
        },
        guideText: this.guia(),
      });
      this.documento.set(guardado);
    } catch (err) {
      // 400 blank profile (case 25) or any rejection: the document is
      // unchanged; surface the backend message.
      this.error.set(errorMessage(err));
    } finally {
      this.guardando.set(false);
    }
  }
}
