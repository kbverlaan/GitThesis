"""
Arch 1+2 analysis for Gemma 2 27B runs.

Loads 100 runs (5 framings × 20 reps), validates completeness,
computes summary statistics, and runs statistical tests.

Usage:
    python -m src.analysis.arch_analysis [--data-dir PATH] [--output-dir PATH]
"""

import json
import glob
import os
import re
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as sp_stats
from typing import Dict, List, Optional, Tuple

from .metrics import (
    gini_coefficient, palma_ratio, cooperation_ratio,
    first_attack_round, action_distribution, cooperation_rate_timeseries
)
from .stats import compute_icc, pairwise_comparisons, power_analysis


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FRAMINGS = ["neutral", "cooperative", "competitive", "strategic", "cautious"]
EXPECTED_REPS = 20
EXPECTED_ROUNDS = 50
N_AGENTS = 30

DATA_DIR_DEFAULT = Path(__file__).parent.parent.parent / "data" / "runs" / "arch_combined_gemma2_27b"
OUTPUT_DIR_DEFAULT = Path(__file__).parent.parent.parent / "data" / "results" / "arch_gemma2"

ACTION_TYPES = ["invest_self", "invest_other", "arm_self", "arm_other", "attack", "no_action", "do_nothing"]


# ---------------------------------------------------------------------------
# Step 1: Data loading & validation
# ---------------------------------------------------------------------------

def parse_run_id(filename: str) -> Optional[Dict[str, str]]:
    """Parse run filename into (model, framing, rep) components.

    Expected pattern:
        model_gemma-2-27b-it_framing_{framing}_rep{N}
    """
    # Strip file type suffix like _history.json, _traces.json etc.
    basename = os.path.basename(filename)
    for suffix in ["_history.json", "_traces.json", "_metrics.json", "_meta.json"]:
        if basename.endswith(suffix):
            basename = basename[:-len(suffix)]
            break

    match = re.match(
        r"model_(?P<model>.+?)_framing_(?P<framing>\w+)_rep(?P<rep>\d+)$",
        basename
    )
    if not match:
        return None
    return {
        "run_id": basename,
        "model": match.group("model"),
        "framing": match.group("framing"),
        "rep": int(match.group("rep")),
    }


def load_run(run_id: str, data_dir: Path) -> Dict:
    """Load all files for a single run. Returns dict with history, metrics, traces, meta."""
    result = {"run_id": run_id}

    for ftype in ["history", "metrics", "traces", "meta"]:
        fpath = data_dir / f"{run_id}_{ftype}.json"
        if fpath.exists():
            with open(fpath) as f:
                result[ftype] = json.load(f)
        else:
            result[ftype] = None

    return result


def load_all_runs(data_dir: Path) -> Tuple[pd.DataFrame, Dict[str, Dict]]:
    """Load all runs and build summary DataFrame.

    Returns:
        df: DataFrame with one row per run
        raw: dict mapping run_id -> full loaded data
    """
    # Discover runs via history files
    history_files = sorted(glob.glob(str(data_dir / "*_history.json")))
    if not history_files:
        raise FileNotFoundError(f"No history files found in {data_dir}")

    rows = []
    raw = {}

    for hfile in history_files:
        parsed = parse_run_id(hfile)
        if parsed is None:
            print(f"  [WARN] Skipping unparseable file: {os.path.basename(hfile)}")
            continue

        run_id = parsed["run_id"]
        run_data = load_run(run_id, data_dir)
        raw[run_id] = run_data

        history_data = run_data.get("history")
        if history_data is None:
            print(f"  [WARN] No history for {run_id}")
            continue

        history = history_data.get("history", [])
        final_resources = history_data.get("final_resources", {})
        total_rounds = history_data.get("total_rounds", len(history))

        # Compute metrics
        final_gini = gini_coefficient(final_resources)
        final_palma = palma_ratio(final_resources)
        coop_ratio = cooperation_ratio(history)
        first_atk = first_attack_round(history)

        # Action distribution across all rounds
        total_actions = {}
        for round_dict in history:
            rd = action_distribution(round_dict.get("actions", []))
            for act, cnt in rd.items():
                total_actions[act] = total_actions.get(act, 0) + cnt

        total_count = sum(total_actions.values()) or 1
        pct = {f"pct_{act}": total_actions.get(act, 0) / total_count
               for act in ACTION_TYPES}

        rows.append({
            "run_id": run_id,
            "model": parsed["model"],
            "framing": parsed["framing"],
            "rep": parsed["rep"],
            "total_rounds": total_rounds,
            "n_agents": len(final_resources),
            "final_gini": final_gini,
            "final_palma": final_palma,
            "coop_ratio": coop_ratio,
            "first_attack": first_atk,
            **pct,
        })

    df = pd.DataFrame(rows)
    return df, raw


