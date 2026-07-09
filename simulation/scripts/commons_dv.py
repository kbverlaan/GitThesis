#!/usr/bin/env python3
"""Commons-DV — leest het per-ronde commons-blok uit een reasoning_live.jsonl en
berekent de stock-uitkomst van de T4-commons-trede.

Draagt de §3-claim "failing to coordinate is directly observable, as the stock
collapses": collapse + tijd-tot-collapse + duurzaamheid, puur uit de gelogde
stock-serie (geen model-call, reproduceerbaar). Geeft None terug voor runs
zonder commons-trede (L1-L3), zodat het veilig in de batch-fingerprint kan.

Engine-dynamiek (src/game/engine.py::_regenerate_commons): elke ronde harvest ->
stock_after_harvest; end-of-round groei new_S = min(K, regen*S), of absorbing
collapse als S < K*collapse_frac. MSY = commons_init = K/2 (maximaal duurzaam peil).

Gebruik: python3 commons_dv.py <reasoning_live.jsonl>
"""
import json
import argparse
import numpy as np


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def commons_metrics(rounds):
    """rounds = lijst van ronde-dicts (uit load()). Return dict met commons-DV's,
    of None als geen enkele ronde een commons-blok heeft (niet-T4-run)."""
    blocks = [r["commons"] for r in rounds
              if isinstance(r, dict) and isinstance(r.get("commons"), dict)]
    if not blocks:
        return None

    K = next((float(b["K"]) for b in blocks if b.get("K")), None)
    if not K:
        return None
    MSY = K / 2.0  # commons_init = K/2 = maximaal duurzaam voorraadpeil

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
    sustained = (not collapsed) and (stock_final >= MSY)  # boven MSY geeindigd

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
        "min_stock_pct": round(min_stock_pct, 2),
        "over_harvest_rate": round(over_harvest_rate, 4),
        "mean_harvest_frac": round(mean_harvest_frac, 4),
        "total_harvested": round(total_harvested, 2),
        "K": K,
        "MSY": MSY,
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
