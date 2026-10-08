"""Composition root for app dependencies (plan §1.2, Constitution §3.2).

`app` wires the shared contracts to their reference implementations
(`TokenStore` and a `JsonStore`-based user directory) and exposes the
reusable session/role guards used by the feature routers. Everything is
expressed with `Annotated` typed dependencies, overridable in tests.

Typed dependency aliases:
  - `TokenStoreDep` / `UserDirectoryDep` / `IdeaLedgerDep` /
    `ConversationStoreDep` / `AssistantClientDep` /
    `NotificationStoreDep`: DI providers (override in tests).
  - `RefinedEmitterDep` / `PublishedEmitterDep` / `RejectedEmitterDep` /
    `RequestedEmitterDep` (G10/T-033): emitters for the four RF-18
    notification events. Each takes the updated `Idea` produced by the
    `ideas` use cases; `Requested` fans out to every active specialist.
    They wire the shared `notifications` use cases from the composition
    root so `ideas`/`assistant` never import `notifications`.
  - `SessionDep`: active bearer `Session` (401 when absent/expired or when the
    account is deactivated; roles are re-read live on every request).
  - `role_dependency(roles)`: `Session` plus a required role subset (403).
"""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Request

from features.assistant.infrastructure.ollama_client import OllamaClient
from features.assistant.use_cases.run_refinement_queue import run_refinement_queue
from features.auth.domain.session import Session
from features.auth.infrastructure.token_store import TokenStore
from features.capture.infrastructure.conversation_store import ConversationStore
from features.ideas.domain.idea import Idea
from features.ideas.infrastructure.idea_store import IdeaStore
from features.notifications.infrastructure.notification_store import NotificationStore
from features.notifications.use_cases.create_notification import (
    create_notification,
    fanout_requested,
)
from shared.config.settings import settings
from shared.contracts.assistant_client import AssistantClient
from shared.contracts.user_directory import UserDirectory
from shared.exceptions.handlers import AuthError, Forbidden
from shared.utils.persistence import JsonStore


def _token_store() -> TokenStore:
    return TokenStore(
        JsonStore(settings.data_dir / "sessions.json"),
        ttl_minutes=settings.session_ttl_minutes,
        now_factory=datetime.now,
    )


def _user_directory() -> UserDirectory:
    from features.users.infrastructure.user_store import UserStore

    return UserStore(JsonStore(settings.data_dir / "users.json"))


def get_token_store() -> TokenStore:
    """DI provider for the session token store (override in tests)."""
    return _token_store()


def get_user_directory() -> UserDirectory:
    """DI provider for the user directory (override in tests)."""
    return _user_directory()


def _idea_ledger() -> IdeaStore:
    return IdeaStore(
        JsonStore(settings.data_dir / "ideas.json"),
        JsonStore(settings.data_dir / "idea_versions.json"),
    )


def get_idea_ledger():
    """DI provider for the idea ledger (override in tests)."""
    return _idea_ledger()


def get_assistant_client() -> OllamaClient:
    """DI provider for the assistant client (override in tests)."""
    return OllamaClient(
        settings.ollama_base_url,
        settings.ollama_model,
        timeout=float(settings.ollama_timeout),
    )


def _conversation_store() -> ConversationStore:
    return ConversationStore(JsonStore(settings.data_dir / "conversations.json"))


def get_conversation_store() -> ConversationStore:
    """DI provider for the capture conversation store (override in tests)."""
    return _conversation_store()


def _notification_store() -> NotificationStore:
    return NotificationStore(JsonStore(settings.data_dir / "notifications.json"))


def get_notification_store() -> NotificationStore:
    """DI provider for the notification store (override in tests)."""
    return _notification_store()


TokenStoreDep = Annotated[TokenStore, Depends(get_token_store)]
UserDirectoryDep = Annotated[UserDirectory, Depends(get_user_directory)]
IdeaLedgerDep = Annotated[IdeaStore, Depends(get_idea_ledger)]
ConversationStoreDep = Annotated[ConversationStore, Depends(get_conversation_store)]
AssistantClientDep = Annotated[AssistantClient, Depends(get_assistant_client)]
NotificationStoreDep = Annotated[NotificationStore, Depends(get_notification_store)]


def _refined_emitter(store, directory):
    """IDEA_REFINED: the IA refined the proponent's manual idea (RF-12)."""

    def _emit(idea) -> None:
        create_notification(
            store, user_id=idea.ownerId, event_type="IDEA_REFINED", idea_id=idea.id
        )

    return _emit


