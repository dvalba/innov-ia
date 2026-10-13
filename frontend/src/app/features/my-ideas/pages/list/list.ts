import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { IdeaCard } from '../../../../shared/components/idea-card/idea-card';
import { MyIdeasService } from '../../services/my-ideas.service';
import { origenLabel } from '../../services/my-idea-fields';
import { formatearDia } from '../../../../shared/utils/format';

/**
 * "Mis ideas" listing (T-046, RF-19; T-056: shared `idea-card`).
 *
 * Lists the proponent's own ideas — title, registration date, origin and state
 * — via `httpResource` (`GET /ideas/me`), newest first (the backend orders
 * them). Each row is the shared `idea-card` in its `compact` variant (title,
 * date + origin and the state badge), wrapped in a `routerLink` so any of them
 * can be opened into the detail page. When there are no ideas, a Spanish empty
 * state is shown.
 */
@Component({
  selector: 'app-idea-list',
  imports: [RouterLink, IdeaCard],
  templateUrl: './list.html',
})
export class IdeaList {
  private readonly ideas = inject(MyIdeasService);

  /** `GET /ideas/me` — the proponent's own ideas, newest first. */
  protected readonly miLista = this.ideas.miLista;
  protected readonly origenLabel = origenLabel;
  protected readonly formatearDia = formatearDia;

  constructor() {
    // Refetch on every entry: the root-level resource keeps its cached list
    // across sessions/users within the same SPA lifecycle.
    this.miLista.reload();
  }
}
