import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { CaptureService } from '../../services/capture.service';

/**
 * Manual capture placeholder (route reserved for T-044, G09).
 *
 * Kept so the manual contingency links (new-idea and chat-assist) resolve. The
 * deployable pre-filled form (`POST /capture/activate-manual` → `capturedFields`)
 * lands in G09/T-044.
 */
@Component({
  selector: 'app-manual-idea',
  templateUrl: './manual.html',
  styleUrl: './manual.css',
})
export class ManualIdea {
  private readonly router = inject(Router);
  readonly contingencia = inject(CaptureService).contingencia;

  protected irInicio(): void {
    void this.router.navigate(['/captura']);
  }
}
