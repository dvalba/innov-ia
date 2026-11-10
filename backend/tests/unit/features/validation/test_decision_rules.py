"""Unit tests for the final-decision pure rules (T-080, RF-27/RF-28, plan §4.9).

Covers `features.validation.domain.decision_rules`:
  - `average`: the simple mean of the criterion scores, 2 decimals (RF-28);
  - `band`: the band the average maps to, closed upward (case 26);
  - the decision-side guards: outcome validity (422), calibration state (409),
    a current non-PENDING evaluation (409), the mandatory reason for
    ARCHIVADA/RECHAZADA (400, case 28), and the band match (409
    DECISION_MISMATCH with `score`/`band`, case 27).
"""

import pytest

from features.validation.domain.decision_rules import (
    OUTCOMES,
    average,
    band,
    enforce_band_match,
    require_calibration_state,
    require_current_evaluation,
    require_reason,
    validate_outcome,
)
from shared.contracts.evaluation import EVALUATION_CRITERIA
from shared.exceptions.handlers import DomainError, ValidationFailed

DEFAULT = {"rejectionThreshold": 4, "acceptanceThreshold": 7}


def _evaluation(scores: list[int], status: str = "ACEPTADA") -> dict:
    criteria = [
        {"criterion": name, "score": scores[i], "justification": "j"}
        for i, name in enumerate(EVALUATION_CRITERIA)
    ]
    return {"status": status, "criteria": criteria}


# -- average (RF-28, PROMEDIO) ----------------------------------------------


def test_average_is_the_mean_of_the_five_scores_two_decimals() -> None:
    assert average(_evaluation([4, 6, 5, 7, 8])) == 6.0
    # 1/5 rounding: (4+5+5+5+9) = 28 / 5 = 5.6
    assert average(_evaluation([4, 5, 5, 5, 9])) == 5.6


def test_average_rounds_to_two_decimals() -> None:
    # (1+1+2+1+2) = 7 / 5 = 1.4
    assert average(_evaluation([1, 1, 2, 1, 2])) == 1.4
    # (1+1+1+1+3) = 7 / 5 = 1.4
    assert average(_evaluation([1, 1, 1, 1, 3])) == 1.4
    # (1+2+2+2+2) = 9 / 5 = 1.8
    assert average(_evaluation([1, 2, 2, 2, 2])) == 1.8


def test_average_of_no_evaluation_is_zero() -> None:
    assert average(None) == 0.0
    assert average({"status": "PENDING", "criteria": []}) == 0.0


# -- band (RF-28, case 26) ----------------------------------------------------


def test_band_below_rejection_is_rechazada() -> None:
    assert band(3.99, DEFAULT) == "RECHAZADA"
    assert band(0.0, DEFAULT) == "RECHAZADA"


def test_band_at_rejection_threshold_is_archivada_upper_band() -> None:
    # Case 26: exactly on the threshold -> the upper band (closed upward).
    assert band(4, DEFAULT) == "ARCHIVADA"


def test_band_in_the_middle_is_archivada() -> None:
    assert band(4.5, DEFAULT) == "ARCHIVADA"
    assert band(6.99, DEFAULT) == "ARCHIVADA"


def test_band_at_acceptance_threshold_is_aceptada_upper_band() -> None:
    # Case 26: exactly on the acceptance threshold -> ACEPTADA (closed upward).
    assert band(7, DEFAULT) == "ACEPTADA"


def test_band_at_or_above_acceptance_is_aceptada() -> None:
    assert band(7.5, DEFAULT) == "ACEPTADA"
    assert band(10.0, DEFAULT) == "ACEPTADA"


def test_band_respects_custom_thresholds() -> None:
    custom = {"rejectionThreshold": 2, "acceptanceThreshold": 9}
    assert band(1.5, custom) == "RECHAZADA"
    assert band(2, custom) == "ARCHIVADA"
    assert band(5.0, custom) == "ARCHIVADA"
    assert band(9, custom) == "ACEPTADA"
    assert band(9.5, custom) == "ACEPTADA"


# -- outcome validation (RF-27, 422) -----------------------------------------


def test_outcomes_are_the_three_final_states() -> None:
    assert set(OUTCOMES) == {"ACEPTADA", "ARCHIVADA", "RECHAZADA"}


@pytest.mark.parametrize("outcome", ["ACEPTADA", "ARCHIVADA", "RECHAZADA"])
def test_valid_outcomes_pass(outcome: str) -> None:
    validate_outcome(outcome)  # must not raise


