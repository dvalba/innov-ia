/**
 * Date formatting utilities (T-009, RNF-2, Spanish UI per RNF-4).
 *
 * Dates from the backend are ISO-8601 strings (plan §2). The helpers render
 * them in Spanish (es-MX) so the whole UI speaks Spanish.
 */

const DATE_TIME_OPTIONS: Intl.DateTimeFormatOptions = {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
};

const DATE_ONLY_OPTIONS: Intl.DateTimeFormatOptions = {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
};

const dateTimeFormatter = new Intl.DateTimeFormat('es-MX', DATE_TIME_OPTIONS);
const dateFormatter = new Intl.DateTimeFormat('es-MX', DATE_ONLY_OPTIONS);

/** Parses an ISO-8601 string into a `Date`; returns `null` when invalid/empty. */
export function parseFecha(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Formats an ISO date as "10 sep 2026, 08:42" (Spanish). */
export function formatearFecha(value: string | null | undefined): string {
  const date = parseFecha(value);
  return date ? dateTimeFormatter.format(date) : '—';
}

/** Formats an ISO date as "10 sep 2026" (Spanish, no time). */
export function formatearDia(value: string | null | undefined): string {
  const date = parseFecha(value);
  return date ? dateFormatter.format(date) : '—';
}
