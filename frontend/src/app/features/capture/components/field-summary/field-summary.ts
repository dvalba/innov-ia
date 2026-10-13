import { Component, OnInit, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  FormResumen,
  construirResumen,
  resumenCompleto,
} from '../../services/fieldsMeta';

/**
 * Editable capture summary (T-043, RF-6).
 *
 * When the 7 fields close (`state: RESUMEN`) this block shows them, editable,
 * so the proponent can correct any of them before confirming. "Confirmar"
 * hands the confirmed 7 fields (structured ones as objects) back to the chat,
 * which calls `POST /capture/finish`; a 201 navigates to "Mis ideas", a 422
 * (incomplete fields / bad contact) is reported field by field and the summary
 * stays editable. UI copy in Spanish (RNF-4).
 */
@Component({
  selector: 'app-field-summary',
  imports: [FormsModule],
  templateUrl: './field-summary.html',
  styleUrl: './field-summary.css',
})
export class FieldSummary implements OnInit {
  /** The captured summary to edit (structured fields may be objects or JSON strings). */
  readonly sumarioInicial = input<Record<string, unknown>>({});
  /** Field names the backend rejected on the last confirmation (RNF-5, case 12). */
  readonly camposError = input<string[]>([]);

  /** Emits the confirmed 7 fields (objects for the structured ones). */
  readonly confirmar = output<Record<string, unknown>>();

  protected readonly formulario = signal<FormResumen>({
    title: '',
    description: '',
    problem: '',
    expectedBenefit: '',
    strategicAlignment: '',
    proponent: { name: '', area: '', contact: '' },
    estimatedResources: { time: '', people: '', budget: '' },
  });

  /** Seeds the editable form from the captured summary (stable once RESUMEN). */
  ngOnInit(): void {
    this.formulario.set(construirResumen(this.sumarioInicial()));
  }

  protected tieneError(nombre: string): boolean {
    return this.camposError().includes(nombre);
  }

  protected esCompleto(): boolean {
    return resumenCompleto(this.formulario());
  }

  protected confirmarIdea(): void {
    if (!this.esCompleto()) return;
    this.confirmar.emit(this.formulario() as unknown as Record<string, unknown>);
  }
}
