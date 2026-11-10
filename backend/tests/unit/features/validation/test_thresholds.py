"""Unit tests for the calibration-thresholds store and rules (T-081, RF-28).

Covers:
  - `threshold_rules.validate_thresholds`: the integer 1-10 range and the
    rejection < acceptance invariant (422 `THRESHOLDS_INVALID` with problems);
  - `ThresholdStore`: the single-record JSON store (get/put/has, no-legacy);
  - `admin_thresholds`: the default (case 31) and the audited save.
"""

import pytest

from features.validation.domain.threshold_rules import (
    DEFAULT_ACCEPTANCE_THRESHOLD,
    DEFAULT_REJECTION_THRESHOLD,
    DEFAULT_THRESHOLD,
    validate_thresholds,
)
from features.validation.infrastructure.threshold_store import ThresholdStore
from features.validation.use_cases.admin_thresholds import get_thresholds, save_thresholds
from shared.exceptions.handlers import ValidationFailed
from tests.conftest import InMemoryStore

DEFAULT_NOW = "2026-11-10T00:00:00"


# -- defaults (RF-28, case 31) -------------------------------------------------


def test_default_thresholds_are_4_and_7() -> None:
    assert DEFAULT_THRESHOLD == {"rejectionThreshold": 4, "acceptanceThreshold": 7}
    assert DEFAULT_REJECTION_THRESHOLD == 4
    assert DEFAULT_ACCEPTANCE_THRESHOLD == 7


# -- validate_thresholds (RF-28) ----------------------------------------------


def test_valid_pair_is_returned_normalized() -> None:
    assert validate_thresholds({"rejectionThreshold": 2, "acceptanceThreshold": 9}) == {
        "rejectionThreshold": 2, "acceptanceThreshold": 9,
    }


def test_default_pair_is_valid() -> None:
    assert validate_thresholds(DEFAULT_THRESHOLD) == DEFAULT_THRESHOLD


def test_boundaries_are_valid() -> None:
    assert validate_thresholds({"rejectionThreshold": 1, "acceptanceThreshold": 10}) == {
        "rejectionThreshold": 1, "acceptanceThreshold": 10,
    }


def test_equality_is_invalid() -> None:
    with pytest.raises(ValidationFailed) as exc:
        validate_thresholds({"rejectionThreshold": 5, "acceptanceThreshold": 5})
    assert exc.value.code == "THRESHOLDS_INVALID"
    assert exc.value.details["problems"]


def test_rejection_greater_than_acceptance_is_invalid() -> None:
    with pytest.raises(ValidationFailed) as exc:
        validate_thresholds({"rejectionThreshold": 7, "acceptanceThreshold": 4})
    assert exc.value.code == "THRESHOLDS_INVALID"


@pytest.mark.parametrize("value", [0, 11, -1])
def test_out_of_range_is_invalid(value) -> None:
    with pytest.raises(ValidationFailed) as exc:
        validate_thresholds({"rejectionThreshold": value, "acceptanceThreshold": 7})
    assert exc.value.code == "THRESHOLDS_INVALID"

    with pytest.raises(ValidationFailed) as exc:
        validate_thresholds({"rejectionThreshold": 4, "acceptanceThreshold": value})
    assert exc.value.code == "THRESHOLDS_INVALID"


@pytest.mark.parametrize("value", [4.5, "5", None, [5], {"v": 5}])
def test_non_integer_is_invalid(value) -> None:
    with pytest.raises(ValidationFailed) as exc:
        validate_thresholds({"rejectionThreshold": value, "acceptanceThreshold": 7})
    assert exc.value.code == "THRESHOLDS_INVALID"


@pytest.mark.parametrize("value", [True, False])
def test_boolean_is_not_an_integer(value) -> None:
    with pytest.raises(ValidationFailed) as exc:
        validate_thresholds({"rejectionThreshold": value, "acceptanceThreshold": 7})
    assert exc.value.code == "THRESHOLDS_INVALID"


def test_missing_fields_are_invalid() -> None:
    with pytest.raises(ValidationFailed) as exc:
        validate_thresholds({})
    assert len(exc.value.details["problems"]) == 2

    with pytest.raises(ValidationFailed) as exc:
        validate_thresholds(None)
    assert len(exc.value.details["problems"]) == 2


def test_multiple_problems_are_all_reported() -> None:
    with pytest.raises(ValidationFailed) as exc:
        validate_thresholds({"rejectionThreshold": 0, "acceptanceThreshold": "x"})
    assert len(exc.value.details["problems"]) == 2


# -- ThresholdStore ------------------------------------------------------------


def test_store_has_nothing_when_empty() -> None:
    store = ThresholdStore(InMemoryStore())
    assert store.has() is False
    assert store.get() is None


def test_store_put_then_get_round_trips() -> None:
    store = ThresholdStore(InMemoryStore())
    saved = store.put({
        "rejectionThreshold": 3, "acceptanceThreshold": 8,
        "updatedBy": "u_admin", "updatedAt": DEFAULT_NOW,
    })
    assert saved == store.get()
    assert store.has() is True


def test_store_put_replaces_the_previous_record() -> None:
    store = ThresholdStore(InMemoryStore())
    store.put({"rejectionThreshold": 4, "acceptanceThreshold": 7,
               "updatedBy": "u_a", "updatedAt": "t1"})
    stored = store.put({"rejectionThreshold": 2, "acceptanceThreshold": 9,
                        "updatedBy": "u_b", "updatedAt": "t2"})
    assert stored["updatedBy"] == "u_b"
    assert store.get() == stored


def test_store_get_returns_a_copy_not_the_stored_reference() -> None:
    store = ThresholdStore(InMemoryStore())
    store.put({"rejectionThreshold": 4, "acceptanceThreshold": 7,
               "updatedBy": "u", "updatedAt": "t"})
    first = store.get()
    first["rejectionThreshold"] = 99
    assert store.get()["rejectionThreshold"] == 4


# -- use cases -----------------------------------------------------------------


def test_get_returns_the_default_when_nothing_is_saved() -> None:
    store = ThresholdStore(InMemoryStore())
    assert get_thresholds(store) == DEFAULT_THRESHOLD
    assert store.has() is False  # a read never persists


def test_get_returns_the_stored_record() -> None:
    store = ThresholdStore(InMemoryStore())
    store.put({"rejectionThreshold": 2, "acceptanceThreshold": 8,
               "updatedBy": "u_admin", "updatedAt": DEFAULT_NOW})
    assert get_thresholds(store) == {
        "rejectionThreshold": 2, "acceptanceThreshold": 8,
        "updatedBy": "u_admin", "updatedAt": DEFAULT_NOW,
    }


def test_save_persists_audited_record() -> None:
    store = ThresholdStore(InMemoryStore())
    saved = save_thresholds(store, {"rejectionThreshold": 3, "acceptanceThreshold": 8},
                            user_id="u_admin", now=DEFAULT_NOW)
    assert saved == {
        "rejectionThreshold": 3, "acceptanceThreshold": 8,
        "updatedBy": "u_admin", "updatedAt": DEFAULT_NOW,
    }
    assert store.get() == saved


def test_save_rejects_a_malformed_payload_and_persists_nothing() -> None:
    store = ThresholdStore(InMemoryStore())
    with pytest.raises(ValidationFailed):
        save_thresholds(store, {"rejectionThreshold": 7, "acceptanceThreshold": 4},
                        user_id="u_admin")
    assert store.has() is False
