import {
  Component,
  afterNextRender,
  effect,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { TituloAccion } from '../../components/title-suggestion/title-suggestion';
import { ChatMessage, MensajeChat } from '../../components/chat-message/chat-message';
import { TitleSuggestion } from '../../components/title-suggestion/title-suggestion';
import { CaptureService } from '../../services/capture.service';
import { FIELD_LABEL, FIELD_ORDER, parseStructuredField } from '../../services/fieldsMeta';

let secuencia = 0;

/**
 * Assisted capture chat (T-042, RF-3..RF-5, plan §1.1 "La conversación").
 *
 * Renders the capture conversation on top of `CaptureService`'s shared state
 * (there is no `conversationId` in the URL): user/assistant bubbles, the fixed
 * quick replies of the current field (a chip is the field's complete answer,
 * RF-5) and the proactive title block (RF-4). The server never returns the
 * history, so the transcript is kept client-side in a signal. Visible loading
 * per IA call (RNF-3). If the IA dies mid-conversation the 503 falls back to
 * the manual contingency without losing the captured fields (RF-7/RNF-10); the
 * editable summary and the finalization continue in G09 (T-043).
 */
@Component({
  selector: 'app-chat-assist',
  imports: [FormsModule, ChatMessage, TitleSuggestion],
  templateUrl: './chat-assist.html',
  styleUrl: './chat-assist.css',
})
export class ChatAssist {
  private readonly capture = inject(CaptureService);
  private readonly router = inject(Router);
  private readonly scrollEl = viewChild<HTMLElement>('scroll');

  /** Client-side transcript (the server keeps the source of truth). */
  protected readonly transcript = signal<MensajeChat[]>([]);
  /** Conversation for which the transcript was seeded (re-seed on change). */
  private seededId = signal<string | null>(null);

  protected readonly sinConversacion = signal(true);

  protected readonly cargando = this.capture.cargando;
  protected readonly turno = this.capture.turno;
  protected readonly estadoConv = this.capture.estadoConv;
  protected readonly resumen = this.capture.resumen;
  protected readonly contingencia = this.capture.contingencia;
  protected readonly conversacionId = this.capture.conversacionId;

  protected readonly texto = signal('');
  protected readonly errorEnvio = signal('');

  constructor() {
    // Start at the bottom of the seeded transcript.
    afterNextRender(() => this.despues());

    // Follow the shared conversation; re-seed the transcript when it changes.
    effect(() => {
      const id = this.capture.conversacionId();
      if (!id) {
        this.sinConversacion.set(true);
        return;
      }
      this.sinConversacion.set(false);
      if (id !== this.seededId()) {
        this.seededId.set(id);
        this.transcript.set([]);
        if (this.capture.retomada()) {
          // Caso 8: an ACTIVA conversation already existed and was resumed.
          this.empujar('system', 'Retomamos tu conversación en curso.');
        }
        const t = this.capture.turno();
        if (t?.text) {
          this.empujar('assistant', t.text);
        }
      }
    });
  }

  /** The current question's index in the fixed 7 (1-based, capped at 7). */
  protected progreso(): number {
    if (this.estadoConv() === 'RESUMEN') return FIELD_ORDER.length;
    const campo = this.turno()?.currentField;
    if (!campo) return 1;
    const idx = FIELD_ORDER.indexOf(campo as (typeof FIELD_ORDER)[number]);
    return idx >= 0 ? idx + 1 : 1;
  }

  /** Spanish label of the current question, or null while none is active. */
  protected campoActual(): string | null {
    if (this.estadoConv() !== 'ACTIVA') return null;
    const campo = this.turno()?.currentField;
    if (!campo) return null;
    const idx = FIELD_ORDER.indexOf(campo as (typeof FIELD_ORDER)[number]);
    return idx >= 0 ? FIELD_LABEL[campo as keyof typeof FIELD_LABEL] : null;
  }

  protected async enviarMensaje(): Promise<void> {
    const id = this.capture.conversacionId();
    const mensaje = this.texto().trim();
    if (!id || !mensaje || this.cargando() || this.estadoConv() !== 'ACTIVA') return;
    this.texto.set('');
    this.errorEnvio.set('');
    this.empujar('user', mensaje);
    await this.llamar(() => this.capture.enviar(id, mensaje));
  }

  protected async elegirChip(chip: string): Promise<void> {
    const id = this.capture.conversacionId();
    if (!id || this.cargando() || this.estadoConv() !== 'ACTIVA') return;
    this.errorEnvio.set('');
    this.empujar('user', chip);
    await this.llamar(() => this.capture.enviar(id, undefined, chip));
  }

  protected async onTitulo(a: TituloAccion): Promise<void> {
    const id = this.capture.conversacionId();
    if (!id || this.cargando()) return;
    this.errorEnvio.set('');
    this.empujar('user', this.textoAccionTitulo(a));
    await this.llamar(() => this.capture.accionTitulo(id, a.action, a.manualText));
  }

  protected irManual(): void {
    void this.router.navigate(['/captura/manual']);
  }

  protected irInicio(): void {
    void this.router.navigate(['/captura']);
  }

  /** The 503 fallback captured fields, as display rows. */
  protected camposPreservados(): Array<{ campo: string; valor: string }> {
    const campos = this.contingencia()?.capturedFields ?? {};
    return Object.entries(campos).map(([campo, valor]) => ({
      campo: FIELD_LABEL[(campo as keyof typeof FIELD_LABEL)] ?? campo,
      valor: this.formatearValor(campo, valor),
    }));
  }

  /** The editable summary rows (read-only display; editing is G09). */
  protected filasResumen(): Array<{ campo: string; valor: string }> {
    const r = this.resumen() ?? {};
    return FIELD_ORDER.map((campo) => ({
      campo: FIELD_LABEL[campo],
      valor: this.formatearValor(campo, r[campo]),
    })).filter((f) => f.valor !== '');
  }

  private textoAccionTitulo(a: TituloAccion): string {
    if (a.action === 'accept') return 'Acepto la sugerencia de título.';
    if (a.action === 'another') return 'Dame otra sugerencia de título.';
    return a.manualText ?? '';
  }

  private formatearValor(campo: string, valor: unknown): string {
    if (valor === null || valor === undefined) return '';
    if (typeof valor === 'string') {
      const estructurado = parseStructuredField(valor);
      if (typeof estructurado !== 'object' || estructurado === null) return valor;
    }
    if (typeof valor === 'object' && valor !== null) {
      const v = valor as Record<string, unknown>;
      if ('area' in v)
        return [v['name'], v['area'], v['contact']].filter(Boolean).join(' — ');
      if ('time' in v)
        return [v['time'], v['people'], v['budget']].filter(Boolean).join(', ');
      return JSON.stringify(valor);
    }
    return String(valor);
  }

  /** Runs a conversation call, folds the returned assistant turn in and scrolls. */
  private async llamar(llamada: () => Promise<{ assistant?: { text: string } | null }>): Promise<void> {
    try {
      const t = await llamada();
      const texto = t.assistant?.text;
      if (texto) this.empujar('assistant', texto);
    } catch (err) {
      if (this.capture.contingencia()) {
        // RNF-10: fields are preserved in `contingencia`; the panel offers the
        // manual continuation. No error is shown on top of it.
        this.empujar('system', 'El asistente no está disponible; tus datos quedaron preservados.');
      } else {
        this.errorEnvio.set(errorMessage(err));
      }
    }
    this.despues();
  }

  private empujar(role: MensajeChat['role'], text: string): void {
    secuencia += 1;
    const msg: MensajeChat = { id: `m-${secuencia}`, role, text };
    this.transcript.update((prev) => [...prev, msg]);
  }

  private despues(): void {
    // Scroll to the end once the rendered turn is in place.
    setTimeout(() => {
      const el = this.scrollEl();
      if (el) el.scrollTop = el.scrollHeight;
    });
  }
}
