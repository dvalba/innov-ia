import { Component, effect, input, output, viewChild } from '@angular/core';

/**
 * Reusable confirmation dialog (T-056, RNF-6, plan §1.1).
 *
 * A small modal confirm/cancel dialog promoted to `shared` because several
 * features need the same pattern: "Solicitar publicación" (my-ideas) and the
 * explicit capture abandonment with its data-loss warning (capture, caso 7).
 * The caller only drives it with the `abierto` input and listens to the two
 * outputs — the dialog never knows what the confirmation does.
 *
 * Keyboard operable (RNF-6): `Escape` cancels, focus moves into the dialog on
 * open (to the confirm button) and is trapped between the two buttons, and the
 * previous focus is restored on close. The overlay carries `role="dialog"` and
 * `aria-modal="true"` with labelled title and message.
 */
@Component({
  selector: 'app-confirm-dialog',
  templateUrl: './confirm-dialog.html',
})
export class ConfirmDialog {
  /** Whether the dialog is open (the caller toggles it). */
  readonly abierto = input(false);
  /** The dialog title (Spanish, RNF-4). */
  readonly titulo = input.required<string>();
  /** The confirmation message (Spanish). */
  readonly mensaje = input.required<string>();
  /** The confirm button label. */
  readonly confirmarEtiqueta = input('Confirmar');
  /** The cancel button label. */
  readonly cancelarEtiqueta = input('Cancelar');
  /** `true` to render the confirm button in the danger color. */
  readonly peligro = input(false);
  /** `true` while the caller's mutation is in flight (locks the buttons). */
  readonly ocupado = input(false);

  /** The confirm action was accepted. */
  readonly confirmado = output<void>();
  /** The dialog was dismissed (cancel button, Escape or backdrop). */
  readonly cancelado = output<void>();

  private readonly panel = viewChild<Element>('panel');
  private readonly confirmarBtn = viewChild<HTMLElement>('confirmar');
  /** The element focused before the dialog opened (restored on close). */
  private lastFocused: HTMLElement | null = null;

  constructor() {
    // Imperative DOM focus management (guideline §3): when the dialog opens,
    // remember the opener and focus the confirm button once the panel exists;
    // when it closes, hand the focus back to the opener.
    effect(() => {
      if (this.abierto()) {
        const activo = document.activeElement;
        this.lastFocused = activo instanceof HTMLElement ? activo : null;
        if (this.panel()) this.confirmarBtn()?.focus();
      } else if (this.lastFocused) {
        this.lastFocused.focus();
        this.lastFocused = null;
      }
    });
  }

  protected onConfirm(): void {
    if (this.ocupado()) return;
    this.confirmado.emit();
  }

  protected onCancel(): void {
    if (this.ocupado()) return;
    this.cancelado.emit();
  }

  /** Escape cancels; Tab/Shift+Tab cycle between the two buttons (focus trap). */
  protected onKeydown(ev: KeyboardEvent): void {
    if (ev.key === 'Escape') {
      ev.preventDefault();
      this.onCancel();
      return;
    }
    if (ev.key === 'Tab') {
      const botones = this.panel()
        ? Array.from(this.panel()!.querySelectorAll<HTMLElement>('button'))
        : [];
      if (botones.length === 0) return;
      const indice = botones.indexOf(document.activeElement as HTMLElement);
      const siguiente =
        (indice + (ev.shiftKey ? -1 : 1) + botones.length) % botones.length;
      botones[siguiente].focus();
      ev.preventDefault();
    }
  }
}
