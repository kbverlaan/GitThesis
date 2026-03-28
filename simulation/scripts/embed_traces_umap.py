#!/usr/bin/env python3
"""
Embed reasoning traces and visualize with UMAP.

Debraj suggestion (Feb 28): embed prompt+response → T×D matrix per run,
UMAP/PCA trajectories → clustering = evidence for distinct reasoning regimes.

Usage:
    python scripts/embed_traces_umap.py <traces.json> [--output plot.png]
    python scripts/embed_traces_umap.py <traces.json> --embed thinking   # chain-of-thought
    python scripts/embed_traces_umap.py <traces.json> --embed response   # action JSON only
    python scripts/embed_traces_umap.py <traces.json> --backend openai   # requires OPENAI_API_KEY

Framing note: reasoning traces are behavioral data, not mechanistic
explanations of internal computation (Turpin et al. 2024, Lanham et al. 2023).
"""

import json
import argparse
import numpy as np
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import umap


# ── Embedding backends ──────────────────────────────────────────────────────

def embed_local(texts: list[str], model_name: str = "nomic-ai/nomic-embed-text-v1.5") -> np.ndarray:
    """Embed with sentence-transformers (local, free).

    Default: nomic-embed-text-v1.5 (8192 token context, 768 dims).
    Nomic requires a task prefix: 'search_document: ' for documents.
    """
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name, trust_remote_code=True)

    # Nomic models require task prefix
    is_nomic = "nomic" in model_name.lower()
    prefix = "search_document: " if is_nomic else ""

    # Use tail of text (conclusion/decision) rather than head (context recap).
    # nomic on CPU: keep to ~2K tokens (6K chars) for feasible runtime.
    # The tail contains the strategic analysis + decision, not the context recap.
    max_chars = 6000 if is_nomic else 2000
    prepared = [prefix + t[-max_chars:] for t in texts]

    embeddings = model.encode(prepared, show_progress_bar=True, batch_size=8)
    return np.array(embeddings)


def embed_openai(texts: list[str], model: str = "text-embedding-3-small") -> np.ndarray:
    """Embed with OpenAI API (requires OPENAI_API_KEY)."""
    import os
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    # text-embedding-3-small: 8191 token limit, ~$0.02/M tokens
    # Truncate to ~30K chars (~8K tokens) per text
    truncated = [t[:30000] for t in texts]
    # Batch in groups of 50
    all_embs = []
    for i in range(0, len(truncated), 50):
        batch = truncated[i:i+50]
        resp = client.embeddings.create(input=batch, model=model)
        all_embs.extend([d.embedding for d in resp.data])
        print(f"  Embedded {min(i+50, len(truncated))}/{len(truncated)}")
    return np.array(all_embs)


# ── Data loading ────────────────────────────────────────────────────────────

def load_traces(path: Path) -> list[dict]:
    """Load traces from _traces.json file.

    Deduplicates retry attempts: keeps only the last (successful) attempt
    per (round, agent_id) pair, and filters out entries with empty responses.
    """
    with open(path) as f:
        data = json.load(f)

    # Keep only the last attempt per (round, agent_id) — retries have higher attempt numbers
    best = {}
    for d in data:
        key = (d.get("round"), d.get("agent_id"))
        resp = d.get("response")
        has_content = resp and str(resp).strip()
        prev = best.get(key)
        if prev is None or has_content:
            best[key] = d

    # Filter: must have thinking or a non-empty response
    valid = [d for d in best.values()
             if (d.get("thinking") or (d.get("response") and str(d["response"]).strip()))]
    valid.sort(key=lambda d: (d["round"], d["agent_id"]))

    n_retries = len(data) - len(best)
    n_empty = len(best) - len(valid)
    print(f"Loaded {len(valid)} traces from {path.name} "
          f"({n_retries} retries removed, {n_empty} empty filtered)")
    return valid


def extract_text(trace: dict, mode: str) -> str:
    """Extract text to embed from a trace entry."""
    if mode == "thinking":
        return trace.get("thinking", "") or trace.get("response", "")
    elif mode == "response":
        return trace.get("response", "")
    elif mode == "prompt_response":
        return (trace.get("prompt", "") + "\n\n" + trace.get("response", ""))
    else:
        raise ValueError(f"Unknown embed mode: {mode}")


