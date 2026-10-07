"""Ideas refinement use cases tests (T-024, RF-8, RF-13, plan §4.5).

Covers the `improve_idea` orchestration with the assistant client injected:
with the IA a PENDIENTE version with `requestedBy=improvement` is registered,
the idea marks `reviewedByAI`/`generando` and manual editing blocks (RF-9);
without the IA (ping down, generation failing or an uninterpretable reply)
the instruction is saved as a pending request with the case-10 notice and no
error is raised (case 10). The `decide_version` and `adjust_in_chat` contracts
completing the RF-8/RF-13 block: accepting applies the version as VIGENTE
keeping EN_DESARROLLO, discarding keeps the current one, and the adjustment
offers the pre-contextualized conversation or falls back to manual editing.
"""

import pathlib

import pytest

from features.ideas.infrastructure.idea_store import IdeaStore
from features.ideas.use_cases.adjust_in_chat import adjust_in_chat
from features.ideas.use_cases.create_idea import create_idea
from features.ideas.use_cases.decide_version import decide_version
from features.ideas.use_cases.edit_idea import edit_idea
from features.ideas.use_cases.improve_idea import improve_idea
from shared.exceptions.handlers import AssistantUnavailable, DomainError
from shared.utils.persistence import JsonStore
from tests.conftest import OllamaMock


def _fields(**overrides: object) -> dict:
    base: dict = {
        "title": "Optimización del proceso de aprobación de proveedores",
        "proponent": {"name": "Ana Torres", "area": "Compras", "contact": "ana.torres@innov-ia.local"},
        "description": "Digitalizar la validación de proveedores eliminando la revisión manual duplicada.",
        "problem": "Tres revisiones manuales independientes que duplican esfuerzo.",
        "expectedBenefit": "Ahorro de 120 horas mensuales de personal.",
        "strategicAlignment": "Agilizar la cadena de suministro de la empresa.",
        "estimatedResources": {"time": "6 semanas", "people": "2 personas", "budget": "50000 PLN"},
    }
    base.update(overrides)
    return base


def _improved_json(**overrides: object) -> str:
    """A strict-JSON reply with the 7 fields, as the assistant would produce it."""
    import json

    return json.dumps(_fields(**overrides))


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> IdeaStore:
    return IdeaStore(
        JsonStore(tmp_path / "ideas.json"),
        JsonStore(tmp_path / "versions.json"),
    )


def _created(store: IdeaStore, owner_id: str = "u_ana") -> dict:
    payload = create_idea(store, owner_id=owner_id, origin="manual", fields=_fields())
    assert payload["state"] == "EN_DESARROLLO"
    return payload


# -- improve_idea with the IA (RF-8) --------------------------------------------


def test_improve_with_ia_registers_a_pending_improvement_version(store: IdeaStore,
                                                                 ollama_mock: OllamaMock) -> None:
    created = _created(store)
    ollama_mock.respond = lambda prompt: _improved_json(
        expectedBenefit="Ahorro de 180 horas mensuales de personal cuantificado."
    )

    result = improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                          instruction="Cuantifica el beneficio")

    version = result["version"]
    assert version["requestedBy"] == "improvement"
    assert version["status"] == "PENDIENTE"
    assert version["ideaId"] == created["id"]
    assert version["fields"]["expectedBenefit"].startswith("Ahorro de 180 horas")
    assert ollama_mock.prompts, "the improvement prompt must be generated for the IA"
    assert "Cuantifica el beneficio" in ollama_mock.prompts[0]

    idea = result["idea"]
    assert idea["reviewedByAI"] is True
    assert idea["generando"] is True
    assert idea["improvementRequest"] is None
    assert store.get(created["id"]) == idea


def test_improve_with_ia_blocks_manual_editing_until_decided(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)
    ollama_mock.respond = lambda prompt: _improved_json()
    improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                 instruction="Mejora el beneficio")

    with pytest.raises(DomainError) as error:
        edit_idea(store, idea_id=created["id"], owner_id="u_ana",
                  fields=_fields(title="Edición concurrente"))
    assert error.value.code == "GENERATION_IN_PROGRESS"


def test_improve_does_not_overwrite_the_current_fields(store: IdeaStore,
                                                       ollama_mock: OllamaMock) -> None:
    created = _created(store)
    ollama_mock.respond = lambda prompt: _improved_json(title="Título mejorado por la IA")
    improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                 instruction="Mejora el título")

    # The proposal is a version; it is never applied automatically (RF-8).
    assert store.get(created["id"])["title"] == created["title"]


# -- improve_idea without the IA (case 10) ---------------------------------------


def test_improve_without_ia_saves_the_pending_request_and_returns_the_notice(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)
    ollama_mock.available = False

    result = improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                          instruction="Cuantifica el beneficio")

    assert result["notice"] == "IA no disponible; tu solicitud quedará registrada."
    assert result["improvementRequest"]["instruction"] == "Cuantifica el beneficio"
    assert result["improvementRequest"]["requestedBy"] == "u_ana"
    assert result["improvementRequest"]["requestedAt"]

    stored = store.get(created["id"])
    assert stored["improvementRequest"]["instruction"] == "Cuantifica el beneficio"
    assert stored["reviewedByAI"] is False
    assert stored["generando"] is False
    assert stored["state"] == "EN_DESARROLLO"
    assert store.versions_of(created["id"]) == []
    assert ollama_mock.prompts == [], "no generation is attempted without the IA"


