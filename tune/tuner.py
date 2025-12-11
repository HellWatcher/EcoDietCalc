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
        raise ModuleNotFoundError("Could not import 'persistence' (tried 'persistence' and 'interface.persistence').") from exc


# Bind once so it's available at runtime.
persistence = _import_persistence()

# -----------------------
# Tunable default ranges
# -----------------------

#: Default calorie budgets evaluated for each trial.
DEFAULT_BUDGETS: Tuple[int, int, int] = (900, 1200, 1500)

#: Ranges for random sampling of each knob (low, high).
RANGE_SOFT_BIAS_GAMMA: Tuple[float, float] = (0.0, 6.0)
RANGE_TIE_ALPHA: Tuple[float, float] = (0.0, 1.0)
RANGE_TIE_BETA: Tuple[float, float] = (0.0, 0.2)
RANGE_TIE_EPSILON: Tuple[float, float] = (0.1, 1.0)
RANGE_CAL_FLOOR: Tuple[float, float] = (200.0, 500.0)
RANGE_CAL_PENALTY_GAMMA: Tuple[float, float] = (0.0, 4.0)


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
    keys = ["SOFT_BIAS_GAMMA", "TIE_ALPHA", "TIE_BETA", "TIE_EPSILON", "CAL_FLOOR", "CAL_PENALTY_GAMMA"]
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
    """Sample a theta dict within given ranges. CAL_FLOOR is rounded to int."""

    def samp(
        name,
    ):
        lo, hi = ranges[name]
        return rng.uniform(
            lo,
            hi,
        )

    return {
        "SOFT_BIAS_GAMMA": samp("SOFT_BIAS_GAMMA"),
        "TIE_ALPHA": samp("TIE_ALPHA"),
        "TIE_BETA": samp("TIE_BETA"),
        "TIE_EPSILON": samp("TIE_EPSILON"),
        "CAL_FLOOR": int(round(samp("CAL_FLOOR"))),
        "CAL_PENALTY_GAMMA": samp("CAL_PENALTY_GAMMA"),
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
        'SOFT_BIAS_GAMMA', 'TIE_ALPHA', 'TIE_BETA', 'TIE_EPSILON',
        'CAL_FLOOR', 'CAL_PENALTY_GAMMA'.
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
    (seed + int(theta["CAL_FLOOR"]) + int(theta["SOFT_BIAS_GAMMA"] * 1_000.0))

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

        per_budget.append(
            {
                "budget": budget_int,
                "final_sp": float(final_sp),
                "delta_sp_per_100kcal": float(delta_sp_per_100kcal),
                "variety_count": int(variety_count),
            },
        )

    n: int = len(per_budget)
    avg_final_sp: float = sum(x["final_sp"] for x in per_budget) / n
    avg_delta_sp_per_100kcal: float = sum(x["delta_sp_per_100kcal"] for x in per_budget) / n
    avg_variety_count: float = sum(x["variety_count"] for x in per_budget) / n

    return {
        "theta": safe_name_knobs(theta),
        "avg_final_sp": float(avg_final_sp),
        "avg_delta_sp_per_100kcal": float(avg_delta_sp_per_100kcal),
        "avg_variety_count": float(avg_variety_count),
        "per_budget": per_budget,
    }


def score_metrics(
    m: Dict[str, Any],
) -> Tuple[float, float, float]:
    """
    Lexicographic score tuple:
      1) avg_final_sp
      2) avg_delta_sp_per_100kcal
      3) avg_variety_count
    Higher is better for all three.
    """
    return (
        m["avg_final_sp"],
        m["avg_delta_sp_per_100kcal"],
        m["avg_variety_count"],
    )


# -------- main loop --------


def main():
    ap = argparse.ArgumentParser(description="Random-search tuner for planner knobs (minimal-touch).")
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
        help=(f"Comma-separated calorie budgets to evaluate (default: {','.join(str(x) for x in DEFAULT_BUDGETS)})"),
    )
    # Search space overrides
    ap.add_argument(
        "--soft",
        type=str,
        default="",
        help="Range for SOFT_BIAS_GAMMA, e.g. '0,6' (default 0,6)",
    )
    ap.add_argument(
        "--tie-alpha",
        type=str,
        default="",
        help="Range for TIE_ALPHA, e.g. '0,1' (default 0,1)",
    )
    ap.add_argument(
        "--tie-beta",
        type=str,
        default="",
        help="Range for TIE_BETA, e.g. '0,0.2' (default 0,0.2)",
    )
    ap.add_argument(
        "--tie-eps",
        type=str,
        default="",
        help="Range for TIE_EPSILON, e.g. '0.1,1.0' (default 0.1,1.0)",
    )
    ap.add_argument(
        "--cal-floor",
        type=str,
        default="",
        help="Range for CAL_FLOOR, e.g. '200,500' (default 200,500)",
    )
    ap.add_argument(
        "--cal-gamma",
        type=str,
        default="",
        help="Range for CAL_PENALTY_GAMMA, e.g. '0,4' (default 0,4)",
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
        "SOFT_BIAS_GAMMA": parse_range(args.soft, RANGE_SOFT_BIAS_GAMMA),
        "TIE_ALPHA": parse_range(args.tie_alpha, RANGE_TIE_ALPHA),
        "TIE_BETA": parse_range(args.tie_beta, RANGE_TIE_BETA),
        "TIE_EPSILON": parse_range(args.tie_eps, RANGE_TIE_EPSILON),
        "CAL_FLOOR": parse_range(args.cal_floor, RANGE_CAL_FLOOR),
        "CAL_PENALTY_GAMMA": parse_range(args.cal_gamma, RANGE_CAL_PENALTY_GAMMA),
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

        rows.append(
            {
                **metrics["theta"],
                "avg_final_sp": metrics["avg_final_sp"],
                "avg_delta_sp_per_100kcal": metrics["avg_delta_sp_per_100kcal"],
                "avg_variety_count": metrics["avg_variety_count"],
                "per_budget": json.dumps(metrics["per_budget"]),
            }
        )

        if (best is None) or (score > best[0]):
            best = (score, metrics)

        # Simple progress line
        print(
            f"[{i:>4}/{args.iters}] score={score!r} theta={metrics['theta']}",
            flush=True,
        )

    # Resolve output paths and ensure directories exist
    csv_path = Path(args.csv)
    json_path = Path(args.json)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV

    fieldnames = [
        "SOFT_BIAS_GAMMA",
        "TIE_ALPHA",
        "TIE_BETA",
        "TIE_EPSILON",
        "CAL_FLOOR",
        "CAL_PENALTY_GAMMA",
        "avg_final_sp",
        "avg_delta_sp_per_100kcal",
        "avg_variety_count",
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
            w.writerow(r)

    # Write JSON for best
    best_payload = {
        "theta": best[1]["theta"],
        "avg_final_sp": best[1]["avg_final_sp"],
        "avg_delta_sp_per_100kcal": best[1]["avg_delta_sp_per_100kcal"],
        "avg_variety_count": best[1]["avg_variety_count"],
        "per_budget": best[1]["per_budget"],
        "score_tuple": best[0],
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
        key=lambda r: (r["avg_final_sp"], r["avg_delta_sp_per_100kcal"], r["avg_variety_count"]),
        reverse=True,
    )[: args.topk]
    for j, r in enumerate(
        top,
        1,
    ):
        print(
            f"{j:>2}. SP={r['avg_final_sp']:.3f} | dSP/100kcal={r['avg_delta_sp_per_100kcal']:.3f} | variety={r['avg_variety_count']:.1f} || "
            f"soft={r['SOFT_BIAS_GAMMA']:.3f}, tie(a,b,eps)=({r['TIE_ALPHA']:.3f},{r['TIE_BETA']:.3f},{r['TIE_EPSILON']:.3f}), "
            f"cal_floor={r['CAL_FLOOR']}, gamma={r['CAL_PENALTY_GAMMA']:.3f}"
        )

    print(f"\nBest saved to: {json_path}")
    print(f"All trials saved to: {csv_path}")


if __name__ == "__main__":
    main()
