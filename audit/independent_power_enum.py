#!/usr/bin/env python3
"""Independent exact-power audit for the locked McNemar design.

This implementation uses only the Python standard library.  It does not
import the repository statistics helper.  Power is evaluated by enumerating
the three task-level outcome categories directly: favored discordance,
opposing discordance, and concordance.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
from functools import lru_cache
import json
from math import comb


DECIMAL_PRECISION = 70
BISECTION_STEPS = 128


@lru_cache(maxsize=None)
def rejection_cells(
    task_count: int, alpha_text: str
) -> tuple[tuple[int, int, int, int], ...]:
    """Return rejecting trinomial cells for the doubled-lower-tail test."""

    alpha = Fraction(alpha_text)
    cells: list[tuple[int, int, int, int]] = []
    for favored in range(task_count + 1):
        for opposing in range(task_count - favored + 1):
            discordant = favored + opposing
            if discordant == 0:
                continue
            lower = min(favored, opposing)
            doubled_tail = Fraction(
                2 * sum(comb(discordant, index) for index in range(lower + 1)),
                2**discordant,
            )
            if doubled_tail <= alpha:
                concordant = task_count - discordant
                multiplicity = comb(task_count, favored) * comb(
                    task_count - favored, opposing
                )
                cells.append((favored, opposing, concordant, multiplicity))
    return tuple(cells)


def _power_term(probability: Decimal, exponent: int) -> Decimal:
    """Define the zero-exponent factor without evaluating Decimal(0) ** 0."""

    return Decimal(1) if exponent == 0 else probability**exponent


def exact_power(
    task_count: int,
    paired_risk_difference: Decimal,
    discordance_rate: Decimal,
    two_sided_alpha: Decimal,
) -> Decimal:
    """Enumerate unconditional rejection probability over trinomial cells."""

    if task_count < 1:
        raise ValueError("task_count must be positive")
    difference = abs(paired_risk_difference)
    if not Decimal(0) < discordance_rate <= Decimal(1):
        raise ValueError("discordance_rate must lie in (0, 1]")
    if difference > discordance_rate:
        raise ValueError("paired risk difference exceeds discordance rate")
    if not Decimal(0) < two_sided_alpha < Decimal(1):
        raise ValueError("two_sided_alpha must lie in (0, 1)")

    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        favored_probability = (discordance_rate + difference) / Decimal(2)
        opposing_probability = (discordance_rate - difference) / Decimal(2)
        concordant_probability = Decimal(1) - discordance_rate
        terms = []
        for favored, opposing, concordant, multiplicity in rejection_cells(
            task_count, str(two_sided_alpha)
        ):
            terms.append(
                Decimal(multiplicity)
                * _power_term(favored_probability, favored)
                * _power_term(opposing_probability, opposing)
                * _power_term(concordant_probability, concordant)
            )
        return sum(terms, Decimal(0))


def minimum_detectable_difference(
    task_count: int,
    target_power: Decimal,
    discordance_rate: Decimal,
    two_sided_alpha: Decimal,
) -> Decimal | None:
    """Invert enumerated power for the smallest effect reaching target power."""

    maximum_power = exact_power(
        task_count,
        discordance_rate,
        discordance_rate,
        two_sided_alpha,
    )
    if maximum_power < target_power:
        return None

    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        lower = Decimal(0)
        upper = discordance_rate
        for _ in range(BISECTION_STEPS):
            midpoint = (lower + upper) / Decimal(2)
            midpoint_power = exact_power(
                task_count,
                midpoint,
                discordance_rate,
                two_sided_alpha,
            )
            if midpoint_power >= target_power:
                upper = midpoint
            else:
                lower = midpoint
        return upper


def _within(observed: Decimal, expected: Decimal, tolerance: Decimal) -> bool:
    return abs(observed - expected) <= tolerance


def main() -> int:
    delta = Decimal("0.2")
    discordance = Decimal("0.5")
    alpha = Decimal("0.05")
    target = Decimal("0.8")
    tolerance = Decimal("5e-15")

    expected_power = {
        8: Decimal("0.015753443828124995"),
        15: Decimal("0.09828469240541773"),
        40: Decimal("0.354433201725586"),
        60: Decimal("0.5249353223627345"),
        102: Decimal("0.7976421823155178"),
        103: Decimal("0.8018189073387402"),
    }
    powers = {
        task_count: exact_power(task_count, delta, discordance, alpha)
        for task_count in expected_power
    }
    attainable_range_power = {
        task_count: exact_power(task_count, delta, discordance, alpha)
        for task_count in range(1, 16)
    }
    maximum_attainable_count, maximum_attainable_power = max(
        attainable_range_power.items(), key=lambda item: item[1]
    )

    expected_mde = {
        40: Decimal("0.3169030957634706"),
        60: Decimal("0.26351894673746423"),
        # This reproduces the arithmetic stored in the superseded receipt.
        # It does not validate 51 selected items as paired analysis units.
        51: Decimal("0.28467835603508285"),
    }
    mdes = {
        task_count: minimum_detectable_difference(
            task_count, target, discordance, alpha
        )
        for task_count in expected_mde
    }
    mde_at_eight = minimum_detectable_difference(8, target, discordance, alpha)
    maximum_power_at_eight = exact_power(8, discordance, discordance, alpha)

    first_target_count = next(
        task_count
        for task_count in range(1, 104)
        if exact_power(task_count, delta, discordance, alpha) >= target
    )

    checks: dict[str, bool] = {}
    for task_count, expected in expected_power.items():
        checks[f"power_n_{task_count}"] = _within(
            powers[task_count], expected, tolerance
        )
    for task_count, expected in expected_mde.items():
        observed = mdes[task_count]
        checks[f"mde_n_{task_count}"] = observed is not None and _within(
            observed, expected, tolerance
        )
    checks["mde_n_8_unattainable"] = mde_at_eight is None
    checks["maximum_power_n_8"] = _within(
        maximum_power_at_eight, Decimal("0.14453125"), tolerance
    )
    checks["all_n_le_15_inadequate"] = all(
        value < target for value in attainable_range_power.values()
    )
    checks["maximum_over_n_le_15_is_n_15"] = maximum_attainable_count == 15
    checks["minimum_pairs_for_target_power"] = first_target_count == 103

    passed = all(checks.values())
    report = {
        "implementation": "independent_direct_trinomial_enumeration",
        "imports_repository_helper": False,
        "assumptions": {
            "paired_risk_difference": str(delta),
            "discordance_rate": str(discordance),
            "two_sided_alpha": str(alpha),
            "target_power": str(target),
        },
        "power": {
            str(task_count): {
                "enumerated": str(value),
                "rounded_six_decimals": f"{value:.6f}",
            }
            for task_count, value in powers.items()
        },
        "mde_at_target_power": {
            str(task_count): str(value) for task_count, value in mdes.items()
        },
        "mde_at_eight_pairs": None,
        "maximum_power_at_eight_pairs": str(maximum_power_at_eight),
        "attainable_range_n_1_through_15": {
            "all_inadequate": checks["all_n_le_15_inadequate"],
            "maximum_power": str(maximum_attainable_power),
            "maximum_power_task_count": maximum_attainable_count,
        },
        "minimum_pairs_for_target_power": first_target_count,
        "checks": checks,
        "tolerance_against_recorded_binary64_values": str(tolerance),
        "status": "PASS" if passed else "FAIL",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