def test_improve_when_the_generation_fails_falls_back_to_case_10(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)

    def _fail(prompt: str) -> str:
        raise AssistantUnavailable("ASSISTANT_UNAVAILABLE", "El asistente no respondió.")

    ollama_mock.respond = _fail

    result = improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                          instruction="Cuantifica el beneficio")

    assert result["notice"] == "IA no disponible; tu solicitud quedará registrada."
    assert store.get(created["id"])["improvementRequest"]["instruction"] == "Cuantifica el beneficio"
    assert store.get(created["id"])["reviewedByAI"] is False
    assert store.versions_of(created["id"]) == []


def test_improve_with_an_uninterpretable_reply_falls_back_to_case_10(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)
    ollama_mock.respond = lambda prompt: "no hay JSON aquí"

    result = improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                          instruction="Cuantifica el beneficio")

    assert result["notice"] == "IA no disponible; tu solicitud quedará registrada."
    assert store.get(created["id"])["improvementRequest"]["requestedBy"] == "u_ana"
    assert store.versions_of(created["id"]) == []


def test_improve_clears_a_previous_pending_request_on_success(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)
    ollama_mock.available = False
    improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                 instruction="Primera solicitud")
    assert store.get(created["id"])["improvementRequest"] is not None

    ollama_mock.available = True
    ollama_mock.respond = lambda prompt: _improved_json()
    improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                 instruction="Segunda solicitud")

    assert store.get(created["id"])["improvementRequest"] is None
    assert store.get(created["id"])["reviewedByAI"] is True


# -- improve_idea guards (RNF-7, RF-8, RF-9) -------------------------------------


def test_improve_of_a_missing_idea_is_404(store: IdeaStore, ollama_mock: OllamaMock) -> None:
    with pytest.raises(DomainError) as error:
        improve_idea(store, ollama_mock, idea_id="nope", owner_id="u_ana", instruction="X")
    assert error.value.status_code == 404
    assert error.value.code == "IDEA_NOT_FOUND"


def test_improve_by_a_non_owner_is_403(store: IdeaStore, ollama_mock: OllamaMock) -> None:
    created = _created(store, owner_id="u_ana")
    with pytest.raises(DomainError) as error:
        improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_otro", instruction="X")
    assert error.value.status_code == 403
    assert error.value.code == "NOT_IDEA_OWNER"
    assert store.versions_of(created["id"]) == []


def test_improve_outside_en_desarrollo_is_409(store: IdeaStore, ollama_mock: OllamaMock) -> None:
    for state in ("SOLICITANDO_PUBLICACION", "VALIDADA_PUBLICA"):
        created = _created(store, owner_id="u_" + state[:3])
        store.update(created["id"], {"state": state})
        with pytest.raises(DomainError) as error:
            improve_idea(store, ollama_mock, idea_id=created["id"],
                         owner_id=f"u_{state[:3]}", instruction="X")
        assert error.value.status_code == 409
        assert error.value.code == "IDEA_NOT_IMPROVABLE"
        assert store.versions_of(created["id"]) == []


def test_improve_while_a_generation_is_in_flight_is_409(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)
    store.add_version(idea_id=created["id"], fields=_fields(title="Candidate"),
                      requested_by="improvement", generating=True)

    with pytest.raises(DomainError) as error:
        improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                     instruction="Otra mejora")
    assert error.value.status_code == 409
    assert error.value.code == "GENERATION_IN_PROGRESS"
    assert len(store.versions_of(created["id"])) == 1
    assert ollama_mock.prompts == []


# -- decide_version (RF-8, RF-13, decision once) ----------------------------------


def test_decide_accept_applies_the_version_and_keeps_en_desarrollo(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)
    ollama_mock.respond = lambda prompt: _improved_json(title="Título vigente")
    version = improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                           instruction="Mejora el título")["version"]

    idea = decide_version(store, idea_id=created["id"], version_id=version["id"],
                          owner_id="u_ana", accept=True)

    assert idea["currentVersionId"] == version["id"]
    assert idea["title"] == "Título vigente"
    assert idea["reviewedByAI"] is True
    assert idea["state"] == "EN_DESARROLLO"
    assert idea["generando"] is False
    assert store.get_version(created["id"], version["id"])["status"] == "VIGENTE"


def test_decide_discard_keeps_the_current_fields(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)
    ollama_mock.respond = lambda prompt: _improved_json(title="Candidata")
    version = improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                           instruction="Mejora")["version"]

    idea = decide_version(store, idea_id=created["id"], version_id=version["id"],
                          owner_id="u_ana", accept=False)

    assert idea["currentVersionId"] is None
    assert idea["title"] == created["title"]
    assert idea["reviewedByAI"] is True  # set by the improvement, kept on discard
    assert idea["generando"] is False
    assert store.get_version(created["id"], version["id"])["status"] == "DESCARTADA"


