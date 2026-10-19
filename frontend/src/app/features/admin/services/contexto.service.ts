import { HttpClient, httpResource } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

/** Fixed profile section of the company-context document (§2.8 contract). */
export interface PerfilEmpresa {
  name: string;
  sector: string;
  description: string;
  mission: string;
  strategicObjectives: string[];
}

/**
 * The single admin-managed company-context document (RF-21, D13).
 *
 * `profile` is the fixed template section; `guideText` the free guidance text
 * injected in every AI operation (RF-22); `updatedAt` the ISO timestamp of
 * the last write (empty for a never-set document — case 24).
 */
export interface DocumentoContexto {
  profile: PerfilEmpresa;
  guideText: string;
  updatedAt: string;
}

/** PUT /admin/contexto payload. */
export interface ContextoIn {
  profile: PerfilEmpresa;
  guideText: string;
}

const PLANTILLA_FILENAME = 'plantilla-contexto-empresa.txt';

/**
 * Company-context API client (T-076, RF-21, RNF-12, D13).
 *
 * The read goes through `httpResource`; the mutations (online editing and
 * file upload) go through the dedicated `HttpClient` per the Angular
 * guidelines (§5). The template download is a plain `text/plain` GET (no
 * multipart: the upload sends the file content as a JSON `content` field —
 * D14).
 */
@Injectable({ providedIn: 'root' })
export class ContextoService {
  private readonly http = inject(HttpClient);

  /** GET /admin/contexto — the current document (or the blank one). */
  readonly documento = httpResource<DocumentoContexto>(() => '/admin/contexto');

  /** PUT /admin/contexto — online editing (profile + guide text). */
  guardar(payload: ContextoIn): Promise<DocumentoContexto> {
    return firstValueFrom(this.http.put<DocumentoContexto>('/admin/contexto', payload));
  }

  /** POST /admin/contexto/subida — replaces the document with the file text. */
  subir(content: string): Promise<DocumentoContexto> {
    return firstValueFrom(this.http.post<DocumentoContexto>('/admin/contexto/subida', { content }));
  }

  /** GET /admin/contexto/plantilla — downloads the `text/plain` skeleton. */
  async descargarPlantilla(): Promise<void> {
    const texto = await firstValueFrom(
      this.http.get('/admin/contexto/plantilla', { responseType: 'text' }),
    );
    const blob = new Blob([texto], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = PLANTILLA_FILENAME;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    URL.revokeObjectURL(url);
  }
}
