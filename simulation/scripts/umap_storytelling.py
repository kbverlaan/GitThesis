#!/usr/bin/env python3
"""
Storytelling UMAP visualizations for reasoning traces.

Builds on embed_traces_umap.py — loads pre-computed embeddings (.npz)
and generates publication-quality plots.

Usage:
    # First generate embeddings:
    python scripts/embed_traces_umap.py data/showcase/L3_baseline_100res_25r_traces.json --embed thinking

    # Then generate storytelling plots:
    python scripts/umap_storytelling.py data/showcase/umap_thinking.npz data/showcase/L3_baseline_100res_25r_reasoning_live.jsonl
"""

import json
import argparse
import numpy as np
from pathlib import Path
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import FancyArrowPatch
from scipy.ndimage import gaussian_filter


# ── Agent classification ────────────────────────────────────────────────────

def classify_agents(live_path: Path) -> dict:
    """Classify agents into archetypes based on behavior."""
    with open(live_path) as f:
        rounds_data = [json.loads(line) for line in f]

    agent_attacks = Counter()
    first_attack = {}
    final_resources = {}

    for rd in rounds_data:
        for agent, d in rd["agents"].items():
            if d["action"] == "attack":
                agent_attacks[agent] += 1
                if agent not in first_attack:
                    first_attack[agent] = rd["round"]
        if rd["round"] == max(r["round"] for r in rounds_data):
            for agent, d in rd["agents"].items():
                final_resources[agent] = d["resources"]

    archetypes = {}
    for agent in final_resources:
        atk = agent_attacks[agent]
        if atk >= 5:
            archetypes[agent] = "predator"
        elif atk >= 2:
            archetypes[agent] = "mixed"
        else:
            archetypes[agent] = "cooperator"

    return archetypes, final_resources, first_attack


# ── Plot 1: Phase density contours ─────────────────────────────────────────

def plot_density_phases(emb2d, rounds, output, title=""):
    """Concentration map: KDE contours per game phase showing drift."""
    phases = {
        "R1-6: Cooperation": (1, 6),
        "R7-12: First attacks": (7, 12),
        "R13-18: Stratification": (13, 18),
        "R19-25: Endgame": (19, 25),
    }
    colors = ["#2166ac", "#66c2a5", "#fdae61", "#d73027"]

    fig, ax = plt.subplots(figsize=(10, 8))

    x_range = (emb2d[:, 0].min() - 1, emb2d[:, 0].max() + 1)
    y_range = (emb2d[:, 1].min() - 1, emb2d[:, 1].max() + 1)

    centroids = []
    for (label, (r_min, r_max)), color in zip(phases.items(), colors):
        mask = (rounds >= r_min) & (rounds <= r_max)
        pts = emb2d[mask]

        # KDE on grid
        xbins = np.linspace(*x_range, 80)
        ybins = np.linspace(*y_range, 80)
        H, xedges, yedges = np.histogram2d(pts[:, 0], pts[:, 1], bins=[xbins, ybins])
        H = gaussian_filter(H.T, sigma=2.0)

        # Contours
        levels = np.percentile(H[H > 0], [30, 60, 90]) if H.max() > 0 else [0.1]
        ax.contour(
            xedges[:-1], yedges[:-1], H,
            levels=levels, colors=[color], linewidths=[0.8, 1.2, 1.8],
            alpha=0.9
        )
        ax.contourf(
            xedges[:-1], yedges[:-1], H,
            levels=[levels[0], H.max()], colors=[color], alpha=0.12
        )

        # Centroid
        cx, cy = pts.mean(axis=0)
        centroids.append((cx, cy, label, color))
        ax.scatter(cx, cy, c=color, s=120, marker="D", edgecolors="black",
                   linewidths=1.2, zorder=10)

    # Arrows between centroids
    for i in range(len(centroids) - 1):
        ax.annotate(
            "", xy=(centroids[i+1][0], centroids[i+1][1]),
            xytext=(centroids[i][0], centroids[i][1]),
            arrowprops=dict(arrowstyle="->", lw=2.0, color="#333333", alpha=0.7),
        )

    # Legend
    for cx, cy, label, color in centroids:
        ax.annotate(label, (cx, cy), fontsize=9, fontweight="bold",
                    xytext=(8, 8), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.3))

    ax.set_xlabel("UMAP 1", fontsize=12)
    ax.set_ylabel("UMAP 2", fontsize=12)
    ax.set_title(title or "Reasoning Regime Drift Over Game Phases", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.15)

    fig.tight_layout()
    fig.savefig(output, dpi=200, bbox_inches="tight")
    print(f"Saved: {output}")
    plt.close(fig)


