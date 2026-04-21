"""
Reasoning depth analysis for Origins experiments.

Analyzes:
1. Reasoning depth pilot/production: per-level metrics and trace validation
2. Origins factorial: phase transitions × reasoning depth interaction

Usage:
    python -m src.analysis.reasoning_analysis [--data-dir PATH] [--output-dir PATH]
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
from .stats import two_way_anova, pairwise_comparisons
from .trace_analysis import parse_trace_response


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REASONING_LEVELS = ["level0", "level1", "level2"]
EXPECTED_ROUNDS = 50
N_AGENTS = 30

ACTION_TYPES = ["invest_self", "invest_other", "arm_self", "arm_other",
                "attack", "no_action", "do_nothing"]


# ---------------------------------------------------------------------------
# Run ID parsing
# ---------------------------------------------------------------------------

def parse_run_id(filename: str) -> Optional[Dict[str, str]]:
    """Parse run filename into components.

    Handles patterns like:
        model_gemma-2-27b-it_reasoning_level_level0_rep0
        model_gemma-2-27b-it_interaction_radius_3_reasoning_level_level2_rep5
    """
    basename = os.path.basename(filename)
    for suffix in ["_history.json", "_traces.json", "_metrics.json", "_meta.json"]:
        if basename.endswith(suffix):
            basename = basename[:-len(suffix)]
            break

    # Extract rep number from end
    rep_match = re.search(r"_rep(\d+)$", basename)
    if not rep_match:
        return None
    rep = int(rep_match.group(1))
    core = basename[:rep_match.start()]

    # Extract known parameters
    result = {"run_id": basename, "rep": rep}

    # Model
    model_match = re.match(r"model_(.+?)(?=_(?:reasoning_level|interaction_radius|framing)_|$)", core)
    if model_match:
        result["model"] = model_match.group(1)

    # Reasoning level
    rl_match = re.search(r"reasoning_level_(level\d+)", core)
    if rl_match:
        result["reasoning_level"] = rl_match.group(1)

    # Interaction radius
    ir_match = re.search(r"interaction_radius_(\d+)", core)
    if ir_match:
        result["interaction_radius"] = int(ir_match.group(1))

    # Framing
    fr_match = re.search(r"framing_(\w+)", core)
    if fr_match:
        result["framing"] = fr_match.group(1)

    return result


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_run(run_id: str, data_dir: Path) -> Dict:
    """Load all files for a single run."""
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
    """Load all runs and build summary DataFrame."""
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

        final_gini = gini_coefficient(final_resources)
        final_palma = palma_ratio(final_resources)
        coop_ratio = cooperation_ratio(history)
        first_atk = first_attack_round(history)

        # Action distribution
        total_actions = {}
        for round_dict in history:
            rd = action_distribution(round_dict.get("actions", []))
            for act, cnt in rd.items():
                total_actions[act] = total_actions.get(act, 0) + cnt

        total_count = sum(total_actions.values()) or 1
        pct = {f"pct_{act}": total_actions.get(act, 0) / total_count
               for act in ACTION_TYPES}

        row = {
            "run_id": run_id,
            "rep": parsed["rep"],
            "total_rounds": total_rounds,
            "n_agents": len(final_resources),
            "final_gini": final_gini,
            "final_palma": final_palma,
            "coop_ratio": coop_ratio,
            "first_attack": first_atk,
            **pct,
        }

        # Add parsed condition variables
        for key in ["model", "reasoning_level", "interaction_radius", "framing"]:
            if key in parsed:
                row[key] = parsed[key]

        rows.append(row)

    df = pd.DataFrame(rows)
    return df, raw


# ---------------------------------------------------------------------------
# Trace analysis: reasoning token counts
# ---------------------------------------------------------------------------

def reasoning_token_counts(raw: Dict[str, Dict], df: pd.DataFrame) -> pd.DataFrame:
    """Count reasoning tokens per run from traces.

    Returns DataFrame with run_id, reasoning_level, mean/median/std token count.
    """
    rows = []
    for _, row in df.iterrows():
        run_id = row["run_id"]
        run_data = raw.get(run_id)
        if run_data is None or run_data.get("traces") is None:
            continue

        traces = run_data["traces"]
        token_counts = []
        for trace_entry in traces:
            response = trace_entry.get("response", "")
            parsed = parse_trace_response(response)
            if parsed and parsed.get("reasoning"):
                # Approximate token count by whitespace splitting
                n_tokens = len(parsed["reasoning"].split())
                token_counts.append(n_tokens)

        if token_counts:
            rows.append({
                "run_id": run_id,
                "reasoning_level": row.get("reasoning_level", "unknown"),
                "mean_tokens": np.mean(token_counts),
                "median_tokens": np.median(token_counts),
                "std_tokens": np.std(token_counts),
                "n_traces": len(token_counts),
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pilot analysis
# ---------------------------------------------------------------------------

def analyze_pilot(df: pd.DataFrame, raw: Dict) -> Dict:
    """Analyze reasoning depth pilot results."""
    results = {}

    if "reasoning_level" not in df.columns:
        return {"error": "No reasoning_level column found — wrong data?"}

    # 1. Per-level descriptive stats
    per_level = {}
    for level in REASONING_LEVELS:
        sub = df[df["reasoning_level"] == level]
        if len(sub) == 0:
            continue
        per_level[level] = {
            "n": int(len(sub)),
            "final_gini": {"mean": float(sub["final_gini"].mean()),
                           "std": float(sub["final_gini"].std())},
            "final_palma": {"mean": float(sub["final_palma"].mean()),
                            "std": float(sub["final_palma"].std())},
            "coop_ratio": {"mean": float(sub["coop_ratio"].mean()),
                           "std": float(sub["coop_ratio"].std())},
            "first_attack_mean": (float(sub["first_attack"].dropna().mean())
                                  if sub["first_attack"].notna().any() else None),
        }
        # Action distribution
        act_cols = [c for c in sub.columns if c.startswith("pct_")]
        per_level[level]["actions"] = {
            c.replace("pct_", ""): float(sub[c].mean())
            for c in act_cols
        }
    results["per_level"] = per_level

    # 2. Token counts from traces
    token_df = reasoning_token_counts(raw, df)
    if len(token_df) > 0:
        token_summary = {}
        for level in REASONING_LEVELS:
            sub = token_df[token_df["reasoning_level"] == level]
            if len(sub) > 0:
                token_summary[level] = {
                    "mean_tokens": float(sub["mean_tokens"].mean()),
                    "median_tokens": float(sub["median_tokens"].mean()),
                }
        results["token_counts"] = token_summary

    # 3. One-way ANOVA (if enough data)
    for metric in ["final_gini", "coop_ratio"]:
        groups = []
        labels = []
        for level in REASONING_LEVELS:
            vals = df[df["reasoning_level"] == level][metric].dropna().values
            if len(vals) > 1:
                groups.append(vals)
                labels.append(level)
        if len(groups) >= 2:
            f_stat, p_value = sp_stats.f_oneway(*groups)
            grand_mean = np.concatenate(groups).mean()
            ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
            ss_total = sum(np.sum((g - grand_mean) ** 2) for g in groups)
            eta_sq = ss_between / ss_total if ss_total > 0 else 0
            results[f"anova_{metric}"] = {
                "F": float(f_stat),
                "p_value": float(p_value),
                "eta_squared": float(eta_sq),
                "significant": p_value < 0.05,
                "note": "pilot — small n, interpret with caution",
            }

    return results


# ---------------------------------------------------------------------------
# Origins factorial analysis
# ---------------------------------------------------------------------------

def analyze_origins_factorial(df: pd.DataFrame, raw: Dict) -> Dict:
    """Analyze reasoning depth × interaction radius factorial."""
    results = {}

    if "reasoning_level" not in df.columns or "interaction_radius" not in df.columns:
        return {"error": "Missing reasoning_level or interaction_radius columns"}

    # 1. Two-way ANOVA: reasoning_level × interaction_radius → final_gini
    anova_data = df[["reasoning_level", "interaction_radius", "final_gini"]].dropna()
    anova_data = anova_data.rename(columns={"interaction_radius": "radius"})
    if len(anova_data) > 10:
        anova_result = two_way_anova(
            anova_data.to_dict("records"),
            "reasoning_level", "radius", "final_gini"
        )
        results["anova_gini"] = anova_result

    # Same for cooperation ratio
    anova_coop = df[["reasoning_level", "interaction_radius", "coop_ratio"]].dropna()
    anova_coop = anova_coop.rename(columns={"interaction_radius": "radius"})
    if len(anova_coop) > 10:
        results["anova_coop"] = two_way_anova(
            anova_coop.to_dict("records"),
            "reasoning_level", "radius", "coop_ratio"
        )

    # 2. Per reasoning level: Gini vs radius (phase transition curves)
    phase_curves = {}
    radii = sorted(df["interaction_radius"].unique())
    for level in REASONING_LEVELS:
        curve = {}
        for r in radii:
            sub = df[(df["reasoning_level"] == level) & (df["interaction_radius"] == r)]
            if len(sub) > 0:
                curve[int(r)] = {
                    "mean_gini": float(sub["final_gini"].mean()),
                    "std_gini": float(sub["final_gini"].std()),
                    "mean_coop": float(sub["coop_ratio"].mean()),
                    "std_coop": float(sub["coop_ratio"].std()),
                    "n": int(len(sub)),
                }
        phase_curves[level] = curve
    results["phase_curves"] = phase_curves

    # 3. Descriptive: per level × radius cell means
    cell_means = (
        df.groupby(["reasoning_level", "interaction_radius"])
        .agg(
            mean_gini=("final_gini", "mean"),
            std_gini=("final_gini", "std"),
            mean_coop=("coop_ratio", "mean"),
            n=("final_gini", "count"),
        )
        .reset_index()
    )
    results["cell_means"] = cell_means.to_dict("records")

    return results


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------

def print_pilot_summary(results: Dict):
    """Print human-readable pilot summary."""
    sep = "=" * 70
    print(f"\n{sep}")
    print("REASONING DEPTH — PILOT ANALYSIS")
    print(sep)

    if "per_level" in results:
        for level, stats in results["per_level"].items():
            print(f"\n  {level} (n={stats['n']}):")
            print(f"    Gini:  {stats['final_gini']['mean']:.4f} ± {stats['final_gini']['std']:.4f}")
            print(f"    Coop:  {stats['coop_ratio']['mean']:.4f} ± {stats['coop_ratio']['std']:.4f}")
            if stats.get("first_attack_mean") is not None:
                print(f"    First attack: round {stats['first_attack_mean']:.1f}")
            if "actions" in stats:
                top_actions = sorted(stats["actions"].items(), key=lambda x: -x[1])[:3]
                acts_str = ", ".join(f"{a}: {p*100:.0f}%" for a, p in top_actions)
                print(f"    Top actions: {acts_str}")

    if "token_counts" in results:
        print(f"\n  Reasoning token counts:")
        for level, tc in results["token_counts"].items():
            print(f"    {level}: mean={tc['mean_tokens']:.0f}, median={tc['median_tokens']:.0f}")

    for metric in ["final_gini", "coop_ratio"]:
        key = f"anova_{metric}"
        if key in results:
            a = results[key]
            sig = "*" if a["significant"] else "ns"
            print(f"\n  ANOVA {metric}: F={a['F']:.3f}, p={a['p_value']:.4f} ({sig}), η²={a['eta_squared']:.4f}")
            if "note" in a:
                print(f"    Note: {a['note']}")


def print_origins_summary(results: Dict):
    """Print human-readable origins factorial summary."""
    sep = "=" * 70
    print(f"\n{sep}")
    print("ORIGINS — REASONING × RADIUS FACTORIAL")
    print(sep)

    if "anova_gini" in results:
        a = results["anova_gini"]
        print(f"\n  Two-way ANOVA on final_gini:")
        for effect_name, effect in a.items():
            if isinstance(effect, dict) and "F" in effect:
                sig = "*" if effect.get("significant") else "ns"
                eta = effect.get("partial_eta_sq", effect.get("eta_squared", 0))
                print(f"    {effect_name}: F={effect['F']:.3f}, p={effect['p_value']:.4f} ({sig}), η²={eta:.4f}")

    if "phase_curves" in results:
        print(f"\n  Phase transition curves (Gini vs radius):")
        for level, curve in results["phase_curves"].items():
            radii_str = ", ".join(
                f"r={r}: {v['mean_gini']:.3f}±{v['std_gini']:.3f}"
                for r, v in sorted(curve.items())
            )
            print(f"    {level}: {radii_str}")


# ---------------------------------------------------------------------------
# JSON safety
# ---------------------------------------------------------------------------

def _make_json_safe(obj):
    """Convert numpy types for JSON serialization."""
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return str(obj)
    return obj


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_analysis(data_dir: Path, output_dir: Path, mode: str = "pilot") -> Dict:
    """Run reasoning depth analysis.

    Args:
        data_dir: Path to run data directory
        output_dir: Path to save results
        mode: "pilot", "production", or "origins"
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading runs from {data_dir}...")
    df, raw = load_all_runs(data_dir)
    print(f"Loaded {len(df)} runs.")

    if mode in ("pilot", "production"):
        results = analyze_pilot(df, raw)
        print_pilot_summary(results)

        if mode == "production":
            # Pairwise comparisons with enough data
            for metric in ["final_gini", "coop_ratio"]:
                data_list = df[["reasoning_level", metric]].dropna().to_dict("records")
                if len(data_list) > 0:
                    pw = pairwise_comparisons(data_list, "reasoning_level", metric)
                    results[f"pairwise_{metric}"] = {
                        f"{k[0]}_vs_{k[1]}": v for k, v in pw.items()
                    }

    elif mode == "origins":
        results = analyze_origins_factorial(df, raw)
        print_origins_summary(results)

    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Save
    df.to_csv(output_dir / f"reasoning_{mode}_df.csv", index=False)
    with open(output_dir / f"reasoning_{mode}_results.json", "w") as f:
        json.dump(_make_json_safe(results), f, indent=2, default=str)

    print(f"\nSaved to {output_dir}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reasoning depth analysis")
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="Path to run data directory")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Path to save results")
    parser.add_argument("--mode", choices=["pilot", "production", "origins"],
                        default="pilot", help="Analysis mode")
    args = parser.parse_args()

    if args.output_dir is None:
        args.output_dir = Path(__file__).parent.parent.parent / "data" / "results" / f"reasoning_{args.mode}"

    run_analysis(args.data_dir, args.output_dir, args.mode)
