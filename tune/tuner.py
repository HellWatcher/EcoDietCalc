"""EcoDietCalculator Knob Tuner.

This module performs random-search tuning of planner "knobs" while
minimally touching the rest of the project. It overrides values in
`constants` at runtime and reloads dependent modules so the planner
sees the changes.

Primary objective
-----------------
Maximize the final SP after planning.

Secondary metrics (for tie-breaking)
------------------------------------
1) Delta SP normalized by budget (ΔSP per 100 kcal).
2) Count of foods that cross the hard variety threshold.

Notes
-----
- Cravings and taste are ignored here.
- Multiple budgets are evaluated per trial to avoid skewing variety.
"""

from __future__ import annotations

import argparse
import builtins
import csv
import importlib
import json
import random
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Iterable, List, Tuple

# Ensure the project root (parent of `tune/`) is importable BEFORE any project imports.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

#: Default output directory for tuner artifacts (keep results inside `tune/`).
DEFAULT_OUTPUT_DIR: Path = Path(__file__).resolve().parent


# -- robust persistence import (supports both layouts) -----------------------
def _import_persistence() -> ModuleType:
    """Import the project's persistence module.

    Tries, in order:
    1) top-level ``persistence``
    2) ``interface.persistence``

    Returns
    -------
    types.ModuleType
        The imported persistence module.

    Raises
    ------
    ModuleNotFoundError
        If neither path can be imported.
    """
    try:
        import persistence as _persistence  # type: ignore

        return _persistence
    except ModuleNotFoundError:
        pass
    try:
        from interface import persistence as _persistence  # type: ignore

        return _persistence
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Could not import 'persistence' (tried 'persistence' and 'interface.persistence')."
        ) from exc


# Bind once so it's available at runtime.
persistence = _import_persistence()

# -----------------------
# Tunable default ranges
# -----------------------

#: Default calorie budgets evaluated for each trial.
DEFAULT_BUDGETS: Tuple[int, ...] = (5000, 10000, 20000, 40000)

#: Ranges for random sampling of each knob (low, high).
RANGE_SOFT_VARIETY_BIAS_STRENGTH: Tuple[float, float] = (0.0, 6.0)
RANGE_PROXIMITY_APPROACH_WEIGHT: Tuple[float, float] = (0.0, 1.0)
RANGE_PROXIMITY_OVERSHOOT_PENALTY: Tuple[float, float] = (0.0, 0.2)
RANGE_TIEBREAK_SCORE_WINDOW_SP: Tuple[float, float] = (0.1, 1.0)
RANGE_LOW_CALORIE_THRESHOLD: Tuple[float, float] = (200.0, 500.0)
RANGE_LOW_CALORIE_PENALTY_STRENGTH: Tuple[float, float] = (0.0, 4.0)
RANGE_BALANCE_IMPROVEMENT_STRENGTH: Tuple[float, float] = (0.0, 3.0)
RANGE_REPETITION_PENALTY_STRENGTH: Tuple[float, float] = (0.0, 2.0)

#: Hill climbing defaults
HILL_CLIMB_MAX_ITERATIONS: int = 20
HILL_CLIMB_FACTORS: Tuple[float, ...] = (0.9, 0.95, 1.05, 1.1)


@contextmanager
def override_constants(
    **overrides,
):
    """
    Temporarily set attributes on the `constants` module, then restore.

    IMPORTANT: Anything that did `from constants import X` will not see new
    values unless the consumer module is reloaded. The tuner handles this by
    reloading `planner` and `calculations` after applying overrides.
    """
    import constants

    old_vals = {}
    missing = object()
    try:
        for k, v in overrides.items():
            old_vals[k] = getattr(
                constants,
                k,
                missing,
            )
            setattr(
                constants,
                k,
                v,
            )
        yield
    finally:
        for k, old in old_vals.items():
            if old is missing:
                delattr(
                    constants,
                    k,
                )
            else:
                setattr(
                    constants,
                    k,
                    old,
                )


