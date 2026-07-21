#!/usr/bin/env python3
"""Exploratieve karakterisering van een T4-commons-run (design-smoke tool).

NIET de governance-DV (dat is commons_dv.py). Dit meet de vier signalen waar de
harvest-mechaniek-kalibratie om draait (Koen 2026-07-21):

  1. CROWD-OUT vs GEINTEGREERD — blijven sociale acties (transfer/take/associate)
     live naast harvest, of verdringt harvest alles? (raakt de T4-nesting-vraag)
  2. ENCLOSURE — oogsten sommigen wel en anderen niet? Gini van harvest, aandeel
     nooit-oogsters, en of het dezelfde subgroep is (harvester-stabiliteit).
  3. STRIP-THEN-DOMINATE — zetten zware oogsters hun buit om in predatie? (correlatie
     harvest <-> takes; timing harvest-fase -> aanvals-fase).
  4. GOVERNANCE — wordt de totale oogst omlaag gecoordineerd (moratorium-signatuur),
     en overleeft de commons?

Gebruik: python3 commons_probe.py run1_log.jsonl [run2_log.jsonl ...]
"""
import json, sys
from collections import Counter, defaultdict

SUSTAINABLE_FLOW = 40.0  # ×1.5-regen duurzaam debiet bij K=120 (K - K/regen)


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def _canon(a):
    a = str(a or "hold").lower()
    if a.startswith("invest") or a == "transfer":
        return "transfer"
    if a.startswith("take") or a == "attack":
        return "take"
    if "arm" in a or a == "strengthen":
        return "strengthen"
    if a.startswith("harvest"):
        return "harvest"
    if a in ("drop", "invite"):
        return "associate"
    return "hold"


def gini(xs):
    xs = sorted(x for x in xs if x is not None)
    n = len(xs)
    if n == 0 or sum(xs) == 0:
        return 0.0
    cum = 0.0
    for i, x in enumerate(xs, 1):
        cum += i * x
    return (2 * cum) / (n * sum(xs)) - (n + 1) / n


