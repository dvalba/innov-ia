import { HttpClient, httpResource } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { DebateDays } from '../../../shared/types/models';

/**
 * Admin global debate-days client (T-090, RF-24, v2.4).
 *
 * Wraps `GET/PUT /admin/debate-days`: `dias` reads the stored integer (default
 * 30 when never set) and `guardar` stores a new value, which the backend audits
 * (RNF-11). Validation lives on the page (integer 1-90) and 422
 * `DEBATE_DAYS_INVALID` is surfaced by the interceptor.
 */
@Injectable({ providedIn: 'root' })
export class DebateDaysService {
  private readonly http = inject(HttpClient);

  /** The stored debate days (default 30 when never set). */
  readonly dias = httpResource<DebateDays>(() => '/admin/debate-days');

  /** `PUT /admin/debate-days` — stores a new audited value. */
  guardar(dias: number): Promise<DebateDays> {
    return firstValueFrom(
      this.http.put<DebateDays>('/admin/debate-days', { debateDays: dias }),
    );
  }
}
