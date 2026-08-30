#!/usr/bin/env python3
"""Deterministic, typed adequacy validation over receipt sets.

Historical note: this validator was implemented after the postmortem.  A
human audit found the 51-item denominator error.  The preserved receipts made
that audit possible, but did not autonomously detect the error at the time.

The validator makes no model call and reads no protected output.  Its only
study input is receipt metadata.  In particular, the adequacy interface does
not accept a bare integer count.  It accepts exactly one canonical set of
eligible-primary-analysis-unit receipts (U_A).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence

from audit.independent_power_enum import exact_power


TYPED_UNIT_RECEIPT_SCHEMA = "masgain-v2-typed-unit-receipt/v1"
ELIGIBLE_UNIT_SET_SCHEMA = "masgain-v2-typed-unit-receipt-set/v1"
ADEQUACY_DECISION_SCHEMA = "masgain-v2-typed-adequacy-decision/v1"
HISTORICAL_SELECTION_SCHEMA = "masgain-v2-prepared-selection-receipt/v2"

LOCKED_ANALYSIS = {
    "method": "unconditional_exact_two_sided_mcnemar",
    "paired_risk_difference": "0.2",
    "discordance_rate": "0.5",
    "two_sided_alpha": "0.05",
    "target_power": "0.8",
}

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_CONTENT_RUN_ID = re.compile(r"^[0-9a-f]{64}$")
_UNIT_ID = re.compile(r"^[a-z][a-z0-9_-]*:sha256:[0-9a-f]{64}$")
_UNIT_RECEIPT_KEYS = {
    "schema",
    "unit_type",
    "unit_id",
    "eligibility_decision",
    "predecessor_receipt_sha256s",
    "receipt_sha256",
}
_UNIT_SET_KEYS = {"schema", "unit_type", "receipts", "receipt_set_sha256"}
_DECISION_KEYS = {
    "schema",
    "decision",
    "input",
    "locked_analysis",
    "result",
    "execution_binding",
    "implementation_context",
    "receipt_sha256",
}


class UnitType(str, Enum):
    """The four downstream unit classes relevant to the adequacy boundary."""

    ELIGIBLE_PRIMARY_ANALYSIS_UNIT = "U_A"
    SUPPLEMENTAL_ITEM = "U_S"
    MIRROR_CAPABLE_TASK = "U_MC"
    ROLE_SWAPPED_MIRROR_PAIR = "U_M"


class ErrorCode(str, Enum):
    """Stable machine-readable rejection classes."""

    BARE_INTEGER = "E_BARE_INTEGER"
    INPUT_SCHEMA = "E_INPUT_SCHEMA"
    UNIT_TYPE_MISMATCH = "E_UNIT_TYPE_MISMATCH"
    RECEIPT_SHAPE = "E_RECEIPT_SHAPE"
    RECEIPT_INTEGRITY = "E_RECEIPT_INTEGRITY"
    UNIT_INELIGIBLE = "E_UNIT_INELIGIBLE"
    DUPLICATE_UNIT = "E_DUPLICATE_UNIT"
    NONCANONICAL_SET = "E_NONCANONICAL_SET"
    PROCEED_RECEIPT_REQUIRED = "E_PROCEED_RECEIPT_REQUIRED"
    PROCEED_RECEIPT_INVALID = "E_PROCEED_RECEIPT_INVALID"
    PROCEED_RECEIPT_UNBOUND = "E_PROCEED_RECEIPT_UNBOUND"
    PROCEED_REQUIRED = "E_PROCEED_REQUIRED"
    EXECUTION_BINDING = "E_EXECUTION_BINDING"


class EnforcementError(RuntimeError):
    """A typed, serializable rejection at the adequacy or call boundary."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        expected_type: str | None = None,
        observed_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.expected_type = expected_type
        self.observed_type = observed_type

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"

    def to_dict(self) -> dict[str, str]:
        value = {"code": self.code.value, "message": self.message}
        if self.expected_type is not None:
            value["expected_type"] = self.expected_type
        if self.observed_type is not None:
            value["observed_type"] = self.observed_type
        return value


@dataclass(frozen=True, slots=True)
class EligibleUnitSet:
    receipt_set_sha256: str
    receipts: tuple[Mapping[str, Any], ...]

    @property
    def count(self) -> int:
        return len(self.receipts)


