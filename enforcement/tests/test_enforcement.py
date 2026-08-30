from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from enforcement.adequacy import (
    ELIGIBLE_UNIT_SET_SCHEMA,
    EnforcementError,
    ErrorCode,
    UnitType,
    content_sha256,
    evaluate_adequacy,
    load_receipt,
    make_receipt_set,
    make_unit_receipt,
    verify_proceed_receipt,
)
from enforcement.main_call_runner import run_main_call


ARTIFACT_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_PATH = (
    ARTIFACT_ROOT
    / "receipts"
    / "superseded-selection-receipt-unit-accounting-error.json"
)
HISTORICAL_STOP_PATH = (
    ARTIFACT_ROOT
    / "receipts"
    / "2026-07-19-power-plan-adequacy-successor.json"
)
CONTENT_RUN_ID = "0" * 64
OTHER_CONTENT_RUN_ID = "1" * 64


def synthetic_set(
    count: int,
    *,
    unit_type: UnitType = UnitType.ELIGIBLE_PRIMARY_ANALYSIS_UNIT,
) -> dict[str, object]:
    receipts = []
    for index in range(count):
        label = f"test-{unit_type.value}-{index:03d}".encode("ascii")
        receipts.append(
            make_unit_receipt(
                unit_type=unit_type,
                unit_id=f"test:sha256:{hashlib.sha256(b'unit:' + label).hexdigest()}",
                predecessor_receipt_sha256s=[
                    hashlib.sha256(b"predecessor:" + label).hexdigest()
                ],
            )
        )
    return make_receipt_set(receipts, unit_type=unit_type)


class TypedAdequacyTests(unittest.TestCase):
    def assert_code(self, expected: ErrorCode, action: object) -> EnforcementError:
        with self.assertRaises(EnforcementError) as raised:
            action()  # type: ignore[operator]
        self.assertEqual(expected, raised.exception.code)
        return raised.exception

    def test_refuses_bare_integer(self) -> None:
        error = self.assert_code(
            ErrorCode.BARE_INTEGER,
            lambda: evaluate_adequacy(51, content_run_id=CONTENT_RUN_ID),
        )
        self.assertEqual("receipt_set<U_A>", error.expected_type)
        self.assertEqual("integer", error.observed_type)

    def test_historical_51_item_negative_control_is_byte_preserved_and_rejected(self) -> None:
        self.assertEqual(
            "ef9192884f95e4f271c1348848f15133a28a295c80a384b3a8c1be52d8b54980",
            hashlib.sha256(HISTORICAL_PATH.read_bytes()).hexdigest(),
        )
        historical = load_receipt(HISTORICAL_PATH)
        error = self.assert_code(
            ErrorCode.UNIT_TYPE_MISMATCH,
            lambda: evaluate_adequacy(
                historical,
                content_run_id=CONTENT_RUN_ID,
            ),
        )
        self.assertEqual(
            "prepared_selection<mixed_selected_main_items>",
            error.observed_type,
        )
        self.assertIn("51 mixed selected main items", str(error))

    def test_each_non_analysis_unit_type_is_rejected(self) -> None:
        for unit_type in (
            UnitType.SUPPLEMENTAL_ITEM,
            UnitType.MIRROR_CAPABLE_TASK,
            UnitType.ROLE_SWAPPED_MIRROR_PAIR,
        ):
            with self.subTest(unit_type=unit_type.value):
                error = self.assert_code(
                    ErrorCode.UNIT_TYPE_MISMATCH,
                    lambda candidate=synthetic_set(1, unit_type=unit_type): evaluate_adequacy(
                        candidate,
                        content_run_id=CONTENT_RUN_ID,
                    ),
                )
                self.assertEqual(f"receipt_set<{unit_type.value}>", error.observed_type)

    def test_individual_receipt_cannot_be_relabelled_as_u_a(self) -> None:
        receipt = synthetic_set(1, unit_type=UnitType.ROLE_SWAPPED_MIRROR_PAIR)[
            "receipts"
        ][0]
        outer = make_receipt_set(
            [receipt], unit_type=UnitType.ELIGIBLE_PRIMARY_ANALYSIS_UNIT
        )
        self.assert_code(
            ErrorCode.UNIT_TYPE_MISMATCH,
            lambda: evaluate_adequacy(outer, content_run_id=CONTENT_RUN_ID),
        )

    def test_tampered_unit_receipt_is_rejected(self) -> None:
        original = synthetic_set(1)
        receipt = dict(original["receipts"][0])
        receipt["eligibility_decision"] = "excluded"
        outer = make_receipt_set([receipt])
        self.assert_code(
            ErrorCode.UNIT_INELIGIBLE,
            lambda: evaluate_adequacy(outer, content_run_id=CONTENT_RUN_ID),
        )

    def test_duplicate_units_are_rejected(self) -> None:
        original = synthetic_set(1)
        receipt = original["receipts"][0]
        duplicate = make_receipt_set([receipt, receipt])
        self.assert_code(
            ErrorCode.DUPLICATE_UNIT,
            lambda: evaluate_adequacy(duplicate, content_run_id=CONTENT_RUN_ID),
        )

    def test_noncanonical_set_order_is_rejected(self) -> None:
        original = synthetic_set(2)
        reversed_receipts = list(reversed(original["receipts"]))
        base = {
            "schema": ELIGIBLE_UNIT_SET_SCHEMA,
            "unit_type": "U_A",
            "receipts": reversed_receipts,
        }
        noncanonical = {**base, "receipt_set_sha256": content_sha256(base)}
        self.assert_code(
            ErrorCode.NONCANONICAL_SET,
            lambda: evaluate_adequacy(
                noncanonical,
                content_run_id=CONTENT_RUN_ID,
            ),
        )

    def test_power_boundary_is_recomputed_from_receipts(self) -> None:
        self.assertEqual(
            "STOP",
            evaluate_adequacy(
                synthetic_set(102),
                content_run_id=CONTENT_RUN_ID,
            ).decision,
        )
        self.assertEqual(
            "PROCEED",
            evaluate_adequacy(
                synthetic_set(103),
                content_run_id=CONTENT_RUN_ID,
            ).decision,
        )

    def test_empty_u_a_set_stops(self) -> None:
        decision = evaluate_adequacy(
            synthetic_set(0),
            content_run_id=CONTENT_RUN_ID,
        )
        self.assertEqual("STOP", decision.decision)
        self.assertEqual("0", decision.receipt["result"]["achieved_power"])


class MainCallBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calls = 0

    def callback(self) -> str:
        self.calls += 1
        return "called"

    def test_missing_proceed_receipt_cannot_execute(self) -> None:
        with self.assertRaises(EnforcementError) as raised:
            run_main_call(
                content_run_id=CONTENT_RUN_ID,
                unit_receipt_set=synthetic_set(0),
                proceed_receipt=None,
                call=self.callback,
            )
        self.assertEqual(ErrorCode.PROCEED_RECEIPT_REQUIRED, raised.exception.code)
        self.assertEqual(0, self.calls)

    def test_historical_stop_receipt_cannot_execute(self) -> None:
        self.assertEqual(
            "4ffc36525345e8d0872568b9b1300e48f249b1aebe8c316b53c1393bd589d2d1",
            hashlib.sha256(HISTORICAL_STOP_PATH.read_bytes()).hexdigest(),
        )
        with self.assertRaises(EnforcementError) as raised:
            run_main_call(
                content_run_id=CONTENT_RUN_ID,
                unit_receipt_set=synthetic_set(0),
                proceed_receipt=load_receipt(HISTORICAL_STOP_PATH),
                call=self.callback,
            )
        self.assertEqual(ErrorCode.PROCEED_RECEIPT_INVALID, raised.exception.code)
        self.assertEqual(0, self.calls)

    def test_stop_receipt_cannot_execute(self) -> None:
        units = synthetic_set(0)
        stop = evaluate_adequacy(units, content_run_id=CONTENT_RUN_ID)
        with self.assertRaises(EnforcementError) as raised:
            run_main_call(
                content_run_id=CONTENT_RUN_ID,
                unit_receipt_set=units,
                proceed_receipt=stop.receipt,
                call=self.callback,
            )
        self.assertEqual(ErrorCode.PROCEED_REQUIRED, raised.exception.code)
        self.assertEqual(0, self.calls)

    def test_forged_proceed_cannot_execute(self) -> None:
        units = synthetic_set(0)
        forged = dict(
            evaluate_adequacy(units, content_run_id=CONTENT_RUN_ID).receipt
        )
        forged["decision"] = "PROCEED"
        base = dict(forged)
        base.pop("receipt_sha256")
        forged["receipt_sha256"] = content_sha256(base)
        with self.assertRaises(EnforcementError) as raised:
            run_main_call(
                content_run_id=CONTENT_RUN_ID,
                unit_receipt_set=units,
                proceed_receipt=forged,
                call=self.callback,
            )
        self.assertEqual(ErrorCode.PROCEED_RECEIPT_UNBOUND, raised.exception.code)
        self.assertEqual(0, self.calls)

    def test_receipt_bound_to_different_set_cannot_execute(self) -> None:
        authorized = synthetic_set(103)
        other = synthetic_set(102)
        proceed = evaluate_adequacy(
            authorized,
            content_run_id=CONTENT_RUN_ID,
        )
        with self.assertRaises(EnforcementError) as raised:
            run_main_call(
                content_run_id=CONTENT_RUN_ID,
                unit_receipt_set=other,
                proceed_receipt=proceed.receipt,
                call=self.callback,
            )
        self.assertEqual(ErrorCode.PROCEED_RECEIPT_UNBOUND, raised.exception.code)
        self.assertEqual(0, self.calls)

    def test_receipt_cannot_be_replayed_for_different_content_run(self) -> None:
        units = synthetic_set(103)
        proceed = evaluate_adequacy(
            units,
            content_run_id=CONTENT_RUN_ID,
        )
        with self.assertRaises(EnforcementError) as raised:
            run_main_call(
                content_run_id=OTHER_CONTENT_RUN_ID,
                unit_receipt_set=units,
                proceed_receipt=proceed.receipt,
                call=self.callback,
            )
        self.assertEqual(ErrorCode.PROCEED_RECEIPT_UNBOUND, raised.exception.code)
        self.assertEqual(0, self.calls)

    def test_valid_recomputed_proceed_executes_once(self) -> None:
        units = synthetic_set(103)
        proceed = evaluate_adequacy(units, content_run_id=CONTENT_RUN_ID)
        verified = verify_proceed_receipt(
            proceed.receipt,
            units,
            content_run_id=CONTENT_RUN_ID,
        )
        self.assertEqual("PROCEED", verified.decision)
        result = run_main_call(
            content_run_id=CONTENT_RUN_ID,
            unit_receipt_set=units,
            proceed_receipt=proceed.receipt,
            call=self.callback,
        )
        self.assertEqual("called", result)
        self.assertEqual(1, self.calls)


if __name__ == "__main__":
    unittest.main()