@contextmanager
def suppress_interactive_prompts(
    persistence_module,
):
    """Temporarily silence tastiness prompts and their warning line.

    During tuner runs we (a) auto-answer “no” to the
    "Would you like to rate them now?" question and (b) filter the single
    warning print about unknown tastiness so it doesn’t spam the console.
    """
    sentinel = object()
    old_yes_no = getattr(
        persistence_module,
        "prompt_yes_no",
        sentinel,
    )
    # Module-level print used inside persistence; default to builtins.print
    had_print_attr = hasattr(
        persistence_module,
        "print",
    )
    original_print = getattr(
        persistence_module,
        "print",
        builtins.print,
    )

    def _always_no(
        *_args,
        **_kwargs,
    ):
        return False

    def _filtered_print(
        *args,
        **kwargs,
    ):
        # Swallow only the unknown-tastiness warning; pass everything else through.
        try:
            text = " ".join(str(a) for a in args)
        except Exception:
            text = None
        if text and "available foods have unknown tastiness" in text:
            return
        return original_print(
            *args,
            **kwargs,
        )

    try:
        if old_yes_no is not sentinel:
            setattr(
                persistence_module,
                "prompt_yes_no",
                _always_no,
            )
        setattr(
            persistence_module,
            "print",
            _filtered_print,
        )
        yield
    finally:
        if old_yes_no is not sentinel:
            setattr(
                persistence_module,
                "prompt_yes_no",
                old_yes_no,
            )
        # Restore module print binding to its previous state
        if had_print_attr:
            setattr(
                persistence_module,
                "print",
                original_print,
            )
        else:
            try:
                delattr(
                    persistence_module,
                    "print",
                )
            except Exception:
                setattr(
                    persistence_module,
                    "print",
                    original_print,
                )


def reload_deps():
    """Reload modules that *consume* constants (not constants itself).

    Returns
    -------
    tuple
        (constants, calculations, planner)
    """
    import calculations as calculations
    import constants as constants
    import planner as planner

    # DO NOT reload `constants` here; overrides are set in-memory.
    importlib.reload(calculations)
    importlib.reload(planner)
    return constants, calculations, planner


def count_hard_variety(
    stomach: Dict[Any, int],
    variety_cal_threshold: int,
) -> int:
    """
    Count foods whose (calories * quantity) >= VARIETY_CAL_THRESHOLD.
    We do not import a helper to keep coupling minimal.
    """
    c = 0
    for food_obj, qty in stomach.items():
        try:
            cals = getattr(
                food_obj,
                "calories",
            )
        except Exception:
            continue
        if cals * int(qty) >= variety_cal_threshold:
            c += 1
    return c


def safe_name_knobs(
    theta: Dict[str, float],
) -> Dict[str, float]:
    """Return a clean mapping for CSV/JSON dump with stable key order."""
    keys = [
        "SOFT_VARIETY_BIAS_STRENGTH",
        "PROXIMITY_APPROACH_WEIGHT",
        "PROXIMITY_OVERSHOOT_PENALTY",
        "TIEBREAK_SCORE_WINDOW_SP",
        "LOW_CALORIE_THRESHOLD",
        "LOW_CALORIE_PENALTY_STRENGTH",
        "BALANCE_IMPROVEMENT_STRENGTH",
        "REPETITION_PENALTY_STRENGTH",
    ]
    return {k: float(theta[k]) for k in keys if k in theta}


# -------- search space --------


def parse_range(
    arg: str,
    default: Tuple[float, float],
) -> Tuple[float, float]:
    if not arg:
        return default
    parts = [p.strip() for p in arg.split(",")]
    if len(parts) != 2:
        raise ValueError(f"Range must be 'lo,hi' (got: {arg})")
    lo, hi = float(parts[0]), float(parts[1])
    if hi < lo:
        lo, hi = hi, lo
    return lo, hi


