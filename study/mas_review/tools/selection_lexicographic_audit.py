"""Re-audit C3 allocation with a primary-unit-first objective.

This command verifies the complete private C3 evidence lineage, reconstructs
the result-free eligibility relation, and solves counterfactual allocations.
It never invokes a model runner or reads human-gold or main-study output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mas_review.canonical import canonical_json, content_sha256  # noqa: E402
from mas_review.clean_archive import verify_completed_clean_run_archive  # noqa: E402
from mas_review.construction import (  # noqa: E402
    STRATUM_ORDER,
    _derive_stratum_selection,
    derive_evidence_constrained_pilot_targets,
    load_pinned_task_universe,
)
from mas_review.independent_archive import (  # noqa: E402
    verify_completed_independent_test_archive,
)
from mas_review.mutation_freeze import verify_mutation_freeze  # noqa: E402
from mas_review.program_review import verify_final_program_review_plan  # noqa: E402
from mas_review.promotion import promote_verified_programs  # noqa: E402
from mas_review.qualification_archive import (  # noqa: E402
    verify_completed_machine_qualification_archive,
)
from mas_review.selection import (  # noqa: E402
    _dev_excluded,
    _locked_order,
    derive_eligibility,
    derive_program_options,
    load_challenge_pool,
    load_selection_config,
)
from mas_review.witness import verify_withheld_plus_witness_plan  # noqa: E402
from mas_review.witness_archive import (  # noqa: E402
    verify_completed_withheld_plus_witness_archive,
)


SUPPLEMENTAL_STRATA = ("both_clean", "both_faulty")
PRIMARY_STRATUM = "mirror"
PROXY_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify and re-audit C3 selection without model calls."
    )
    parser.add_argument("--bundle-root", required=True)
    parser.add_argument("--clean-run-root", required=True)
    parser.add_argument("--freeze-root", required=True)
    parser.add_argument("--qualification-run-root", required=True)
    parser.add_argument("--witness-plan-root", required=True)
    parser.add_argument("--witness-run-root", required=True)
    parser.add_argument("--program-review-root", required=True)
    parser.add_argument("--review-plan-root", required=True)
    parser.add_argument("--independent-run-root", required=True)
    parser.add_argument("--selection-config", required=True)
    parser.add_argument("--challenge-pool", required=True)
    parser.add_argument("--predecessor-receipt", required=True)
    parser.add_argument("--recorded-date", required=True)
    return parser


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strict_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def _verified_execution_boundary() -> dict[str, bool]:
    remaining_proxy_variables = [
        name for name in PROXY_VARIABLES if name in os.environ
    ]
    if remaining_proxy_variables:
        raise RuntimeError(
            "selection audit requires proxy variables to be absent: "
            + ", ".join(remaining_proxy_variables)
        )
    process_id = os.getpid()
    session_id = os.getsid(0)
    if session_id != process_id:
        raise RuntimeError(
            "selection audit must run as a setsid session leader"
        )
    return {
        "proxy_variables_removed": not remaining_proxy_variables,
        "setsid_used": session_id == process_id,
    }


def _tie_rank(seed: str, case_id: str, task_id: str, assignment: str) -> str:
    material = canonical_json(
        {
            "schema": "masgain-v2-selection-audit-tie/v1",
            "selection_seed_material": seed,
            "case_id": case_id,
            "task_id": task_id,
            "assignment": assignment,
        }
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _solve(
    *,
    case_id: str,
    order: Sequence[Any],
    eligibility: Sequence[Any],
    seed: str,
    minimum: Mapping[str, int],
    exact: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Solve task-disjoint allocation by exhaustive dynamic programming.

    The objective is lexicographic.  It maximizes mirror tasks, then total
    supplemental tasks, then minimizes a deterministic vector of SHA-256
    choice ranks.  Minimum or exact supplemental quotas are hard constraints.
    """

    records = {record.task_id: record for record in eligibility}
    flexible = [
        entry
        for entry in order
        if records.get(entry.task_id) is not None
        and records[entry.task_id].eligible_strata.intersection(
            {*SUPPLEMENTAL_STRATA, PRIMARY_STRATUM}
        )
    ]

    # State is (both_clean, both_faulty, mirror).  For each count state, keep
    # the lexicographically least hash-ranked decision vector and its choices.
    states: dict[
        tuple[int, int, int], tuple[tuple[str, ...], tuple[str, ...]]
    ] = {(0, 0, 0): ((), ())}
    for entry in flexible:
        eligible = records[entry.task_id].eligible_strata
        choices = ("unselected",) + tuple(
            name
            for name in (*SUPPLEMENTAL_STRATA, PRIMARY_STRATUM)
            if name in eligible
        )
        successor: dict[
            tuple[int, int, int], tuple[tuple[str, ...], tuple[str, ...]]
        ] = {}
        for counts, (signature, assignments) in states.items():
            for choice in choices:
                clean, faulty, mirror = counts
                if choice == "both_clean":
                    clean += 1
                elif choice == "both_faulty":
                    faulty += 1
                elif choice == "mirror":
                    mirror += 1
                next_counts = (clean, faulty, mirror)
                if exact is not None and (
                    clean > exact.get("both_clean", len(flexible))
                    or faulty > exact.get("both_faulty", len(flexible))
                ):
                    continue
                candidate = (
                    signature + (_tie_rank(seed, case_id, entry.task_id, choice),),
                    assignments + (choice,),
                )
                incumbent = successor.get(next_counts)
                if incumbent is None or candidate[0] < incumbent[0]:
                    successor[next_counts] = candidate
        states = successor

    feasible: list[
        tuple[
            tuple[int, int, int],
            tuple[tuple[str, ...], tuple[str, ...]],
        ]
    ] = []
    for counts, trace in states.items():
        clean, faulty, _ = counts
        if clean < minimum.get("both_clean", 0):
            continue
        if faulty < minimum.get("both_faulty", 0):
            continue
        if exact is not None and (
            clean != exact.get("both_clean", clean)
            or faulty != exact.get("both_faulty", faulty)
        ):
            continue
        feasible.append((counts, trace))
    if not feasible:
        return {
            "case_id": case_id,
            "feasible": False,
            "minimum_supplemental_tasks": dict(minimum),
            "exact_supplemental_tasks": dict(exact) if exact is not None else None,
        }

    maximum_mirror = max(counts[2] for counts, _ in feasible)
    mirror_optimal = [row for row in feasible if row[0][2] == maximum_mirror]
    maximum_supplemental = max(row[0][0] + row[0][1] for row in mirror_optimal)
    objective_optimal = [
        row
        for row in mirror_optimal
        if row[0][0] + row[0][1] == maximum_supplemental
    ]
    counts, (tie_signature, assignments) = min(
        objective_optimal,
        key=lambda row: row[1][0],
    )
    selected = {name: [] for name in (*SUPPLEMENTAL_STRATA, PRIMARY_STRATUM)}
    for entry, assignment in zip(flexible, assignments, strict=True):
        if assignment != "unselected":
            selected[assignment].append(entry.task_id)
    projection = {
        name: selected[name]
        for name in (*SUPPLEMENTAL_STRATA, PRIMARY_STRATUM)
    }
    return {
        "case_id": case_id,
        "feasible": True,
        "minimum_supplemental_tasks": dict(minimum),
        "exact_supplemental_tasks": dict(exact) if exact is not None else None,
        "objective": {
            "primary_mirror_tasks": counts[2],
            "supplemental_tasks": counts[0] + counts[1],
        },
        "selected_tasks": {
            "both_clean": counts[0],
            "both_faulty": counts[1],
            "mirror": counts[2],
        },
        "assignment_sha256": content_sha256(projection),
        "tie_break_signature_sha256": content_sha256(list(tie_signature)),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    verified_execution = _verified_execution_boundary()
    clean = verify_completed_clean_run_archive(
        bundle_root=args.bundle_root,
        run_root=args.clean_run_root,
        candidates=load_pinned_task_universe(),
    )
    freeze = verify_mutation_freeze(args.freeze_root, archive=clean)
    qualification = verify_completed_machine_qualification_archive(
        freeze=freeze,
        run_root=args.qualification_run_root,
    )
    witness_plan = verify_withheld_plus_witness_plan(
        args.witness_plan_root,
        freeze=freeze,
        qualification=qualification,
    )
    witness = verify_completed_withheld_plus_witness_archive(
        plan=witness_plan,
        run_root=args.witness_run_root,
    )
    review_plan = verify_final_program_review_plan(
        args.review_plan_root,
        bundle_root=args.program_review_root,
        freeze=freeze,
        qualification=qualification,
        witness=witness,
    )
    independent = verify_completed_independent_test_archive(
        plan=review_plan,
        run_root=args.independent_run_root,
    )
    promotion = promote_verified_programs(
        freeze=freeze,
        qualification=qualification,
        witness=witness,
        review_plan=review_plan,
        independent=independent,
    )
    config = load_selection_config(args.selection_config)
    challenge_pool = load_challenge_pool(args.challenge_pool)
    order, _ = _locked_order(clean)
    dev_ids = [str(row["task_id"]) for row in _dev_excluded(clean)["items"]]
    challenge_ids = tuple(str(row["task_id"]) for row in challenge_pool)
    options = derive_program_options(
        clean_archive=clean,
        freeze=freeze,
        promotion=promotion,
    )
    eligibility = derive_eligibility(
        order,
        dev_task_ids=dev_ids,
        challenge_seed_ids=challenge_ids,
        options=options,
    )
    historical_targets = derive_evidence_constrained_pilot_targets(order, eligibility)
    historical_selection, _ = _derive_stratum_selection(
        order,
        eligibility,
        historical_targets,
    )
    predecessor_path = Path(args.predecessor_receipt).resolve(strict=True)
    predecessor = _strict_json(predecessor_path)
    historical_counts = {
        name: len(historical_selection[name]) for name in STRATUM_ORDER
    }
    expected_predecessor_counts = {
        name: int(predecessor["pilot_allocation"][name]) for name in STRATUM_ORDER
    }
    if historical_counts != expected_predecessor_counts:
        raise ValueError("replayed historical selection differs from predecessor receipt")

    fixed = {
        "development": len(historical_selection["dev"]),
        "challenge": len(historical_selection["challenge"]),
    }
    cases = [
        _solve(
            case_id="no_supplemental_constraints",
            order=order,
            eligibility=eligibility,
            seed=str(config["selection_seed_material"]),
            minimum={"both_clean": 0, "both_faulty": 0},
        ),
        _solve(
            case_id="one_per_supplemental_stratum",
            order=order,
            eligibility=eligibility,
            seed=str(config["selection_seed_material"]),
            minimum={"both_clean": 1, "both_faulty": 1},
        ),
        _solve(
            case_id="historical_pilot_locked_supplemental_quotas",
            order=order,
            eligibility=eligibility,
            seed=str(config["selection_seed_material"]),
            minimum={
                "both_clean": int(historical_targets.both_clean),
                "both_faulty": int(historical_targets.both_faulty),
            },
            exact={
                "both_clean": int(historical_targets.both_clean),
                "both_faulty": int(historical_targets.both_faulty),
            },
        ),
    ]
    for case in cases:
        if case["feasible"]:
            counts = case["selected_tasks"]
            objective = case.pop("objective")
            case["fixed_selected_quotas"] = fixed
            case["primary_mirror_tasks"] = objective["primary_mirror_tasks"]
            case["supplemental_tasks"] = objective["supplemental_tasks"]
            case["potential_main_items"] = (
                fixed["challenge"]
                + counts["both_clean"]
                + counts["both_faulty"]
                + 2 * counts["mirror"]
            )
            case["potential_main_model_invocations"] = (
                case["potential_main_items"]
                * int(config["protocol_manifest"]["model_calls_per_item"])
            )

    target_quota = _solve(
        case_id="diagnostic_preregistered_target_supplemental_quotas",
        order=order,
        eligibility=eligibility,
        seed=str(config["selection_seed_material"]),
        minimum={"both_clean": 10, "both_faulty": 10},
        exact={"both_clean": 10, "both_faulty": 10},
    )
    minimum_quota = _solve(
        case_id="diagnostic_preregistered_minimum_supplemental_quotas",
        order=order,
        eligibility=eligibility,
        seed=str(config["selection_seed_material"]),
        minimum={"both_clean": 8, "both_faulty": 8},
        exact={"both_clean": 8, "both_faulty": 8},
    )
    historical_primary_maximal = (
        historical_counts["mirror"] == cases[2]["selected_tasks"]["mirror"]
    )

    raw_option_counts = {
        "both_clean": sum(record.both_clean is not None for record in options),
        "both_faulty": sum(record.both_faulty is not None for record in options),
        "mirror": sum(record.mirror is not None for record in options),
    }
    eligible_counts = {
        name: sum(name in record.eligible_strata for record in eligibility)
        for name in (*SUPPLEMENTAL_STRATA, PRIMARY_STRATUM)
    }
    predecessor_content_sha256 = content_sha256(predecessor)
    if len(predecessor_content_sha256) != 64:
        raise ValueError("predecessor content hash is not one SHA-256 digest")
    payload: dict[str, Any] = {
        "schema": "masgain-v2-selection-lexicographic-audit/v1",
        "audit_id": "c3-primary-unit-first-selection-audit-2026-07-19",
        "recorded_date": args.recorded_date,
        "purpose": (
            "Successor audit of the historical evidence-constrained pilot selector. "
            "The historical receipt and executed selection are preserved and are not "
            "overwritten."
        ),
        "predecessor": {
            "repository_path": "run-records/DEVIATIONS/2026-07-18-c3-evidence-constrained-pilot.json",
            "file_sha256": _file_sha256(predecessor_path),
            "content_sha256": predecessor_content_sha256,
        },
        "verified_lineage": {
            "clean_archive_sha256": clean.archive_sha256,
            "freeze_id": freeze.freeze_id,
            "promotion_sha256": promotion.promotion_sha256,
            "config_sha256": content_sha256(config),
            "challenge_pool_sha256": content_sha256(
                {"schema": "masgain-v2-challenge-pool/v1", "records": list(challenge_pool)}
            ),
            "locked_order_sha256": content_sha256(
                [
                    {
                        "position": entry.position,
                        "task_id": entry.task_id,
                        "task_sha256": entry.task_sha256,
                        "rank_sha256": entry.rank_sha256,
                    }
                    for entry in order
                ]
            ),
        },
        "verified_evidence": {
            "qualified_clean_programs": len(promotion.clean),
            "qualified_fault_programs": len(promotion.fault),
            "raw_program_option_task_counts": raw_option_counts,
            "eligible_task_counts_after_identity_reservations": eligible_counts,
            "identity_reservations": {
                "development": len(dev_ids),
                "challenge": len(challenge_ids),
            },
            "fixed_selected_quotas_in_all_requested_cases": fixed,
        },
        "method": {
            "primary_unit": "mirror_task",
            "supplemental_strata": list(SUPPLEMENTAL_STRATA),
            "task_disjointness": True,
            "reservation_policy_applies_to_all_requested_cases": True,
            "objective_order": [
                "maximize_primary_mirror_tasks",
                "satisfy_case_specific_minimum_supplemental_strata",
                "maximize_supplemental_tasks",
                "deterministic_sha256_choice_rank",
            ],
            "solver": "exhaustive_dynamic_programming_over_verified_task_eligibility",
            "tie_break": (
                "Lexicographically minimize per-task SHA-256 choice ranks in the locked "
                "task order using the private selection seed, case identity, task identity, "
                "and assigned stratum. The receipt discloses none of those private values."
            ),
            "no_supplemental_constraint_semantics": (
                "Both supplemental lower bounds are zero. Supplemental tasks remain "
                "optional and are maximized only after the number of primary mirror tasks "
                "is fixed at its maximum."
            ),
            "historical_locked_quota_semantics": (
                "The historical locked quotas in the third requested case are exactly 26 "
                "both-clean tasks and one both-faulty task from the preserved pilot receipt. "
                "They are not the infeasible preregistered target quotas."
            ),
            "audit_tool_repository_path": "tools/selection_lexicographic_audit.py",
            "audit_tool_file_sha256": _file_sha256(Path(__file__)),
        },
        "historical_replay": {
            "selector_objective": (
                "maximize_total_main_items_then_mirror_tasks_under_sequential_reservation"
            ),
            "selected_tasks": {
                "development": historical_counts["dev"],
                "challenge": historical_counts["challenge"],
                "both_clean": historical_counts["both_clean"],
                "both_faulty": historical_counts["both_faulty"],
                "mirror": historical_counts["mirror"],
            },
            "main_items": historical_targets.main_items,
            "primary_mirror_tasks": historical_targets.mirror,
            "reproduced_predecessor_counts": True,
        },
        "requested_cases": cases,
        "locked_protocol_quota_diagnostics": {
            "scope": (
                "Supplemental quotas only. Challenge and development identities remain "
                "reserved, so their selected quota does not change the mirror ceiling."
            ),
            "preregistered_target": {
                "exact_supplemental_tasks": target_quota["exact_supplemental_tasks"],
                "feasible": target_quota["feasible"],
                "reason": "Only nine both-faulty-capable tasks exist after qualification.",
            },
            "preregistered_minimum": {
                "exact_supplemental_tasks": minimum_quota["exact_supplemental_tasks"],
                "feasible": minimum_quota["feasible"],
                "maximum_primary_mirror_tasks": minimum_quota["objective"][
                    "primary_mirror_tasks"
                ],
                "assignment_sha256": minimum_quota["assignment_sha256"],
                "tie_break_signature_sha256": minimum_quota[
                    "tie_break_signature_sha256"
                ],
            },
        },
        "finding": {
            "historical_eight_truly_maximal_under_primary_unit_first_objective": (
                historical_primary_maximal
            ),
            "maximum_without_supplemental_constraints": cases[0]["selected_tasks"]["mirror"],
            "maximum_with_one_per_supplemental_stratum": cases[1]["selected_tasks"]["mirror"],
            "maximum_with_historical_pilot_supplemental_quotas": cases[2]["selected_tasks"]["mirror"],
            "interpretation": (
                "Eight was the executed historical selection under the total-item-first "
                "sequential selector. It was not the maximum number of pre-gold primary "
                "mirror candidates supported by the verified pool."
            ),
        },
        "limitations": [
            (
                "All three allocations are counterfactual re-audits of pre-gold "
                "eligibility. They do not replace the historical selection."
            ),
            (
                "The mirror counts are upper bounds before final adjudication. Final gold "
                "could only decrease the number of primary estimand units."
            ),
            (
                "No counterfactual allocation was exported and no main comparison call "
                "was entered."
            ),
        ],
        "execution_boundary": {
            "canonical_private_lineage_reverified": True,
            "proxy_variables_removed": verified_execution[
                "proxy_variables_removed"
            ],
            "setsid_used": verified_execution["setsid_used"],
            "runner_fast_used": False,
            "model_calls_performed": 0,
            "human_gold_records_read": 0,
            "main_outputs_read": 0,
            "command_shape": (
                "env without HTTP proxy variables, then setsid python3 "
                "tools/selection_lexicographic_audit.py with verified private roots"
            ),
        },
    }
    payload["receipt_sha256"] = content_sha256(payload)
    print(canonical_json(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
