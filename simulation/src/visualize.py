"""Generate figures for Sprint 2 meeting with Debraj (Feb 27).

Plots:
1. Gini trajectory over rounds (per sweep condition, with rep shading)
2. Action distribution over rounds (stacked area)
3. Spatial radius comparison (bar chart: cooperation vs radius)
4. Information 2x2 factorial (grouped bar chart)
5. Reputation 2x2 factorial (grouped bar chart)
6. Action stability over rounds
"""

import json
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data" / "runs"
FIG_DIR = Path(__file__).parent.parent / "data" / "figures"
FIG_DIR.mkdir(exist_ok=True)

# -- Helpers ------------------------------------------------------------------

def load_metrics(run_id: str):
    path = DATA_DIR / f"{run_id}_metrics.json"
    with open(path) as f:
        return json.load(f)


def avg_reps(run_ids: list[str]):
    """Load multiple reps, return per-round averages and per-round lists."""
    all_data = [load_metrics(rid) for rid in run_ids]
    n_rounds = min(len(d) for d in all_data)
    rounds = list(range(1, n_rounds + 1))

    gini_per_round = []
    stability_per_round = []
    actions_per_round = []

    for r_idx in range(n_rounds):
        ginis = [d[r_idx]["gini"] for d in all_data]
        gini_per_round.append(ginis)

        stabs = [d[r_idx].get("action_stability") for d in all_data]
        stabs = [s for s in stabs if s is not None]
        stability_per_round.append(stabs)

        # Merge action distributions
        merged = defaultdict(list)
        for d in all_data:
            dist = d[r_idx]["action_distribution"]
            total = sum(dist.values())
            for act, count in dist.items():
                merged[act].append(count / total * 100 if total > 0 else 0)
        actions_per_round.append(merged)

    return rounds, gini_per_round, stability_per_round, actions_per_round


def mean_std(values_list):
    """Return mean and std arrays from list of lists."""
    means = [np.mean(v) if v else 0 for v in values_list]
    stds = [np.std(v) if len(v) > 1 else 0 for v in values_list]
    return np.array(means), np.array(stds)


ACTION_COLORS = {
    "invest_other": "#2ecc71",
    "arm_self": "#e67e22",
    "attack": "#e74c3c",
    "do_nothing": "#95a5a6",
    "arm_other": "#3498db",
    "invest_self": "#9b59b6",
}

ACTION_ORDER = ["invest_other", "arm_self", "attack", "do_nothing", "arm_other", "invest_self"]


def setup_style():
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
    })


# -- Plot 1: Gini trajectories (spatial radius sweep) -------------------------

def plot_gini_spatial_radius():
    """Gini over rounds for different spatial radii."""
    setup_style()
    fig, ax = plt.subplots(figsize=(8, 5))

    conditions = [
        ("r=1", ["spatial_7x7_r1_rep1", "spatial_7x7_r1_rep2"]),
        ("r=2", ["spatial_7x7_r2_rep1", "spatial_7x7_r2_rep2"]),
        ("r=3", ["spatial_7x7_r3_rep1", "spatial_7x7_r3_rep2"]),
        ("10x10 r=2", ["spatial_10x10_r2_rep1", "spatial_10x10_r2_rep2"]),
    ]

    colors = ["#2ecc71", "#3498db", "#e74c3c", "#9b59b6"]

    for (label, run_ids), color in zip(conditions, colors):
        rounds, gini_lists, _, _ = avg_reps(run_ids)
        means, stds = mean_std(gini_lists)
        ax.plot(rounds, means, "o-", label=label, color=color, linewidth=2, markersize=5)
        ax.fill_between(rounds, means - stds, means + stds, alpha=0.15, color=color)

    ax.set_xlabel("Round")
    ax.set_ylabel("Gini Coefficient")
    ax.set_title("Inequality Over Time by Spatial Radius")
    ax.legend()
    ax.set_ylim(0, 0.8)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    fig.tight_layout()
    fig.savefig(FIG_DIR / "gini_spatial_radius.png", dpi=150)
    plt.close(fig)
    print(f"  Saved gini_spatial_radius.png")


# -- Plot 2: Action distribution over rounds (stacked area) -------------------