def load_executed_actions(traces_path: Path) -> dict[tuple[int, str], str]:
    """Load ground-truth executed actions from the companion _reasoning_live.jsonl.

    Returns dict mapping (round, agent_id) -> action as actually executed by the engine.
    """
    live_path = traces_path.parent / traces_path.name.replace("_traces.json", "_reasoning_live.jsonl")
    if not live_path.exists():
        return {}

    actions = {}
    with open(live_path) as f:
        for line in f:
            rd = json.loads(line)
            r = rd["round"]
            for agent_id, agent_data in rd.get("agents", {}).items():
                action = agent_data.get("action", "unknown")
                actions[(r, agent_id)] = action.lower() if action else "unknown"

    print(f"  Loaded {len(actions)} executed actions from {live_path.name}")
    return actions


def extract_action(trace: dict, executed_actions: dict[tuple[int, str], str] | None = None) -> str:
    """Get the action that was actually executed for this trace.

    Uses the ground-truth from reasoning_live.jsonl (engine-recorded),
    falling back to response JSON parsing only if the live file is unavailable.
    """
    # Ground truth from engine
    if executed_actions:
        key = (trace.get("round"), trace.get("agent_id"))
        action = executed_actions.get(key)
        if action and action != "unknown":
            return action

    # Fallback: parse response JSON
    resp = trace.get("response") or ""
    if resp and "{" in resp:
        try:
            start = resp.index("{")
            end = resp.rindex("}") + 1
            data = json.loads(resp[start:end])
            return data.get("action", "unknown").lower()
        except (json.JSONDecodeError, ValueError):
            pass

    return "unknown"


# ── Plotting ────────────────────────────────────────────────────────────────

