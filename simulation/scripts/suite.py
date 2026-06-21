#!/usr/bin/env python3
"""
suite.py — ONE entry point for the full per-run analysis suite.

Runs ALL the existing analyses on a single run file OR a whole directory and
prints one consolidated report. It does NOT reimplement any metric — every
number comes from the existing modules (YAGNI: reuse, not rebuild):

  - classify_run   : regime classification + named institutions + role-claims
  - batch_suite    : the DV fingerprint (gini, takes/predation, consensus,
                     norm-public/private, enforcement, survivors, growth,
                     modularity/cohesion)
  - commstruct     : communication-structure (breadth, DM/broadcast, reach)
  - order_suite    : per-run order metrics (economy/regime, action-drift,
                     attack structure)

Graceful degrade: if igraph/leidenalg are missing, the graph-dependent parts
(modularity/cohesion from batch_suite, subgroups from order_suite) are skipped
with a note; all non-graph parts still run.

Usage:
    python suite.py RUN_reasoning_live.jsonl        # one run
    python suite.py --batch DIR/                    # all runs in DIR + aggregate
"""
import argparse
import glob
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import classify_run
import commstruct
import order_suite

# batch_suite imports igraph/leidenalg at module top; degrade gracefully.
try:
    import batch_suite
    HAVE_BATCH = True
    BATCH_IMPORT_ERR = None
except Exception as e:  # ImportError on igraph/leidenalg, etc.
    HAVE_BATCH = False
    BATCH_IMPORT_ERR = e


# ─── one run ────────────────────────────────────────────────────────────────

def analyze_run(path, params):
    """Run every analysis on one run file. Returns a dict of sub-reports.
    Never reimplements a metric — only calls the existing module functions."""
    report = {"path": path, "name": os.path.basename(path)}

    # (a) regime classification (classify_run, whole-run mode for a single label)
    whole_params = dict(params)
    whole_params["window_size"] = 0
    cls = classify_run.classify_file(path, whole_params)
    report["classify"] = cls
    feats = cls.get("features", {})

    # (b) named institutions + role-claims (reuse classify_run detectors)
    rounds = classify_run.load_log(path)
    named, _named_raw = classify_run.detect_named_structures(rounds)
    top_agent = feats.get("top_agent")
    role_claims = classify_run.detect_role_claims(
        rounds, top_agents={top_agent} if top_agent else None)
    report["named_structures"] = named
    report["role_claims"] = role_claims

    # (c) DV fingerprint (batch_suite). Needs igraph/leidenalg for Q/cohesion.
    if HAVE_BATCH:
        report["dv"] = batch_suite.analyze(path)
    else:
        report["dv"] = None

    # (d) communication structure (commstruct)
    report["comm"] = commstruct.analyze(path)

    # (e) order metrics (order_suite) — reuse load/parse/economy/action_dist_drift
    lines = order_suite.load(path)
    agents, T, Mc, attacks, per_round = order_suite.parse(lines)
    pr, tot, g, top, alive, N, reg = order_suite.economy(per_round)
    dist, drift, cmean, cstd = order_suite.action_dist_drift(per_round)
    report["order"] = {
        "n_agents": len(agents), "n_rounds": len(per_round),
        "regime": reg, "growth_per_round": pr, "growth_total": tot,
        "gini": g, "top_share": top, "alive": alive, "N": N,
        "action_dist": dist, "drift": drift,
        "consensus_mean": cmean, "consensus_std": cstd,
        "n_attacks": len(attacks),
    }
    return report


