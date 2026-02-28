"""
Reasoning trace analysis for Gemma 2 27B runs (Step 4).

Analyzes LLM reasoning traces to determine whether reasoning language
is epiphenomenal or systematically related to emergent outcomes.

Usage:
    python -m src.analysis.trace_analysis [--data-dir PATH] [--output-dir PATH]
"""

import json
import os
import re
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional, Tuple

from .arch_analysis import load_all_runs, DATA_DIR_DEFAULT, OUTPUT_DIR_DEFAULT, FRAMINGS


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STOPWORDS = frozenset({
    "that", "this", "with", "from", "have", "will", "they", "their", "them",
    "been", "more", "also", "other", "which", "would", "could", "should",
    "being", "each", "some", "into", "about", "than", "very", "most", "only",
    "over", "just", "make", "like", "does", "made", "after", "before", "while",
    "when", "what", "your", "there", "since", "still", "given", "based", "well",
    "much", "want", "round", "currently", "agent", "agents", "nearby",
    "resources", "resource", "need", "keep", "might", "take", "help",
    "good", "best", "sure", "time", "look", "seem", "seems", "many",
    "then", "next", "same", "back", "come", "know", "think",
})

MIN_WORD_LENGTH = 4


# ---------------------------------------------------------------------------
# Trace parsing
# ---------------------------------------------------------------------------

def parse_trace_response(response: str) -> Optional[Dict]:
    """Extract action and reasoning from a trace response JSON."""
    if not response or "{" not in response:
        return None
    try:
        start = response.index("{")
        end = response.rindex("}") + 1
        data = json.loads(response[start:end])
        action = data.get("action", "")
        reasoning = data.get("reasoning", "")
        target = data.get("target", None)
        if action:
            return {"action": action, "reasoning": reasoning, "target": target}
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def extract_words(text: str) -> List[str]:
    """Extract meaningful words from reasoning text."""
    words = re.findall(r"\b[a-z]{" + str(MIN_WORD_LENGTH) + r",}\b", text.lower())
    return [w for w in words if w not in STOPWORDS]


def load_traces_for_run(run_id: str, data_dir: Path) -> List[Dict]:
    """Load and parse all traces for a single run."""
    trace_file = data_dir / f"{run_id}_traces.json"
    if not trace_file.exists():
        return []

    with open(trace_file) as f:
        raw_traces = json.load(f)

    parsed = []
    for entry in raw_traces:
        result = parse_trace_response(entry.get("response", ""))
        if result:
            result["round"] = entry.get("round", -1)
            result["agent_id"] = entry.get("agent_id", "")
            parsed.append(result)

    return parsed


# ---------------------------------------------------------------------------
# Step 4.1: Per-framing keyword analysis
# ---------------------------------------------------------------------------

def keywords_per_framing(df: pd.DataFrame, data_dir: Path,
                         top_n: int = 20) -> Dict[str, Dict]:
    """Compute top reasoning keywords per framing.

    Returns dict mapping framing -> {
        "total_traces": int,
        "top_keywords": [(word, count), ...],
        "keywords_by_action": {action: [(word, count), ...]},
    }
    """
    results = {}

    for framing in FRAMINGS:
        sub = df[df["framing"] == framing]
        all_words = Counter()
        words_by_action = {}
        total_traces = 0

        for _, row in sub.iterrows():
            traces = load_traces_for_run(row["run_id"], data_dir)
            for t in traces:
                total_traces += 1
                words = extract_words(t["reasoning"])
                all_words.update(words)

                action = t["action"]
                if action not in words_by_action:
                    words_by_action[action] = Counter()
                words_by_action[action].update(words)

        results[framing] = {
            "total_traces": total_traces,
            "top_keywords": all_words.most_common(top_n),
            "keywords_by_action": {
                act: counter.most_common(top_n)
                for act, counter in words_by_action.items()
            },
        }

    return results


# ---------------------------------------------------------------------------
# Step 4.2 & 4.3: High vs low Gini outcome analysis
# ---------------------------------------------------------------------------