def sample_theta(
    rng: random.Random,
    ranges: Dict[str, Tuple[float, float]],
):
    """Sample a theta dict within given ranges. LOW_CALORIE_THRESHOLD is rounded to int."""

    def samp(
        name,
    ):
        lo, hi = ranges[name]
        return rng.uniform(
            lo,
            hi,
        )

    return {
        "SOFT_VARIETY_BIAS_STRENGTH": samp("SOFT_VARIETY_BIAS_STRENGTH"),
        "PROXIMITY_APPROACH_WEIGHT": samp("PROXIMITY_APPROACH_WEIGHT"),
        "PROXIMITY_OVERSHOOT_PENALTY": samp("PROXIMITY_OVERSHOOT_PENALTY"),
        "TIEBREAK_SCORE_WINDOW_SP": samp("TIEBREAK_SCORE_WINDOW_SP"),
        "LOW_CALORIE_THRESHOLD": int(round(samp("LOW_CALORIE_THRESHOLD"))),
        "LOW_CALORIE_PENALTY_STRENGTH": samp("LOW_CALORIE_PENALTY_STRENGTH"),
        "BALANCE_IMPROVEMENT_STRENGTH": samp("BALANCE_IMPROVEMENT_STRENGTH"),
        "REPETITION_PENALTY_STRENGTH": samp("REPETITION_PENALTY_STRENGTH"),
    }


# -------- evaluation --------


def evaluate_theta(
    theta: Dict[str, float],
    budgets: Iterable[int],
    seed: int,
) -> Dict[str, Any]:
    """Evaluate one knob set across multiple calorie budgets.

    Parameters
    ----------
    theta
        Mapping of knob names to values. Expected keys:
        'SOFT_VARIETY_BIAS_STRENGTH', 'PROXIMITY_APPROACH_WEIGHT',
        'PROXIMITY_OVERSHOOT_PENALTY', 'TIEBREAK_SCORE_WINDOW_SP',
        'LOW_CALORIE_THRESHOLD', 'LOW_CALORIE_PENALTY_STRENGTH'.
    budgets
        Calorie budgets to evaluate (e.g., 900, 1200, 1500).
    seed
        Random seed used to make the evaluation deterministic.

    Returns
    -------
    dict
        Metrics summary with:
        - 'theta': sanitized knob mapping
        - 'avg_final_sp': float
        - 'avg_delta_sp_per_100kcal': float
        - 'avg_variety_count': float
        - 'per_budget': list of per-budget metric dicts
    """

    # Deterministic per-theta seed; kept for potential future stochastic logic.
    (
        seed
        + int(theta["LOW_CALORIE_THRESHOLD"])
        + int(theta["SOFT_VARIETY_BIAS_STRENGTH"] * 1_000.0)
    )

    per_budget: List[Dict[str, Any]] = []

    for budget in budgets:
        # Build a fresh manager; planner mutates state during planning.

        # Build a fresh manager; planner mutates state during planning.
        # Suppress interactive tastiness rating prompts during tuner runs.
        with suppress_interactive_prompts(persistence):
            manager = persistence.load_food_state(
                reset_stomach=False,
                reset_tastiness=False,
            )

        initial_sp: float = manager.get_current_sp(
            cravings=[],
            cravings_satisfied=0,
        )

        # Apply overrides and reload the dependent modules so they read the new values.
        with override_constants(**theta):
            constants, calculations, planner = reload_deps()

            # Guard against invalid budgets.
            budget_int: int = max(1, int(budget))

            # Run the planner. Support both kw/positional signatures.
            try:
                planner.plan_meal(
                    manager=manager,
                    cravings=[],
                    cravings_satisfied=0,
                    remaining_calories=budget_int,
                )
            except TypeError:
                planner.plan_meal(
                    manager,
                    [],
                    0,
                    budget_int,
                )

            final_sp: float = manager.get_current_sp(
                cravings=[],
                cravings_satisfied=0,
            )
            delta_sp: float = final_sp - initial_sp
            delta_sp_per_100kcal: float = (delta_sp / float(budget_int)) * 100.0

            variety_threshold: int = getattr(
                constants,
                "VARIETY_CAL_THRESHOLD",
                2_000,
            )
            variety_count: int = count_hard_variety(
                manager.stomach,
                variety_threshold,
            )

            # Calculate balance ratio (min/max nutrient density)
            balance_ratio: float = calculations.get_balance_ratio(manager.stomach)

        per_budget.append(
            {
                "budget": budget_int,
                "final_sp": float(final_sp),
                "delta_sp_per_100kcal": float(delta_sp_per_100kcal),
                "variety_count": int(variety_count),
                "balance_ratio": float(balance_ratio),
            },
        )

    n: int = len(per_budget)
    avg_final_sp: float = sum(x["final_sp"] for x in per_budget) / n
    avg_delta_sp_per_100kcal: float = (
        sum(x["delta_sp_per_100kcal"] for x in per_budget) / n
    )
    avg_variety_count: float = sum(x["variety_count"] for x in per_budget) / n
    avg_balance_ratio: float = sum(x["balance_ratio"] for x in per_budget) / n

    return {
        "theta": safe_name_knobs(theta),
        "avg_final_sp": float(avg_final_sp),
        "avg_delta_sp_per_100kcal": float(avg_delta_sp_per_100kcal),
        "avg_variety_count": float(avg_variety_count),
        "avg_balance_ratio": float(avg_balance_ratio),
        "per_budget": per_budget,
    }


