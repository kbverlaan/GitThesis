#!/usr/bin/env python3
"""δ-equivalentietoets — het refutatie-criterium van §2 operationeel.

§2: "One result would refute the account, namely an order-type profile
invariant across both variables, equivalent within a pre-registered margin δ."

Operationalisatie:
  - profiel per cel = verdeling over de geneste order-ladder-labels (0..5)
    van de runs in die cel;
  - afstand tussen twee cellen = total variation (TV): 0.5 * som |p_k - q_k|;
  - per hendel de MAX paarsgewijze TV over de cellen van die sweep
    (actie-ruimte: rungen bij vaste payoff; payoff: cellen binnen een rung);
  - equivalentie-claim (refutatie van het account) alleen als de BOVENGRENS
    van het bootstrap-95%-CI van die max-TV < δ (TOST-geest: je moet
    gelijkheid aantonen, niet slechts geen verschil vinden).

δ zelf is een KOEN-beslissing (pre-reg; config/dv_thresholds.yaml
order_ladder.delta — null tot vastgelegd).

Input: JSONL met per run {"run": ..., "rung": "L1".."L4",
"payoff": "scar|knife|abund", "nested_level": 0..5}
(te genereren met order_ladder_gate.py --json | jq, of de batch-suite).

Gebruik: python3 delta_equivalence.py results.jsonl [--delta 0.2] [--boot 2000]
"""
import argparse, json, os, random, sys
from collections import defaultdict

import yaml

K_LEVELS = 6
CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config",
                   "dv_thresholds.yaml")


def profile(levels):
    p = [0.0] * K_LEVELS
    for l in levels:
        p[int(l)] += 1
    n = len(levels) or 1
    return [x / n for x in p]


def tv(p, q):
    return 0.5 * sum(abs(a - b) for a, b in zip(p, q))


def max_pairwise_tv(groups):
    """groups = {celnaam: [nested_levels]}. Max TV over alle celparen."""
    keys = sorted(groups)
    best = 0.0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            best = max(best, tv(profile(groups[keys[i]]), profile(groups[keys[j]])))
    return best


def bootstrap_ci(groups, n_boot, rng, alpha=0.05):
    stats = []
    for _ in range(n_boot):
        res = {k: [rng.choice(v) for _ in v] for k, v in groups.items()}
        stats.append(max_pairwise_tv(res))
    stats.sort()
    lo = stats[int(alpha / 2 * n_boot)]
    hi = stats[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", help="JSONL: run, rung, payoff, nested_level")
    ap.add_argument("--delta", type=float, default=None,
                    help="equivalentiemarge; default uit dv_thresholds.yaml")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    delta = args.delta
    if delta is None:
        with open(CFG) as f:
            delta = (yaml.safe_load(f).get("order_ladder") or {}).get("delta")
    if delta is None:
        print("NB: geen δ vastgelegd (order_ladder.delta = null) — alleen "
              "beschrijvende afstanden, geen verdict.\n")

    rows = [json.loads(l) for l in open(args.results) if l.strip()]
    rng = random.Random(args.seed)

    # Hendel 1 — actie-ruimte: per payoff-cel de rungen vergelijken.
    # Hendel 2 — payoff: per rung de payoff-cellen vergelijken.
    sweeps = {}
    for pay in sorted({r["payoff"] for r in rows}):
        g = defaultdict(list)
        for r in rows:
            if r["payoff"] == pay:
                g[r["rung"]].append(r["nested_level"])
        if len(g) > 1:
            sweeps[f"actie-ruimte @ payoff={pay}"] = dict(g)
    for rung in sorted({r["rung"] for r in rows}):
        g = defaultdict(list)
        for r in rows:
            if r["rung"] == rung:
                g[r["payoff"]].append(r["nested_level"])
        if len(g) > 1:
            sweeps[f"payoff @ rung={rung}"] = dict(g)

    if not sweeps:
        sys.exit("te weinig cellen om een hendel te vergelijken")

    print(f"δ-equivalentie  (n={len(rows)} runs, {args.boot} bootstrap, "
          f"δ={'?' if delta is None else delta})\n")
    all_hi = []
    for name, groups in sweeps.items():
        obs = max_pairwise_tv(groups)
        lo, hi = bootstrap_ci(groups, args.boot, rng)
        all_hi.append(hi)
        cells = ", ".join(f"{k}(n={len(v)})" for k, v in sorted(groups.items()))
        print(f"  {name:34s} max-TV {obs:.3f}  CI95 [{lo:.3f}, {hi:.3f}]   {cells}")

    if delta is not None:
        equivalent = all(hi < delta for hi in all_hi)
        print(f"\n  VERDICT: profiel {'EQUIVALENT binnen δ — account GEREFUTEERD'
              if equivalent else 'niet equivalent — refutatie NIET ondersteund'}"
              f"  (alle CI-bovengrenzen {'<' if equivalent else 'niet alle <'} δ={delta})")


if __name__ == "__main__":
    main()
