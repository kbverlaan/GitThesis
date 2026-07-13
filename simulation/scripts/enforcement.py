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
    # ── Governance-rol-attributie (rol-laag, 2026-07-07; Aoki-verfijning 2026-07-08) ──
    # WIE handhaaft, en OP WIE? Geconcentreerde geframede sanctie (lens A) op een
    # paar agents = een monitor/sanctioner-ROL is ontstaan. MAAR: concentratie van
    # sanctiecapaciteit ALLEEN volstaat niet om governance te herkennen. Aoki (2001)
    # Ch.6 laat zien dat dezelfde hoge top-share past op zowel een democratische/
    # rule-of-law-staat (een handhaver die een gedeelde regel volgt) als een
    # COLLUSIEVE/roof-staat (handhaver + kliek roven systematisch een minderheid):
    # "A government strong enough to protect property rights and enforce contracts is
    # also strong enough to confiscate the wealth of its citizens" (Weingast, in Aoki
    # p.151). Het onderscheidende is niet de concentratie maar (a) WIE het doelwit is
    # -- systematisch dezelfde minderheid (collusief) vs roterend onder gedeelde
    # dreiging (democratisch; Aoki p.156 "punished by the withdrawal of the support of
    # private agents ... nonvictims" / p.158 "lack of government's information about the
    # identity ... a commitment device ... to abstain from random extortion"); en (b) of
    # de tophandhaver ZELF disciplineerbaar is (ooit zelf doelwit van geframede sanctie;
    # Glorious-Revolution-mechaniek, Aoki p.161-162). Daarom meten we naast enforcer-
    # concentratie ook TARGET-concentratie en enforcer-disciplineerbaarheid.
    # Alle drempels ONGEKALIBREERD (nog geen bevestigde governance-run; voorspeld pas
    # op de commons-trede) -> conservatief + gevlagd.
    enf_by_actor = Counter(actor for (r, actor, label, tg, frm, s) in triples["A"])
    counts = [enf_by_actor.get(a, 0) for a in agents]
    total_enf = sum(counts)
    enforcer_gini = gini(counts)
    n_enforcers = sum(1 for c in counts if c > 0)
    top_enf = enf_by_actor.most_common(1)[0] if enf_by_actor else (None, 0)
    top_enf_share = top_enf[1] / total_enf if total_enf else 0.0
    # Target-laag: op wie valt de geframede sanctie? Vaste minderheid = roof-signatuur;
    # roterend = democratische-zelfbeperking-signatuur (Aoki p.156/p.158).
    tgt_by_target = Counter(tg for (r, actor, label, tg, frm, s) in triples["A"])
    tcounts = [tgt_by_target.get(a, 0) for a in agents]
    target_gini = gini(tcounts)
    n_targets = sum(1 for c in tcounts if c > 0)
    top_tgt = tgt_by_target.most_common(1)[0] if tgt_by_target else (None, 0)
    top_tgt_share = top_tgt[1] / total_enf if total_enf else 0.0
    # Disciplineerbaarheid: is de tophandhaver zélf ooit doelwit van geframede sanctie?
    # (democratisch = de handhaver-rol is zelf onderworpen aan de orde; Aoki p.152/p.161)
    top_enforcer_targeted = bool(top_enf[0]) and tgt_by_target.get(top_enf[0], 0) > 0
    return dict(name=os.path.basename(path), nr=nr,
                neg_rate=rate("A"), pos_rate=rate("B"),
                n_takedrop=n_act["A"], n_investarm=n_act["B"],
                n_neg=n_framed["A"], n_pos=n_framed["B"],
                enforcer_gini=enforcer_gini, n_enforcers=n_enforcers,
                top_enforcer=top_enf[0], top_enf_share=top_enf_share,
                target_gini=target_gini, n_targets=n_targets,
                top_target=top_tgt[0], top_tgt_share=top_tgt_share,
                top_enforcer_targeted=top_enforcer_targeted,
                triples=triples)


def print_single(r, top):
    print(f"\n{r['name']}  ({r['nr']} rondes)")
    print(f"  LENS A  normhandhaving (take/drop als straf) : {r['neg_rate']:.3f}"
          f"   ({r['n_neg']}/{r['n_takedrop']} geframed)")
    print(f"  LENS B  normvervulling (invest/arm als naleving): {r['pos_rate']:.3f}"
          f"   ({r['n_pos']}/{r['n_investarm']} geframed)")
    te = f"{r['top_enforcer']} ({r['top_enf_share']:.0%})" if r['top_enforcer'] else "-"
    tt = f"{r['top_target']} ({r['top_tgt_share']:.0%})" if r['top_target'] else "-"
    # Rol-verdict: top_enf_share (dominantie van EEN handhaver) is de betere
    # discriminator dan Gini -- Gini over de hele populatie vuurt al bij "niet
    # iedereen handhaaft". Maar concentratie alleen scheidt democratisch niet van
    # collusief (Aoki Ch.6, zie analyze()) -> gebruik de target-laag + enforcer-
    # disciplineerbaarheid als tweede as. Alle drempels ONGEKALIBREERD -> gevlagd.
    if not r['n_enforcers']:
        verdict = ""
    elif r['top_enf_share'] >= 0.40 and r['n_enforcers'] <= 4:
        # Er is een concentreerde handhaver-rol. Aoki-discriminator dem. vs collusief:
        if r['top_enforcer_targeted']:
            verdict = "-> concentr. handhaver MAAR zelf disciplineerbaar = rule-of-law/democratisch? [ongekalibreerd]"
        elif r['top_tgt_share'] >= 0.40:
            verdict = "-> concentr. handhaver + vast doelwit + niet zelf gesanctioneerd = COLLUSIEF/roof? [ongekalibreerd]"
        else:
            verdict = "-> concentr. sanctioner-rol; doelwit roteert = ambigu [ongekalibreerd]"
    else:
        verdict = "-> diffuse handhaving (geen duidelijke rol)"
    print(f"  GOV-ROL  handhaving: Gini {r['enforcer_gini']:.3f}, top-share {r['top_enf_share']:.0%}"
          f"   ({r['n_enforcers']} handhaver(s); top {te})   {verdict}")
    disc = "ja (disciplineerbaar)" if r['top_enforcer_targeted'] else "nee"
    print(f"  GOV-TGT  doelwit: Gini {r['target_gini']:.3f}, top-share {r['top_tgt_share']:.0%}"
          f"   ({r['n_targets']} doelwit(en); top {tt}); tophandhaver zelf gesanctioneerd: {disc}")
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
