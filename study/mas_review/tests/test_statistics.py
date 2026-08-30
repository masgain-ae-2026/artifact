from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mas_review.statistics import (  # noqa: E402
    DEFAULT_BOOTSTRAP_SEED,
    mcnemar_exact,
    mcnemar_exact_power,
    mcnemar_mde_for_power,
    paired_bootstrap_risk_difference,
    paired_risk_difference,
)


class McNemarTests(unittest.TestCase):
    def test_four_discordant_pairs_on_one_side_have_exact_p_one_eighth(self):
        result = mcnemar_exact([1, 1, 1, 1], [0, 0, 0, 0])
        self.assertEqual(result.g3r_only, 4)
        self.assertEqual(result.m4_only, 0)
        self.assertEqual(result.discordant, 4)
        self.assertEqual((result.p_numerator, result.p_denominator), (1, 8))
        self.assertEqual(result.p_value, 0.125)

    def test_one_versus_three_discordances_has_known_two_sided_p(self):
        result = mcnemar_exact([1, 0, 0, 0], [0, 1, 1, 1])
        self.assertEqual((result.g3r_only, result.m4_only), (1, 3))
        self.assertEqual((result.p_numerator, result.p_denominator), (5, 8))
        self.assertEqual(result.p_value, 0.625)

    def test_no_discordance_has_p_one(self):
        result = mcnemar_exact([1, 0, 1], [1, 0, 1])
        self.assertEqual(result.discordant, 0)
        self.assertEqual((result.p_numerator, result.p_denominator), (1, 1))

    def test_paired_inputs_are_strictly_validated(self):
        with self.assertRaisesRegex(ValueError, "different lengths"):
            mcnemar_exact([1], [1, 0])
        with self.assertRaisesRegex(ValueError, "not binary"):
            mcnemar_exact([1, 2], [1, 0])
        with self.assertRaisesRegex(ValueError, "not binary"):
            mcnemar_exact([1.0], [1])
        with self.assertRaisesRegex(ValueError, "at least one"):
            mcnemar_exact([], [])

    def test_exact_power_uses_primary_mirror_tasks_not_all_main_items(self):
        assumptions = {
            "paired_risk_difference": 0.2,
            "two_sided_alpha": 0.05,
            "discordance_rate": 0.5,
        }
        self.assertAlmostEqual(
            mcnemar_exact_power(40, **assumptions), 0.3544332017255856
        )
        self.assertAlmostEqual(
            mcnemar_exact_power(60, **assumptions), 0.5249353223627351
        )
        self.assertAlmostEqual(
            mcnemar_exact_power(8, **assumptions), 0.015753443828125
        )
        self.assertAlmostEqual(
            mcnemar_exact_power(
                8,
                paired_risk_difference=0.5,
                two_sided_alpha=0.05,
                discordance_rate=0.5,
            ),
            0.14453125,
        )
        with self.assertRaisesRegex(ValueError, "unattainable"):
            mcnemar_mde_for_power(
                8,
                target_power=0.8,
                two_sided_alpha=0.05,
                discordance_rate=0.5,
            )


class PairedRiskDifferenceTests(unittest.TestCase):
    def test_estimate_is_m4_minus_g3r(self):
        self.assertEqual(paired_risk_difference([1, 0, 0, 1], [1, 1, 1, 0]), 0.25)

    def test_degenerate_bootstrap_interval_is_exact(self):
        result = paired_bootstrap_risk_difference([0] * 8, [1] * 8)
        self.assertEqual(result.estimate, 1.0)
        self.assertEqual(result.lower, 1.0)
        self.assertEqual(result.upper, 1.0)
        self.assertEqual(result.seed, 20260715)
        self.assertEqual(result.replicates, 10_000)
        self.assertEqual(result.method, "paired-percentile-type7")

    def test_bootstrap_is_deterministic_for_locked_seed(self):
        g3r = [1, 1, 0, 0, 1, 0]
        m4 = [1, 0, 1, 1, 1, 0]
        first = paired_bootstrap_risk_difference(
            g3r,
            m4,
            replicates=1_000,
            seed=DEFAULT_BOOTSTRAP_SEED,
        )
        second = paired_bootstrap_risk_difference(
            g3r,
            m4,
            replicates=1_000,
            seed=DEFAULT_BOOTSTRAP_SEED,
        )
        self.assertEqual(first, second)
        self.assertEqual(first.estimate, paired_risk_difference(g3r, m4))
        self.assertLessEqual(first.lower, first.estimate)
        self.assertGreaterEqual(first.upper, first.estimate)

    def test_bootstrap_arguments_are_validated(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            paired_bootstrap_risk_difference([0], [1], replicates=0)
        with self.assertRaisesRegex(ValueError, "strictly"):
            paired_bootstrap_risk_difference([0], [1], confidence=1.0)
        with self.assertRaisesRegex(ValueError, "seed"):
            paired_bootstrap_risk_difference([0], [1], seed=True)


if __name__ == "__main__":
    unittest.main()
