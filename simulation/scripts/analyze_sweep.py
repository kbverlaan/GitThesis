#!/usr/bin/env python3
"""
Quick sweep analysis: summary tables + key plots.

Usage:
    python scripts/analyze_sweep.py data/runs/qwen_sweep_conflict_cost
    python scripts/analyze_sweep.py data/runs/qwen_sweep_conflict_cost --plot
    python scripts/analyze_sweep.py data/runs/qwen_sweep_conflict_cost --compare data/runs/sweep_conflict_cost_reasoning
"""
import json
import glob
import os
import sys
import argparse
from pathlib import Path
from collections import defaultdict


def load_run(metrics_path):
    """Load a single run's metrics (list of per-round dicts)."""
    with open(metrics_path) as f:
        return json.load(f)


def load_traces(traces_path):
    """Load traces for a run."""
    with open(traces_path) as f:
        return json.load(f)


def parse_run_name(filename, prefix=""):
    """Extract condition and rep from filename."""
    name = os.path.basename(filename).replace("_metrics.json", "")
    if prefix:
        name = name.replace(prefix, "")
    # Extract rep number
    parts = name.rsplit("_rep", 1)
    condition = parts[0]
    rep = int(parts[1]) if len(parts) > 1 else 1
    return condition, rep


def aggregate_actions(rounds):
    """Sum action distributions across all rounds."""
    total = defaultdict(int)
    for r in rounds:
        for act, cnt in r.get("action_distribution", {}).items():
            total[act] += cnt
    return dict(total)


def compute_summary(rounds):
    """Compute summary stats for a run."""
    total_actions = aggregate_actions(rounds)
    total_count = sum(total_actions.values())

    # Action percentages
    pcts = {}
    if total_count > 0:
        pcts = {k: round(v / total_count * 100, 1)
                for k, v in sorted(total_actions.items(), key=lambda x: -x[1])}

    # Gini trajectory
    gini_vals = [r.get("gini", 0) for r in rounds]
    final_gini = gini_vals[-1] if gini_vals else 0
    mean_gini = sum(gini_vals) / len(gini_vals) if gini_vals else 0

    # Resource stats from final round
    final_resources = rounds[-1].get("resources", {}) if rounds else {}
    res_values = list(final_resources.values()) if final_resources else []

    return {
        "action_pcts": pcts,
        "total_actions": total_count,
        "final_gini": final_gini,
        "mean_gini": round(mean_gini, 3),
        "n_rounds": len(rounds),
        "final_res_mean": round(sum(res_values) / len(res_values), 1) if res_values else 0,
        "final_res_std": round((sum((x - sum(res_values)/len(res_values))**2 for x in res_values) / len(res_values))**0.5, 1) if res_values else 0,
        "gini_trajectory": gini_vals,
    }


def print_sweep_table(sweep_dir):
    """Print a summary table for all runs in a sweep directory."""
    files = sorted(glob.glob(os.path.join(sweep_dir, "*_metrics.json")))
    if not files:
        print(f"No metrics files found in {sweep_dir}")
        return {}

    # Detect common prefix
    names = [os.path.basename(f).replace("_metrics.json", "") for f in files]

    # Group by condition (aggregate reps)
    conditions = defaultdict(list)
    all_runs = {}

    for f in files:
        name = os.path.basename(f).replace("_metrics.json", "")
        condition, rep = parse_run_name(f)
        rounds = load_run(f)
        summary = compute_summary(rounds)
        conditions[condition].append(summary)
        all_runs[name] = summary

    # Collect all action types
    all_actions = set()
    for runs in conditions.values():
        for r in runs:
            all_actions.update(r["action_pcts"].keys())
    action_cols = sorted(all_actions)

    # Print header
    act_header = "".join(f"{a:>12}" for a in action_cols)
    print(f"\n{'Condition':<55} {'Reps':>4} {act_header} {'Gini':>8} {'Res±σ':>12}")
    print("-" * (55 + 4 + 12 * len(action_cols) + 8 + 12))

    # Print rows (grouped by condition, averaged over reps)
    for condition in sorted(conditions.keys()):
        runs = conditions[condition]
        n_reps = len(runs)

        # Average action percentages
        avg_pcts = {}
        for act in action_cols:
            vals = [r["action_pcts"].get(act, 0) for r in runs]
            avg_pcts[act] = sum(vals) / len(vals)

        avg_gini = sum(r["final_gini"] for r in runs) / n_reps
        avg_res = sum(r["final_res_mean"] for r in runs) / n_reps
        avg_std = sum(r["final_res_std"] for r in runs) / n_reps

        act_vals = "".join(f"{avg_pcts.get(a, 0):>11.1f}%" for a in action_cols)
        print(f"{condition:<55} {n_reps:>4} {act_vals} {avg_gini:>8.3f} {avg_res:>6.1f}±{avg_std:.1f}")

    print()
    return all_runs