def test_decide_releases_the_generating_flag_for_manual_editing(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)
    ollama_mock.respond = lambda prompt: _improved_json()
    version = improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                           instruction="Mejora")["version"]

    decide_version(store, idea_id=created["id"], version_id=version["id"],
                   owner_id="u_ana", accept=False)

    updated = edit_idea(store, idea_id=created["id"], owner_id="u_ana",
                        fields=_fields(title="Edición tras decidir"))
    assert updated["title"] == "Edición tras decidir"


def test_decide_is_once_409_on_the_second_attempt(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)
    ollama_mock.respond = lambda prompt: _improved_json()
    version = improve_idea(store, ollama_mock, idea_id=created["id"], owner_id="u_ana",
                           instruction="Mejora")["version"]

    decide_version(store, idea_id=created["id"], version_id=version["id"],
                   owner_id="u_ana", accept=True)
    with pytest.raises(DomainError) as error:
        decide_version(store, idea_id=created["id"], version_id=version["id"],
                       owner_id="u_ana", accept=False)
    assert error.value.status_code == 409
    assert error.value.code == "VERSION_ALREADY_DECIDED"


def test_decide_of_an_unknown_version_or_idea_is_404(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)
    for kwargs in (
        {"idea_id": created["id"], "version_id": "ver_nope_99"},
        {"idea_id": "idea_nadie", "version_id": "ver_nadie_01"},
    ):
        with pytest.raises(DomainError) as error:
            decide_version(store, owner_id="u_ana", accept=True, **kwargs)
        assert error.value.status_code == 404


def test_decide_by_a_non_owner_is_403(store: IdeaStore) -> None:
    created = _created(store, owner_id="u_ana")
    version = store.add_version(idea_id=created["id"], fields=_fields(title="Candidata"),
                                requested_by="improvement")
    with pytest.raises(DomainError) as error:
        decide_version(store, idea_id=created["id"], version_id=version["id"],
                       owner_id="u_otro", accept=True)
    assert error.value.status_code == 403
    assert error.value.code == "NOT_IDEA_OWNER"
    assert store.get_version(created["id"], version["id"])["status"] == "PENDIENTE"


# -- adjust_in_chat (RF-13, RF-2, RF-9) --------------------------------------------


def test_adjust_with_the_ia_offers_the_precontextualized_conversation(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)

    result = adjust_in_chat(store, ollama_mock, idea_id=created["id"], owner_id="u_ana")

    assert result["mode"] == "chat"
    assert result["ideaId"] == created["id"]
    assert result["newCapture"] is False
    assert result["fields"] == _fields()
    assert store.versions_of(created["id"]) == [], "no version is created yet (RF-13)"


def test_adjust_without_the_ia_falls_back_to_manual_editing(
    store: IdeaStore, ollama_mock: OllamaMock
) -> None:
    created = _created(store)
    ollama_mock.available = False

    result = adjust_in_chat(store, ollama_mock, idea_id=created["id"], owner_id="u_ana")

    assert result["mode"] == "manual"
    assert result["ideaId"] == created["id"]
    assert result["fields"] == _fields()
    assert store.versions_of(created["id"]) == []
    assert ollama_mock.prompts == []


def test_adjust_of_a_missing_idea_is_404(store: IdeaStore, ollama_mock: OllamaMock) -> None:
    with pytest.raises(DomainError) as error:
        adjust_in_chat(store, ollama_mock, idea_id="nope", owner_id="u_ana")
    assert error.value.status_code == 404
    assert error.value.code == "IDEA_NOT_FOUND"


def test_adjust_by_a_non_owner_is_403(store: IdeaStore, ollama_mock: OllamaMock) -> None:
    created = _created(store, owner_id="u_ana")
    with pytest.raises(DomainError) as error:
        adjust_in_chat(store, ollama_mock, idea_id=created["id"], owner_id="u_otro")
    assert error.value.status_code == 403
    assert error.value.code == "NOT_IDEA_OWNER"


def test_adjust_outside_en_desarrollo_is_409(store: IdeaStore, ollama_mock: OllamaMock) -> None:
    for state in ("SOLICITANDO_PUBLICACION", "VALIDADA_PUBLICA"):
        created = _created(store, owner_id="u_" + state[:3])
        store.update(created["id"], {"state": state})
        with pytest.raises(DomainError) as error:
            adjust_in_chat(store, ollama_mock, idea_id=created["id"],
                           owner_id=f"u_{state[:3]}")
        assert error.value.status_code == 409
        assert error.value.code == "IDEA_NOT_ADJUSTABLE"


# -- contracts sanity ---------------------------------------------------------------


def test_the_ollama_mock_and_client_satisfy_the_assistant_contract() -> None:
    from features.assistant.infrastructure.ollama_client import OllamaClient
    from shared.contracts.assistant_client import AssistantClient

    mock = OllamaMock(available=False)
    real = OllamaClient("http://localhost:11434", "llama3.2")
    assert isinstance(mock, AssistantClient)
    assert isinstance(real, AssistantClient)
