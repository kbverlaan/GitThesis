#!/usr/bin/env python3
"""
enforcement.py — NORM->DAAD marker (no-LLM, triage + subagent-haakjes).

Deontische dichtheid (deontic.py) meet of er een NORM is (taal). Deze marker
meet of die norm de ACTIES stuurt -> de norm->institutie-brug: worden woorden daden?

Twee lenzen (de twee kanten van de deontische logica):
  - LENS A  NORMHANDHAVING  : take/drop uitgevoerd als STRAF (handhaving van een verbod)
                              "punish the betrayer", "exile X", "X violated the pact"
  - LENS B  NORMVERVULLING  : transfer/arm uitgevoerd als NALEVING (uitvoering van een gebod)
                              "support our member", "mutual aid for anyone below 60"

Mechaniek (deterministisch): voor elke gerichte actie a->t in ronde r, kijk in de
PUBLIEKE berichten van venster [r-1, r] (berichten crossen 1 ronde, dus de recht-
vaardiging gaat meestal vooraf). Bevat een zin daar (i) het juiste lexicon EN
(ii) de naam van target t? -> de actie is GEFRAMED. Associatief, niet causaal —
maar genoeg om runs te TRIAGEREN en de (actie, citaat, ronde)-TRIPLES te leveren
waar een subagent in kan duiken.

Gebruik:
    python scripts/enforcement.py RUN.jsonl            # scores + triples van 1 run
    python scripts/enforcement.py DIR/                 # triage-ranking over een map
    python scripts/enforcement.py RUN.jsonl --top 30
"""
import json, re, sys, glob, os, argparse
from collections import defaultdict, Counter


def gini(xs):
    """Gini over niet-negatieve tellingen (0 = gelijk verdeeld, ->1 = geconcentreerd)."""
    xs = sorted(xs); n = len(xs); s = sum(xs)
    if n == 0 or s <= 0:
        return 0.0
    return (2 * sum((i + 1) * x for i, x in enumerate(xs))) / (n * s) - (n + 1) / n

# ── LEXICONS (Engels) ────────────────────────────────────────────────────────
# Lens A: straf / handhaving van een verbod.
SANCTION = [r"punish", r"exile", r"expel", r"banish", r"oust", r"ostrac\w*",
            r"betray\w*", r"traitor", r"wolves?", r"violat\w*", r"retaliat\w*",
            r"sanction", r"purge", r"cast out", r"make an example", r"cut off",
            r"deserv\w*", r"bring (?:him|her|them|down)", r"must fall",
            r"must be (?:stopped|removed|punished)", r"hold (?:him|them) accountable",
            r"backstab\w*", r"liar", r"hypocri\w*", r"deal with", r"target the"]
# Lens B: naleving / uitvoering van een gebod (institutioneel, niet zomaar 'aardig').
FULFILMENT = [r"mutual aid", r"support (?:our|the|each)", r"defend (?:our|the)",
              r"protect (?:our|the|each)", r"loyal\w*", r"reciprocat\w*",
              r"contribut\w*", r"reinforce", r"stand with", r"back (?:you|our)",
              r"reward", r"uphold", r"honou?r (?:our|the)", r"as (?:agreed|promised)",
              r"keep (?:our|my) word", r"fulfil\w*", r"our (?:duty|obligation|pact|core|member)",
              r"the (?:pact|council|core|alliance|vsc)", r"stability (?:pact|core)",
              r"rotation", r"aid (?:to|for) (?:the|our|any)"]
RX_SANC = re.compile(r"(?:" + "|".join(SANCTION) + r")", re.I)
RX_FULF = re.compile(r"(?:" + "|".join(FULFILMENT) + r")", re.I)
SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def cat(info):
    """Geef (lens, target) voor de gerichte actie van deze agent, of (None,None).
    take/attack -> ('A', target); transfer/invest -> ('B', target); arm -> ('B', target).
    Drops worden apart afgehandeld (rewire_intent)."""
    a = str(info.get("action") or "hold").lower()
    tg = info.get("target")
    if not tg:
        return (None, None)
    if a.startswith("take") or a == "attack":
        return ("A", tg)
    if a.startswith("invest") or a == "transfer":
        return ("B", tg)
    if "arm" in a or "strengthen" in a:
        return ("B", tg)
    return (None, None)