def print_run(report):
    name = report["name"]
    print(f"\n{'='*74}\n{name}\n{'='*74}")

    # (a) regime
    cls = report["classify"]
    print("\n[REGIME — classify_run]")
    print(f"  label: {cls.get('label')} ({cls.get('label_name')})")
    l2 = cls.get("layer2", {})
    if l2:
        print(f"  layer2: coordination={l2.get('coordination')} / outcome={l2.get('outcome')}")
    if cls.get("flags"):
        print(f"  flags: {cls['flags']}")

    # (b) named institutions + role-claims
    print("\n[NAMED INSTITUTIONS — detect_named_structures]")
    if report["named_structures"]:
        for n, c in report["named_structures"].most_common():
            print(f"    {n:<32} x{c}")
    else:
        print("    (none above threshold)")
    print("[ROLE CLAIMS — detect_role_claims (top agent)]")
    if report["role_claims"]:
        for aid, claims in report["role_claims"].items():
            print(f"    {aid}: {dict(claims)}")
    else:
        print("    (none)")

    # (c) DV fingerprint
    print("\n[DV FINGERPRINT — batch_suite]")
    dv = report["dv"]
    if dv is None:
        print(f"    SKIPPED (igraph/leidenalg unavailable: {BATCH_IMPORT_ERR})")
    else:
        print(f"    regime={dv['reg']} | growth {dv['pr']:+.2f}%/r | gini {dv['g']:.2f} | top {dv['top']:.0f}%")
        print(f"    takes={dv['tt']} (betrayal {dv['verr']:.0f}%) | mob {dv['mob']:.1f} | alive {dv['alive']}")
        print(f"    modularity Q={dv['Q']:.3f} | clubs K={dv['K']} | cohesion {100*dv['coh']:.0f}%")
        print(f"    survivors {100*dv['surv']:.0f}% | bankrupt/gone {dv['gone']}")
        print(f"    consensus mean {dv['cmean']:.2f} / std {dv['cstd']:.2f} | drift {dv['drift']:.3f} | rewire {dv['rw']:.1f}/r")
        print(f"    norm-public {dv['norm_pub']:.3f} | norm-private {dv['norm_priv']:.3f} | "
              f"sanction {dv['sanc']:.3f} | enforce-neg {dv['enf_neg']:.3f} | enforce-pos {dv['enf_pos']:.3f}")

    # (d) communication structure
    c = report["comm"]
    print("\n[COMMUNICATION STRUCTURE — commstruct]")
    print(f"    {c['n_msg']} msgs, {c['n']} agents | breadth {c['breedte']:.2f} recipients/msg")
    print(f"    DM-rate {c['dm_rate']:.3f} | broadcast-rate {c['broad_rate']:.3f} | reach {c['reach']:.3f}")
    print(f"    in-gini {c['in_gini']:.3f} | focus-gini {c['focus_gini']:.3f} | "
          f"central node {c['top_name']} ({c['top_recv']:.3f})")

    # (e) order metrics
    o = report["order"]
    print("\n[ORDER METRICS — order_suite]")
    print(f"    economy: {o['regime']} {o['growth_per_round']:+.2f}%/r ({o['growth_total']:+.1f}% tot) | "
          f"gini {o['gini']:.2f} | top {o['top_share']:.0f}% | alive {o['alive']}/{o['N']}")
    mix = " ".join(f"{k.split('_')[0] if 'strength' not in k else k[10:]}:{o['action_dist'][k]:.0f}%"
                   for k in order_suite.PRIMARY)
    print(f"    actions: {mix}")
    print(f"    drift {o['drift']:.3f} | consensus mean {o['consensus_mean']:.2f} / std {o['consensus_std']:.2f} | "
          f"attacks {o['n_attacks']}")


# ─── batch ──────────────────────────────────────────────────────────────────

def run_batch(dir_path, params):
    files = sorted(glob.glob(os.path.join(os.path.expanduser(dir_path),
                                          "*_reasoning_live.jsonl")))
    if not files:
        print(f"No *_reasoning_live.jsonl files in {dir_path}")
        return
    for f in files:
        report = analyze_run(f, params)
        print_run(report)

    # aggregate: delegate to batch_suite's own directory roll-up (reuse, not rebuild)
    print(f"\n{'#'*74}\n# AGGREGATE — batch_suite\n{'#'*74}")
    if HAVE_BATCH:
        _aggregate(dir_path)
    else:
        print(f"  SKIPPED (igraph/leidenalg unavailable: {BATCH_IMPORT_ERR})")


def _aggregate(dir_path):
    """Reproduce batch_suite's directory aggregate by reusing its analyze()."""
    import numpy as np
    files = sorted(glob.glob(os.path.join(os.path.expanduser(dir_path),
                                          "*_reasoning_live.jsonl")))
    rows = []
    for f in files:
        try:
            r = batch_suite.analyze(f)
        except Exception:
            r = None
        if r:
            rows.append(r)
    if not rows:
        return
    name = os.path.basename(dir_path.rstrip("/"))
    regs = Counter(r["reg"] for r in rows)
    mean = lambda k: np.mean([r[k] for r in rows])
    print(f"\n### {name}  (n={len(rows)})")
    print(f"  regimes: {dict(regs)}")
    print(f"  Q {mean('Q'):.2f} | mob {mean('mob'):.1f} | cohesion {100*mean('coh'):.0f}% | "
          f"drift {mean('drift'):.3f} | growth {mean('pr'):+.1f}%/r | top {mean('top'):.0f}% | "
          f"gini {mean('g'):.2f} | takes {mean('tt'):.0f} (betrayal {mean('verr'):.0f}%) | "
          f"rewire {mean('rw'):.1f}/r")
    print(f"  survivors {100*mean('surv'):.0f}% | bankrupt/gone {mean('gone'):.1f}")
    print(f"  consensus: mean {mean('cmean'):.2f} | std {mean('cstd'):.2f}")
    print(f"  COMM: norm-public {mean('norm_pub'):.3f} | norm-private {mean('norm_priv'):.3f} | "
          f"enforce {mean('enf_neg'):.3f} | fulfill {mean('enf_pos'):.3f}")
    Qs = sorted(r["Q"] for r in rows)
    print(f"  Q-spread: min {Qs[0]:.2f} med {Qs[len(Qs)//2]:.2f} max {Qs[-1]:.2f}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", nargs="?", help="a single *_reasoning_live.jsonl run file")
    p.add_argument("--batch", help="directory of runs; report each + aggregate")
    args = p.parse_args()

    params = dict(classify_run.DEFAULTS)

    if args.batch:
        run_batch(args.batch, params)
        return
    if not args.path:
        p.error("provide a run file, or --batch <dir>")
    report = analyze_run(args.path, params)
    print_run(report)


if __name__ == "__main__":
    main()