@dataclass(frozen=True, slots=True)
class AdequacyDecision:
    receipt: Mapping[str, Any]

    @property
    def decision(self) -> str:
        return str(self.receipt["decision"])

    @property
    def receipt_sha256(self) -> str:
        return str(self.receipt["receipt_sha256"])


def _validate_json(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"non-string key at {path}")
            _validate_json(item, f"{path}.{key}")
        return
    raise TypeError(f"non-JSON value at {path}: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    _validate_json(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def content_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _hash_without(value: Mapping[str, Any], field: str) -> str:
    base = dict(value)
    base.pop(field, None)
    return content_sha256(base)


def _strict_json(path: str | Path) -> Mapping[str, Any]:
    def reject_constant(token: str) -> None:
        raise ValueError(f"non-finite constant {token}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise EnforcementError(
            ErrorCode.INPUT_SCHEMA,
            f"cannot read one strict JSON receipt object from {path}",
        ) from error
    if not isinstance(value, dict):
        raise EnforcementError(
            ErrorCode.INPUT_SCHEMA,
            "receipt input must be one JSON object",
        )
    return value


def load_receipt(path: str | Path) -> Mapping[str, Any]:
    """Read a strict JSON receipt without reading any referenced output."""

    return _strict_json(path)


def make_unit_receipt(
    *,
    unit_type: UnitType,
    unit_id: str,
    predecessor_receipt_sha256s: Sequence[str],
    eligibility_decision: str = "eligible",
) -> dict[str, Any]:
    """Construct a canonical typed receipt (also used by synthetic tests)."""

    base: dict[str, Any] = {
        "schema": TYPED_UNIT_RECEIPT_SCHEMA,
        "unit_type": unit_type.value,
        "unit_id": unit_id,
        "eligibility_decision": eligibility_decision,
        "predecessor_receipt_sha256s": list(predecessor_receipt_sha256s),
    }
    return {**base, "receipt_sha256": content_sha256(base)}


def make_receipt_set(
    receipts: Sequence[Mapping[str, Any]],
    *,
    unit_type: UnitType = UnitType.ELIGIBLE_PRIMARY_ANALYSIS_UNIT,
) -> dict[str, Any]:
    """Construct a deterministically ordered typed receipt set."""

    ordered = sorted((dict(item) for item in receipts), key=lambda item: str(item.get("unit_id")))
    base: dict[str, Any] = {
        "schema": ELIGIBLE_UNIT_SET_SCHEMA,
        "unit_type": unit_type.value,
        "receipts": ordered,
    }
    return {**base, "receipt_set_sha256": content_sha256(base)}


def _unit_type_error(observed: str, detail: str) -> EnforcementError:
    expected = "receipt_set<U_A>"
    return EnforcementError(
        ErrorCode.UNIT_TYPE_MISMATCH,
        f"adequacy requires {expected}; received {detail}",
        expected_type=expected,
        observed_type=observed,
    )


def validate_eligible_primary_analysis_units(value: Any) -> EligibleUnitSet:
    """Validate exactly one set of U_A receipts; never accept a count.

    U_S, U_MC, U_M, prepared-selection receipts, and bare integers are rejected
    before the power calculation is reached.
    """

    if isinstance(value, (bool, int)):
        raise EnforcementError(
            ErrorCode.BARE_INTEGER,
            "adequacy refuses a bare integer N; provide receipt_set<U_A>",
            expected_type="receipt_set<U_A>",
            observed_type="integer",
        )
    if not isinstance(value, Mapping):
        raise EnforcementError(
            ErrorCode.INPUT_SCHEMA,
            "adequacy input must be one typed receipt-set object",
            expected_type="receipt_set<U_A>",
            observed_type=type(value).__name__,
        )

    schema = value.get("schema")
    if schema == HISTORICAL_SELECTION_SCHEMA:
        main_items = value.get("main_items")
        count_text = str(main_items) if isinstance(main_items, int) else "unknown-count"
        raise _unit_type_error(
            "prepared_selection<mixed_selected_main_items>",
            f"{HISTORICAL_SELECTION_SCHEMA} with {count_text} mixed selected main items",
        )
    if schema != ELIGIBLE_UNIT_SET_SCHEMA:
        raise EnforcementError(
            ErrorCode.INPUT_SCHEMA,
            f"expected schema {ELIGIBLE_UNIT_SET_SCHEMA}; received {schema!r}",
            expected_type="receipt_set<U_A>",
            observed_type=str(schema),
        )

    observed_unit_type = value.get("unit_type")
    if observed_unit_type != UnitType.ELIGIBLE_PRIMARY_ANALYSIS_UNIT.value:
        raise _unit_type_error(
            f"receipt_set<{observed_unit_type}>",
            f"receipt_set<{observed_unit_type}>",
        )
    if set(value) != _UNIT_SET_KEYS:
        raise EnforcementError(
            ErrorCode.RECEIPT_SHAPE,
            "U_A receipt set has missing or unexpected fields",
        )
    stored_set_hash = value.get("receipt_set_sha256")
    if not isinstance(stored_set_hash, str) or not _HEX64.fullmatch(stored_set_hash):
        raise EnforcementError(
            ErrorCode.RECEIPT_INTEGRITY,
            "U_A receipt set lacks one lowercase SHA-256 content hash",
        )
    if stored_set_hash != _hash_without(value, "receipt_set_sha256"):
        raise EnforcementError(
            ErrorCode.RECEIPT_INTEGRITY,
            "U_A receipt-set content hash does not match its contents",
        )

    raw_receipts = value.get("receipts")
    if not isinstance(raw_receipts, list):
        raise EnforcementError(
            ErrorCode.RECEIPT_SHAPE,
            "U_A receipt set must contain a JSON array named receipts",
        )

    verified: list[Mapping[str, Any]] = []
    unit_ids: set[str] = set()
    for index, receipt in enumerate(raw_receipts):
        label = f"U_A receipt {index}"
        if not isinstance(receipt, Mapping) or set(receipt) != _UNIT_RECEIPT_KEYS:
            raise EnforcementError(
                ErrorCode.RECEIPT_SHAPE,
                f"{label} has missing or unexpected fields",
            )
        if receipt.get("schema") != TYPED_UNIT_RECEIPT_SCHEMA:
            raise EnforcementError(
                ErrorCode.RECEIPT_SHAPE,
                f"{label} has an unexpected schema",
            )
        observed = receipt.get("unit_type")
        if observed != UnitType.ELIGIBLE_PRIMARY_ANALYSIS_UNIT.value:
            raise _unit_type_error(
                f"receipt<{observed}>",
                f"receipt<{observed}> at receipts[{index}]",
            )
        if receipt.get("eligibility_decision") != "eligible":
            raise EnforcementError(
                ErrorCode.UNIT_INELIGIBLE,
                f"{label} is not marked eligible",
                expected_type="eligible U_A",
                observed_type=str(receipt.get("eligibility_decision")),
            )
        unit_id = receipt.get("unit_id")
        if not isinstance(unit_id, str) or not _UNIT_ID.fullmatch(unit_id):
            raise EnforcementError(
                ErrorCode.RECEIPT_SHAPE,
                f"{label} lacks one namespaced SHA-256 unit id",
            )
        if unit_id in unit_ids:
            raise EnforcementError(
                ErrorCode.DUPLICATE_UNIT,
                f"U_A receipt set repeats unit id {unit_id}",
            )
        predecessors = receipt.get("predecessor_receipt_sha256s")
        if (
            not isinstance(predecessors, list)
            or not predecessors
            or any(not isinstance(item, str) or not _HEX64.fullmatch(item) for item in predecessors)
            or len(predecessors) != len(set(predecessors))
        ):
            raise EnforcementError(
                ErrorCode.RECEIPT_SHAPE,
                f"{label} requires a nonempty set of predecessor receipt hashes",
            )
        stored_hash = receipt.get("receipt_sha256")
        if (
            not isinstance(stored_hash, str)
            or not _HEX64.fullmatch(stored_hash)
            or stored_hash != _hash_without(receipt, "receipt_sha256")
        ):
            raise EnforcementError(
                ErrorCode.RECEIPT_INTEGRITY,
                f"{label} content hash does not match its contents",
            )
        unit_ids.add(unit_id)
        verified.append(dict(receipt))

    observed_order = [str(item["unit_id"]) for item in verified]
    if observed_order != sorted(observed_order):
        raise EnforcementError(
            ErrorCode.NONCANONICAL_SET,
            "U_A receipts must be ordered lexicographically by unit_id",
        )
    return EligibleUnitSet(stored_set_hash, tuple(verified))


def _power_for_count(count: int) -> Decimal:
    if count == 0:
        return Decimal(0)
    return exact_power(
        count,
        Decimal(LOCKED_ANALYSIS["paired_risk_difference"]),
        Decimal(LOCKED_ANALYSIS["discordance_rate"]),
        Decimal(LOCKED_ANALYSIS["two_sided_alpha"]),
    )


def _validated_content_run_id(value: Any) -> str:
    if not isinstance(value, str) or not _CONTENT_RUN_ID.fullmatch(value):
        raise EnforcementError(
            ErrorCode.EXECUTION_BINDING,
            "adequacy decision requires one lowercase SHA-256 content_run_id",
        )
    return value


def evaluate_adequacy(
    unit_receipt_set: Any,
    *,
    content_run_id: str,
) -> AdequacyDecision:
    """Evaluate locked power for U_A and bind it to one content run."""

    units = validate_eligible_primary_analysis_units(unit_receipt_set)
    bound_run_id = _validated_content_run_id(content_run_id)
    achieved_power = _power_for_count(units.count)
    target_power = Decimal(LOCKED_ANALYSIS["target_power"])
    decision = "PROCEED" if achieved_power >= target_power else "STOP"
    base: dict[str, Any] = {
        "schema": ADEQUACY_DECISION_SCHEMA,
        "decision": decision,
        "input": {
            "receipt_set_sha256": units.receipt_set_sha256,
            "unit_type": UnitType.ELIGIBLE_PRIMARY_ANALYSIS_UNIT.value,
            "eligible_primary_analysis_units": units.count,
        },
        "locked_analysis": dict(LOCKED_ANALYSIS),
        "result": {
            "achieved_power": str(achieved_power),
            "target_power_met": achieved_power >= target_power,
        },
        "execution_binding": {"content_run_id": bound_run_id},
        "implementation_context": {
            "implemented_after_postmortem": True,
            "historical_error_detection": "human_audit",
            "model_calls_performed": 0,
            "protected_outputs_read": False,
        },
    }
    receipt = {**base, "receipt_sha256": content_sha256(base)}
    return AdequacyDecision(receipt)


def verify_proceed_receipt(
    proceed_receipt: Any,
    unit_receipt_set: Any,
    *,
    content_run_id: str,
) -> AdequacyDecision:
    """Recompute a proceed receipt for the exact U_A set and content run."""

    if proceed_receipt is None:
        raise EnforcementError(
            ErrorCode.PROCEED_RECEIPT_REQUIRED,
            "main-call boundary requires a valid PROCEED receipt",
        )
    if not isinstance(proceed_receipt, Mapping):
        raise EnforcementError(
            ErrorCode.PROCEED_RECEIPT_INVALID,
            "PROCEED receipt must be one JSON object",
        )
    if set(proceed_receipt) != _DECISION_KEYS or proceed_receipt.get("schema") != ADEQUACY_DECISION_SCHEMA:
        raise EnforcementError(
            ErrorCode.PROCEED_RECEIPT_INVALID,
            "PROCEED receipt has an unexpected schema or shape",
        )
    stored_hash = proceed_receipt.get("receipt_sha256")
    if (
        not isinstance(stored_hash, str)
        or not _HEX64.fullmatch(stored_hash)
        or stored_hash != _hash_without(proceed_receipt, "receipt_sha256")
    ):
        raise EnforcementError(
            ErrorCode.PROCEED_RECEIPT_INVALID,
            "PROCEED receipt content hash does not match its contents",
        )

    expected = evaluate_adequacy(
        unit_receipt_set,
        content_run_id=content_run_id,
    )
    if canonical_json(dict(proceed_receipt)) != canonical_json(dict(expected.receipt)):
        raise EnforcementError(
            ErrorCode.PROCEED_RECEIPT_UNBOUND,
            "decision receipt is not bound to the supplied U_A receipt set and locked analysis",
        )
    if expected.decision != "PROCEED":
        raise EnforcementError(
            ErrorCode.PROCEED_REQUIRED,
            f"main-call boundary is closed because adequacy decision is {expected.decision}",
        )
    return expected


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a receipt_set<U_A> and emit its deterministic adequacy decision."
    )
    parser.add_argument("receipt_set", help="path to one typed unit receipt set")
    parser.add_argument(
        "--content-run-id",
        required=True,
        help="lowercase SHA-256 content-run identifier bound into the decision",
    )
    arguments = parser.parse_args(argv)
    try:
        decision = evaluate_adequacy(
            load_receipt(arguments.receipt_set),
            content_run_id=arguments.content_run_id,
        )
    except EnforcementError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(decision.receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
