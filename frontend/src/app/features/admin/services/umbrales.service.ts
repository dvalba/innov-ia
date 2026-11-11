import { HttpClient, httpResource } from '@angular/common/http';
import { inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { CalibrationThresholds } from '../../../shared/types/models';
import { UmbralesCalibracion } from '../../../shared/utils/decision';

/**
 * Admin calibration-thresholds client (T-084, RF-28 v2.2).
 *
 * Wraps `GET/PUT /admin/calibration-thresholds`: `umbrales` reads the stored
 * integer thresholds (defaults 4/7 when never set) and `guardar` stores a new
 * pair, which the backend audits (RNF-2/RNF-3). Validation lives on the page
 * (integers 1-10, `rechazo < aceptacion`) and 422 `THRESHOLDS_INVALID` is
 * surfaced by the interceptor.
 */
export class UmbralesService {
  private readonly http = inject(HttpClient);

  /** The stored thresholds (defaults 4/7 when never set). */
  readonly umbrales = httpResource<CalibrationThresholds>(
    () => '/admin/calibration-thresholds',
  );

  /** `PUT /admin/calibration-thresholds` — stores a new audited pair. */
  guardar(payload: UmbralesCalibracion): Promise<CalibrationThresholds> {
    return firstValueFrom(
      this.http.put<CalibrationThresholds>(
        '/admin/calibration-thresholds',
        payload,
      ),
    );
  }
}