def analyze(path):
    rounds = [json.loads(l) for l in open(path) if l.strip()]
    nr = len(rounds)
    msgs_by_round = defaultdict(list)            # r -> [(from, text)]
    actions = []                                 # (r, lens, actor, target, action_label)
    agents = set()
    for d in rounds:
        r = d.get("round") or 0
        for m in d.get("messages", []) or []:
            if m.get("text"):
                msgs_by_round[r].append((m.get("from"), m["text"]))
        for aid, info in (d.get("agents") or {}).items():
            agents.add(aid)
            lens, tg = cat(info)
            if lens:
                actions.append((r, lens, aid, tg, str(info.get("action"))))
            drop = (info.get("rewire_intent") or {}).get("drop")
            if drop:                              # drop = sociale uitsluiting -> lens A
                actions.append((r, "A", aid, drop, "drop"))

    ADDRESSEE = re.compile(r"^\s*[A-Z]\w+(?:,\s*[A-Z]\w+)*\s*:\s*")  # "Copper, Gold, Green: ..."

    def framing(r, target, rx):
        """Zoek in venster [r-1, r] een publieke zin waar target het DOELWIT van de
        framing is. Twee precisie-eisen bovenop lexicon+naam:
          1. strip de adressaat-kop ("Copper, Gold:") -> target mag geen geadresseerde zijn;
          2. nabijheid: target-naam binnen ~40 tekens van de lexicon-trigger
             -> target is object/subject van de straf, geen losse vermelding.
        Naam case-SENSITIVE (agent-namen zijn Capitalized)."""
        name_rx = re.compile(r"\b" + re.escape(target) + r"\b")
        for rr in (r - 1, r):
            for frm, txt in msgs_by_round.get(rr, []):
                for s in SENT.split(txt):
                    s2 = ADDRESSEE.sub("", s)            # adressaat-kop weg
                    for lm in rx.finditer(s2):
                        for nm in name_rx.finditer(s2):
                            if abs(lm.start() - nm.start()) <= 40:
                                return (frm, s2.strip())
        return None

    triples = {"A": [], "B": []}
    n_act = {"A": 0, "B": 0}
    n_framed = {"A": 0, "B": 0}
    for (r, lens, actor, tg, label) in actions:
        n_act[lens] += 1
        rx = RX_SANC if lens == "A" else RX_FULF
        f = framing(r, tg, rx)
        if f:
            n_framed[lens] += 1
            triples[lens].append((r, actor, label, tg, f[0], f[1][:150]))
    rate = lambda l: n_framed[l] / n_act[l] if n_act[l] else 0.0
    # ── Governance-rol-attributie (rol-laag, 2026-07-07) ─────────────────────
    # WIE voert de handhaving uit? Geconcentreerde geframede sanctie (lens A) op
    # een paar agents = een monitor/sanctioner-ROL is ontstaan (governance-rol;
    # design-voorspelling: pas op de commons-trede robuust). Diffuus = geen
    # handhaver-rol. Macht-rollen (sovereign/tribuut) meet de actie-familie
    # (flow-centralisatie) apart -- dit is de GOVERNANCE-kant, niet de macht-kant.
    enf_by_actor = Counter(actor for (r, actor, label, tg, frm, s) in triples["A"])
    counts = [enf_by_actor.get(a, 0) for a in agents]
    total_enf = sum(counts)
    enforcer_gini = gini(counts)
    n_enforcers = sum(1 for c in counts if c > 0)
    top_enf = enf_by_actor.most_common(1)[0] if enf_by_actor else (None, 0)
    top_enf_share = top_enf[1] / total_enf if total_enf else 0.0
    return dict(name=os.path.basename(path), nr=nr,
                neg_rate=rate("A"), pos_rate=rate("B"),
                n_takedrop=n_act["A"], n_investarm=n_act["B"],
                n_neg=n_framed["A"], n_pos=n_framed["B"],
                enforcer_gini=enforcer_gini, n_enforcers=n_enforcers,
                top_enforcer=top_enf[0], top_enf_share=top_enf_share,
                triples=triples)


def print_single(r, top):
    print(f"\n{r['name']}  ({r['nr']} rondes)")
    print(f"  LENS A  normhandhaving (take/drop als straf) : {r['neg_rate']:.3f}"
          f"   ({r['n_neg']}/{r['n_takedrop']} geframed)")
    print(f"  LENS B  normvervulling (invest/arm als naleving): {r['pos_rate']:.3f}"
          f"   ({r['n_pos']}/{r['n_investarm']} geframed)")
    te = f"{r['top_enforcer']} ({r['top_enf_share']:.0%})" if r['top_enforcer'] else "-"
    print(f"  GOV-ROL  handhaver-concentratie (Gini): {r['enforcer_gini']:.3f}"
          f"   ({r['n_enforcers']} handhaver(s); top {te})"
          f"   {'-> geconcentreerde sanctioner-rol' if r['enforcer_gini'] >= 0.6 and r['n_enforcers'] else '-> diffuus/geen rol' if r['n_enforcers'] else ''}")
    for lens, tag in (("A", "NORMHANDHAVING (straf)"), ("B", "NORMVERVULLING (steun)")):
        tr = sorted(r["triples"][lens])
        print(f"\n  --- TOP {top} {tag}-TRIPLES (actie | citaat | ronde) ---")
        for (rd, actor, label, tg, frm, s) in tr[:top]:
            print(f"  R{rd:<2} {actor} {label}->{tg}  | [{frm}]: \"{s}\"")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--top", type=int, default=12)
    args = p.parse_args()
    if os.path.isdir(args.path):
        files = sorted(glob.glob(os.path.join(args.path, "*_reasoning_live.jsonl")))
        rows = [analyze(f) for f in files]
        rows.sort(key=lambda r: -(r["neg_rate"] + r["pos_rate"]))
        print(f"\nTRIAGE — norm->daad  ({len(rows)} runs in {args.path})\n")
        print(f"  {'run':<50} {'handhaving':>10} {'vervulling':>11}  (#take/drop, #inv/arm)")
        for r in rows:
            print(f"  {r['name'][:49]:<50} {r['neg_rate']:10.3f} {r['pos_rate']:11.3f}"
                  f"   ({r['n_takedrop']},{r['n_investarm']})")
    else:
        print_single(analyze(args.path), args.top)


if __name__ == "__main__":
    main()
