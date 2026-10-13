import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { CaptureService } from '../../services/capture.service';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';

/**
 * "New idea" entry page (T-041, RF-2/RF-7, plan §1.1 "Arranque de la captura").
 *
 * Decides the capture path from `GET /capture/assistant-status`:
 *   - assistant OK: shows the "Modo asistido por IA" toggle (on by default);
 *     with it on the primary action opens the assisted conversation (`POST
 *     /capture/start`, which transparently resumes the unique ACTIVA
 *     conversation, caso 8, or creates it) and moves to the chat; with it off
 *     the primary action goes straight to the manual form.
 *   - assistant UNAVAILABLE: the toggle defaults off and the manual
 *     contingency is deployed with the notice and the prefilled fields (RF-7,
 *     caso 1, RNF-10: nothing is lost).
 *
 * UI copy is in Spanish (RNF-4) and the availability probe shows a visible
 * loading state (RNF-3).
 */
@Component({
  selector: 'app-new-idea',
  templateUrl: './new-idea.html',
  styleUrl: './new-idea.css',
})
export class NewIdea {
  private readonly capture = inject(CaptureService);
  private readonly router = inject(Router);

  /** Page stage machine: probe → branch → (starting | error). */
  readonly fase = signal<'comprobando' | 'disponible' | 'manual' | 'iniciando' | 'error'>('comprobando');
  /** The "asistido por IA" toggle (RF-7): on when the assistant is available. */
  readonly asistido = signal(true);
  readonly error = signal('');

  readonly cargando = this.capture.cargando;
  readonly contingencia = this.capture.contingencia;

  /** Captured fields prefilled for the manual form, as display rows. */
  readonly camposPrellenados = signal<Array<{ campo: string; valor: string }>>([]);

  constructor() {
    void this.comprobar();
  }

  /** Probes the assistant (RNF-3) and picks the assisted vs manual branch. */
  protected async comprobar(): Promise<void> {
    this.error.set('');
    this.camposPrellenados.set([]);
    this.fase.set('comprobando');
    try {
      const status = await this.capture.assistantStatus();
      if (status.status === 'UNAVAILABLE') {
        // RF-7, caso 1: `start` returns the manual payload (notice + prefill).
        this.asistido.set(false);
        await this.capture.iniciar();
        this.levantarPrellenado();
        this.fase.set('manual');
      } else {
        this.asistido.set(true);
        this.fase.set('disponible');
      }
    } catch (err) {
      this.error.set(errorMessage(err));
      this.fase.set('error');
    }
  }

  /** Flips the "asistido por IA" mode between the two capture paths. */
  protected alternarAsistido(): void {
    this.asistido.update((v) => !v);
  }

  /** Opens the assisted conversation (resume-or-create) and moves to the chat. */
  protected async empezar(): Promise<void> {
    this.error.set('');
    this.fase.set('iniciando');
    try {
      const resultado = await this.capture.iniciar();
      if (resultado.mode === 'manual') {
        // The assistant went down between the probe and the start: fall through
        // to the manual contingency (RNF-10).
        this.levantarPrellenado();
        this.fase.set('manual');
        return;
      }
      void this.router.navigate(['/captura/chat-assist']);
    } catch (err) {
      this.error.set(errorMessage(err));
      this.fase.set('disponible');
    }
  }

  /** Continues on the manual form (deployed in G09/T-044). */
  protected irManual(): void {
    void this.router.navigate(['/captura/manual']);
  }

  /** Reads the shared contingency and maps its captured fields to rows. */
  private levantarPrellenado(): void {
    const cont = this.capture.contingencia();
    const campos = cont?.capturedFields ?? {};
    this.camposPrellenados.set(
      Object.entries(campos).map(([campo, valor]) => ({
        campo: this.etiquetaCampo(campo),
        valor: String(valor),
      })),
    );
  }

  private etiquetaCampo(campo: string): string {
    const mapa: Record<string, string> = {
      description: 'Descripción',
      title: 'Título',
      problem: 'Problema u oportunidad',
      expectedBenefit: 'Beneficio esperado',
      strategicAlignment: 'Alineación estratégica',
      estimatedResources: 'Recursos estimados',
      proponent: 'Proponente',
    };
    return mapa[campo] ?? campo;
  }
}