def _published_emitter(store):
    """IDEA_PUBLISHED: the specialist validated and published the idea (RF-15)."""

    def _emit(idea) -> None:
        create_notification(
            store, user_id=idea.ownerId, event_type="IDEA_PUBLISHED", idea_id=idea.id
        )

    return _emit


def _rejected_emitter(store):
    """IDEA_REJECTED: the specialist rejected the idea (RF-16)."""

    def _emit(idea) -> None:
        create_notification(
            store, user_id=idea.ownerId, event_type="IDEA_REJECTED", idea_id=idea.id
        )

    return _emit


def _requested_emitter(store, directory):
    """IDEA_REQUESTED: fanned out to every active specialist (RF-18)."""

    def _emit(idea) -> None:
        fanout_requested(store, directory, idea_id=idea.id)

    return _emit


def get_refined_emitter(store: NotificationStoreDep, directory: UserDirectoryDep):
    """Builds the IDEA_REFINED emitter (bound to the shared notification store)."""
    return _refined_emitter(store, directory)


def get_published_emitter(store: NotificationStoreDep):
    """Builds the IDEA_PUBLISHED emitter (bound to the shared notification store)."""
    return _published_emitter(store)


def get_rejected_emitter(store: NotificationStoreDep):
    """Builds the IDEA_REJECTED emitter (bound to the shared notification store)."""
    return _rejected_emitter(store)


def get_requested_emitter(store: NotificationStoreDep, directory: UserDirectoryDep):
    """Builds the IDEA_REQUESTED fanout emitter (RF-18), bound to the directory."""
    return _requested_emitter(store, directory)


RefinedEmitterDep = Annotated[Callable[[Idea], None], Depends(get_refined_emitter)]
PublishedEmitterDep = Annotated[Callable[[Idea], None], Depends(get_published_emitter)]
RejectedEmitterDep = Annotated[Callable[[Idea], None], Depends(get_rejected_emitter)]
RequestedEmitterDep = Annotated[Callable[[Idea], None], Depends(get_requested_emitter)]


def get_assistant_check(ledger: IdeaLedgerDep, assistant: AssistantClientDep,
                        emit: RefinedEmitterDep) -> Callable[[], dict]:
    """Builds the on-demand assistant check (T-062, RF-11).

    Wraps `run_refinement_queue` bound to the ledger, the assistant and the
    IDEA_REFINED emitter (the idea payload is adapted to the `Idea` the
    emitter contract expects). The zero-arg callable performs the pass when
    invoked; building it is cheap — no probe until the check runs.
    """

    def _check() -> dict:
        return run_refinement_queue(
            ledger, assistant, emit=lambda payload: emit(Idea.from_payload(payload))
        )

    return _check


AssistantCheckDep = Annotated[Callable[[], dict], Depends(get_assistant_check)]


def _extract_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header[len("Bearer "):].strip()
    return token or None


def require_session(request: Request, tokens: TokenStoreDep,
                    directory: UserDirectoryDep) -> Session:
    """Returns the active `Session` for the bearer token or raises 401.

    Covers case 15: an expired session is rejected (RNF-7: without a session,
    no access). The account is re-read on every request (live session):
    deactivating a user or stripping it of its roles (RF-17, case 16) removes
    the access immediately, without waiting for the session to expire.
    """
    token = _extract_token(request)
    if token is None:
        raise AuthError(code="SESSION_REQUIRED", message="No existe una sesión activa.")
    session = tokens.resolve(token, now=datetime.now())
    if session is None:
        raise AuthError(code="SESSION_REQUIRED", message="La sesión ha caducado o no es válida.")
    user = directory.get(session.user_id)
    if user is None or not user.get("active", True):
        tokens.revoke(token)
        raise AuthError(code="SESSION_REVOKED",
                        message="La cuenta no está habilitada; el acceso ha sido revocado.")
    return Session(token=session.token, user_id=session.user_id,
                   expires_at=session.expires_at, roles=tuple(user.get("roles", [])))


SessionDep = Annotated[Session, Depends(require_session)]


def require_role(*roles: str):
    """Builds a guard that requires the session to hold all the given roles."""

    def _guard(session: SessionDep) -> Session:
        if not roles:
            return session
        if not session.has_roles(tuple(roles)):
            raise Forbidden(
                code="ROLE_NOT_ALLOWED", message=f"Se requiere el rol: {', '.join(roles)}."
            )
        return session

    return _guard


def role_dependency(*roles: str):
    """Returns a typed dependency requiring all the given roles (403)."""
    return Annotated[Session, Depends(require_role(*roles))]
