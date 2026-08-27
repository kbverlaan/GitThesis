"""M31 · Wat elke trede verliest als het berichtenkanaal uitgaat (grootboek S19).

Scope   Alleen knife-edge: de vier controlecellen tegen hun sprekende
        tegenhangers. Vijf runs per controle, tien of vijftien met kanaal.

Het oorspronkelijke script (`nocomm_compare.py`) bestaat niet meer. Herbouwd uit
de beschrijving in S19, met de maten die uit de actie- en rewire-velden volgen.

Wat hier staat en wat niet: `transfer`-aandeel, `take`-aandeel, wederzijdse
paren, drops, eindbezit en eind-Gini komen rechtstreeks uit de logs en zijn
volledig herberekend. De maten die een tekstdetector nodig hebben — doelrang naar
vermogen, aanvallen op de top drie, aantekeningen met een plan tegen de leider —
staan in S19 maar zitten hier nog niet in; die hangen aan andere measures en
worden daar opgehaald.

⚠️ De vergelijking is asymmetrisch in n: vijf controleruns tegen tien of vijftien
sprekende. Verschillen worden daarom met de spreiding erbij gerapporteerd, niet
als kale getallen.
"""
from __future__ import annotations

import json
import sys

import runset
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))
from graph import mutual_dyads
from base import (ACTIONS, action_shares, final_gini, log_path, mean_sd,
                  rewire_shares, rounds)
from M39_form_profile import _run as vormen

PAREN = [("L1", "prod_L1_knife", "prod_L1_knife_nocomm"),
         ("L2", "prod_L2_knife", "prod_L2_knife_nocomm"),
         ("L3", "prod_L3_knife", "prod_L3_knife_nocomm"),
         ("L4", "prod_L4_knife", "prod_L4_knife_nocomm")]


def _eindbezit(p) -> float:
    rs = rounds(log_path(p))
    if not rs:
        return 0.0
    res = [a.get("resources") or 0 for a in (rs[-1].get("agents") or {}).values()]
    return sum(res) / len(res) if res else 0.0


def _cel(naam: str) -> dict:
    paths = runset.cel(naam)
    aand, _ = action_shares(paths)
    rew, _ = rewire_shares(paths)
    per = [vormen(p) for p in paths]
    gini = [final_gini(p) for p in paths]
    bezit = [_eindbezit(p) for p in paths]
    g_m, g_sd = mean_sd(gini)
    b_m, b_sd = mean_sd(bezit)
    # Mutual pairs come from the shared primitive, not from the form profile.
    # The two disagree: `vormen` counts dyads over transfer AND strengthen,
    # while the chapter counts transfers only, and at L2 that is 10.4 against
    # 6.1. One concept, one definition --- see core/graph.py::mutual_dyads().
    dy_m, dy_sd = mean_sd([mutual_dyads(x, min_count=1) for x in paths])
    return {
        "n": len(paths),
        "transfer": round(aand["transfer"], 1),
        "take": round(aand["take"], 1),
        "harvest": round(aand["harvest"], 1),
        "drops": round(rew["drop"], 2),
        "paren": (round(dy_m, 1), round(dy_sd, 1)),
        "benoemd": round(sum(x["benoemd"] for x in per) / len(per), 1),
        "gini": (round(g_m, 3), round(g_sd, 3)),
        "bezit": (round(b_m, 1), round(b_sd, 1)),
    }


def compute() -> dict:
    return {trede: {"met": _cel(aan), "zonder": _cel(uit)}
            for trede, aan, uit in PAREN}


if __name__ == "__main__":
    try:
        res = compute()
    except runset.RunsetError as e:
        sys.exit(f"RUNSET: {e}")
    if "--json" in sys.argv:
        print(json.dumps(res, indent=1)); raise SystemExit
    rijen = [("transfer %", "transfer"), ("take %", "take"), ("harvest %", "harvest"),
             ("drops %", "drops"), ("benoemde vormen", "benoemd")]
    for trede, r in res.items():
        a, b = r["met"], r["zonder"]
        print(f"\n=== {trede} knife-edge   met kanaal n={a['n']}, zonder n={b['n']} ===")
        print(f"{'':22}{'met':>10}{'zonder':>10}")
        for label, k in rijen:
            print(f"  {label:20}{a[k]:10}{b[k]:10}")
        print(f"  {'wederzijdse paren':20}{a['paren'][0]:7}±{a['paren'][1]:<3}"
              f"{b['paren'][0]:7}±{b['paren'][1]:<3}")
        print(f"  {'eind-Gini':20}{a['gini'][0]:7}±{a['gini'][1]:<3}"
              f"{b['gini'][0]:7}±{b['gini'][1]:<3}")
        print(f"  {'eindbezit':20}{a['bezit'][0]:7}±{a['bezit'][1]:<3}"
              f"{b['bezit'][0]:7}±{b['bezit'][1]:<3}")
