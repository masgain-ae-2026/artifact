"""Paired confirmatory statistics for the v2 mirror-task analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import math
import random
from collections.abc import Iterable, Sequence
from typing import Any


DEFAULT_BOOTSTRAP_REPLICATES = 10_000
DEFAULT_BOOTSTRAP_SEED = 20260715


def _binary_vector(values: Iterable[bool | int], name: str) -> tuple[int, ...]:
    vector = tuple(values)
    for index, value in enumerate(vector):
        is_binary = isinstance(value, bool) or (
            isinstance(value, int) and not isinstance(value, bool) and value in (0, 1)
        )
        if not is_binary:
            raise ValueError(f"{name}[{index}] is not binary: {value!r}")
    return tuple(int(value) for value in vector)


def _paired_binary(
    g3r_success: Iterable[bool | int],
    m4_success: Iterable[bool | int],
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    g3r = _binary_vector(g3r_success, "g3r_success")
    m4 = _binary_vector(m4_success, "m4_success")
    if len(g3r) != len(m4):
        raise ValueError(f"paired inputs have different lengths: {len(g3r)} and {len(m4)}")
    if not g3r:
        raise ValueError("paired analysis requires at least one task")
    return g3r, m4


@dataclass(frozen=True, slots=True)
class McNemarExactResult:
    task_count: int
    g3r_only: int
    m4_only: int
    discordant: int
    p_numerator: int
    p_denominator: int
    p_value: float
    alternative: str = "two-sided"

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


def mcnemar_exact(
    g3r_success: Iterable[bool | int],
    m4_success: Iterable[bool | int],
) -> McNemarExactResult:
    """Compute the exact two-sided McNemar test under Binomial(n, 0.5).

    The two-sided convention doubles the lower tail at the smaller discordant
    count and caps the result at one.  The reduced exact fraction is retained
    alongside its floating-point representation.
    """

    g3r, m4 = _paired_binary(g3r_success, m4_success)
    g3r_only = sum(left == 1 and right == 0 for left, right in zip(g3r, m4, strict=True))
    m4_only = sum(left == 0 and right == 1 for left, right in zip(g3r, m4, strict=True))
    discordant = g3r_only + m4_only
    if discordant == 0:
        exact = Fraction(1, 1)
    else:
        lower = min(g3r_only, m4_only)
        tail_numerator = sum(math.comb(discordant, index) for index in range(lower + 1))
        exact = min(Fraction(1, 1), Fraction(2 * tail_numerator, 2**discordant))
    return McNemarExactResult(
        task_count=len(g3r),
        g3r_only=g3r_only,
        m4_only=m4_only,
        discordant=discordant,
        p_numerator=exact.numerator,
        p_denominator=exact.denominator,
        p_value=float(exact),
    )


def mcnemar_exact_power(
    task_count: int,
    *,
    paired_risk_difference: float,
    two_sided_alpha: float,
    discordance_rate: float,
) -> float:
    """Return unconditional power for the exact two-sided McNemar test.

    The number of discordant pairs is integrated over
    ``Binomial(task_count, discordance_rate)``.  Conditional on that count,
    the favored-direction discordance probability is derived from the paired
    risk difference.  Rejection uses the same doubled-lower-tail convention
    as :func:`mcnemar_exact`.
    """

    if not isinstance(task_count, int) or isinstance(task_count, bool) or task_count < 1:
        raise ValueError("task_count must be a positive integer")
    if not 0.0 < two_sided_alpha < 1.0:
        raise ValueError("two_sided_alpha must lie strictly between zero and one")
    if not 0.0 < discordance_rate <= 1.0:
        raise ValueError("discordance_rate must lie in (0, 1]")
    difference = abs(float(paired_risk_difference))
    if difference > discordance_rate:
        raise ValueError("paired risk difference cannot exceed discordance rate")

    favored_probability = (discordance_rate + difference) / (2.0 * discordance_rate)
    power = 0.0
    for discordant in range(task_count + 1):
        discordant_probability = (
            math.comb(task_count, discordant)
            * discordance_rate**discordant
            * (1.0 - discordance_rate) ** (task_count - discordant)
        )
        for favored in range(discordant + 1):
            lower = min(favored, discordant - favored)
            null_p_value = min(
                1.0,
                2.0
                * sum(math.comb(discordant, index) for index in range(lower + 1))
                / 2**discordant,
            )
            if null_p_value <= two_sided_alpha:
                power += (
                    discordant_probability
                    * math.comb(discordant, favored)
                    * favored_probability**favored
                    * (1.0 - favored_probability) ** (discordant - favored)
                )
    return power


def mcnemar_mde_for_power(
    task_count: int,
    *,
    target_power: float,
    two_sided_alpha: float,
    discordance_rate: float,
) -> float:
    """Invert exact McNemar power for the smallest positive risk difference."""

    if not 0.0 < target_power < 1.0:
        raise ValueError("target_power must lie strictly between zero and one")
    maximum_power = mcnemar_exact_power(
        task_count,
        paired_risk_difference=discordance_rate,
        two_sided_alpha=two_sided_alpha,
        discordance_rate=discordance_rate,
    )
    if maximum_power < target_power:
        raise ValueError("target power is unattainable under the discordance assumption")
    lower = 0.0
    upper = discordance_rate
    for _ in range(64):
        midpoint = (lower + upper) / 2.0
        power = mcnemar_exact_power(
            task_count,
            paired_risk_difference=midpoint,
            two_sided_alpha=two_sided_alpha,
            discordance_rate=discordance_rate,
        )
        if power >= target_power:
            upper = midpoint
        else:
            lower = midpoint
    return upper


def paired_risk_difference(
    g3r_success: Iterable[bool | int],
    m4_success: Iterable[bool | int],
) -> float:
    """Return ``mean(M4 - G3R)`` over task-level mirror-pair successes."""

    g3r, m4 = _paired_binary(g3r_success, m4_success)
    return sum(right - left for left, right in zip(g3r, m4, strict=True)) / len(g3r)


def _type7_quantile(sorted_values: Sequence[float], probability: float) -> float:
    """R type-7 empirical quantile, with linear interpolation."""

    if not sorted_values:
        raise ValueError("quantile requires at least one value")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must lie in [0, 1]")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


@dataclass(frozen=True, slots=True)
class PairedBootstrapInterval:
    task_count: int
    estimate: float
    lower: float
    upper: float
    confidence: float
    replicates: int
    seed: int
    method: str = "paired-percentile-type7"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def paired_bootstrap_risk_difference(
    g3r_success: Iterable[bool | int],
    m4_success: Iterable[bool | int],
    *,
    replicates: int = DEFAULT_BOOTSTRAP_REPLICATES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
    confidence: float = 0.95,
) -> PairedBootstrapInterval:
    """Return a deterministic paired percentile interval for ``M4 - G3R``.

    Tasks, not individual orientations, are resampled.  The seed and the
    type-7 percentile convention are part of the returned result so a paper
    table cannot silently change either choice.
    """

    g3r, m4 = _paired_binary(g3r_success, m4_success)
    if not isinstance(replicates, int) or isinstance(replicates, bool) or replicates <= 0:
        raise ValueError("replicates must be a positive integer")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between zero and one")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")

    differences = tuple(right - left for left, right in zip(g3r, m4, strict=True))
    task_count = len(differences)
    rng = random.Random(seed)
    samples = [
        sum(differences[rng.randrange(task_count)] for _ in range(task_count)) / task_count
        for _ in range(replicates)
    ]
    samples.sort()
    alpha = 1.0 - confidence
    return PairedBootstrapInterval(
        task_count=task_count,
        estimate=sum(differences) / task_count,
        lower=_type7_quantile(samples, alpha / 2.0),
        upper=_type7_quantile(samples, 1.0 - alpha / 2.0),
        confidence=confidence,
        replicates=replicates,
        seed=seed,
    )