def validate_runs(df: pd.DataFrame) -> Dict:
    """Validate completeness: 5 framings × 20 reps, no crashed runs."""
    issues = []

    # Check framing completeness
    for framing in FRAMINGS:
        n = len(df[df["framing"] == framing])
        if n != EXPECTED_REPS:
            issues.append(f"Framing '{framing}': expected {EXPECTED_REPS} reps, got {n}")

    # Check for crashed runs (final round != 50)
    crashed = df[df["total_rounds"] < EXPECTED_ROUNDS]
    if len(crashed) > 0:
        for _, row in crashed.iterrows():
            issues.append(f"Run {row['run_id']}: only {row['total_rounds']} rounds (expected {EXPECTED_ROUNDS})")

    # Check for unexpected framings
    unexpected = set(df["framing"].unique()) - set(FRAMINGS)
    if unexpected:
        issues.append(f"Unexpected framings: {unexpected}")

    report = {
        "total_runs": len(df),
        "expected_runs": len(FRAMINGS) * EXPECTED_REPS,
        "framings_found": sorted(df["framing"].unique().tolist()),
        "reps_per_framing": df.groupby("framing").size().to_dict(),
        "crashed_runs": len(crashed),
        "issues": issues,
        "valid": len(issues) == 0,
    }

    return report


# ---------------------------------------------------------------------------
# Step 2: Arch 1 — Fingerprint (neutral runs)
# ---------------------------------------------------------------------------

def arch1_fingerprint(df: pd.DataFrame, raw: Dict) -> Dict:
    """Analyze baseline behavior from neutral framing runs."""
    neutral = df[df["framing"] == "neutral"].copy()

    if len(neutral) == 0:
        return {"error": "No neutral runs found"}

    results = {}

    # 1. Descriptive stats
    metrics = ["final_gini", "final_palma", "coop_ratio"]
    desc = {}
    for m in metrics:
        vals = neutral[m].dropna()
        desc[m] = {
            "mean": float(vals.mean()),
            "std": float(vals.std()),
            "median": float(vals.median()),
            "min": float(vals.min()),
            "max": float(vals.max()),
            "n": int(len(vals)),
        }
    results["descriptive"] = desc

    # 2. ICC — how much variance is between-runs vs within-run?
    # Build per-round Gini data for ICC (agent-level within runs)
    icc_data = []
    for _, row in neutral.iterrows():
        run_data = raw.get(row["run_id"])
        if run_data is None or run_data.get("history") is None:
            continue
        history = run_data["history"].get("history", [])
        for rd in history:
            resources = {}
            # Use resource_changes to get per-round state is tricky;
            # use final_resources approach or metrics if available
            pass

    # Simpler ICC: treat each run as a group, each round's Gini as observation
    icc_rows = []
    for _, row in neutral.iterrows():
        run_data = raw.get(row["run_id"])
        if run_data is None:
            continue

        metrics_data = run_data.get("metrics")
        history_data = run_data.get("history")

        if metrics_data is not None:
            # metrics.json has per-round data
            for rd in metrics_data:
                icc_rows.append({
                    "group": row["run_id"],
                    "value": rd.get("gini", 0),
                })
        elif history_data is not None:
            # Compute from history
            history = history_data.get("history", [])
            final_res = history_data.get("final_resources", {})
            # Reconstruct per-round resources
            round_resources = _reconstruct_round_resources(history_data)
            for rnd_idx, res in enumerate(round_resources):
                icc_rows.append({
                    "group": row["run_id"],
                    "value": gini_coefficient(res),
                })

    if len(icc_rows) > 0:
        results["icc_gini"] = compute_icc(icc_rows, "group", "value")
    else:
        results["icc_gini"] = {"icc": None, "note": "No per-round data available"}

    # 3. Gini & cooperation trajectories (for plotting)
    gini_trajectories = []
    coop_trajectories = []
    for _, row in neutral.iterrows():
        run_data = raw.get(row["run_id"])
        if run_data is None or run_data.get("history") is None:
            continue

        history_data = run_data["history"]
        history = history_data.get("history", [])

        # Gini trajectory from metrics or recompute
        metrics_data = run_data.get("metrics")
        if metrics_data is not None:
            gini_traj = [rd.get("gini", 0) for rd in metrics_data]
        else:
            round_resources = _reconstruct_round_resources(history_data)
            gini_traj = [gini_coefficient(res) for res in round_resources]

        gini_trajectories.append(gini_traj)

        # Cooperation trajectory
        coop_traj = cooperation_rate_timeseries(history)
        coop_trajectories.append(coop_traj)

    results["gini_trajectories"] = _trajectory_stats(gini_trajectories)
    results["coop_trajectories"] = _trajectory_stats(coop_trajectories)

    # 4. Action distribution
    act_cols = [c for c in neutral.columns if c.startswith("pct_")]
    results["action_distribution"] = {
        c.replace("pct_", ""): {
            "mean": float(neutral[c].mean()),
            "std": float(neutral[c].std()),
        }
        for c in act_cols
    }

    # 5. First attack round
    fa = neutral["first_attack"].dropna()
    results["first_attack"] = {
        "mean": float(fa.mean()) if len(fa) > 0 else None,
        "std": float(fa.std()) if len(fa) > 0 else None,
        "n_runs_with_attack": int(len(fa)),
        "n_runs_no_attack": int(neutral["first_attack"].isna().sum()),
    }

    return results


