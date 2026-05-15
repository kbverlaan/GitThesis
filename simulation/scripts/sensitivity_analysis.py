#!/usr/bin/env python3
"""Sensitivity analysis for pilot 5 regime classifier (cached version)."""
import sys, json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path.home() / "GitThesis/.claude/worktrees/pilot5-classifier/simulation/scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location(
    "classify_run",
    str(Path.home() / "GitThesis/.claude/worktrees/pilot5-classifier/simulation/scripts/classify_run.py")
)
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)


DATA_DIRS = [
    str(Path.home() / "GitThesis/simulation/data/canonical_runs"),
    str(Path.home() / "GitThesis/simulation/data/sweep_pilot_9cell"),
    str(Path.home() / "Desktop/pilot-runs"),
]


def collect_runs():
    runs = []
    seen = set()
    for d in DATA_DIRS:
        for fp in sorted(Path(d).glob("*_log.jsonl")):
            stem = fp.name.replace("_log.jsonl", "")
            if stem in seen: continue
            seen.add(stem)
            runs.append((stem, fp))
        for fp in sorted(Path(d).glob("*_reasoning_live.jsonl")):
            stem = fp.name.replace("_reasoning_live.jsonl", "")
            if stem in seen: continue
            seen.add(stem)
            runs.append((stem, fp))
    return runs


# Re-implement classify_file but with rounds passed in (avoid reloading)
def classify_rounds(rounds, params):
    window_size = params.get("window_size", 0)
    if window_size <= 0:
        features = cr.extract_features(rounds, params)
        label, trace, flags = cr.classify(features, params)
        return label, "(whole-run)"
    windows = cr.classify_trajectory(rounds, params, window_size, params["window_step"])
    if not windows:
        return None, None
    episodes = cr.compress_trajectory(windows)
    pattern = cr.trajectory_pattern(episodes)
    return windows[-1]["label"], pattern


BASELINE = dict(cr.DEFAULTS)

VARIANTS = {
    "event_window":              [1, 2, 5, 7],
    "attempt_threshold":         [0, 2, 3],
    "window_size":               [5, 7, 15],
    "hegemony_runnerup_ratio":   [1.2, 2.0, 3.0],
    "hegemony_top_ratio":        [1.5, 3.0, 4.0],
    "solo_predator_min_strikes": [1, 3, 4],
    "paralysis_stdev":           [2.5, 10.0, 20.0],
    "paralysis_do_nothing":      [0.4, 0.8],
}


def main():
    runs = collect_runs()
    print(f"# Sensitivity analysis — {len(runs)} runs", flush=True)
    print(f"# Loading all logs into memory ...", flush=True)

    # Load all logs once
    cache = {}
    for stem, fp in runs:
        cache[stem] = cr.load_log(fp)
    print(f"# Loaded {len(cache)} logs.", flush=True)
    print(f"# Baseline params: window_size={BASELINE['window_size']}, "
          f"event_window={BASELINE['event_window']}, attempt_threshold={BASELINE['attempt_threshold']}, "
          f"hegemony_runnerup_ratio={BASELINE['hegemony_runnerup_ratio']}, "
          f"hegemony_top_ratio={BASELINE['hegemony_top_ratio']}, "
          f"solo_predator_min_strikes={BASELINE['solo_predator_min_strikes']}, "
          f"paralysis_stdev={BASELINE['paralysis_stdev']}, "
          f"paralysis_do_nothing={BASELINE['paralysis_do_nothing']}", flush=True)
    print()

    def classify_all(params):
        out = {}
        for stem, rounds in cache.items():
            try:
                end, pat = classify_rounds(rounds, params)
                out[stem] = (end, pat)
            except Exception as e:
                out[stem] = (f"ERR:{e}"[:30], None)
        return out

    print("# Computing baseline ...", flush=True)
    baseline = classify_all(BASELINE)

    print()
    print("## Per-threshold sensitivity", flush=True)
    print()
    print(f"| Threshold                    | Baseline | Variant | Δ end_state | Δ trajectory_pattern |")
    print(f"|------------------------------|----------|---------|-------------|----------------------|")

    per_run_changes = defaultdict(int)
    total_variant_count = 0
    for param, values in VARIANTS.items():
        baseline_val = BASELINE[param]
        for variant in values:
            total_variant_count += 1
            new_params = dict(BASELINE)
            new_params[param] = variant
            result = classify_all(new_params)
            d_end = 0
            d_pat = 0
            for run, (e, p) in result.items():
                base_e, base_p = baseline.get(run, (None, None))
                if base_e != e:
                    d_end += 1
                    per_run_changes[run] += 0.5
                if base_p != p:
                    d_pat += 1
                    per_run_changes[run] += 0.5
            n = len(runs)
            print(f"| {param:<28s} | {str(baseline_val):>8s} | {str(variant):>7s} | "
                  f"{d_end:>2d}/{n} ({100*d_end/n:>3.0f}%) | {d_pat:>2d}/{n} ({100*d_pat/n:>3.0f}%) |", flush=True)

    print()
    print(f"## Per-run robustness (over {total_variant_count} variants)")
    print()
    print(f"| Run | Baseline end | Baseline pattern | Change-score | Stability |")
    print(f"|-----|--------------|------------------|--------------|-----------|")
    for run, (e, p) in sorted(baseline.items()):
        score = per_run_changes[run]
        pct = 100*score/total_variant_count
        print(f"| {run[:50]} | {str(e):>4s} | {str(p)[:26]:<26s} | {score:>4.1f}/{total_variant_count} | {100-pct:.0f}% |")


if __name__ == "__main__":
    main()
