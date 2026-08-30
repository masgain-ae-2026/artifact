#!/usr/bin/env python3
"""One-command reproduction of the postmortem enforcement controls."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .adequacy import (
    EnforcementError,
    UnitType,
    evaluate_adequacy,
    load_receipt,
    make_receipt_set,
    make_unit_receipt,
    validate_eligible_primary_analysis_units,
)
from .main_call_runner import run_main_call


ARTIFACT_ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_RECEIPT = (
    ARTIFACT_ROOT
    / "receipts"
    / "superseded-selection-receipt-unit-accounting-error.json"
)
HISTORICAL_STOP_RECEIPT = (
    ARTIFACT_ROOT
    / "receipts"
    / "2026-07-19-power-plan-adequacy-successor.json"
)
SYNTHETIC_CONTENT_RUN_ID = "0" * 64


def _synthetic_units(count: int) -> dict[str, object]:
    """Create explicitly non-study U_A receipts for interface testing only."""

    receipts = []
    for index in range(count):
        label = f"synthetic-interface-test-{index:03d}".encode("ascii")
        unit_hash = hashlib.sha256(b"unit:" + label).hexdigest()
        predecessor_hash = hashlib.sha256(b"predecessor:" + label).hexdigest()
        receipts.append(
            make_unit_receipt(
                unit_type=UnitType.ELIGIBLE_PRIMARY_ANALYSIS_UNIT,
                unit_id=f"synthetic:sha256:{unit_hash}",
                predecessor_receipt_sha256s=[predecessor_hash],
            )
        )
    return make_receipt_set(receipts)


def _expect_rejection(label: str, action: object) -> EnforcementError:
    try:
        action()  # type: ignore[operator]
    except EnforcementError as error:
        print(f"{label}: REJECTED {error}")
        return error
    raise AssertionError(f"{label} unexpectedly passed")


def main() -> int:
    print(
        "POSTMORTEM_VALIDATOR implemented_after_postmortem=true "
        "historical_error_detection=human_audit"
    )
    print("SIDE_EFFECTS model_calls=0 protected_outputs_read=false")

    historical = load_receipt(HISTORICAL_RECEIPT)
    _expect_rejection(
        "NEGATIVE_CONTROL historical_51",
        lambda: validate_eligible_primary_analysis_units(historical),
    )
    _expect_rejection(
        "INPUT_CONTROL bare_integer_51",
        lambda: validate_eligible_primary_analysis_units(51),
    )
    for unit_type in (
        UnitType.SUPPLEMENTAL_ITEM,
        UnitType.MIRROR_CAPABLE_TASK,
        UnitType.ROLE_SWAPPED_MIRROR_PAIR,
    ):
        wrong_set = make_receipt_set([], unit_type=unit_type)
        _expect_rejection(
            f"TYPE_CONTROL {unit_type.value}",
            lambda candidate=wrong_set: validate_eligible_primary_analysis_units(candidate),
        )

    callback_calls = 0

    def blocked_callback() -> str:
        nonlocal callback_calls
        callback_calls += 1
        return "unexpected"

    empty_u_a = make_receipt_set([])
    _expect_rejection(
        "RUNNER_CONTROL missing_proceed",
        lambda: run_main_call(
            content_run_id=SYNTHETIC_CONTENT_RUN_ID,
            unit_receipt_set=empty_u_a,
            proceed_receipt=None,
            call=blocked_callback,
        ),
    )
    if callback_calls != 0:
        raise AssertionError("missing-receipt control crossed the call boundary")
    print(f"RUNNER_CONTROL missing_proceed_callback_calls={callback_calls}")

    historical_stop = load_receipt(HISTORICAL_STOP_RECEIPT)
    _expect_rejection(
        "RUNNER_CONTROL historical_stop_not_proceed",
        lambda: run_main_call(
            content_run_id=SYNTHETIC_CONTENT_RUN_ID,
            unit_receipt_set=empty_u_a,
            proceed_receipt=historical_stop,
            call=blocked_callback,
        ),
    )
    if callback_calls != 0:
        raise AssertionError("historical STOP control crossed the call boundary")
    print(f"RUNNER_CONTROL historical_stop_callback_calls={callback_calls}")

    stop = evaluate_adequacy(
        empty_u_a,
        content_run_id=SYNTHETIC_CONTENT_RUN_ID,
    )
    _expect_rejection(
        "RUNNER_CONTROL synthetic_empty_U_A_stop",
        lambda: run_main_call(
            content_run_id=SYNTHETIC_CONTENT_RUN_ID,
            unit_receipt_set=empty_u_a,
            proceed_receipt=stop.receipt,
            call=blocked_callback,
        ),
    )
    if callback_calls != 0:
        raise AssertionError("STOP control crossed the call boundary")
    print(
        "RUNNER_CONTROL synthetic_empty_U_A_stop_callback_calls="
        f"{callback_calls} study_evidence=false"
    )

    synthetic_u_a = _synthetic_units(103)
    proceed = evaluate_adequacy(
        synthetic_u_a,
        content_run_id=SYNTHETIC_CONTENT_RUN_ID,
    )
    if proceed.decision != "PROCEED":
        raise AssertionError("103-unit positive interface control did not proceed")

    def dry_run_callback() -> str:
        nonlocal callback_calls
        callback_calls += 1
        return "dry-run-only"

    result = run_main_call(
        content_run_id=SYNTHETIC_CONTENT_RUN_ID,
        unit_receipt_set=synthetic_u_a,
        proceed_receipt=proceed.receipt,
        call=dry_run_callback,
    )
    if result != "dry-run-only" or callback_calls != 1:
        raise AssertionError("positive interface control did not cross exactly once")
    print(
        "POSITIVE_CONTROL synthetic_U_A_103: decision=PROCEED "
        "callback_calls=1 study_evidence=false model_calls=0"
    )
    print("RESULT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