# ---------------------------------------------------------------------------
# Step 3: Arch 2 — Framing effect
# ---------------------------------------------------------------------------

def arch2_framing_effect(df: pd.DataFrame, raw: Dict) -> Dict:
    """Analyze framing effects across all 5 conditions."""
    results = {}

    # 1. One-way ANOVA per metric
    for metric in ["final_gini", "final_palma", "coop_ratio"]:
        groups = []
        group_labels = []
        for framing in FRAMINGS:
            vals = df[df["framing"] == framing][metric].dropna().values
            if len(vals) > 0:
                groups.append(vals)
                group_labels.append(framing)

        if len(groups) >= 2:
            f_stat, p_value = sp_stats.f_oneway(*groups)

            # Eta-squared: SS_between / SS_total
            grand_mean = np.concatenate(groups).mean()
            ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
            ss_total = sum(np.sum((g - grand_mean) ** 2) for g in groups)
            eta_sq = ss_between / ss_total if ss_total > 0 else 0

            results[f"anova_{metric}"] = {
                "F": float(f_stat),
                "p_value": float(p_value),
                "eta_squared": float(eta_sq),
                "groups": group_labels,
                "group_means": {l: float(g.mean()) for l, g in zip(group_labels, groups)},
                "group_stds": {l: float(g.std()) for l, g in zip(group_labels, groups)},
                "significant": p_value < 0.05,
            }

    # 2. Pairwise comparisons
    for metric in ["final_gini", "final_palma", "coop_ratio"]:
        data_list = df[["framing", metric]].dropna().to_dict("records")
        if len(data_list) > 0:
            pw = pairwise_comparisons(data_list, "framing", metric)
            # Convert tuple keys to strings for JSON serialization
            results[f"pairwise_{metric}"] = {
                f"{k[0]}_vs_{k[1]}": v for k, v in pw.items()
            }

    # 3. Descriptive stats per framing
    per_framing = {}
    for framing in FRAMINGS:
        sub = df[df["framing"] == framing]
        if len(sub) == 0:
            continue
        per_framing[framing] = {
            "n": int(len(sub)),
            "final_gini": {"mean": float(sub["final_gini"].mean()), "std": float(sub["final_gini"].std())},
            "final_palma": {"mean": float(sub["final_palma"].mean()), "std": float(sub["final_palma"].std())},
            "coop_ratio": {"mean": float(sub["coop_ratio"].mean()), "std": float(sub["coop_ratio"].std())},
            "first_attack_mean": float(sub["first_attack"].dropna().mean()) if sub["first_attack"].notna().any() else None,
        }
        # Action distribution
        act_cols = [c for c in sub.columns if c.startswith("pct_")]
        per_framing[framing]["actions"] = {
            c.replace("pct_", ""): float(sub[c].mean())
            for c in act_cols
        }
    results["per_framing"] = per_framing

    # 4. Gini trajectories per framing (for temporal dynamics plot)
    trajectories_by_framing = {}
    for framing in FRAMINGS:
        gini_trajectories = []
        sub = df[df["framing"] == framing]
        for _, row in sub.iterrows():
            run_data = raw.get(row["run_id"])
            if run_data is None or run_data.get("history") is None:
                continue

            metrics_data = run_data.get("metrics")
            if metrics_data is not None:
                gini_traj = [rd.get("gini", 0) for rd in metrics_data]
            else:
                history_data = run_data["history"]
                round_resources = _reconstruct_round_resources(history_data)
                gini_traj = [gini_coefficient(res) for res in round_resources]

            gini_trajectories.append(gini_traj)

        trajectories_by_framing[framing] = _trajectory_stats(gini_trajectories)
    results["gini_trajectories_by_framing"] = trajectories_by_framing

    # 5. First attack per framing
    first_atk = {}
    for framing in FRAMINGS:
        fa = df[df["framing"] == framing]["first_attack"].dropna()
        first_atk[framing] = {
            "mean": float(fa.mean()) if len(fa) > 0 else None,
            "std": float(fa.std()) if len(fa) > 0 else None,
            "n_with_attack": int(len(fa)),
            "n_without_attack": int((df[df["framing"] == framing]["first_attack"].isna()).sum()),
        }
    results["first_attack_by_framing"] = first_atk

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reconstruct_round_resources(history_data: Dict) -> List[Dict[str, float]]:
    """Reconstruct per-round resource snapshots from history.

    Works backwards from final_resources using resource_changes.
    Returns list of dicts, one per round.
    """
    final_resources = history_data.get("final_resources", {})
    history = history_data.get("history", [])

    if not history or not final_resources:
        return []

    n_rounds = len(history)
    # Start from final and work backwards
    snapshots = [None] * n_rounds
    current = dict(final_resources)

    for i in range(n_rounds - 1, -1, -1):
        snapshots[i] = dict(current)
        changes = history[i].get("resource_changes", {})
        for agent, change in changes.items():
            current[agent] = current.get(agent, 0) - change

    return snapshots