def score_metrics(
    m: Dict[str, Any],
) -> Tuple[float, float, float, float]:
    """
    Lexicographic score tuple:
      1) avg_final_sp
      2) avg_delta_sp_per_100kcal
      3) avg_variety_count
      4) avg_balance_ratio
    Higher is better for all four.
    """
    return (
        m["avg_final_sp"],
        m["avg_delta_sp_per_100kcal"],
        m["avg_variety_count"],
        m.get("avg_balance_ratio", 0.0),
    )


def is_dominated_by(
    a: Dict[str, Any],
    b: Dict[str, Any],
) -> bool:
    """Check if result `a` is dominated by result `b`.

    Dominated means: b is >= in ALL metrics and > in at least one.
    """
    dominated_sp = b["avg_final_sp"] >= a["avg_final_sp"]
    dominated_efficiency = (
        b["avg_delta_sp_per_100kcal"] >= a["avg_delta_sp_per_100kcal"]
    )
    dominated_variety = b["avg_variety_count"] >= a["avg_variety_count"]
    dominated_balance = b.get("avg_balance_ratio", 0) >= a.get("avg_balance_ratio", 0)

    all_geq = (
        dominated_sp
        and dominated_efficiency
        and dominated_variety
        and dominated_balance
    )

    any_strictly_better = (
        b["avg_final_sp"] > a["avg_final_sp"]
        or b["avg_delta_sp_per_100kcal"] > a["avg_delta_sp_per_100kcal"]
        or b["avg_variety_count"] > a["avg_variety_count"]
        or b.get("avg_balance_ratio", 0) > a.get("avg_balance_ratio", 0)
    )

    return all_geq and any_strictly_better


def pareto_frontier(
    results: List[Dict[str, Any]],
) -> List[int]:
    """Extract Pareto-optimal (non-dominated) result indices.

    Returns indices of results that are not dominated by any other result.
    """
    return [
        idx
        for idx, candidate in enumerate(results)
        if not any(is_dominated_by(candidate, other) for other in results)
    ]