@pytest.mark.parametrize("bad", ["Aprobada", "aceptada", "ARCHIVADA ", "", None, "PUBLICADA"])
def test_invalid_outcome_is_422(bad) -> None:
    with pytest.raises(ValidationFailed) as exc:
        validate_outcome(bad)
    # `ValidationFailed` is always a 422 (shared handler).
    assert exc.value.code == "DECISION_INVALID"
    assert exc.value.details["problems"]


# -- calibration state guard (RF-27, 409) ------------------------------------


def test_validada_publica_is_the_calibration_stage() -> None:
    require_calibration_state("VALIDADA_PUBLICA")  # must not raise


@pytest.mark.parametrize(
    "state",
    ["EN_DESARROLLO", "SOLICITANDO_PUBLICACION", "ACEPTADA", "ARCHIVADA", "RECHAZADA"],
)
def test_other_states_are_409(state: str) -> None:
    with pytest.raises(DomainError) as exc:
        require_calibration_state(state)
    assert exc.value.status_code == 409
    assert exc.value.code == "DECISION_STATE_INVALID"


# -- current evaluation guard (RF-27, case 22, 409) --------------------------


def test_missing_evaluation_is_409() -> None:
    with pytest.raises(DomainError) as exc:
        require_current_evaluation(None)
    assert exc.value.status_code == 409
    assert exc.value.code == "EVALUATION_MISSING"


def test_pending_evaluation_is_409() -> None:
    with pytest.raises(DomainError) as exc:
        require_current_evaluation(_evaluation([5, 5, 5, 5, 5], status="PENDING"))
    assert exc.value.status_code == 409
    assert exc.value.code == "EVALUATION_PENDING"


@pytest.mark.parametrize("status", ["GENERADA", "ACEPTADA", "SUSTITUIDA"])
def test_non_pending_evaluation_passes(status: str) -> None:
    evaluation = _evaluation([5, 5, 5, 5, 5], status=status)
    assert require_current_evaluation(evaluation) is evaluation


# -- reason guard (RF-27, case 28, 400) ---------------------------------------


@pytest.mark.parametrize("reason", ["Insuficiente alineación estratégica.", "  motivo  "])
def test_archivada_and_rechazada_accept_a_non_blank_reason(reason: str) -> None:
    require_reason("ARCHIVADA", reason)
    require_reason("RECHAZADA", reason)


def test_aceptada_never_requires_a_reason() -> None:
    require_reason("ACEPTADA", None)
    require_reason("ACEPTADA", "")


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_archivada_without_reason_is_400(reason) -> None:
    with pytest.raises(DomainError) as exc:
        require_reason("ARCHIVADA", reason)
    assert exc.value.status_code == 400
    assert exc.value.code == "DECISION_REASON_REQUIRED"


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_rechazada_without_reason_is_400(reason) -> None:
    with pytest.raises(DomainError) as exc:
        require_reason("RECHAZADA", reason)
    assert exc.value.status_code == 400
    assert exc.value.code == "DECISION_REASON_REQUIRED"


# -- band match (RF-27/RF-28, case 27, 409) ----------------------------------


@pytest.mark.parametrize(
    ("avg", "outcome"),
    [(8.0, "ACEPTADA"), (4.5, "ARCHIVADA"), (2.0, "RECHAZADA"), (7, "ACEPTADA"), (4, "ARCHIVADA")],
)
def test_matching_band_passes_and_returns_the_band(avg: float, outcome: str) -> None:
    assert enforce_band_match(outcome, avg, DEFAULT) == outcome


def test_mismatch_is_409_with_score_and_band() -> None:
    # Average 4.5 is ARCHIVADA; forcing ACEPTADA must be rejected (case 27).
    with pytest.raises(DomainError) as exc:
        enforce_band_match("ACEPTADA", 4.5, DEFAULT)
    assert exc.value.status_code == 409
    assert exc.value.code == "DECISION_MISMATCH"
    assert exc.value.details == {"score": 4.5, "band": "ARCHIVADA"}


def test_mismatch_lower_band_is_409() -> None:
    # Average 8.0 is ACEPTADA; forcing RECHAZADA must be rejected.
    with pytest.raises(DomainError) as exc:
        enforce_band_match("RECHAZADA", 8.0, DEFAULT)
    assert exc.value.status_code == 409
    assert exc.value.code == "DECISION_MISMATCH"
    assert exc.value.details == {"score": 8.0, "band": "ACEPTADA"}


def test_threshold_change_moves_the_band_not_previously_decided() -> None:
    # Case 31 is about NOT recalculating; here the band simply follows the
    # thresholds passed in: the same average maps to a different band under
    # different thresholds.
    assert band(5.0, DEFAULT) == "ARCHIVADA"
    assert band(5.0, {"rejectionThreshold": 3, "acceptanceThreshold": 5}) == "ACEPTADA"