def _trajectory_stats(trajectories: List[List[float]]) -> Dict:
    """Compute mean, std, CI bounds for a set of trajectories."""
    if not trajectories:
        return {"mean": [], "std": [], "ci_lower": [], "ci_upper": [], "n": 0}

    min_len = min(len(t) for t in trajectories)
    arr = np.array([t[:min_len] for t in trajectories])

    mean = arr.mean(axis=0)
    std = arr.std(axis=0)
    n = arr.shape[0]
    se = std / np.sqrt(n)
    ci_lower = mean - 1.96 * se
    ci_upper = mean + 1.96 * se

    return {
        "mean": mean.tolist(),
        "std": std.tolist(),
        "ci_lower": ci_lower.tolist(),
        "ci_upper": ci_upper.tolist(),
        "n": n,
        "rounds": list(range(min_len)),
    }


def print_summary(df: pd.DataFrame, validation: Dict, arch1: Dict, arch2: Dict):
    """Print human-readable summary of all results."""
    sep = "=" * 70

    print(f"\n{sep}")
    print("GEMMA 2 27B — ARCH 1+2 ANALYSIS SUMMARY")
    print(sep)

    # Validation
    print(f"\n--- DATA VALIDATION ---")
    print(f"Total runs loaded: {validation['total_runs']} / {validation['expected_runs']}")
    print(f"Framings: {validation['framings_found']}")
    print(f"Reps per framing: {validation['reps_per_framing']}")
    if validation["issues"]:
        print("ISSUES:")
        for issue in validation["issues"]:
            print(f"  ⚠ {issue}")
    else:
        print("All checks passed.")

    # Arch 1: Fingerprint
    print(f"\n{sep}")
    print("ARCH 1 — NEUTRAL BASELINE FINGERPRINT")
    print(sep)
    if "descriptive" in arch1:
        for m, stats in arch1["descriptive"].items():
            print(f"  {m}: {stats['mean']:.4f} ± {stats['std']:.4f} (n={stats['n']})")
    if "icc_gini" in arch1 and arch1["icc_gini"].get("icc") is not None:
        print(f"  ICC (Gini): {arch1['icc_gini']['icc']:.4f}")
    if "first_attack" in arch1:
        fa = arch1["first_attack"]
        print(f"  First attack round: {fa['mean']:.1f} ± {fa['std']:.1f}" if fa["mean"] else "  No attacks in neutral runs")
        print(f"  Runs with attack: {fa['n_runs_with_attack']} / {fa['n_runs_with_attack'] + fa['n_runs_no_attack']}")
    if "action_distribution" in arch1:
        print("  Action distribution:")
        for act, stats in arch1["action_distribution"].items():
            print(f"    {act}: {stats['mean']*100:.1f}% ± {stats['std']*100:.1f}%")

    # Arch 2: Framing effect
    print(f"\n{sep}")
    print("ARCH 2 — FRAMING EFFECT")
    print(sep)

    for metric in ["final_gini", "final_palma", "coop_ratio"]:
        key = f"anova_{metric}"
        if key in arch2:
            a = arch2[key]
            sig = "*" if a["significant"] else "ns"
            print(f"\n  ANOVA {metric}: F={a['F']:.3f}, p={a['p_value']:.4f} ({sig}), η²={a['eta_squared']:.4f}")
            for framing in FRAMINGS:
                if framing in a["group_means"]:
                    print(f"    {framing:12s}: {a['group_means'][framing]:.4f} ± {a['group_stds'][framing]:.4f}")

    # Pairwise comparisons
    for metric in ["final_gini"]:
        key = f"pairwise_{metric}"
        if key in arch2:
            print(f"\n  Pairwise comparisons ({metric}):")
            print(f"  {'Comparison':30s} {'d':>8s} {'p_corr':>8s} {'BF10':>8s} {'sig':>5s}")
            for pair_key, v in arch2[key].items():
                sig = "*" if v.get("significant") else ""
                bf = v.get("bf10", 0)
                bf_str = f"{bf:.2f}" if bf < 1000 else f"{bf:.0f}"
                print(f"  {pair_key:30s} {v['cohens_d']:8.3f} {v['p_corrected']:8.4f} {bf_str:>8s} {sig:>5s}")

    # First attack by framing
    if "first_attack_by_framing" in arch2:
        print(f"\n  First attack round by framing:")
        for framing in FRAMINGS:
            fa = arch2["first_attack_by_framing"].get(framing, {})
            if fa.get("mean") is not None:
                print(f"    {framing:12s}: round {fa['mean']:.1f} ± {fa['std']:.1f} ({fa['n_with_attack']}/{fa['n_with_attack']+fa['n_without_attack']} runs)")
            else:
                print(f"    {framing:12s}: no attacks")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_analysis(data_dir: Path = None, output_dir: Path = None) -> Tuple[pd.DataFrame, Dict, Dict, Dict]:
    """Run full Arch 1+2 analysis. Returns (df, validation, arch1, arch2)."""
    if data_dir is None:
        data_dir = DATA_DIR_DEFAULT
    if output_dir is None:
        output_dir = OUTPUT_DIR_DEFAULT

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading runs from {data_dir}...")
    df, raw = load_all_runs(data_dir)
    print(f"Loaded {len(df)} runs.")

    print("Validating...")
    validation = validate_runs(df)

    print("Running Arch 1 — Neutral fingerprint...")
    arch1 = arch1_fingerprint(df, raw)

    print("Running Arch 2 — Framing effect...")
    arch2 = arch2_framing_effect(df, raw)

    # Print summary
    print_summary(df, validation, arch1, arch2)

    # Save outputs
    df.to_csv(output_dir / "summary_df.csv", index=False)
    print(f"\nSaved summary DataFrame to {output_dir / 'summary_df.csv'}")

    # Save JSON results
    results_json = {
        "validation": validation,
        "arch1": _make_json_safe(arch1),
        "arch2": _make_json_safe(arch2),
    }
    with open(output_dir / "analysis_results.json", "w") as f:
        json.dump(results_json, f, indent=2, default=str)
    print(f"Saved analysis results to {output_dir / 'analysis_results.json'}")

    return df, validation, arch1, arch2


def _make_json_safe(obj):
    """Convert numpy types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Arch 1+2 analysis for Gemma 2 27B")
    parser.add_argument("--data-dir", type=Path, default=None,
                        help="Path to arch_combined_gemma2_27b data directory")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Path to save results")
    args = parser.parse_args()

    run_analysis(data_dir=args.data_dir, output_dir=args.output_dir)