def plot_action_trajectory(run_ids, title, filename):
    """Stacked area chart of action distribution over rounds."""
    setup_style()
    fig, ax = plt.subplots(figsize=(8, 5))

    rounds, _, _, actions_per_round = avg_reps(run_ids)

    # Collect all actions present
    all_actions = set()
    for apd in actions_per_round:
        all_actions.update(apd.keys())
    ordered = [a for a in ACTION_ORDER if a in all_actions]

    # Build stacked data
    data = {}
    for act in ordered:
        data[act] = [np.mean(actions_per_round[r].get(act, [0])) for r in range(len(rounds))]

    bottoms = np.zeros(len(rounds))
    for act in ordered:
        vals = np.array(data[act])
        ax.fill_between(rounds, bottoms, bottoms + vals,
                        label=act, color=ACTION_COLORS.get(act, "#666"), alpha=0.8)
        bottoms += vals

    ax.set_xlabel("Round")
    ax.set_ylabel("Action Share (%)")
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_ylim(0, 105)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    fig.tight_layout()
    fig.savefig(FIG_DIR / filename, dpi=150)
    plt.close(fig)
    print(f"  Saved {filename}")


# -- Plot 3: Spatial radius comparison bar chart --------------------------------

def plot_spatial_radius_bars():
    """Bar chart comparing action distributions across spatial radii."""
    setup_style()
    fig, ax = plt.subplots(figsize=(8, 5))

    conditions = [
        ("r=1", ["spatial_7x7_r1_rep1", "spatial_7x7_r1_rep2"]),
        ("r=2", ["spatial_7x7_r2_rep1", "spatial_7x7_r2_rep2"]),
        ("r=3", ["spatial_7x7_r3_rep1", "spatial_7x7_r3_rep2"]),
    ]

    actions_to_show = ["invest_other", "arm_self", "attack", "do_nothing"]
    x = np.arange(len(conditions))
    width = 0.18

    for i, act in enumerate(actions_to_show):
        vals = []
        for label, run_ids in conditions:
            all_data = [load_metrics(rid) for rid in run_ids]
            total_act = 0
            total_all = 0
            for d in all_data:
                for m in d:
                    total_act += m["action_distribution"].get(act, 0)
                    total_all += sum(m["action_distribution"].values())
            vals.append(total_act / total_all * 100 if total_all else 0)
        ax.bar(x + i * width, vals, width, label=act,
               color=ACTION_COLORS.get(act, "#666"))

    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels([c[0] for c in conditions])
    ax.set_ylabel("Action Share (%)")
    ax.set_title("Action Distribution by Spatial Radius (7x7 grid, 10 agents)")
    ax.legend()
    ax.set_ylim(0, 80)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "spatial_radius_bars.png", dpi=150)
    plt.close(fig)
    print(f"  Saved spatial_radius_bars.png")


# -- Plot 4: Information 2x2 factorial -----------------------------------------