def plot_umap(
    embeddings_2d: np.ndarray,
    traces: list[dict],
    output: Path,
    title: str = "Reasoning Trace Embeddings (UMAP)",
    executed_actions: dict[tuple[int, str], str] | None = None,
):
    """Create a multi-panel UMAP plot: by round, by agent, by action, + trajectories."""
    agents = sorted(set(d["agent_id"] for d in traces))
    rounds = np.array([d["round"] for d in traces])
    agent_ids = [d["agent_id"] for d in traces]
    actions = [extract_action(d, executed_actions) for d in traces]

    agent_cmap = plt.cm.tab10
    action_types = sorted(set(actions))
    action_colors = {a: plt.cm.Set2(i / max(len(action_types), 1)) for i, a in enumerate(action_types)}

    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    fig.suptitle(title, fontsize=16, fontweight="bold", y=0.98)

    # ── Panel 1: Color by round (temporal) ──
    ax = axes[0, 0]
    sc = ax.scatter(
        embeddings_2d[:, 0], embeddings_2d[:, 1],
        c=rounds, cmap="viridis", s=30, alpha=0.7, edgecolors="none"
    )
    plt.colorbar(sc, ax=ax, label="Round")
    ax.set_title("By Round (temporal progression)", fontsize=12)
    ax.set_xlabel("UMAP 1")
    ax.set_ylabel("UMAP 2")

    # ── Panel 2: Color by agent ──
    ax = axes[0, 1]
    for i, agent in enumerate(agents):
        mask = [a == agent for a in agent_ids]
        ax.scatter(
            embeddings_2d[mask, 0], embeddings_2d[mask, 1],
            c=[agent_cmap(i / len(agents))], s=30, alpha=0.7,
            label=agent, edgecolors="none"
        )
    ax.legend(fontsize=7, ncol=2, loc="best", framealpha=0.8)
    ax.set_title("By Agent", fontsize=12)
    ax.set_xlabel("UMAP 1")
    ax.set_ylabel("UMAP 2")

    # ── Panel 3: Color by action ──
    ax = axes[1, 0]
    for action in action_types:
        mask = [a == action for a in actions]
        ax.scatter(
            embeddings_2d[mask, 0], embeddings_2d[mask, 1],
            c=[action_colors[action]], s=30, alpha=0.7,
            label=action, edgecolors="none"
        )
    ax.legend(fontsize=9, loc="best", framealpha=0.8)
    ax.set_title("By Action", fontsize=12)
    ax.set_xlabel("UMAP 1")
    ax.set_ylabel("UMAP 2")

    # ── Panel 4: Agent trajectories (lines connecting rounds) ──
    ax = axes[1, 1]
    for i, agent in enumerate(agents):
        idxs = [j for j, a in enumerate(agent_ids) if a == agent]
        # Sort by round
        idxs = sorted(idxs, key=lambda j: traces[j]["round"])
        if len(idxs) < 2:
            continue
        points = embeddings_2d[idxs]
        # Draw trajectory with fading alpha
        segments = np.array([[points[k], points[k+1]] for k in range(len(points)-1)])
        alphas = np.linspace(0.2, 0.9, len(segments))
        color = agent_cmap(i / len(agents))
        for seg, alpha in zip(segments, alphas):
            ax.plot(seg[:, 0], seg[:, 1], color=color, alpha=alpha, linewidth=1.0)
        # Mark start and end
        ax.scatter(points[0, 0], points[0, 1], c=[color], s=80, marker="o",
                   edgecolors="black", linewidths=0.8, zorder=5)
        ax.scatter(points[-1, 0], points[-1, 1], c=[color], s=80, marker="X",
                   edgecolors="black", linewidths=0.8, zorder=5, label=agent)
    ax.legend(fontsize=7, ncol=2, loc="best", framealpha=0.8)
    ax.set_title("Agent Trajectories (○ = start, ✕ = end)", fontsize=12)
    ax.set_xlabel("UMAP 1")
    ax.set_ylabel("UMAP 2")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(output, dpi=200, bbox_inches="tight")
    print(f"Saved plot to {output}")
    plt.close(fig)

    # Also save embeddings for reproducibility
    emb_path = output.with_suffix(".npz")
    np.savez_compressed(
        emb_path,
        embeddings_2d=embeddings_2d,
        rounds=rounds,
        agents=np.array(agent_ids),
        actions=np.array(actions),
    )
    print(f"Saved embeddings to {emb_path}")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Embed reasoning traces → UMAP plot")
    parser.add_argument("traces", type=Path, help="Path to _traces.json file")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Output plot path (default: same dir as traces)")
    parser.add_argument("--embed", choices=["thinking", "response", "prompt_response"],
                        default="thinking",
                        help="Which text to embed (default: thinking = chain-of-thought)")
    parser.add_argument("--backend", choices=["local", "openai"], default="local",
                        help="Embedding backend (default: local sentence-transformers)")
    parser.add_argument("--n-neighbors", type=int, default=15,
                        help="UMAP n_neighbors (default: 15)")
    parser.add_argument("--min-dist", type=float, default=0.1,
                        help="UMAP min_dist (default: 0.1)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Load
    traces = load_traces(args.traces)
    if not traces:
        print("No valid traces found.")
        return

    # Extract text
    texts = [extract_text(t, args.embed) for t in traces]
    print(f"Embedding {len(texts)} traces (mode={args.embed}, backend={args.backend})")
    print(f"  Avg text length: {np.mean([len(t) for t in texts]):.0f} chars")

    # Embed
    if args.backend == "openai":
        embeddings = embed_openai(texts)
    else:
        embeddings = embed_local(texts)
    print(f"  Embedding shape: {embeddings.shape}")

    # UMAP
    print(f"Running UMAP (n_neighbors={args.n_neighbors}, min_dist={args.min_dist})")
    reducer = umap.UMAP(
        n_neighbors=args.n_neighbors,
        min_dist=args.min_dist,
        n_components=2,
        metric="cosine",
        random_state=args.seed,
    )
    embeddings_2d = reducer.fit_transform(embeddings)

    # Load ground-truth actions from reasoning_live.jsonl
    executed_actions = load_executed_actions(args.traces)

    # Plot
    output = args.output or args.traces.parent / f"umap_{args.embed}.png"
    run_name = args.traces.stem.replace("_traces", "")
    plot_umap(
        embeddings_2d, traces, output,
        title=f"Reasoning Trace Embeddings — {run_name} ({args.embed})",
        executed_actions=executed_actions,
    )


if __name__ == "__main__":
    main()