def outcome_split_analysis(df: pd.DataFrame, data_dir: Path,
                           top_n: int = 20,
                           max_runs_per_group: int = 10) -> Dict[str, Dict]:
    """Split runs into high/low Gini within each framing and compare reasoning.

    Returns dict mapping framing -> {
        "median_gini": float,
        "low_gini": {...},   # group stats
        "high_gini": {...},  # group stats
        "differential_words": [(word, diff, low_count, high_count), ...],
    }
    """
    results = {}

    for framing in FRAMINGS:
        sub = df[df["framing"] == framing].dropna(subset=["final_gini"])
        if len(sub) < 4:
            continue

        median_gini = sub["final_gini"].median()
        low_runs = sub[sub["final_gini"] <= median_gini]
        high_runs = sub[sub["final_gini"] > median_gini]

        low_stats = _analyze_group(low_runs, data_dir, max_runs_per_group, top_n)
        high_stats = _analyze_group(high_runs, data_dir, max_runs_per_group, top_n)

        # Differential words
        diff_words = _compute_differential_words(
            low_stats["word_counts"], high_stats["word_counts"],
            min_freq=20
        )

        results[framing] = {
            "median_gini": float(median_gini),
            "low_gini": {
                "n_runs": len(low_runs),
                "gini_range": [float(low_runs["final_gini"].min()),
                               float(low_runs["final_gini"].max())],
                "action_distribution": low_stats["action_dist"],
                "top_keywords": low_stats["top_keywords"],
                "total_traces": low_stats["total_traces"],
            },
            "high_gini": {
                "n_runs": len(high_runs),
                "gini_range": [float(high_runs["final_gini"].min()),
                               float(high_runs["final_gini"].max())],
                "action_distribution": high_stats["action_dist"],
                "top_keywords": high_stats["top_keywords"],
                "total_traces": high_stats["total_traces"],
            },
            "differential_words": diff_words,
        }

    return results


# ---------------------------------------------------------------------------
# Step 4.4: Action-level reasoning comparison
# ---------------------------------------------------------------------------

def action_level_reasoning(df: pd.DataFrame, data_dir: Path,
                           top_n: int = 15,
                           max_runs_per_group: int = 10) -> Dict[str, Dict]:
    """Compare reasoning for the same action in high vs low Gini runs.

    For each framing, for each action type, compare the reasoning
    vocabulary when that action is chosen in high vs low Gini runs.
    """
    results = {}

    for framing in FRAMINGS:
        sub = df[df["framing"] == framing].dropna(subset=["final_gini"])
        if len(sub) < 4:
            continue

        median_gini = sub["final_gini"].median()
        low_runs = sub[sub["final_gini"] <= median_gini].head(max_runs_per_group)
        high_runs = sub[sub["final_gini"] > median_gini].head(max_runs_per_group)

        action_comparison = {}

        for label, group in [("low_gini", low_runs), ("high_gini", high_runs)]:
            words_by_action = {}
            for _, row in group.iterrows():
                traces = load_traces_for_run(row["run_id"], data_dir)
                for t in traces:
                    action = t["action"]
                    if action not in words_by_action:
                        words_by_action[action] = Counter()
                    words_by_action[action].update(extract_words(t["reasoning"]))

            for action, counter in words_by_action.items():
                if action not in action_comparison:
                    action_comparison[action] = {}
                action_comparison[action][label] = counter

        # Compute differential per action
        framing_results = {}
        for action, groups in action_comparison.items():
            low_words = groups.get("low_gini", Counter())
            high_words = groups.get("high_gini", Counter())
            diff = _compute_differential_words(low_words, high_words, min_freq=10)
            framing_results[action] = {
                "low_gini_top": low_words.most_common(top_n),
                "high_gini_top": high_words.most_common(top_n),
                "differential": diff,
            }

        results[framing] = framing_results

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _analyze_group(group_df: pd.DataFrame, data_dir: Path,
                   max_runs: int, top_n: int) -> Dict:
    """Analyze traces for a group of runs."""
    action_counts = Counter()
    word_counts = Counter()
    total_traces = 0

    for _, row in group_df.head(max_runs).iterrows():
        traces = load_traces_for_run(row["run_id"], data_dir)
        for t in traces:
            action_counts[t["action"]] += 1
            word_counts.update(extract_words(t["reasoning"]))
            total_traces += 1

    total = sum(action_counts.values()) or 1
    action_dist = {act: count / total for act, count in action_counts.items()}

    return {
        "action_dist": action_dist,
        "word_counts": word_counts,
        "top_keywords": word_counts.most_common(top_n),
        "total_traces": total_traces,
    }


def _compute_differential_words(low_words: Counter, high_words: Counter,
                                min_freq: int = 20,
                                top_n: int = 10) -> Dict:
    """Compute words that differentiate low vs high Gini groups.

    Returns dict with 'more_in_low' and 'more_in_high' lists.
    Each entry: (word, diff, low_count, high_count).
    """
    low_total = sum(low_words.values()) or 1
    high_total = sum(high_words.values()) or 1

    all_words = set(low_words.keys()) | set(high_words.keys())
    diffs = []

    for word in all_words:
        lc = low_words.get(word, 0)
        hc = high_words.get(word, 0)
        if lc + hc < min_freq:
            continue
        low_pct = lc / low_total
        high_pct = hc / high_total
        diffs.append((word, low_pct - high_pct, lc, hc))

    diffs.sort(key=lambda x: x[1], reverse=True)

    return {
        "more_in_low": [(w, float(d), lc, hc) for w, d, lc, hc in diffs[:top_n]],
        "more_in_high": [(w, float(d), lc, hc) for w, d, lc, hc in diffs[-top_n:]],
    }


