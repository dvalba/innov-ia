import { Injectable, computed, effect, signal } from '@angular/core';
import { Usuario } from '../types/models';

/** Persisted payload under a fixed per-tab (sessionStorage) key. */
const STORAGE_KEY = 'innov-ia.sesion';

function readPersisted(): { token: string; usuario: Usuario; mustChangePassword?: boolean } | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { token: string; usuario: Usuario; mustChangePassword?: boolean };
    if (!parsed?.token || !parsed?.usuario) return null;
    return parsed;
  } catch {
    return null;
  }
}

/**
 * Shared session state (T-006, RF-1, RNF-7).
 *
 * Exposes reactive signals for the active session, the signed-in user and
 * their roles; persists the session in `sessionStorage` so it survives a page
 * reload **per tab**. The per-tab storage is what makes multiple accounts
 * work side by side: each tab keeps its own session, so logging in with a
 * different account in another tab does not replace this tab's session.
 * Uses `effect()` exclusively for the sessionStorage integration, as required
 * by the Angular guidelines; derived values use `computed()`.
 */
@Injectable({ providedIn: 'root' })
export class SessionService {
  readonly token = signal<string | null>(null);
  readonly usuario = signal<Usuario | null>(null);
  readonly mustChangePassword = signal(false);

  /** Derived: whether a session is active. */
  readonly sesionActiva = computed(() => this.token() !== null);

  /** Derived: the user's roles. */
  readonly roles = computed(() => this.usuario()?.roles ?? []);

  constructor() {
    const persisted = readPersisted();
    if (persisted) {
      this.token.set(persisted.token);
      this.usuario.set(persisted.usuario);
      this.mustChangePassword.set(persisted.mustChangePassword ?? false);
    }

    // Persist on change (imperative integration with sessionStorage).
    effect(() => {
      const tok = this.token();
      const user = this.usuario();
      const forced = this.mustChangePassword();
      if (tok && user) {
        sessionStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ token: tok, usuario: user, mustChangePassword: forced }),
        );
      } else {
        sessionStorage.removeItem(STORAGE_KEY);
      }
    });
  }

  /** Starts a session from login credentials. */
  iniciar(token: string, usuario: Usuario, mustChangePassword = false): void {
    this.token.set(token);
    this.usuario.set(usuario);
    this.mustChangePassword.set(mustChangePassword);
  }

  /** Clears the session (logout or forced redirect on 401). */
  cerrar(): void {
    this.token.set(null);
    this.usuario.set(null);
    this.mustChangePassword.set(false);
  }

  /** True when the user holds every one of the given roles. */
  tieneRol(...roles: string[]): boolean {
    const current = this.roles();
    return roles.every((role) => current.includes(role));
  }
}