# ── Plot 2: Archetype split ────────────────────────────────────────────────

def plot_archetype_density(emb2d, rounds, agents, archetypes, output, title=""):
    """Side-by-side density maps for predators vs cooperators."""
    arch_config = {
        "predator": {"color": "#d73027", "label": "Predators (≥5 attacks)"},
        "cooperator": {"color": "#2166ac", "label": "Cooperators (0-1 attacks)"},
        "mixed": {"color": "#fdae61", "label": "Mixed (2-4 attacks)"},
    }

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle(title or "Reasoning Regimes by Player Archetype", fontsize=14, fontweight="bold")

    x_range = (emb2d[:, 0].min() - 1, emb2d[:, 0].max() + 1)
    y_range = (emb2d[:, 1].min() - 1, emb2d[:, 1].max() + 1)
    xbins = np.linspace(*x_range, 80)
    ybins = np.linspace(*y_range, 80)

    phase_colors = ["#2166ac", "#66c2a5", "#fdae61", "#d73027"]
    phase_bounds = [(1, 6), (7, 12), (13, 18), (19, 25)]
    phase_labels = ["R1-6", "R7-12", "R13-18", "R19-25"]

    for ax, arch_type in zip(axes, ["predator", "cooperator", "mixed"]):
        cfg = arch_config[arch_type]
        arch_agents = [a for a, t in archetypes.items() if t == arch_type]
        mask = np.array([a in arch_agents for a in agents])

        if mask.sum() == 0:
            ax.set_title(f"{cfg['label']}\n(no agents)")
            continue

        # Background: all points in grey
        ax.scatter(emb2d[:, 0], emb2d[:, 1], c="#dddddd", s=10, alpha=0.3, zorder=1)

        # Phase centroids for this archetype
        for (r_min, r_max), pc, pl in zip(phase_bounds, phase_colors, phase_labels):
            phase_mask = mask & (rounds >= r_min) & (rounds <= r_max)
            pts = emb2d[phase_mask]
            if len(pts) < 2:
                continue

            # Scatter
            ax.scatter(pts[:, 0], pts[:, 1], c=pc, s=30, alpha=0.6, edgecolors="none", zorder=3)

            # Centroid
            cx, cy = pts.mean(axis=0)
            ax.scatter(cx, cy, c=pc, s=100, marker="D", edgecolors="black",
                       linewidths=1, zorder=5)
            ax.annotate(pl, (cx, cy), fontsize=8, fontweight="bold",
                        xytext=(5, 5), textcoords="offset points",
                        bbox=dict(boxstyle="round,pad=0.2", facecolor=pc, alpha=0.3))

        # Individual trajectories
        for agent in arch_agents:
            agent_mask = np.array([a == agent for a in agents])
            idxs = np.where(agent_mask)[0]
            agent_rounds = rounds[idxs]
            order = np.argsort(agent_rounds)
            pts = emb2d[idxs[order]]
            ax.plot(pts[:, 0], pts[:, 1], color=cfg["color"], alpha=0.15, linewidth=0.8, zorder=2)

        n_agents = len(arch_agents)
        ax.set_title(f"{cfg['label']}\n({', '.join(arch_agents)})", fontsize=11)
        ax.set_xlabel("UMAP 1")
        ax.set_ylabel("UMAP 2")
        ax.grid(True, alpha=0.15)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(output, dpi=200, bbox_inches="tight")
    print(f"Saved: {output}")
    plt.close(fig)


# ── Plot 3: Centroid trajectory with confidence ellipses ────────────────────