def print_trace_summary(keywords: Dict, outcomes: Dict, action_level: Dict):
    """Print human-readable trace analysis summary."""
    sep = "=" * 70

    print(f"\n{sep}")
    print("REASONING TRACE ANALYSIS")
    print(sep)

    # Keywords per framing
    print(f"\n--- TOP KEYWORDS PER FRAMING ---")
    for framing in FRAMINGS:
        if framing not in keywords:
            continue
        kw = keywords[framing]
        top = ", ".join(f"{w}({c})" for w, c in kw["top_keywords"][:10])
        print(f"\n  {framing} (n={kw['total_traces']} traces):")
        print(f"    {top}")

    # Outcome split
    print(f"\n--- HIGH vs LOW GINI COMPARISON ---")
    for framing in FRAMINGS:
        if framing not in outcomes:
            continue
        o = outcomes[framing]
        print(f"\n  {framing} (median Gini: {o['median_gini']:.4f}):")

        for label in ["low_gini", "high_gini"]:
            g = o[label]
            top_actions = sorted(g["action_distribution"].items(),
                                 key=lambda x: x[1], reverse=True)[:4]
            acts_str = ", ".join(f"{a}={v*100:.1f}%" for a, v in top_actions)
            print(f"    {label} (n={g['n_runs']}, Gini {g['gini_range'][0]:.3f}-{g['gini_range'][1]:.3f}): {acts_str}")

        diff = o["differential_words"]
        if diff["more_in_low"]:
            words_low = ", ".join(f"{w}(+{d:.4f})" for w, d, _, _ in diff["more_in_low"][:5])
            print(f"    Words → low Gini: {words_low}")
        if diff["more_in_high"]:
            words_high = ", ".join(f"{w}({d:.4f})" for w, d, _, _ in diff["more_in_high"][:5])
            print(f"    Words → high Gini: {words_high}")

    # Action-level comparison (just show invest_other for each framing)
    print(f"\n--- ACTION-LEVEL REASONING (invest_other) ---")
    for framing in FRAMINGS:
        if framing not in action_level or "invest_other" not in action_level[framing]:
            continue
        al = action_level[framing]["invest_other"]
        if al["differential"]:
            low_w = ", ".join(f"{w}" for w, _, _, _ in al["differential"]["more_in_low"][:5])
            high_w = ", ".join(f"{w}" for w, _, _, _ in al["differential"]["more_in_high"][:5])
            print(f"  {framing}:")
            print(f"    invest_other → low Gini vocab: {low_w}")
            print(f"    invest_other → high Gini vocab: {high_w}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_trace_analysis(data_dir: Path = None,
                       output_dir: Path = None) -> Tuple[Dict, Dict, Dict]:
    """Run full trace analysis. Returns (keywords, outcomes, action_level)."""
    if data_dir is None:
        data_dir = DATA_DIR_DEFAULT
    if output_dir is None:
        output_dir = OUTPUT_DIR_DEFAULT

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading runs from {data_dir}...")
    df, raw = load_all_runs(data_dir)
    print(f"Loaded {len(df)} runs.")

    print("Analyzing keywords per framing...")
    keywords = keywords_per_framing(df, data_dir)

    print("Analyzing high vs low Gini outcomes...")
    outcomes = outcome_split_analysis(df, data_dir)

    print("Analyzing action-level reasoning...")
    action_level = action_level_reasoning(df, data_dir)

    print_trace_summary(keywords, outcomes, action_level)

    # Save results
    def _serialize(obj):
        """Make Counter objects JSON-safe."""
        if isinstance(obj, Counter):
            return dict(obj)
        if isinstance(obj, dict):
            return {str(k): _serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_serialize(v) for v in obj]
        if isinstance(obj, tuple):
            return list(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        return obj

    with open(output_dir / "trace_analysis.json", "w") as f:
        json.dump({
            "keywords_per_framing": _serialize(keywords),
            "outcome_split": _serialize(outcomes),
            "action_level": _serialize(action_level),
        }, f, indent=2, default=str)
    print(f"\nSaved trace analysis to {output_dir / 'trace_analysis.json'}")

    return keywords, outcomes, action_level


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reasoning trace analysis for Gemma 2 27B")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    run_trace_analysis(data_dir=args.data_dir, output_dir=args.output_dir)