def select_balanced(
    results: List[Dict[str, Any]],
    pareto_indices: List[int],
) -> int | None:
    """Select the most "balanced" result from Pareto frontier.

    Uses normalized Euclidean distance to the ideal point (max of each metric).
    """
    if not pareto_indices:
        return None

    frontier = [results[i] for i in pareto_indices]

    # Find min/max for normalization
    sps = [r["avg_final_sp"] for r in frontier]
    vars_ = [r["avg_variety_count"] for r in frontier]
    bals = [r.get("avg_balance_ratio", 0) for r in frontier]
    effs = [r["avg_delta_sp_per_100kcal"] for r in frontier]

    min_sp, max_sp = min(sps), max(sps)
    min_var, max_var = min(vars_), max(vars_)
    min_bal, max_bal = min(bals), max(bals)
    min_eff, max_eff = min(effs), max(effs)

    def normalize(val: float, lo: float, hi: float) -> float:
        if abs(hi - lo) < 1e-10:
            return 1.0
        return (val - lo) / (hi - lo)

    best_idx = pareto_indices[0]
    best_distance = float("inf")

    for idx in pareto_indices:
        r = results[idx]
        norm_sp = normalize(r["avg_final_sp"], min_sp, max_sp)
        norm_var = normalize(r["avg_variety_count"], min_var, max_var)
        norm_bal = normalize(r.get("avg_balance_ratio", 0), min_bal, max_bal)
        norm_eff = normalize(r["avg_delta_sp_per_100kcal"], min_eff, max_eff)

        # Euclidean distance to ideal (1, 1, 1, 1)
        distance = (
            (1.0 - norm_sp) ** 2
            + (1.0 - norm_var) ** 2
            + (1.0 - norm_bal) ** 2
            + (1.0 - norm_eff) ** 2
        ) ** 0.5

        if distance < best_distance:
            best_distance = distance
            best_idx = idx

    return best_idx


def perturb_theta(
    theta: Dict[str, float],
    knob_name: str,
    factor: float,
    ranges: Dict[str, Tuple[float, float]],
) -> Dict[str, float]:
    """Perturb a single knob by a factor, clamped to its range."""
    new_theta = dict(theta)
    lo, hi = ranges.get(knob_name, (0, 1e9))
    new_val = theta[knob_name] * factor
    new_val = max(lo, min(hi, new_val))
    if knob_name == "LOW_CALORIE_THRESHOLD":
        new_val = int(round(new_val))
    new_theta[knob_name] = new_val
    return new_theta


def hill_climb(
    initial: Dict[str, Any],
    budgets: List[int],
    seed: int,
    ranges: Dict[str, Tuple[float, float]],
    *,
    max_iterations: int = HILL_CLIMB_MAX_ITERATIONS,
    factors: Tuple[float, ...] = HILL_CLIMB_FACTORS,
) -> Dict[str, Any]:
    """Refine a result using hill climbing.

    Tries small perturbations to each knob, keeping changes that improve.
    """
    best = initial
    knob_names = list(initial["theta"].keys())

    for _ in range(max_iterations):
        improved = False

        for knob_name in knob_names:
            for factor in factors:
                candidate_theta = perturb_theta(
                    best["theta"], knob_name, factor, ranges
                )

                # Skip if unchanged
                if candidate_theta == best["theta"]:
                    continue

                candidate = evaluate_theta(candidate_theta, budgets, seed)

                # Accept if candidate dominates current best
                if is_dominated_by(best, candidate):
                    best = candidate
                    improved = True
                    break

        if not improved:
            break

    return best


# -------- main loop --------