def plot_info_factorial():
    """Grouped bar chart for information 2x2 factorial."""
    setup_style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    conditions = [
        ("Hist+Vis", ["info_hist_vis_rep1", "info_hist_vis_rep2"]),
        ("Hist+Hid", ["info_hist_hid_rep1", "info_hist_hid_rep2"]),
        ("NoHist+Vis", ["info_nohist_vis_rep1", "info_nohist_vis_rep2"]),
        ("NoHist+Hid", ["info_nohist_hid_rep1", "info_nohist_hid_rep2"]),
    ]

    # Panel A: Action distribution
    ax = axes[0]
    actions_to_show = ["invest_other", "arm_self", "attack", "do_nothing"]
    x = np.arange(len(conditions))
    width = 0.18

    for i, act in enumerate(actions_to_show):
        vals = []
        for label, run_ids in conditions:
            all_data = [load_metrics(rid) for rid in run_ids]
            total_act = 0
            total_all = 0
            for d in all_data:
                for m in d:
                    total_act += m["action_distribution"].get(act, 0)
                    total_all += sum(m["action_distribution"].values())
            vals.append(total_act / total_all * 100 if total_all else 0)
        ax.bar(x + i * width, vals, width, label=act,
               color=ACTION_COLORS.get(act, "#666"))

    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels([c[0] for c in conditions], fontsize=9)
    ax.set_ylabel("Action Share (%)")
    ax.set_title("A) Action Distribution")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 80)

    # Panel B: Gini trajectory
    ax = axes[1]
    colors = ["#2ecc71", "#e74c3c", "#3498db", "#e67e22"]
    for (label, run_ids), color in zip(conditions, colors):
        rounds, gini_lists, _, _ = avg_reps(run_ids)
        means, stds = mean_std(gini_lists)
        ax.plot(rounds, means, "o-", label=label, color=color, linewidth=2, markersize=4)
        ax.fill_between(rounds, means - stds, means + stds, alpha=0.15, color=color)

    ax.set_xlabel("Round")
    ax.set_ylabel("Gini Coefficient")
    ax.set_title("B) Inequality Over Time")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 0.8)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    fig.suptitle("Information 2x2 Factorial (30 agents, spatial)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "info_factorial.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved info_factorial.png")


# -- Plot 5: Reputation 2x2 factorial ------------------------------------------

def plot_reputation_factorial():
    """Grouped bar chart for reputation 2x2 factorial."""
    setup_style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    conditions = [
        ("Vis+NoRep", ["rep_vis_norep_rep1", "rep_vis_norep_rep2"]),
        ("Vis+Rep", ["rep_vis_rep_rep1", "rep_vis_rep_rep2"]),
        ("Hid+NoRep", ["rep_hid_norep_rep1", "rep_hid_norep_rep2"]),
        ("Hid+Rep", ["rep_hid_rep_rep1", "rep_hid_rep_rep2"]),
    ]

    # Panel A: Action distribution
    ax = axes[0]
    actions_to_show = ["invest_other", "arm_self", "attack", "do_nothing"]
    x = np.arange(len(conditions))
    width = 0.18

    for i, act in enumerate(actions_to_show):
        vals = []
        for label, run_ids in conditions:
            all_data = [load_metrics(rid) for rid in run_ids]
            total_act = 0
            total_all = 0
            for d in all_data:
                for m in d:
                    total_act += m["action_distribution"].get(act, 0)
                    total_all += sum(m["action_distribution"].values())
            vals.append(total_act / total_all * 100 if total_all else 0)
        ax.bar(x + i * width, vals, width, label=act,
               color=ACTION_COLORS.get(act, "#666"))

    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels([c[0] for c in conditions], fontsize=9)
    ax.set_ylabel("Action Share (%)")
    ax.set_title("A) Action Distribution")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 80)

    # Panel B: Gini trajectory
    ax = axes[1]
    colors = ["#2ecc71", "#3498db", "#e74c3c", "#e67e22"]
    for (label, run_ids), color in zip(conditions, colors):
        rounds, gini_lists, _, _ = avg_reps(run_ids)
        means, stds = mean_std(gini_lists)
        ax.plot(rounds, means, "o-", label=label, color=color, linewidth=2, markersize=4)
        ax.fill_between(rounds, means - stds, means + stds, alpha=0.15, color=color)

    ax.set_xlabel("Round")
    ax.set_ylabel("Gini Coefficient")
    ax.set_title("B) Inequality Over Time")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 0.8)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    fig.suptitle("Reputation 2x2 Factorial (30 agents, spatial)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "reputation_factorial.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved reputation_factorial.png")


# -- Plot 6: Action stability over rounds -------------------------------------

def plot_action_stability():
    """Action stability over rounds for a selection of conditions."""
    setup_style()
    fig, ax = plt.subplots(figsize=(8, 5))

    conditions = [
        ("Spatial r=2 (10ag)", ["spatial_7x7_r2_rep1", "spatial_7x7_r2_rep2"]),
        ("Info: Vis+Hist (30ag)", ["info_hist_vis_rep1", "info_hist_vis_rep2"]),
        ("Info: Hid+Hist (30ag)", ["info_hist_hid_rep1", "info_hist_hid_rep2"]),
    ]

    colors = ["#2ecc71", "#3498db", "#e74c3c"]

    for (label, run_ids), color in zip(conditions, colors):
        rounds, _, stab_lists, _ = avg_reps(run_ids)
        # Stability is 0-1 fraction, convert to %. Skip round 1 (None).
        valid_rounds = []
        valid_means = []
        valid_stds = []
        for r, sl in zip(rounds, stab_lists):
            if sl:  # non-empty list (None values already filtered)
                valid_rounds.append(r)
                valid_means.append(np.mean(sl) * 100)
                valid_stds.append(np.std(sl) * 100 if len(sl) > 1 else 0)
        if valid_rounds:
            ms = np.array(valid_means)
            ss = np.array(valid_stds)
            ax.plot(valid_rounds, ms, "o-", label=label, color=color, linewidth=2, markersize=5)
            ax.fill_between(valid_rounds, ms - ss, ms + ss, alpha=0.15, color=color)

    ax.set_xlabel("Round")
    ax.set_ylabel("Action Stability (%)")
    ax.set_title("Action Stability Over Time (% agents repeating previous action)")
    ax.legend()
    ax.set_ylim(0, 100)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    fig.tight_layout()
    fig.savefig(FIG_DIR / "action_stability.png", dpi=150)
    plt.close(fig)
    print(f"  Saved action_stability.png")


# -- Plot 7: Action order comparison -------------------------------------------

def plot_action_order():
    """Bar chart comparing simultaneous vs sequential action order."""
    setup_style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    conditions = [
        ("Simultaneous", ["action_order_simultaneous_rep1", "action_order_simultaneous_rep2", "action_order_simultaneous_rep3"]),
        ("Sequential", ["action_order_sequential_rep1", "action_order_sequential_rep2", "action_order_sequential_rep3"]),
    ]

    # Panel A: Action distribution bars
    ax = axes[0]
    actions_to_show = ["invest_other", "arm_self", "attack", "do_nothing"]
    x = np.arange(len(conditions))
    width = 0.18

    for i, act in enumerate(actions_to_show):
        vals = []
        for label, run_ids in conditions:
            all_data = [load_metrics(rid) for rid in run_ids]
            total_act = 0
            total_all = 0
            for d in all_data:
                for m in d:
                    total_act += m["action_distribution"].get(act, 0)
                    total_all += sum(m["action_distribution"].values())
            vals.append(total_act / total_all * 100 if total_all else 0)
        ax.bar(x + i * width, vals, width, label=act,
               color=ACTION_COLORS.get(act, "#666"))

    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels([c[0] for c in conditions])
    ax.set_ylabel("Action Share (%)")
    ax.set_title("A) Action Distribution")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 70)

    # Panel B: Gini trajectory
    ax = axes[1]
    colors = ["#2ecc71", "#e74c3c"]
    for (label, run_ids), color in zip(conditions, colors):
        rounds, gini_lists, _, _ = avg_reps(run_ids)
        means, stds = mean_std(gini_lists)
        ax.plot(rounds, means, "o-", label=label, color=color, linewidth=2, markersize=5)
        ax.fill_between(rounds, means - stds, means + stds, alpha=0.15, color=color)

    ax.set_xlabel("Round")
    ax.set_ylabel("Gini Coefficient")
    ax.set_title("B) Inequality Over Time")
    ax.legend()
    ax.set_ylim(0, 0.8)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    fig.suptitle("Action Order: Simultaneous vs Sequential (10 agents, spatial)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "action_order.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved action_order.png")


# -- Main ----------------------------------------------------------------------

if __name__ == "__main__":
    print("Generating figures...")

    print("\n1. Gini trajectory by spatial radius")
    plot_gini_spatial_radius()

    print("\n2. Action trajectory (spatial r=2 baseline)")
    plot_action_trajectory(
        ["spatial_7x7_r2_rep1", "spatial_7x7_r2_rep2"],
        "Action Distribution Over Time (spatial r=2, 10 agents)",
        "action_trajectory_spatial_r2.png",
    )

    print("\n3. Spatial radius comparison bars")
    plot_spatial_radius_bars()

    print("\n4. Information 2x2 factorial")
    plot_info_factorial()

    print("\n5. Reputation 2x2 factorial")
    plot_reputation_factorial()

    print("\n6. Action stability over time")
    plot_action_stability()

    print("\n7. Action order comparison")
    plot_action_order()

    print(f"\nAll figures saved to {FIG_DIR}/")
