"""Ideas publication-cycle use cases tests (T-021: RF-10/RF-15/RF-16, RNF-8/RNF-9).

Covers the three publication flows: request-publication (EN_DESARROLLO ->
SOLICITANDO_PUBLICACION, `requestDate`, `IDEA_REQUESTED` fanout), approval
(specialist permission, self-validation case 9, `publishedBy`/`publishedAt`
trail, `IDEA_PUBLISHED`) and rejection (mandatory comment 400 case 13,
issuer identity trail, `IDEA_REJECTED`), plus the double transition: per
RNF-9 the first action wins and the second is discarded with 409.
"""

import pathlib

import pytest

from features.ideas.domain.idea import Idea
from features.ideas.infrastructure.idea_store import IdeaStore
from features.ideas.use_cases.approve_idea import approve_idea
from features.ideas.use_cases.create_idea import create_idea
from features.ideas.use_cases.reject_idea import reject_idea
from features.ideas.use_cases.request_publication import request_publication
from shared.exceptions.handlers import DomainError, Forbidden
from shared.utils.persistence import JsonStore

SPECIALIST = ("especialista",)
PROPOSER_ONLY = ("proponente",)


def _fields(**overrides: object) -> dict:
    base: dict = {
        "title": "Optimización del proceso de aprobación de proveedores",
        "proponent": {"name": "Ana Torres", "area": "Compras", "contact": "ana.torres@innov-ia.local"},
        "description": "Digitalizar la validación de proveedores eliminando la revisión manual duplicada.",
        "problem": "Tres revisiones manuales independientes que duplican esfuerzo.",
        "expectedBenefit": "Ahorro de 120 horas mensuales de personal.",
        "strategicAlignment": "Agilizar la cadena de suministro de la empresa.",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> IdeaStore:
    return IdeaStore(
        JsonStore(tmp_path / "ideas.json"),
        JsonStore(tmp_path / "versions.json"),
    )


def _idea(store: IdeaStore, owner_id: str = "u_ana", origin: str = "manual") -> dict:
    return create_idea(store, owner_id=owner_id, origin=origin, fields=_fields())


def _requested(store: IdeaStore, *, owner_id: str = "u_ana") -> dict:
    created = _idea(store, owner_id=owner_id)
    return request_publication(store, idea_id=created["id"], user_id=owner_id, user_name="Ana Torres")


# -- request-publication (RF-10, RF-18) -----------------------------------------


def test_request_publication_moves_to_solicitando_and_fixes_request_date(store: IdeaStore) -> None:
    created = _idea(store)
    updated = request_publication(store, idea_id=created["id"], user_id="u_ana",
                                  user_name="Ana Torres")
    assert updated["state"] == "SOLICITANDO_PUBLICACION"
    assert updated["requestDate"]
    assert updated["publishedAt"] is None and updated["publishedBy"] is None
    assert store.get(created["id"]) == updated


def test_request_publication_emits_idea_requested_once_per_specialist(store: IdeaStore) -> None:
    created = _idea(store)
    emitted: list[Idea] = []
    updated = request_publication(store, idea_id=created["id"], user_id="u_ana",
                                  user_name="Ana Torres", emit_notification=emitted.append)
    assert [record.id for record in emitted] == [updated["id"]]
    assert emitted[0].ownerId == "u_ana"


def test_request_publication_of_a_missing_idea_is_404(store: IdeaStore) -> None:
    with pytest.raises(DomainError) as error:
        request_publication(store, idea_id="nope", user_id="u_ana")
    assert error.value.status_code == 404
    assert error.value.code == "IDEA_NOT_FOUND"


def test_request_publication_by_a_non_owner_is_403(store: IdeaStore) -> None:
    created = _idea(store, owner_id="u_ana")
    with pytest.raises(DomainError) as error:
        request_publication(store, idea_id=created["id"], user_id="u_otro")
    assert error.value.status_code == 403
    assert store.get(created["id"])["state"] == "EN_DESARROLLO"


def test_request_publication_outside_en_desarrollo_is_409(store: IdeaStore) -> None:
    created = _idea(store)
    request_publication(store, idea_id=created["id"], user_id="u_ana")
    with pytest.raises(DomainError) as error:
        request_publication(store, idea_id=created["id"], user_id="u_ana")
    assert error.value.status_code == 409
    assert error.value.code == "INVALID_TRANSITION"


# -- approval (RF-15, RNF-8, case 9) ---------------------------------------------


def test_approve_by_specialist_publishes_with_the_mandatory_trail(store: IdeaStore) -> None:
    created = _requested(store)
    updated = approve_idea(store, idea_id=created["id"], user_id="u_experto",
                           user_name="Elena Ruiz", user_roles=SPECIALIST)
    assert updated["state"] == "VALIDADA_PUBLICA"
    assert updated["publishedBy"] == "u_experto"
    assert updated["publishedAt"]
    assert store.get(created["id"]) == updated


def test_approve_emits_idea_published_for_the_proponent(store: IdeaStore) -> None:
    created = _requested(store)
    emitted: list[Idea] = []
    approve_idea(store, idea_id=created["id"], user_id="u_experto", user_roles=SPECIALIST,
                 emit_notification=emitted.append)
    assert len(emitted) == 1
    assert emitted[0].ownerId == created["ownerId"]
    assert emitted[0].state == "VALIDADA_PUBLICA"


def test_approve_allows_self_validation_with_the_same_trail_case_9(store: IdeaStore) -> None:
    created = _requested(store)
    updated = approve_idea(store, idea_id=created["id"], user_id="u_ana", user_name="Ana Torres",
                           user_roles=("especialista", "proponente"))
    assert updated["state"] == "VALIDADA_PUBLICA"
    assert updated["publishedBy"] == "u_ana"  # RNF-8: the trail records the self-validator
    assert updated["publishedAt"]


def test_approve_by_a_non_specialist_is_403_and_changes_nothing(store: IdeaStore) -> None:
    created = _requested(store)
    with pytest.raises(Forbidden) as error:
        approve_idea(store, idea_id=created["id"], user_id="u_ana", user_roles=PROPOSER_ONLY)
    assert error.value.code == "ROLE_NOT_ALLOWED"
    assert store.get(created["id"])["state"] == "SOLICITANDO_PUBLICACION"
    assert store.get(created["id"])["publishedBy"] is None


def test_approve_of_a_missing_idea_is_404(store: IdeaStore) -> None:
    with pytest.raises(DomainError) as error:
        approve_idea(store, idea_id="nope", user_id="u_experto", user_roles=SPECIALIST)
    assert error.value.status_code == 404


def test_approve_outside_solicitando_is_409(store: IdeaStore) -> None:
    created = _idea(store)
    with pytest.raises(DomainError) as error:
        approve_idea(store, idea_id=created["id"], user_id="u_experto", user_roles=SPECIALIST)
    assert error.value.status_code == 409
    assert error.value.code == "INVALID_TRANSITION"


# -- rejection (RF-16, case 13, RNF-8) -------------------------------------------


def test_reject_returns_to_en_desarrollo_with_the_comment_and_the_issuer(store: IdeaStore) -> None:
    created = _requested(store)
    updated = reject_idea(store, idea_id=created["id"], user_id="u_experto",
                          user_name="Elena Ruiz", user_roles=SPECIALIST,
                          comment="Falta la alineación estratégica con el área de I+D.")
    assert updated["state"] == "EN_DESARROLLO"
    note = updated["rejectionNote"]
    assert note["by"] == "u_experto"
    assert note["byName"] == "Elena Ruiz"
    assert note["comment"] == "Falta la alineación estratégica con el área de I+D."
    assert note["at"]
    assert store.get(created["id"]) == updated


def test_reject_empties_the_publication_trail_and_keeps_request_date(store: IdeaStore) -> None:
    created = _requested(store)
    assert created["requestDate"]
    updated = reject_idea(store, idea_id=created["id"], user_id="u_experto",
                          user_roles=SPECIALIST, comment="Reconsiderar alcance.")
    assert updated["publishedBy"] is None and updated["publishedAt"] is None
    assert updated["requestDate"] == created["requestDate"]


def test_reject_requires_a_comment_400_case_13(store: IdeaStore) -> None:
    created = _requested(store)
    for empty in ("", "   "):
        with pytest.raises(DomainError) as error:
            reject_idea(store, idea_id=created["id"], user_id="u_experto",
                        user_roles=SPECIALIST, comment=empty)
        assert error.value.status_code == 400
        assert error.value.code == "REJECTION_COMMENT_REQUIRED"
    assert store.get(created["id"])["state"] == "SOLICITANDO_PUBLICACION"
    assert store.get(created["id"])["rejectionNote"] is None


def test_reject_emits_idea_rejected_for_the_proponent(store: IdeaStore) -> None:
    created = _requested(store)
    emitted: list[Idea] = []
    reject_idea(store, idea_id=created["id"], user_id="u_experto", user_roles=SPECIALIST,
                comment="Comentario de prueba.", emit_notification=emitted.append)
    assert len(emitted) == 1
    assert emitted[0].ownerId == created["ownerId"]
    assert emitted[0].state == "EN_DESARROLLO"


def test_reject_by_a_non_specialist_is_403(store: IdeaStore) -> None:
    created = _requested(store)
    with pytest.raises(Forbidden):
        reject_idea(store, idea_id=created["id"], user_id="u_ana", user_roles=PROPOSER_ONLY,
                    comment="Comentario.")
    assert store.get(created["id"])["state"] == "SOLICITANDO_PUBLICACION"


# -- RNF-9: simultaneous actions over one idea -----------------------------------


def test_second_transition_is_discarded_with_409_after_approval(store: IdeaStore) -> None:
    """First approve wins (RNF-9, case 11): the idea is VALIDADA_PUBLICA,
    terminal, so the concurrent reject is discarded with 409 and the state
    and the trail stay consistent."""
    created = _requested(store)
    updated = approve_idea(store, idea_id=created["id"], user_id="u_experto",
                           user_roles=SPECIALIST)
    assert updated["state"] == "VALIDADA_PUBLICA"
    with pytest.raises(DomainError) as error:
        reject_idea(store, idea_id=created["id"], user_id="u_otro",
                    user_roles=SPECIALIST, comment="Tarde.")
    assert error.value.status_code == 409
    final = store.get(created["id"])
    assert final["state"] == "VALIDADA_PUBLICA"
    assert final["publishedBy"] == "u_experto"
    assert final["rejectionNote"] is None


def test_request_lost_to_an_approval_is_discarded_with_409(store: IdeaStore) -> None:
    created = _idea(store)
    requested = request_publication(store, idea_id=created["id"], user_id="u_ana")
    approve_idea(store, idea_id=requested["id"], user_id="u_experto", user_roles=SPECIALIST)
    with pytest.raises(DomainError) as error:
        approve_idea(store, idea_id=requested["id"], user_id="u_otro", user_roles=SPECIALIST)
    assert error.value.status_code == 409
    assert store.get(created["id"])["publishedBy"] == "u_experto"


def test_a_rejected_idea_can_be_requested_again_and_re_decided(store: IdeaStore) -> None:
    created = _idea(store)
    request_publication(store, idea_id=created["id"], user_id="u_ana")
    rejected = reject_idea(store, idea_id=created["id"], user_id="u_experto",
                           user_roles=SPECIALIST, comment="Primer intento.")
    assert rejected["state"] == "EN_DESARROLLO" and rejected["rejectionNote"]
    re_requested = request_publication(store, idea_id=created["id"], user_id="u_ana")
    assert re_requested["state"] == "SOLICITANDO_PUBLICACION"
    published = approve_idea(store, idea_id=created["id"], user_id="u_experto",
                             user_roles=SPECIALIST)
    assert published["state"] == "VALIDADA_PUBLICA"
    assert published["publishedBy"] == "u_experto"
    assert published["rejectionNote"] == rejected["rejectionNote"]  # the trail is preserved
