import { Injectable, computed, effect, signal } from '@angular/core';

/** Persisted theme preference (the key matches the pre-paint script in index.html). */
const STORAGE_KEY = 'innov-ia.theme';

/** The three selectable appearances. */
export type ThemePreference = 'light' | 'dark' | 'system';

function readPersisted(): ThemePreference | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === 'light' || saved === 'dark' ? saved : null;
  } catch {
    return null;
  }
}

/**
 * Shared appearance state.
 *
 * Exposes the selectable theme (`light`, `dark`, `system`) and the resolved
 * dark-mode flag; persists the explicit choice in `localStorage` (the key is
 * read by the pre-paint script in `index.html` to avoid a flash on load) and
 * toggles the `dark` class on `<html>`. The `system` preference follows the
 * OS color scheme live. `effect()` is used exclusively for the imperative
 * DOM/localStorage integration, as required by the Angular guidelines.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly theme = signal<ThemePreference>(readPersisted() ?? 'system');
  readonly systemDark = signal(false);

  /** Derived: whether the interface must render in dark mode. */
  readonly isDark = computed(() =>
    this.theme() === 'system' ? this.systemDark() : this.theme() === 'dark',
  );

  constructor() {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    this.systemDark.set(mq.matches);
    mq.addEventListener('change', (e) => this.systemDark.set(e.matches));

    // Imperative integration: apply the class and persist the preference.
    effect(() => {
      document.documentElement.classList.toggle('dark', this.isDark());
      const pref = this.theme();
      if (pref === 'system') {
        localStorage.removeItem(STORAGE_KEY);
      } else {
        localStorage.setItem(STORAGE_KEY, pref);
      }
    });
  }

  /** Selects a theme preference from the settings view. */
  setTheme(pref: ThemePreference): void {
    this.theme.set(pref);
  }
}