def print_comparison(dir1, dir2):
    """Print side-by-side comparison of two sweep directories."""
    print(f"\n{'='*60}")
    print(f"SWEEP 1: {os.path.basename(dir1)}")
    print(f"{'='*60}")
    runs1 = print_sweep_table(dir1)

    print(f"\n{'='*60}")
    print(f"SWEEP 2: {os.path.basename(dir2)}")
    print(f"{'='*60}")
    runs2 = print_sweep_table(dir2)


def check_thinking_traces(sweep_dir):
    """Quick check: are thinking traces being saved?"""
    files = sorted(glob.glob(os.path.join(sweep_dir, "*_traces.json")))[:3]
    if not files:
        print("No trace files found.")
        return

    print("\n--- Thinking Trace Check ---")
    for f in files:
        name = os.path.basename(f).replace("_traces.json", "")
        traces = load_traces(f)
        if isinstance(traces, list):
            with_thinking = sum(1 for t in traces if len(t.get("thinking") or "") > 100)
            total = len(traces)
            avg_len = sum(len(t.get("thinking") or "") for t in traces) / total if total else 0
            print(f"  {name}: {with_thinking}/{total} traces have thinking ({avg_len:.0f} avg chars)")
        else:
            print(f"  {name}: unexpected format ({type(traces)})")


