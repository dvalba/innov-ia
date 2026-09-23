"""Idea state machine tests (T-018, RF-10/RF-15/RF-16, RNF-8/RNF-9, plan §4.6).

Pure domain: no FastAPI/Pydantic imports are allowed here.
"""

import pytest

from features.ideas.domain.idea import Idea
from features.ideas.domain.state_machine import (
    ACTIONS,
    TRANSITIONS,
    InvalidTransition,
    transicionar,
)
from shared.exceptions.handlers import DomainError

NOW = "2026-09-23T10:00:00"


def _idea(state: str) -> Idea:
    return Idea(
        id="idea_1",
        ownerId="u_ana",
        title="Optimización de procesos de compra",
        proponent={"name": "Ana", "area": "Compras", "contact": "ana@innov-ia.local"},
        description="Digitalizar la validación de proveedores duplicada entre áreas.",
        problem="Tres revisiones manuales independientes causan retrasos.",
        expectedBenefit="Ahorro de 120 horas mensuales.",
        strategicAlignment="Agilizar la cadena de suministro.",
        estimatedResources={"time": "6 semanas", "people": "2 personas", "budget": "50000 PLN"},
        state=state,
    )


# -- the exact transition table (§4.6) -----------------------------------------


def test_transition_table_is_exactly_the_spec() -> None:
    assert TRANSITIONS == {
        "EN_DESARROLLO": {"request-publication": "SOLICITANDO_PUBLICACION"},
        "SOLICITANDO_PUBLICACION": {"approve": "VALIDADA_PUBLICA", "reject": "EN_DESARROLLO"},
        "VALIDADA_PUBLICA": {},
    }
    assert ACTIONS == ("request-publication", "approve", "reject")


def test_validada_publica_is_terminal() -> None:
    assert TRANSITIONS["VALIDADA_PUBLICA"] == {}


def test_request_publication_is_the_only_entry_to_solicitando() -> None:
    target = TRANSITIONS["EN_DESARROLLO"]
    assert list(target) == ["request-publication"]
    assert target["request-publication"] == "SOLICITANDO_PUBLICACION"


# -- valid transitions ------------------------------------------------------------


def test_request_publication_moves_in_development_to_waiting() -> None:
    idea = transicionar(_idea("EN_DESARROLLO"), "request-publication", by_user="u_ana", now=NOW, apply=False)
    assert idea.state == "SOLICITANDO_PUBLICACION"
    assert idea.requestDate == NOW


@pytest.mark.parametrize(
    ("original", "action", "now"),
    [
        ("EN_DESARROLLO", "request-publication", "2026-09-24T12:00:00"),
        ("SOLICITANDO_PUBLICACION", "approve", "2026-09-26T09:00:00"),
        ("SOLICITANDO_PUBLICACION", "reject", "2026-09-26T09:00:00"),
    ],
)
def test_the_same_action_after_it_is_applied_is_rejected(original: str, action: str, now: str) -> None:
    idea = _idea(original)
    transicionar(idea, action, by_user="u_x", now=now, apply=True, comment="Comentario del rechazo")
    with pytest.raises(InvalidTransition):
        transicionar(idea, action, by_user="u_x", now=now, apply=True, comment="Comentario del rechazo")


# -- invalid transitions (RNF-9: DomainError 409) ----------------------------------


VALID_STATES = ("EN_DESARROLLO", "SOLICITANDO_PUBLICACION", "VALIDADA_PUBLICA")
ALL_ACTIONS = list(ACTIONS) + ["nonsense"]


@pytest.mark.parametrize("state", VALID_STATES)
@pytest.mark.parametrize("action", ALL_ACTIONS)
def test_each_state_action_combo_allowed_or_rejected(state: str, action: str) -> None:
    allowed = state in TRANSITIONS and action in TRANSITIONS[state]
    idea = _idea(state)
    if allowed:
        transicionar(idea, action, by_user="u_x", now=NOW, apply=True, comment="Comentario del rechazo")
        assert idea.state == TRANSITIONS[state][action]
    else:
        with pytest.raises(InvalidTransition):
            transicionar(idea, action, by_user="u_x", now=NOW, apply=True)
        assert idea.state == state  # the idea keeps its state


def test_invalid_transition_error_is_a_409_domain_error() -> None:
    with pytest.raises(DomainError) as error:
        transicionar(_idea("EN_DESARROLLO"), "approve", by_user="u_x", now=NOW, apply=False)
    assert error.value.status_code == 409


def test_an_action_for_an_unknown_state_is_rejected() -> None:
    with pytest.raises(InvalidTransition):
        transicionar(_idea("EN_DESARROLLO"), "deploy", by_user="u_x", now=NOW, apply=False)


# -- RNF-8 trail ------------------------------------------------------------------


def test_approve_records_who_and_when() -> None:
    idea = transicionar(_idea("SOLICITANDO_PUBLICACION"), "approve", by_user="u_experto", now=NOW, apply=False)
    assert idea.state == "VALIDADA_PUBLICA"
    assert idea.publishedBy == "u_experto"
    assert idea.publishedAt == NOW


def test_approve_is_allowed_for_the_owner_too_case_9() -> None:
    idea = transicionar(_idea("SOLICITANDO_PUBLICACION"), "approve", by_user="u_ana", now=NOW, apply=False)
    assert idea.publishedBy == "u_ana"  # self validation, same trail


def test_reject_requires_a_comment_case_13() -> None:
    for comment in (None, "", "   "):
        with pytest.raises(DomainError) as error:
            transicionar(_idea("SOLICITANDO_PUBLICACION"), "reject", by_user="u_experto", now=NOW,
                         comment=comment, apply=False)
        assert error.value.status_code == 400


def test_reject_returns_to_development_and_attaches_the_comment_with_identity() -> None:
    idea = transicionar(_idea("SOLICITANDO_PUBLICACION"), "reject", by_user="u_experto", by_name="Experto",
                        now=NOW, comment="Falta estimación de costos", apply=False)
    assert idea.state == "EN_DESARROLLO"
    assert idea.rejectionNote == {
        "by": "u_experto",
        "byName": "Experto",
        "comment": "Falta estimación de costos",
        "at": NOW,
    }


def test_request_publication_sets_request_date() -> None:
    idea = transicionar(_idea("EN_DESARROLLO"), "request-publication", by_user="u_ana", now=NOW, apply=False)
    assert idea.requestDate == NOW
    assert idea.publishedAt is None


def test_apply_false_returns_a_copy_without_touching_the_original() -> None:
    original = _idea("EN_DESARROLLO")
    returned = transicionar(original, "request-publication", by_user="u_ana", now=NOW, apply=False)
    assert returned is not original
    assert original.state == "EN_DESARROLLO"
    assert returned.state == "SOLICITANDO_PUBLICACION"