def plot_centroid_trajectory(emb2d, rounds, agents, archetypes, output, title=""):
    """Single clean plot: per-round centroids with confidence ellipses per archetype."""
    from matplotlib.patches import Ellipse

    arch_config = {
        "predator": {"color": "#d73027", "marker": "^", "label": "Predators"},
        "cooperator": {"color": "#2166ac", "marker": "o", "label": "Cooperators"},
        "mixed": {"color": "#fdae61", "marker": "s", "label": "Mixed"},
    }

    fig, ax = plt.subplots(figsize=(10, 8))

    unique_rounds = sorted(set(rounds))

    for arch_type, cfg in arch_config.items():
        arch_agents = [a for a, t in archetypes.items() if t == arch_type]
        mask = np.array([a in arch_agents for a in agents])
        if mask.sum() == 0:
            continue

        centroids = []
        for r in unique_rounds:
            r_mask = mask & (rounds == r)
            if r_mask.sum() > 0:
                pts = emb2d[r_mask]
                centroids.append((r, pts.mean(axis=0), pts.std(axis=0)))

        if not centroids:
            continue

        # Plot trajectory line
        cx = [c[1][0] for c in centroids]
        cy = [c[1][1] for c in centroids]
        rs = [c[0] for c in centroids]

        ax.plot(cx, cy, color=cfg["color"], linewidth=2.0, alpha=0.7, zorder=3)

        # Plot round markers with size scaling
        for r, (mx, my), (sx, sy) in centroids:
            alpha = 0.3 + 0.7 * (r / max(unique_rounds))
            size = 30 + 60 * (r / max(unique_rounds))
            ax.scatter(mx, my, c=cfg["color"], s=size, marker=cfg["marker"],
                       alpha=alpha, edgecolors="black", linewidths=0.5, zorder=4)

        # Label start and end
        ax.annotate(f"R{rs[0]}", (cx[0], cy[0]), fontsize=8,
                    xytext=(-15, -15), textcoords="offset points",
                    color=cfg["color"], fontweight="bold")
        ax.annotate(f"R{rs[-1]}", (cx[-1], cy[-1]), fontsize=8,
                    xytext=(8, 8), textcoords="offset points",
                    color=cfg["color"], fontweight="bold")

    # Legend
    from matplotlib.lines import Line2D
    handles = []
    for arch_type, cfg in arch_config.items():
        handles.append(Line2D([0], [0], color=cfg["color"], marker=cfg["marker"],
                              linewidth=2, markersize=8, label=cfg["label"]))
    ax.legend(handles=handles, fontsize=11, loc="best", framealpha=0.9)

    ax.set_xlabel("UMAP 1", fontsize=12)
    ax.set_ylabel("UMAP 2", fontsize=12)
    ax.set_title(title or "Reasoning Trajectory by Archetype (per-round centroids)", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.15)

    fig.tight_layout()
    fig.savefig(output, dpi=200, bbox_inches="tight")
    print(f"Saved: {output}")
    plt.close(fig)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Storytelling UMAP visualizations")
    parser.add_argument("npz", type=Path, help="Pre-computed embeddings (.npz)")
    parser.add_argument("live", type=Path, help="reasoning_live.jsonl file")
    parser.add_argument("--output-dir", "-o", type=Path, default=None)
    parser.add_argument("--plots", nargs="+",
                        choices=["density", "archetypes", "centroids", "all"],
                        default=["all"])
    args = parser.parse_args()

    # Load
    data = np.load(args.npz, allow_pickle=True)
    emb2d = data["embeddings_2d"]
    rounds = data["rounds"]
    agents = list(data["agents"])

    archetypes, final_resources, first_attack = classify_agents(args.live)

    out_dir = args.output_dir or args.npz.parent
    plots = args.plots if "all" not in args.plots else ["density", "archetypes", "centroids"]

    run_name = args.npz.stem.replace("umap_", "")

    if "density" in plots:
        plot_density_phases(
            emb2d, rounds,
            out_dir / "story_density_phases.png",
            title=f"Reasoning Regime Drift — {run_name}"
        )

    if "archetypes" in plots:
        plot_archetype_density(
            emb2d, rounds, agents, archetypes,
            out_dir / "story_archetypes.png",
            title=f"Reasoning by Player Archetype — {run_name}"
        )

    if "centroids" in plots:
        plot_centroid_trajectory(
            emb2d, rounds, agents, archetypes,
            out_dir / "story_centroid_trajectory.png",
            title=f"Reasoning Trajectory by Archetype — {run_name}"
        )


if __name__ == "__main__":
    main()