def plot_sweep(sweep_dir, output_dir=None):
    """Generate key plots for a sweep."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib not available. Install with: pip install matplotlib")
        return

    files = sorted(glob.glob(os.path.join(sweep_dir, "*_metrics.json")))
    if not files:
        return

    if output_dir is None:
        output_dir = os.path.join(sweep_dir, "plots")
    os.makedirs(output_dir, exist_ok=True)

    # Group by condition
    conditions = defaultdict(list)
    for f in files:
        condition, rep = parse_run_name(f)
        rounds = load_run(f)
        conditions[condition].append(compute_summary(rounds))

    sweep_name = os.path.basename(sweep_dir)

    # --- Plot 1: Action distribution bar chart ---
    fig, ax = plt.subplots(figsize=(max(10, len(conditions) * 1.2), 6))

    all_actions = set()
    for runs in conditions.values():
        for r in runs:
            all_actions.update(r["action_pcts"].keys())
    action_types = sorted(all_actions)

    colors = {
        "do_nothing": "#95a5a6",
        "invest_other": "#27ae60",
        "invest_self": "#2ecc71",
        "arm_self": "#e67e22",
        "arm_other": "#f39c12",
        "attack": "#e74c3c",
    }

    cond_names = sorted(conditions.keys())
    x = np.arange(len(cond_names))
    width = 0.8

    bottom = np.zeros(len(cond_names))
    for act in action_types:
        vals = []
        for cond in cond_names:
            runs = conditions[cond]
            avg = sum(r["action_pcts"].get(act, 0) for r in runs) / len(runs)
            vals.append(avg)
        vals = np.array(vals)
        color = colors.get(act, "#bdc3c7")
        ax.bar(x, vals, width, bottom=bottom, label=act, color=color)
        bottom += vals

    ax.set_ylabel("% of actions")
    ax.set_title(f"Action Distribution — {sweep_name}")
    ax.set_xticks(x)
    # Shorter labels
    short_labels = []
    for c in cond_names:
        parts = c.split("_")
        # Try to extract the key varying value + reasoning level
        label = c.replace("reasoning_level_", "").replace("conflict_cost_pct_", "cc").replace("attack_take_pct_", "tk").replace("arm_cost_pct_", "ac").replace("arm_other_cost_pct_", "ao").replace("invest_other_return_pct_", "ret").replace("invest_other_cost_pct_", "ic").replace("interaction_radius_", "r").replace("allow_invest_self_", "is").replace("memory_enabled_", "mem")
        short_labels.append(label)
    ax.set_xticklabels(short_labels, rotation=45, ha="right", fontsize=8)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_ylim(0, 105)
    plt.tight_layout()
    path1 = os.path.join(output_dir, f"{sweep_name}_actions.png")
    plt.savefig(path1, dpi=150)
    plt.close()
    print(f"  Saved: {path1}")

    # --- Plot 2: Gini by condition (L1 vs L3) ---
    fig, ax = plt.subplots(figsize=(max(8, len(conditions) * 0.8), 5))

    # Separate L1 and L3
    l1_conds = {c: r for c, r in conditions.items() if "level1" in c}
    l3_conds = {c: r for c, r in conditions.items() if "level3" in c}

    if l1_conds and l3_conds:
        # Extract the parameter value from condition names
        def extract_param(cond):
            """Get the swept parameter value."""
            for part in cond.split("_"):
                try:
                    return float(part)
                except ValueError:
                    continue
            return 0

        l1_sorted = sorted(l1_conds.items(), key=lambda x: extract_param(x[0]))
        l3_sorted = sorted(l3_conds.items(), key=lambda x: extract_param(x[0]))

        l1_params = [extract_param(c) for c, _ in l1_sorted]
        l1_ginis = [sum(r["final_gini"] for r in runs) / len(runs) for _, runs in l1_sorted]
        l1_errs = []
        for _, runs in l1_sorted:
            vals = [r["final_gini"] for r in runs]
            l1_errs.append((max(vals) - min(vals)) / 2 if len(vals) > 1 else 0)

        l3_params = [extract_param(c) for c, _ in l3_sorted]
        l3_ginis = [sum(r["final_gini"] for r in runs) / len(runs) for _, runs in l3_sorted]
        l3_errs = []
        for _, runs in l3_sorted:
            vals = [r["final_gini"] for r in runs]
            l3_errs.append((max(vals) - min(vals)) / 2 if len(vals) > 1 else 0)

        ax.errorbar(l1_params, l1_ginis, yerr=l1_errs, marker="o", label="L1", capsize=4, linewidth=2)
        ax.errorbar(l3_params, l3_ginis, yerr=l3_errs, marker="s", label="L3", capsize=4, linewidth=2)
        ax.set_xlabel("Parameter value")
        ax.set_ylabel("Final Gini")
        ax.set_title(f"Inequality by Reasoning Level — {sweep_name}")
        ax.legend()
        ax.grid(True, alpha=0.3)
    else:
        # Just plot all conditions
        conds = sorted(conditions.items(), key=lambda x: x[0])
        names = [c for c, _ in conds]
        ginis = [sum(r["final_gini"] for r in runs) / len(runs) for _, runs in conds]
        ax.bar(range(len(names)), ginis, color="#3498db")
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("Final Gini")
        ax.set_title(f"Final Gini — {sweep_name}")

    plt.tight_layout()
    path2 = os.path.join(output_dir, f"{sweep_name}_gini.png")
    plt.savefig(path2, dpi=150)
    plt.close()
    print(f"  Saved: {path2}")

    # --- Plot 3: Gini trajectories (one line per condition) ---
    fig, ax = plt.subplots(figsize=(10, 5))

    for cond in sorted(conditions.keys()):
        runs = conditions[cond]
        # Average gini trajectory across reps
        max_len = max(len(r["gini_trajectory"]) for r in runs)
        avg_traj = []
        for i in range(max_len):
            vals = [r["gini_trajectory"][i] for r in runs if i < len(r["gini_trajectory"])]
            avg_traj.append(sum(vals) / len(vals))

        label = cond.replace("reasoning_level_", "").replace("conflict_cost_pct_", "cc").replace("attack_take_pct_", "tk")
        style = "--" if "level1" in cond else "-"
        ax.plot(range(1, len(avg_traj) + 1), avg_traj, style, label=label, linewidth=1.5)

    ax.set_xlabel("Round")
    ax.set_ylabel("Gini coefficient")
    ax.set_title(f"Gini Trajectories — {sweep_name}")
    ax.legend(fontsize=7, loc="best")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path3 = os.path.join(output_dir, f"{sweep_name}_gini_traj.png")
    plt.savefig(path3, dpi=150)
    plt.close()
    print(f"  Saved: {path3}")

    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Quick sweep analysis")
    parser.add_argument("sweep_dir", help="Path to sweep results directory")
    parser.add_argument("--plot", action="store_true", help="Generate plots")
    parser.add_argument("--compare", help="Second sweep dir for comparison")
    parser.add_argument("--traces", action="store_true", help="Check thinking traces")
    parser.add_argument("--output", help="Output directory for plots")
    args = parser.parse_args()

    sweep_dir = args.sweep_dir

    if args.compare:
        print_comparison(sweep_dir, args.compare)
    else:
        print(f"\n{'='*60}")
        print(f"SWEEP: {os.path.basename(sweep_dir)}")
        print(f"{'='*60}")
        print_sweep_table(sweep_dir)

    if args.traces:
        check_thinking_traces(sweep_dir)

    if args.plot:
        print("\nGenerating plots...")
        plot_dir = plot_sweep(sweep_dir, args.output)
        if plot_dir:
            print(f"\nPlots saved to: {plot_dir}")


if __name__ == "__main__":
    main()
