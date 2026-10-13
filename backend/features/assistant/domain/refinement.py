"""Refinement rules for manual ideas (T-060, plan §4.5, spec RF-11).

Pure domain module (Constitution §4.2). It owns two things:
  1. The queue selection: ideas in `EN_DESARROLLO` with origin `manual` that
     still have no valid refined version, ordered from the oldest to the most
     recent (RF-11).
  2. The interpretation of the assistant's raw reply: the 7 fields are
     validated and any uninterpretable reply is a failure (spec case 6/14).
"""

import json
from collections.abc import Callable, Iterable
from typing import Any

from shared.contracts.idea_ledger import IDEA_FIELDS, ORIGIN_MANUAL, STATE_EN_DESARROLLO

# Requested-by marker that identifies a refinement pass (plan §2.5).
REQUESTED_BY_REFINEMENT = "refinement"

# A version in one of these statuses means the idea has already been refined
# for the current request, so it is out of the queue (RF-11 "válida").
_REFINED_STATUSES = ("PENDIENTE", "ACEPTADA", "VIGENTE")

# Sub-fields that the structured objects must contain (schema plan §2.2).
_PROPOSER_KEYS = ("name", "area", "contact")
_RESOURCE_KEYS = ("time", "people", "budget")


def needs_refinement(idea: dict, versions: Iterable[dict] = ()) -> bool:
    """`True` when the idea belongs to the refinement queue (RF-11).

    Criteria (conjunction): origin is `manual`, state is `EN_DESARROLLO`, and
    there is no refinement version in a refined status. A version whose only
    request was discarded does not count, so the idea may be refined again.
    """
    if idea.get("origin") != ORIGIN_MANUAL or idea.get("state") != STATE_EN_DESARROLLO:
        return False
    for version in versions:
        if (
            version.get("requestedBy") == REQUESTED_BY_REFINEMENT
            and version.get("status") in _REFINED_STATUSES
        ):
            return False
    return True


def build_refinement_queue(
    ideas: Iterable[dict], versions_for: Callable[[str], Iterable[dict]]
) -> list[dict]:
    """Orders the queue from the oldest to the most recent (RF-11).

    `versions_for` receives an idea id and yields its versions; it is injected
    by the caller so this module stays free of any store dependency.
    """
    candidates = [
        idea for idea in ideas if needs_refinement(idea, versions_for(idea.get("id", "")))
    ]
    candidates.sort(key=lambda idea: (idea.get("createdAt") or "", idea.get("id") or ""))
    return candidates


def extract_json_object(raw: str) -> dict | None:
    """Recovers the JSON object the assistant meant to return, or `None`.

    The model is asked for pure JSON (`think: false` in the client), but the
    reply may still arrive wrapped in code fences or preceded by prose — even
    a reasoning preamble that embeds sample objects. The text is parsed as a
    whole first; otherwise any thinking fence is dropped and the scan keeps the
    LAST well-formed top-level object, so an embedded example never shadows the
    real payload. `None` when no object can be recovered.
    """
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError):
        pass
    cut = 0
    for marker in ("</thinking>", "</think>"):
        idx = text.rfind(marker)
        if idx != -1:
            cut = max(cut, idx + len(marker))
    if cut:
        text = text[cut:].strip()
    decoder = json.JSONDecoder()
    result: dict | None = None
    i = 0
    while i < len(text):
        if text[i] != "{":
            i += 1
            continue
        try:
            obj, end = decoder.raw_decode(text, i)
        except (json.JSONDecodeError, ValueError):
            i += 1
            continue
        if isinstance(obj, dict):
            result = obj
        i = end
    return result


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _non_empty_obj(value: Any, keys: tuple[str, ...]) -> bool:
    if not isinstance(value, dict):
        return False
    return all(_non_empty_str(value.get(key)) for key in keys)


def interpret_fields(raw: str) -> dict | None:
    """Validates the 7 fields in the assistant reply; `None` on failure (case 14).

    The reply must contain exactly the 7 idea fields (plan §2.2): the four
    scalar strings plus `title`, with `proponent` and `estimatedResources` as
    structured objects whose sub-fields are present and non-empty.
    """
    data = extract_json_object(raw)
    if not isinstance(data, dict):
        return None
    for field in IDEA_FIELDS:
        if field not in data:
            return None
    if not _non_empty_str(data.get("title")):
        return None
    for field in ("description", "problem", "expectedBenefit", "strategicAlignment"):
        if not _non_empty_str(data.get(field)):
            return None
    if not _non_empty_obj(data.get("proponent"), _PROPOSER_KEYS):
        return None
    resources = data.get("estimatedResources")
    if not isinstance(resources, dict):
        return None
    if not all(isinstance(resources.get(key), str) for key in _RESOURCE_KEYS):
        return None
    return {field: data[field] for field in IDEA_FIELDS}
