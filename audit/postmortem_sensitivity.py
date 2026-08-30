#!/usr/bin/env python3
"""Reproduce newly derived postmortem sensitivity boundaries.

This check is not part of the historical protocol.  It imports the preserved
independent exact-power implementation, makes no model call, and reads no
protected study output.
"""

from __future__ import annotations

from decimal import Decimal
import json

from independent_power_enum import exact_power


ALPHA = Decimal("0.05")
TARGET_POWER = Decimal("0.8")
SOURCE_RECORD_CONTENT_SHA256 = (
    "5c7563e5c2a47b0a79b2d54c1e75d75e951e275f40dc0472c100ac60834d5582"
)
RECORDED_REMAINING_CAPACITY = 1184
MODEL_CALLS_PER_ITEM = 8

BOUNDARIES = (
    (Decimal("0.2"), Decimal("0.3"), 61),
    (Decimal("0.2"), Decimal("0.5"), 103),
    (Decimal("0.2"), Decimal("0.7"), 144),
    (Decimal("0.1"), Decimal("0.5"), 408),
    (Decimal("0.3"), Decimal("0.5"), 46),
)


def main() -> int:
    assert 51 * MODEL_CALLS_PER_ITEM == 408
    assert 63 * MODEL_CALLS_PER_ITEM == 504
    assert RECORDED_REMAINING_CAPACITY == 1184

    cases = []
    for difference, discordance, first_n in BOUNDARIES:
        below = exact_power(first_n - 1, difference, discordance, ALPHA)
        reached = exact_power(first_n, difference, discordance, ALPHA)
        assert below < TARGET_POWER <= reached
        cases.append(
            {
                "delta": str(difference),
                "discordance": str(discordance),
                "first_n": first_n,
                "power_at_n_minus_1": f"{below:.6f}",
                "power_at_n": f"{reached:.6f}",
            }
        )

    report = {
        "schema": "masgain-v2-postmortem-sensitivity/v1",
        "status": "PASS",
        "classification": "newly_derived_postmortem_sensitivity",
        "historical_protocol_amended": False,
        "two_sided_alpha": str(ALPHA),
        "target_power": str(TARGET_POWER),
        "call_accounting": {
            "source_record_content_sha256": SOURCE_RECORD_CONTENT_SHA256,
            "source_json_pointers": {
                "recorded_remaining_capacity": "/remaining_logical_call_capacity",
                "model_calls_per_item": "/protocol_manifest/model_calls_per_item",
            },
            "recorded_remaining_capacity": RECORDED_REMAINING_CAPACITY,
            "model_calls_per_item": MODEL_CALLS_PER_ITEM,
            "derived_calls": {
                "historical_51_items": 408,
                "quota_only_reaudit_63_items": 504,
            },
        },
        "cases": cases,
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