def main():
    ap = argparse.ArgumentParser(
        description="Random-search tuner for planner knobs (minimal-touch)."
    )
    ap.add_argument(
        "--iters",
        type=int,
        default=300,
        help="Number of random samples to try (default: 300)",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=123,
        help="Random seed (default: 123)",
    )
    ap.add_argument(
        "--budgets",
        type=str,
        default=",".join(str(x) for x in DEFAULT_BUDGETS),
        help=(
            f"Comma-separated calorie budgets to evaluate (default: {','.join(str(x) for x in DEFAULT_BUDGETS)})"
        ),
    )
    # Search space overrides
    ap.add_argument(
        "--soft",
        type=str,
        default="",
        help="Range for SOFT_VARIETY_BIAS_STRENGTH, e.g. '0,6' (default 0,6)",
    )
    ap.add_argument(
        "--proximity-approach",
        type=str,
        default="",
        help="Range for PROXIMITY_APPROACH_WEIGHT, e.g. '0,1' (default 0,1)",
    )
    ap.add_argument(
        "--proximity-overshoot",
        type=str,
        default="",
        help="Range for PROXIMITY_OVERSHOOT_PENALTY, e.g. '0,0.2' (default 0,0.2)",
    )
    ap.add_argument(
        "--tiebreak-window",
        type=str,
        default="",
        help="Range for TIEBREAK_SCORE_WINDOW_SP, e.g. '0.1,1.0' (default 0.1,1.0)",
    )
    ap.add_argument(
        "--low-cal-threshold",
        type=str,
        default="",
        help="Range for LOW_CALORIE_THRESHOLD, e.g. '200,500' (default 200,500)",
    )
    ap.add_argument(
        "--low-cal-penalty",
        type=str,
        default="",
        help="Range for LOW_CALORIE_PENALTY_STRENGTH, e.g. '0,4' (default 0,4)",
    )
    ap.add_argument(
        "--balance-strength",
        type=str,
        default="",
        help="Range for BALANCE_IMPROVEMENT_STRENGTH, e.g. '0,3' (default 0,3)",
    )
    ap.add_argument(
        "--rep-strength",
        type=str,
        default="",
        help="Range for REPETITION_PENALTY_STRENGTH, e.g. '0,2' (default 0,2)",
    )
    ap.add_argument(
        "--no-hill-climb",
        action="store_true",
        help="Disable hill climbing refinement",
    )

    ap.add_argument(
        "--csv",
        type=str,
        default=str((DEFAULT_OUTPUT_DIR / "tuner_results.csv")),
        help="Output CSV path (default: tune/tuner_results.csv)",
    )
    ap.add_argument(
        "--json",
        type=str,
        default="tuner_best.json",
        help="Output JSON path for best result (default: tuner_best.json)",
    )
    ap.add_argument(
        "--topk",
        type=int,
        default=10,
        help="How many top rows to print (default: 10)",
    )

    args = ap.parse_args()

    # Parse budgets string into a concrete list of ints.
    budgets: list[int] = [int(b.strip()) for b in args.budgets.split(",") if b.strip()]
    if not budgets:
        raise SystemExit("No budgets provided.")

    # Default ranges
    ranges = {
        "SOFT_VARIETY_BIAS_STRENGTH": parse_range(
            args.soft, RANGE_SOFT_VARIETY_BIAS_STRENGTH
        ),
        "PROXIMITY_APPROACH_WEIGHT": parse_range(
            args.proximity_approach, RANGE_PROXIMITY_APPROACH_WEIGHT
        ),
        "PROXIMITY_OVERSHOOT_PENALTY": parse_range(
            args.proximity_overshoot, RANGE_PROXIMITY_OVERSHOOT_PENALTY
        ),
        "TIEBREAK_SCORE_WINDOW_SP": parse_range(
            args.tiebreak_window, RANGE_TIEBREAK_SCORE_WINDOW_SP
        ),
        "LOW_CALORIE_THRESHOLD": parse_range(
            args.low_cal_threshold, RANGE_LOW_CALORIE_THRESHOLD
        ),
        "LOW_CALORIE_PENALTY_STRENGTH": parse_range(
            args.low_cal_penalty, RANGE_LOW_CALORIE_PENALTY_STRENGTH
        ),
        "BALANCE_IMPROVEMENT_STRENGTH": parse_range(
            args.balance_strength, RANGE_BALANCE_IMPROVEMENT_STRENGTH
        ),
        "REPETITION_PENALTY_STRENGTH": parse_range(
            args.rep_strength, RANGE_REPETITION_PENALTY_STRENGTH
        ),
    }

    rng = random.Random(
        args.seed,
    )
    rows = []
    best = None  # tuple(score, metrics)

    for i in range(1, args.iters + 1):
        theta = sample_theta(
            rng,
            ranges,
        )
        metrics = evaluate_theta(
            theta,
            budgets,
            seed=args.seed,
        )
        score = score_metrics(
            metrics,
        )

        rows.append(metrics)

        if (best is None) or (score > best[0]):
            best = (score, metrics)

        # Progress indicator every 10%
        if i % max(1, args.iters // 10) == 0:
            pct = (i / args.iters) * 100
            print(f"\r{pct:.0f}% complete", end="", flush=True)

    print()  # Newline after progress

    # Compute Pareto frontier
    pareto_indices = pareto_frontier(rows)
    print(f"\nPareto frontier: {len(pareto_indices)} non-dominated solutions")

    # Hill climbing refinement
    if not args.no_hill_climb and pareto_indices:
        print(
            f"Refining {len(pareto_indices)} Pareto-optimal results with hill climbing..."
        )
        refined_count = 0
        for idx in pareto_indices.copy():
            original = rows[idx]
            refined = hill_climb(original, budgets, args.seed, ranges)

            # Check if refinement improved
            if is_dominated_by(original, refined):
                refined_count += 1
                rows.append(refined)

        if refined_count > 0:
            print(f"  {refined_count} results improved by hill climbing")
            # Recompute Pareto frontier with refined results
            pareto_indices = pareto_frontier(rows)
            print(
                f"  Updated Pareto frontier: {len(pareto_indices)} non-dominated solutions"
            )
        else:
            print("  No improvements found (already at local optima)")

    # Select balanced pick from Pareto frontier
    balanced_idx = select_balanced(rows, pareto_indices)
    if balanced_idx is not None:
        balanced = rows[balanced_idx]
        print(
            f"Balanced pick: SP={balanced['avg_final_sp']:.2f} "
            f"variety={balanced['avg_variety_count']:.1f} "
            f"balance={balanced.get('avg_balance_ratio', 0):.3f}"
        )

    # Resolve output paths and ensure directories exist
    csv_path = Path(args.csv)
    json_path = Path(args.json)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV (flatten rows for CSV output)
    fieldnames = [
        "SOFT_VARIETY_BIAS_STRENGTH",
        "PROXIMITY_APPROACH_WEIGHT",
        "PROXIMITY_OVERSHOOT_PENALTY",
        "TIEBREAK_SCORE_WINDOW_SP",
        "LOW_CALORIE_THRESHOLD",
        "LOW_CALORIE_PENALTY_STRENGTH",
        "BALANCE_IMPROVEMENT_STRENGTH",
        "REPETITION_PENALTY_STRENGTH",
        "avg_final_sp",
        "avg_delta_sp_per_100kcal",
        "avg_variety_count",
        "avg_balance_ratio",
        "per_budget",
    ]
    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        w.writeheader()
        for r in rows:
            flat = {
                **r["theta"],
                "avg_final_sp": r["avg_final_sp"],
                "avg_delta_sp_per_100kcal": r["avg_delta_sp_per_100kcal"],
                "avg_variety_count": r["avg_variety_count"],
                "avg_balance_ratio": r.get("avg_balance_ratio", 0),
                "per_budget": json.dumps(r["per_budget"]),
            }
            w.writerow(flat)

    # Write JSON for balanced (or best) pick
    best_result = (
        rows[balanced_idx]
        if balanced_idx is not None
        else (best[1] if best else rows[0])
    )
    best_payload = {
        "knobs": best_result["theta"],
        "metrics": {
            "avg_final_sp": best_result["avg_final_sp"],
            "avg_delta_sp_per_100kcal": best_result["avg_delta_sp_per_100kcal"],
            "avg_variety_count": best_result["avg_variety_count"],
            "avg_balance_ratio": best_result.get("avg_balance_ratio", 0),
        },
        "per_budget": best_result["per_budget"],
    }
    with open(
        json_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            best_payload,
            f,
            indent=2,
        )

    # Pretty print the top-k
    print("\nTop candidates (by score):")
    top = sorted(
        rows,
        key=lambda r: score_metrics(r),
        reverse=True,
    )[: args.topk]
    for j, r in enumerate(top, 1):
        t = r["theta"]
        print(
            f"{j:>2}. SP={r['avg_final_sp']:.2f} | var={r['avg_variety_count']:.1f} | "
            f"bal={r.get('avg_balance_ratio', 0):.3f} || "
            f"soft={t['SOFT_VARIETY_BIAS_STRENGTH']:.2f} low_cal={t['LOW_CALORIE_THRESHOLD']:.0f}"
        )

    print(f"\nBest saved to: {json_path}")
    print(f"All trials saved to: {csv_path}")


if __name__ == "__main__":
    main()
