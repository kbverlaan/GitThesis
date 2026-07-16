#!/usr/bin/env python3
"""Commons-DV — leest het per-ronde commons-blok uit een reasoning_live.jsonl en
berekent de stock-uitkomst van de T4-commons-trede.

Draagt de §3-claim "failing to coordinate is directly observable, as the stock
collapses": collapse + tijd-tot-collapse + duurzaamheid, puur uit de gelogde
stock-serie (geen model-call, reproduceerbaar). Geeft None terug voor runs
zonder commons-trede (L1-L3), zodat het veilig in de batch-fingerprint kan.

Engine-dynamiek (src/game/engine.py::_regenerate_commons): elke ronde harvest ->
stock_after_harvest; end-of-round groei new_S = min(K, regen*S), of absorbing
collapse als S < K*collapse_frac. NB het klassieke MSY-anker (K/2, logistisch)
is ONGEGROND voor deze multiplicatieve groei: het engine-afgeleide duurzame punt
is post-harvest >= K/regen (2/3*K bij regen 1.5), duurzaam debiet K*(1-1/regen)
(= K/3 = 40/ronde). Zie T4-smoke 2026-07-15 (tragedie -> moratorium -> quota).

De 'sustained'-gate is configureerbaar (config/dv_thresholds.yaml commons:
sustained_rule) — KOEN beslist de regel vóór de freeze; alle kandidaten worden
naast elkaar gerapporteerd (sustained_by_rule) zodat de keuze op data rust:
  window_stock : gem. eind-stock laatste W rondes >= frac*K  (v0 PROPOSED)
  final_stock  : eind-stock >= frac*K
  window_flow  : gem. oogst laatste W rondes <= K*(1-1/regen) en geen collapse
  no_collapse  : GovSim-binair (geen collapse over de run)
Alle regels impliceren 'geen collapse' (collapse is absorbing naar 0).

Gebruik: python3 commons_dv.py <reasoning_live.jsonl>
"""
import json
import argparse
import os
import numpy as np
import yaml

_CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                         "config", "dv_thresholds.yaml")


def _commons_cfg():
    with open(_CFG_PATH) as f:
        return yaml.safe_load(f).get("commons", {})


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def commons_metrics(rounds, cfg=None):
    """rounds = lijst van ronde-dicts (uit load()). Return dict met commons-DV's,
    of None als geen enkele ronde een commons-blok heeft (niet-T4-run).
    cfg = commons-blok uit dv_thresholds.yaml (default: van schijf)."""
    blocks = [r["commons"] for r in rounds
              if isinstance(r, dict) and isinstance(r.get("commons"), dict)]
    if not blocks:
        return None

    K = next((float(b["K"]) for b in blocks if b.get("K")), None)
    if not K:
        return None
    if cfg is None:
        cfg = _commons_cfg()
    regen = float(cfg.get("regen", 1.5))
    frac = float(cfg.get("sustained_stock_frac", 1.0 / regen))
    W = int(cfg.get("sustained_window", 10))
    rule = cfg.get("sustained_rule", "window_stock")
    flow_max = K * (1.0 - 1.0 / regen)   # duurzaam debiet (40 bij K=120, regen 1.5)

    def end_stock(b):
        # Eind-van-ronde stock (na regen) = toestand die de volgende ronde ingaat.
        # Val terug op harvest/before als een ronde geen regen logde.
        if b.get("stock_after_regen") is not None:
            return float(b["stock_after_regen"])
        if b.get("stock_after_harvest") is not None:
            return float(b["stock_after_harvest"])
        return float(b.get("stock_before", 0.0))

    stock_before = np.array([float(b.get("stock_before", 0.0)) for b in blocks])
    stock_end = np.array([end_stock(b) for b in blocks])

    # Collapse is absorbing -> eerste ronde met collapsed=True.
    collapsed_flags = [bool(b.get("collapsed", False)) for b in blocks]
    collapsed = any(collapsed_flags)
    round_of_collapse = (collapsed_flags.index(True) + 1) if collapsed else None

    stock_final = float(stock_end[-1])
    sustainability = stock_final / K                    # 0 = leeg/collapse, 1 = vol
    min_stock_pct = 100.0 * float(stock_end.min()) / K  # dieptepunt over de run

    # Alle kandidaat-gates naast elkaar (kalibratie); 'sustained' = de gekozen regel.
    def _harv(b):
        if b.get("harvested") is not None:
            return float(b["harvested"])
        if b.get("stock_after_harvest") is not None:   # oudere/synthetische logs
            return max(0.0, float(b.get("stock_before", 0.0)) - float(b["stock_after_harvest"]))
        return 0.0
    harvested = np.array([_harv(b) for b in blocks])
    by_rule = {
        "window_stock": (not collapsed) and float(stock_end[-W:].mean()) >= frac * K,
        "final_stock": (not collapsed) and stock_final >= frac * K,
        "window_flow": (not collapsed) and float(harvested[-W:].mean()) <= flow_max,
        "no_collapse": not collapsed,
    }
    if rule not in by_rule:
        raise ValueError(f"onbekende sustained_rule '{rule}'")
    sustained = by_rule[rule]

    # Over-harvest: netto voorraaddaling per ronde (onttrekking > aangroei).
    net_change = stock_end - stock_before
    over_harvest_rate = float(np.mean(net_change < 0)) if len(net_change) else 0.0

    # Oogst-agressiviteit: gemiddelde harvest-fractie over alle agent-oogsten.
    fracs = []
    for b in blocks:
        hf = b.get("harvest_frac")
        if isinstance(hf, dict):
            fracs.extend(float(v) for v in hf.values())
    mean_harvest_frac = float(np.mean(fracs)) if fracs else 0.0
    total_harvested = float(sum(b.get("harvested", 0.0) or 0.0 for b in blocks))

    return {
        "has_commons": True,
        "collapsed": collapsed,
        "round_of_collapse": round_of_collapse,
        "sustainability": round(sustainability, 4),
        "sustained": sustained,
        "sustained_rule": rule,
        "sustained_by_rule": by_rule,
        "min_stock_pct": round(min_stock_pct, 2),
        "over_harvest_rate": round(over_harvest_rate, 4),
        "mean_harvest_frac": round(mean_harvest_frac, 4),
        "total_harvested": round(total_harvested, 2),
        "K": K,
        "sustained_stock_frac": frac,
        "flow_max": round(flow_max, 2),
        "n_rounds": len(blocks),
    }


def main():
    ap = argparse.ArgumentParser(description="Commons-DV uit een reasoning_live.jsonl")
    ap.add_argument("log", help="pad naar reasoning_live.jsonl")
    args = ap.parse_args()
    m = commons_metrics(load(args.log))
    if m is None:
        print("geen commons-trede in deze run (geen commons-blok gelogd)")
        return
    for k, v in m.items():
        print(f"{k:20s} {v}")


if __name__ == "__main__":
    main()
