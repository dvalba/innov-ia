import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CaptureService } from '../../services/capture.service';
import { FormResumen, construirResumen, resumenCompleto } from '../../services/fieldsMeta';
import { SessionService } from '../../../../shared/services/session.service';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';

const FORM_VACIO: FormResumen = {
  title: '',
  description: '',
  problem: '',
  expectedBenefit: '',
  strategicAlignment: '',
  proponent: { name: '', area: '', contact: '' },
  estimatedResources: { time: '', people: '', budget: '' },
};

/**
 * Manual capture form (T-044, RF-7).
 *
 * Covers the capture without the assistant (caso 1, G08) and the mid-conversation
 * contingency (T-045): it deploys the 7 mandatory fields, prefills the proponent
 * from the account (correctable) and any field the assistant already captured
 * (the shared `contingencia.capturedFields`; RNF-10 — nothing is lost), gates the
 * submit on non-empty + a valid contact (case 12), and posts to `POST /ideas`
 * with origin `manual`. On a failed send the data stays on screen (caso 17).
 */
@Component({
  selector: 'app-manual-idea',
  imports: [FormsModule],
  templateUrl: './manual.html',
  styleUrl: './manual.css',
})
export class ManualIdea implements OnInit {
  private readonly capture = inject(CaptureService);
  private readonly router = inject(Router);
  private readonly session = inject(SessionService);

  readonly formulario = signal<FormResumen>(FORM_VACIO);
  readonly enviando = signal(false);
  readonly error = signal('');
  readonly contingencia = this.capture.contingencia;

  ngOnInit(): void {
    const base = this.contingencia()?.capturedFields ?? {};
    const user = this.session.usuario();
    const cuenta = user
      ? { name: user.name, area: user.area, contact: user.contact }
      : undefined;
    this.formulario.set(construirResumen(base, cuenta));
  }

  /** Whether all 7 fields are present with a valid contact (RNF-5, case 12). */
  protected completo(): boolean {
    return resumenCompleto(this.formulario());
  }

  /** Submits `POST /ideas` (origin manual); on failure the data stays (caso 17). */
  protected async enviar(): Promise<void> {
    if (!this.completo() || this.enviando()) return;
    this.enviando.set(true);
    this.error.set('');
    try {
      await this.capture.crearManual(this.formulario());
      void this.router.navigate(['/mis-ideas']);
    } catch (err) {
      this.error.set(errorMessage(err));
    } finally {
      this.enviando.set(false);
    }
  }

  protected irInicio(): void {
    void this.router.navigate(['/captura']);
  }
}
