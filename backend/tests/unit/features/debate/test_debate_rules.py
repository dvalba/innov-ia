"""Global debate-days rules tests (T-089, RF-24, RNF-11).

Covers the pure domain module `debate_rules`: the default (30 days), the
`1..90` integer validation (booleans, floats, strings and missing fields are
rejected), and the deadline computation that is fixed at opening and never
recomputed (v2.4, decision D23).
"""

import pytest

from features.debate.domain.debate_rules import (
    DEBATE_DAYS_DEFAULT,
    DEBATE_DAYS_MAX,
    DEBATE_DAYS_MIN,
    DEFAULT_DEBATE_DAYS,
    deadline_after_days,
    validate_debate_days,
)
from shared.exceptions.handlers import ValidationFailed

# -- defaults -------------------------------------------------------------------


def test_the_default_debate_days_record_is_30() -> None:
    assert DEBATE_DAYS_DEFAULT == 30
    assert DEBATE_DAYS_MIN == 1
    assert DEBATE_DAYS_MAX == 90
    assert DEFAULT_DEBATE_DAYS == {"debateDays": 30, "updatedBy": None, "updatedAt": None}


def test_the_default_deadline_is_published_plus_30_days() -> None:
    assert deadline_after_days("2026-06-01T00:00:00") == "2026-07-01T00:00:00"


# -- validation (RF-24) ---------------------------------------------------------


@pytest.mark.parametrize("value", [1, 30, 90])
def test_validate_accepts_an_integer_in_the_range(value) -> None:
    assert validate_debate_days({"debateDays": value}) == value


@pytest.mark.parametrize("payload", [
    {"debateDays": 0},
    {"debateDays": 91},
    {"debateDays": -5},
    {"debateDays": 30.0},
    {"debateDays": "30"},
    {"debateDays": True},
    {"debateDays": False},
    {"debateDays": None},
    {},
])
def test_validate_rejects_a_malformed_payload_with_debate_days_invalid(payload) -> None:
    with pytest.raises(ValidationFailed) as error:
        validate_debate_days(payload)
    assert error.value.code == "DEBATE_DAYS_INVALID"
    assert error.value.details["problems"]


def test_validate_rejects_a_non_dict_payload() -> None:
    with pytest.raises(ValidationFailed) as error:
        validate_debate_days("30")
    assert error.value.code == "DEBATE_DAYS_INVALID"


# -- the deadline is fixed at opening (v2.4) ------------------------------------


def test_the_deadline_adds_the_configured_days_to_the_reference() -> None:
    assert deadline_after_days("2026-06-01T00:00:00", 40) == "2026-07-11T00:00:00"
    assert deadline_after_days("2026-06-01T00:00:00", 1) == "2026-06-02T00:00:00"
    assert deadline_after_days("2026-06-01T00:00:00", 90) == "2026-08-30T00:00:00"


def test_the_deadline_never_reads_or_recomputes_from_the_configuration() -> None:
    # v2.4 (D23): the deadline only depends on the reference date and the number
    # of days in force at opening; there is no access to the stored record.
    assert deadline_after_days("2026-06-01T00:00:00", 30) == "2026-07-01T00:00:00"
    assert deadline_after_days("2026-06-01T00:00:00", 30) == "2026-07-01T00:00:00"