def analyze(path):
    rounds = load(path)
    per_agent_harvest = defaultdict(float)   # cumulatief geoogste units
    per_agent_harv_rounds = defaultdict(int)  # # rondes waarin geoogst
    per_agent_takes = defaultdict(int)        # # take-acties
    harvester_sets = []                       # set van oogsters per (open) ronde
    action_mix = []                           # (round, Counter) alleen open rondes
    harvest_series = []                        # (round, totale harvest)
    take_series = []
    open_rounds = 0
    final_res = {}

    for r in rounds:
        rd = r.get("round")
        ag = r.get("agents", {}) or {}
        cm = r.get("commons", {}) or {}
        harvested = cm.get("harvested")
        frac = cm.get("harvest_frac", {}) or {}
        is_open = bool(frac) or (harvested is not None and harvested > 0) or \
            (cm and not cm.get("closed_until") and cm.get("opens_in_round") is None)
        acts = Counter()
        harvesters = set()
        for aid, a in ag.items():
            act = _canon(a.get("action"))
            acts[act] += 1
            if act == "take":
                per_agent_takes[aid] += 1
            b = a.get("breakdown", {}) or {}
            h = b.get("harvest", 0.0) or 0.0
            if h > 0 or aid in frac:
                per_agent_harvest[aid] += h
                per_agent_harv_rounds[aid] += 1
                harvesters.add(aid)
            final_res[aid] = a.get("resources", final_res.get(aid, 0))
        if is_open and acts:
            open_rounds += 1
            action_mix.append((rd, acts))
            harvester_sets.append(harvesters)
            harvest_series.append((rd, harvested or 0.0))
            take_series.append((rd, len(r.get("combat", []) or [])))

    n_agents = len(final_res) or 1
    # ---- 1. crowd-out vs geintegreerd ----
    tot = Counter()
    for _, c in action_mix:
        tot += c
    grand = sum(tot.values()) or 1
    mix_pct = {k: round(100 * v / grand, 1) for k, v in tot.most_common()}

    # ---- 2. enclosure ----
    harvests = [per_agent_harvest.get(a, 0.0) for a in final_res]
    never = sum(1 for a in final_res if per_agent_harvest.get(a, 0.0) <= 0)
    g_harv = gini(harvests)
    # harvester-stabiliteit: gem. Jaccard tussen opeenvolgende oogster-sets
    jac = []
    for i in range(1, len(harvester_sets)):
        a, b = harvester_sets[i - 1], harvester_sets[i]
        if a or b:
            jac.append(len(a & b) / len(a | b))
    stability = round(sum(jac) / len(jac), 2) if jac else None

    # ---- 3. strip-then-dominate ----
    # splits agents in zware oogsters (top-kwart cum. harvest) vs rest; vergelijk takes
    ranked = sorted(final_res, key=lambda a: -per_agent_harvest.get(a, 0.0))
    q = max(1, n_agents // 4)
    big = ranked[:q]
    rest = ranked[q:]
    takes_big = sum(per_agent_takes.get(a, 0) for a in big) / max(len(big), 1)
    takes_rest = sum(per_agent_takes.get(a, 0) for a in rest) / max(len(rest), 1)

    # ---- 4. governance ----
    peak = max((h for _, h in harvest_series), default=0.0)
    last3 = [h for _, h in harvest_series[-3:]]
    tail = sum(last3) / len(last3) if last3 else 0.0
    moratorium = peak > SUSTAINABLE_FLOW and tail < 0.6 * peak  # oogst piekte en zakte
    cm_blocks = [r["commons"] for r in rounds if isinstance(r.get("commons"), dict)]
    collapsed = any(b.get("collapsed") for b in cm_blocks)
    coll_round = next((i + 1 for i, b in enumerate(cm_blocks) if b.get("collapsed")), None)

    return dict(
        name=path.split("/")[-1], rounds=len(rounds), open_rounds=open_rounds,
        mix=mix_pct,
        social_alive_pct=round(100 * (tot["transfer"] + tot["take"] + tot["associate"]) / grand, 1),
        harvest_pct=mix_pct.get("harvest", 0.0),
        enclosure=dict(gini_harvest=round(g_harv, 2), never_harvested=never,
                       n_agents=n_agents, harvester_stability=stability),
        strip_dominate=dict(takes_per_big_harvester=round(takes_big, 2),
                            takes_per_other=round(takes_rest, 2)),
        governance=dict(peak_harvest=round(peak, 1), tail_harvest=round(tail, 1),
                        moratorium_signature=moratorium, collapsed=collapsed,
                        collapse_round=coll_round, sustainable_flow=SUSTAINABLE_FLOW),
    )


def report(m):
    print(f"\n{'='*70}\n{m['name']}  ({m['rounds']} rondes, {m['open_rounds']} met open commons)")
    print(f"{'='*70}")
    print(f"1. CROWD-OUT?  actie-mix: {m['mix']}")
    print(f"   harvest={m['harvest_pct']}%  |  sociale acties (transfer+take+assoc)={m['social_alive_pct']}%")
    verdict = "GEINTEGREERD (sociaal blijft live)" if m['social_alive_pct'] >= 20 else \
        ("CROWD-OUT (harvest verdringt sociaal)" if m['harvest_pct'] >= 70 else "gemengd")
    print(f"   -> {verdict}")
    e = m['enclosure']
    print(f"2. ENCLOSURE?  Gini(harvest)={e['gini_harvest']}  nooit-geoogst={e['never_harvested']}/{e['n_agents']}"
          f"  harvester-stabiliteit={e['harvester_stability']}")
    encl = "ENCLOSURE (geconcentreerd/stabiele subgroep)" if (e['gini_harvest'] >= 0.4 or e['never_harvested'] >= e['n_agents'] // 3) else "uniform (iedereen oogst ~gelijk)"
    print(f"   -> {encl}")
    s = m['strip_dominate']
    print(f"3. STRIP-DOMINATE?  takes/zware-oogster={s['takes_per_big_harvester']}  vs takes/overig={s['takes_per_other']}")
    sd = "AANWIJZING (zware oogsters domineren meer)" if s['takes_per_big_harvester'] > 1.5 * max(s['takes_per_other'], 0.1) and s['takes_per_big_harvester'] >= 1 else "geen duidelijke strip-dominate"
    print(f"   -> {sd}")
    g = m['governance']
    print(f"4. GOVERNANCE?  piek-oogst={g['peak_harvest']} (duurzaam={g['sustainable_flow']})  staart={g['tail_harvest']}"
          f"  moratorium-signatuur={g['moratorium_signature']}")
    print(f"   commons: collapsed={g['collapsed']}" + (f" (ronde {g['collapse_round']})" if g['collapsed'] else " (overleefde)"))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        try:
            report(analyze(p))
        except Exception as e:
            print(f"\n{p}: FOUT {type(e).__name__}: {e}")
