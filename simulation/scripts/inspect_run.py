#!/usr/bin/env python3
"""
Inspect a single run: per-round action table, resource dynamics, trace samples.

Usage:
    python scripts/inspect_run.py data/runs/qwen_sweep_conflict_cost/conflict_cost_pct_2_reasoning_level_level3_rep1
    python scripts/inspect_run.py <run_prefix> --thinking     # show thinking trace samples
    python scripts/inspect_run.py <run_prefix> --agent agent_1 # focus on one agent
"""
import json
import os
import sys
import argparse
from collections import defaultdict


def load_run_files(run_prefix):
    """Load all files for a run given the prefix (without _metrics.json etc)."""
    data = {}
    for suffix in ["metrics", "history", "traces", "meta", "network"]:
        path = f"{run_prefix}_{suffix}.json"
        if os.path.exists(path):
            with open(path) as f:
                data[suffix] = json.load(f)
    return data


def print_round_table(metrics):
    """Print per-round action distribution table."""
    if not metrics:
        print("No metrics data.")
        return

    # Collect all action types
    all_actions = set()
    for r in metrics:
        all_actions.update(r.get("action_distribution", {}).keys())
    action_cols = sorted(all_actions)

    # Header
    act_header = "".join(f"{a:>14}" for a in action_cols)
    print(f"\n{'Round':>5} {act_header} {'Gini':>8} {'Palma':>8}")
    print("-" * (5 + 14 * len(action_cols) + 16))

    for r in metrics:
        rnd = r.get("round", "?")
        dist = r.get("action_distribution", {})
        total = sum(dist.values())
        gini = r.get("gini", 0)
        palma = r.get("palma", 0)

        acts = ""
        for a in action_cols:
            cnt = dist.get(a, 0)
            pct = cnt / total * 100 if total else 0
            acts += f"{cnt:>6} ({pct:4.0f}%)"

        print(f"{rnd:>5} {acts} {gini:>8.3f} {palma:>8.2f}")

    # Summary row
    total_actions = defaultdict(int)
    for r in metrics:
        for act, cnt in r.get("action_distribution", {}).items():
            total_actions[act] += cnt
    grand_total = sum(total_actions.values())
    acts_total = ""
    for a in action_cols:
        cnt = total_actions.get(a, 0)
        pct = cnt / grand_total * 100 if grand_total else 0
        acts_total += f"{cnt:>6} ({pct:4.0f}%)"

    final_gini = metrics[-1].get("gini", 0) if metrics else 0
    print("-" * (5 + 14 * len(action_cols) + 16))
    print(f"{'TOTAL':>5} {acts_total} {final_gini:>8.3f}")
    print()


def print_resource_table(metrics):
    """Print resource evolution per agent."""
    if not metrics or "resources" not in metrics[0]:
        return

    agents = sorted(metrics[0]["resources"].keys())
    print(f"\n{'Round':>5}" + "".join(f"{a:>10}" for a in agents))
    print("-" * (5 + 10 * len(agents)))

    for r in metrics:
        rnd = r.get("round", "?")
        res = r.get("resources", {})
        vals = "".join(f"{res.get(a, 0):>10.1f}" for a in agents)
        print(f"{rnd:>5}{vals}")
    print()


def print_thinking_samples(traces, n=3, agent_filter=None, action_filter=None):
    """Show thinking trace samples."""
    if not traces:
        print("No traces data.")
        return

    print(f"\n--- Thinking Trace Samples ---\n")

    candidates = []
    for t in traces:
        thinking = t.get("thinking") or ""
        if len(thinking) < 100:
            continue
        if agent_filter and t.get("agent_id") != agent_filter:
            continue
        resp = t.get("response") or ""
        if action_filter and action_filter not in resp:
            continue
        candidates.append(t)

    if not candidates:
        print("No traces with substantial thinking found.")
        if action_filter:
            print(f"  (filtered for action: {action_filter})")
        return

    # Pick diverse samples: early, mid, late
    if len(candidates) >= 3:
        samples = [candidates[0], candidates[len(candidates)//2], candidates[-1]]
    else:
        samples = candidates[:n]

    for t in samples:
        rnd = t.get("round", "?")
        aid = t.get("agent_id", "?")
        thinking = t.get("thinking") or ""
        resp = t.get("response") or ""
        latency = t.get("latency_s", 0)
        usage = t.get("usage", {})
        tokens = usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0

        print(f"=== Round {rnd}, {aid} ({latency:.0f}s, {tokens} tokens) ===")
        # Show first 1500 chars and last 500 chars
        if len(thinking) > 2500:
            print(thinking[:1500])
            print(f"\n  ... ({len(thinking) - 2000} chars omitted) ...\n")
            print(thinking[-500:])
        else:
            print(thinking)
        print(f"\nRESPONSE: {resp[:200]}")
        print()


def print_agent_timeline(traces, agent_id):
    """Show one agent's actions across all rounds."""
    if not traces:
        return

    print(f"\n--- Timeline for {agent_id} ---\n")
    agent_traces = [t for t in traces if t.get("agent_id") == agent_id]

    for t in agent_traces:
        rnd = t.get("round", "?")
        resp = t.get("response") or ""
        thinking = t.get("thinking") or ""
        # Extract action from response
        try:
            action_data = json.loads(resp.strip())
            action = action_data.get("action", "?")
            target = action_data.get("target", "")
        except (json.JSONDecodeError, AttributeError):
            action = "parse_error"
            target = ""

        target_str = f" → {target}" if target else ""
        thinking_len = len(thinking)
        attempt = t.get("attempt", 1)
        retry = f" (retry {attempt})" if attempt > 1 else ""

        print(f"  R{rnd:>2}: {action:<14}{target_str:<12} | thinking={thinking_len:>5} chars{retry}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Inspect a single simulation run")
    parser.add_argument("run_prefix", help="Run prefix (path without _metrics.json)")
    parser.add_argument("--thinking", action="store_true", help="Show thinking trace samples")
    parser.add_argument("--agent", help="Focus on specific agent (e.g., agent_1)")
    parser.add_argument("--action", help="Filter traces by action (e.g., invest_other)")
    parser.add_argument("--resources", action="store_true", help="Show resource table")
    args = parser.parse_args()

    data = load_run_files(args.run_prefix)

    if not data:
        print(f"No files found for prefix: {args.run_prefix}")
        sys.exit(1)

    run_name = os.path.basename(args.run_prefix)
    print(f"\n{'='*60}")
    print(f"RUN: {run_name}")
    print(f"{'='*60}")

    # Meta info
    if "meta" in data:
        meta = data["meta"]
        if isinstance(meta, dict):
            print(f"  Model: {meta.get('model', '?')}")
            print(f"  Config: {json.dumps({k: v for k, v in meta.items() if k not in ('model', 'run_id')}, indent=None)[:200]}")

    # Round-by-round table
    if "metrics" in data:
        print_round_table(data["metrics"])

    # Resource table
    if args.resources and "metrics" in data:
        print_resource_table(data["metrics"])

    # Agent timeline
    if args.agent and "traces" in data:
        print_agent_timeline(data["traces"], args.agent)

    # Thinking samples
    if args.thinking and "traces" in data:
        print_thinking_samples(
            data["traces"],
            agent_filter=args.agent,
            action_filter=args.action,
        )


if __name__ == "__main__":
    main()
