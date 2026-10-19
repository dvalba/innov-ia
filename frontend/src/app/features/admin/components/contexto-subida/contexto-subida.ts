import { Component, inject, signal } from '@angular/core';
import { errorMessage } from '../../../../shared/interceptors/error.interceptor';
import { ContextoService } from '../../services/contexto.service';

/**
 * Company-context file upload (T-076, RF-21, case 25).
 *
 * Reads the selected text file (`.txt` / `.md`) on the client and sends its
 * content to `POST /admin/contexto/subida` (a JSON `content` field — D14, no
 * multipart), which replaces the whole document. On a successful upload the
 * shared `documento` read is updated in place, so the online editor
 * rehydrates automatically from the new document.
 */
@Component({
  selector: 'app-contexto-subida',
  templateUrl: './contexto-subida.html',
})
export class ContextoSubida {
  protected readonly nombreArchivo = signal('');
  protected readonly contenido = signal('');
  protected readonly subiendo = signal(false);
  protected readonly error = signal('');

  private readonly contexto = inject(ContextoService);

  private leerArchivo(archivo: File): void {
    const lector = new FileReader();
    lector.addEventListener('load', () => {
      this.contenido.set(typeof lector.result === 'string' ? lector.result : '');
      this.error.set('');
    });
    lector.addEventListener('error', () => this.error.set('No se pudo leer el archivo seleccionado.'));
    lector.readAsText(archivo);
  }

  protected onSeleccionar(event: Event): void {
    const entrada = event.target as HTMLInputElement;
    const archivo = entrada.files?.[0];
    if (archivo) {
      this.nombreArchivo.set(archivo.name);
      this.leerArchivo(archivo);
    } else {
      this.nombreArchivo.set('');
      this.contenido.set('');
    }
  }

  protected async onSubir(): Promise<void> {
    if (this.subiendo() || !this.contenido()) return;
    this.subiendo.set(true);
    this.error.set('');
    try {
      const actualizado = await this.contexto.subir(this.contenido());
      this.contexto.documento.set(actualizado);
      this.nombreArchivo.set('');
      this.contenido.set('');
    } catch (err) {
      // 400 blank / corrupt file (case 25) or any rejection: the document is
      // unchanged; surface the backend message.
      this.error.set(errorMessage(err));
    } finally {
      this.subiendo.set(false);
    }
  }
}
