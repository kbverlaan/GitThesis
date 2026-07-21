#!/usr/bin/env python3
"""Order-ladder gate (P1) — ordinale orde-type-label per run.

Zet de sociale-orde-hiërarchie (§2/§3) om in een samengestelde beslisregel:

    0 coordination < 1 cooperation < 2 convention < 3 norm
                   < 4 institution < 5 governance

Elke poort hergebruikt een bestaande detector i.p.v. eigen metrieken te
verzinnen (forking-paths-discipline):
  cooperation  — order_suite   transfer-share (laatste venster) + wederkerige dyades
  convention   — order_suite   clubs-Q + cohesie (vast/split), achter de Q-gate;
                               op assoc-rungs ook rewire-kristallisatie (laat/vroeg)
  norm         — deontic       publieke norm-dichtheid + sanctie-uitingen
  institution  — classify_run  named-structure-detector (pre-reg: >=2 agents, >=3 occ)
  governance   — commons_dv    sustained-gate (alleen T4; None elders)

Label = NESTED: hoogste trede k waarvoor poort 1..k ALLEMAAL passen (theorie-
getrouw — elke trede vooronderstelt de machinerie van de vorige, Aoki/§2).
De volle gate-vector wordt meegeleverd zodat niet-geneste passages (bv.
institutie zonder conventie-structuur) zichtbaar blijven — dat is een
bevinding, geen classificatiefout.

Drempels: config/dv_thresholds.yaml blok `order_ladder:` — v0 PROPOSED
(Claude-scaffold); KOEN beslist de waarden, freeze na IRR (fixplan Fase 3).
--frozen blokkeert CLI-overrides (pre-reg-mode).

Gebruik:
  python3 order_ladder_gate.py <reasoning_live.jsonl> [...]
  python3 order_ladder_gate.py --batch <dir> [--frozen]
"""
import argparse, glob, json, os, sys

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import order_suite as osuite
import deontic
import commons_dv
import enforcement
from classify_run import detect_named_structures
from order_suite import HAVE_LEIDEN

CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config",
                   "dv_thresholds.yaml")

# Sociale-orde-ladder: geneste ordinale as (coordination..institution).
# Governance is een APARTE as (resource-orde, Koen 2026-07-16) — commons-beheer,
# NIET de 6e geneste trede. Aparte T4-samenlevingen kunnen laag op de sociale
# ladder zitten én de commons goed beheren (of omgekeerd); zie 3_design.md.
LEVELS = ["coordination", "cooperation", "convention", "norm", "institution"]
GOVERNANCE = "governance"


def load_thresholds(path=CFG):
    with open(path) as f:
        cfg = yaml.safe_load(f)
    if "order_ladder" not in cfg:
        sys.exit("dv_thresholds.yaml mist het 'order_ladder:'-blok")
    return cfg["order_ladder"]


def _cohesion(agents, memb, A, tau):
    """Fractie agents met thuis-share >= tau (vast/split-ratio, DVs.md)."""
    n, K = len(agents), len(set(memb))
    vast = 0
    for i in range(n):
        s = np.array([A[i, memb == c].sum() for c in range(K)])
        tot = s.sum()
        if tot > 0 and s[memb[i]] / tot >= tau:
            vast += 1
    return vast / n if n else 0.0


def _coordination_coverage(lines, agents, attacks, window):
    """Fractie agents die over het slotvenster tot een PERSISTENTE gecoördineerde
    groep behoort (Koen 2026-07-16 — conventie = stabiele groep die samen dingen
    blijft doen). Een tie telt als coördinerend als het paar in >= min_rounds
    venster-rondes samen overmaakt, berichten, OF samen outsiders aanvalt (zonder
    elkaar aan te vallen — vijandige paren tellen niet). Chaos (schuivende,
    eenmalige ties) -> lage coverage -> coordination, niet convention."""
    aset = set(agents)
    rounds = sorted({d.get("round") for d in lines})
    W = set(rounds[-window:]) if rounds else set()
    hostile = {tuple(sorted((a, t))) for (rd, a, t) in attacks
               if a in aset and t in aset}
    from collections import defaultdict
    tie_rounds = defaultdict(set)
    for d in lines:
        rd = d.get("round")
        if rd not in W:
            continue
        ag = d.get("agents") or {}
        for aid, i in ag.items():
            a = osuite.cat(osuite.effective_action(i))
            if a == "transfer" and i.get("target"):
                tie_rounds[tuple(sorted((aid, i["target"])))].add(rd)
        for m in (d.get("messages") or []):
            to = m.get("to")
            tos = to if isinstance(to, list) else ([] if to in (None, "all") else [to])
            for t in tos:
                if m.get("from"):
                    tie_rounds[tuple(sorted((m["from"], t)))].add(rd)
        atk = [(aid, i.get("target")) for aid, i in ag.items()
               if osuite.cat(osuite.effective_action(i)) == "take" and i.get("target")]
        for x in range(len(atk)):
            for y in range(x + 1, len(atk)):
                (a1, t1), (a2, t2) = atk[x], atk[y]
                if a1 != a2 and t1 != a2 and t2 != a1:
                    tie_rounds[tuple(sorted((a1, a2)))].add(rd)
    covered = set()
    for pair, rds in tie_rounds.items():
        if len(rds) >= 3 and pair not in hostile:
            covered.update(pair)
    return len(covered) / len(agents) if agents else 0.0


def _coalition_matrix(agents, attacks):
    """Alliantie-matrix: agents die SAMEN outsiders aanvallen en elkaar NIET
    aanvallen (Koen 2026-07-16 — dezelfde subgroep aanvallers = coalitie = een
    vorm van conventie). Cm[i,j] = # rondes waarin i en j allebei aanvielen,
    geen van beiden de ander als doelwit had; op 0 gezet als ze elkaar OOIT
    aanvielen (dan zijn het vijanden, geen bondgenoten). Alles-tegen-allen ->
    geen coalitie -> geen structuur."""
    idx = {a: i for i, a in enumerate(agents)}
    n = len(agents)
    Cm = np.zeros((n, n))
    hostile = set()
    by_round = {}
    for (rd, a, t) in attacks:
        if a in idx and t in idx:
            hostile.add((idx[a], idx[t])); hostile.add((idx[t], idx[a]))
        by_round.setdefault(rd, []).append((a, t))
    for rd, acts in by_round.items():
        attackers = [(idx[a], t) for (a, t) in acts if a in idx]
        for x in range(len(attackers)):
            for y in range(x + 1, len(attackers)):
                i, ti = attackers[x]; j, tj = attackers[y]
                if i == j:
                    continue
                # bondgenoten: geen van beiden viel de ander aan deze ronde
                if ti != agents[j] and tj != agents[i]:
                    Cm[i, j] += 1; Cm[j, i] += 1
    # vijanden ontkoppelen (ooit elkaar aangevallen -> geen alliantie)
    for (i, j) in hostile:
        Cm[i, j] = 0.0
    return Cm


def _rewire_rates(lines):
    """(vroege, late) drop+invite-acties per ronde (helft/helft-split).
    None als de run de affordance niet heeft (geen enkele rewire-poging)."""
    per_round = []
    for d in lines:
        c = sum(1 for info in (d.get("agents") or {}).values()
                if osuite.cat(osuite.effective_action(info)) in ("drop", "invite"))
        per_round.append(c)
    if not any(per_round):
        return None
    h = len(per_round) // 2 or 1
    return (float(np.mean(per_round[:h])), float(np.mean(per_round[h:])))


def gate_run(path, thr):
    lines = osuite.load(path)
    agents, T, Mc, attacks, per_round = osuite.parse(lines)
    W = int(thr["window"])
    gates, detail = {}, {}

    # persistente-coördinatie-coverage (transfer/bericht/coalitie over >=3
    # venster-rondes) — draagt zowel de cooperation- als de convention-poort.
    coverage = _coordination_coverage(lines, agents, attacks, W)

    # ── 1 cooperation: volgehouden gecoördineerde GEZAMENLIJKE actie ─────────
    # Verbreed (Koen 2026-07-16): reciprociteit (naar elkaar overmaken) ÓF een
    # volgehouden coalitie (samen als groep optreden) — samen aanvallen is ook
    # een coöperatiegroep. Repareert de nesting: een predatie-coalitie zakt niet
    # meer door de cooperation-trede.
    late = per_round[-W:]
    n_tr = sum(r["counts"].get("transfer", 0) for r in late)
    n_all = sum(sum(r["counts"].values()) for r in late)
    tshare = n_tr / n_all if n_all else 0.0
    recip = sum(1 for (a, b), v in T.items()
                if a < b and v > 0 and T.get((b, a), 0) > 0)
    reciprocity = tshare >= thr["coop_transfer_share"] and recip >= thr["coop_recip_dyads"]
    gates["cooperation"] = bool(reciprocity or coverage >= thr.get("coop_coverage_min", 0.3))
    detail["transfer_share_lastW"] = round(tshare, 3)
    detail["recip_dyads"] = recip

    # ── 2 convention: persistente coördinerende subgroep (Koen 2026-07-16) ──
    # Lewis-getrouw verbreed: een conventie is een STABIELE cluster die samen
    # dingen blijft doen — of ze nu naar elkaar overmaken (coöperatie), elkaar
    # berichten (communicatie), OF samen buitenstaanders aanvallen (coalitie).
    # Gaat NIET om mob-grootte of focal doelwit (blijkt uit de data, deep-dive),
    # maar om DEZELFDE subgroep die aanhoudend coördineert. Coalitie-edge: agents
    # die samen outsiders aanvallen en elkaar NIET aanvallen (alles-tegen-allen
    # heeft geen coalitie -> geen conventie). Gate = echte clusterstructuur
    # (coverage boven; Q gerapporteerd als detail).
    gates["convention"] = bool(coverage >= thr.get("conv_coverage_min", 0.5))
    detail["coord_coverage"] = round(coverage, 2)
    if HAVE_LEIDEN:                                  # Q + clusters: gerapporteerd, niet gepoort
        Cm = _coalition_matrix(agents, attacks)
        memb, Q, A, Tm, idx = osuite.subgroups(
            agents, T, Mc, thr["alpha"], Cm=Cm, coal_weight=thr.get("conv_coal_weight", 1.0))
        detail["Q"] = round(float(Q), 3)
        detail["n_clusters"] = len(set(memb))
        detail["cohesion"] = round(_cohesion(agents, memb, A, thr["tau"]), 2)
        detail["coalition_ties"] = int((Cm > 0).sum() // 2)

    # ── 3 norm: collectieve deontische prescriptie (CO's ADIC — GEEN handhaving)
    # Koen 2026-07-16: CO's grammatica heeft DRIE niveaus. Norm (ADIC) = een
    # collectief-voorschrijvende deontische uiting ("we must hold", "attacking is
    # a violation of the NAP") — handhaving is NIET vereist; dat is het rule/
    # institutie-niveau (ADICO). Een ingeroepen-maar-onafgedwongen norm is een
    # norm. Daarom: sanctie-EIS eruit (die hoorde bij institutie).
    #
    # PUBLIC-ONLY (Koen 2026-07-17): een norm is per definitie een COLLECTIEF
    # object — een gedeelde ought die publiek wordt ingeroepen (Bicchieri's
    # normatieve verwachting; CO's ADIC-prescriptie is een uiting IN de gedeelde
    # ruimte). Een privé-note is een privé-overtuiging, geen norm. De poort kijkt
    # daarom ALLEEN naar publieke berichten. Privé-dichtheid blijft gerapporteerd
    # als secundaire observatie (internalisering), maar poort NIET meer.
    # Consequentie: zonder kanaal (comms-off) is er per definitie geen publieke
    # norm — de comms-off norm-afwezigheid is dan DEFINITORISCH, niet empirisch;
    # de falsifieerbare comms-off-voorspellingen zijn (i) coöp overleeft +
    # (iii) geweld blijft uit (zie §3/§5). Grensgeval-drijver weg: de dunne
    # private Sugden-route telde strategisch "we should grow"-geklets als norm
    # (Gemini/DeepSeek-probes 2026-07-17) — die rand is nu dicht.
    deo = deontic.analyze(path)
    gates["norm"] = bool(deo["norm"] >= thr["norm_density_min"])
    detail["norm_density_pub"] = round(deo["norm"], 4)
    detail["norm_density_priv"] = round(deo["priv"]["norm"], 4)  # gerapporteerd, poort NIET
    detail["sanctions"] = deo["sanction"]

    # ── 4 institution: norm + HANDHAVING van overtreding (Crawford-Ostrom OR ELSE)
    # PRIMAIRE DEFINITIE (Koen 2026-07-16): CO's rule = norm + "the OR ELSE, the
    # sanction assigned to detected NONCOMPLIANCE with an institutional statement"
    # (p.586). Cumulatief (via nesting: norm moet al passen). Institutie = er wordt
    # gehandhaafd op een OVERTREDING, niet louter gecoördineerde agressie op een
    # focal doelwit ("level the whale" = conventie). enforcement.py co_enforce_rate
    # meet precies dit (violatie-lexicon + nabijheid). Searle's benoemde-structuur
    # is een APARTE, secundaire as (named_bespoke in detail), niet de gate.
    # Institutie-poort (Koen 2026-07-16): handhaving INGEROEPEN/aanwezig — er is
    # minstens een echte poging tot sanctie op een overtreder (>= inst_min_enforce
    # violatie-geframede sancties). CO-grammatica-getrouw + Aoki: een institutie is
    # een gedeeld-geloof-evenwicht; handhaving is een off-path dreiging die zelden
    # uitgevoerd hoeft. De EFFECTIVITEIT (uitgevoerde handhaving = co_enforce_rate,
    # 'kerst op de taart') en het STANDHOUDEN (P3, apart) zijn aparte maten — een
    # institutie mag instorten (oorlogs-ruïne = ingeroepen maar hol, geen vertrouwen).
    # COLLECTIEF gedragen (Koen 2026-07-16): één agent die "ik straf schenders"
    # roept zonder dat anderen het overnemen = cheap talk = conventie, geen
    # institutie. Bicchieri (norm = collectieve verwachting) + Searle (collectieve
    # acceptatie): handhaving moet van >= inst_min_enforcers distincte handhavers
    # komen. n_enforcers uit enforcement.py (bron-agents van violatie-sancties).
    enf = enforcement.analyze(path)
    co_enforcers = len({t[1] for t in enf.get("co_triples", [])})  # distincte violatie-handhavers
    gates["institution"] = bool(
        enf["n_co_enforce"] >= thr.get("inst_min_enforce", 3)
        and co_enforcers >= thr.get("inst_min_enforcers", 2))
    detail["n_co_enforce"] = enf["n_co_enforce"]          # handhaving aanwezig (poort)
    detail["n_co_enforcers"] = co_enforcers              # collectief gedragen (poort)
    detail["co_enforce_rate"] = round(enf["co_enforce_rate"], 3)  # effectiviteit/degree (kerst)

    # CO-NESTING: institutie ⟹ norm (Koen 2026-07-21, rewpar-diagnose). Een
    # institutie handhaaft de OVERTREDING van een norm; je kunt geen breuk van een
    # niet-bestaande regel bestraffen. Collectieve handhaving van een BENOEMDE
    # overtreding ("this is a violation of our NAP", "X is a traitor") is dus zélf
    # bewijs dat de norm publiek operatief is — de norm wordt ingeroepen-via-z'n-breuk.
    # De norm-DICHTHEIDS-poort (regel 231) telt expliciete prescriptie ("we must
    # hold"), maar de schendings-vorm zit in het violatie-lexicon (enforcement.py) en
    # telt daar apart. Zonder deze regel mist de nesting een echte institutie zodra
    # normativiteit als schendings-taal wordt uitgedrukt (oorlogscellen) — false-
    # negative op rewpar (norm_density 0.0134 < 0.02, maar 29 handhavers straffen
    # NAP-verraad). Een vurende institutie bevredigt daarom het norm-niveau. De
    # STANDALONE norm-trede (prescriptie zónder handhaving) blijft op de dichtheids-
    # poort staan — dit raakt alleen runs die al institution-handhaving vertonen.
    if gates["institution"]:
        gates["norm"] = True
        detail["norm_via_enforcement"] = True   # norm afgeleid uit handhaving, niet dichtheid

    # Secundaire as (Searle, GERAPPORTEERD niet gepoort): benoemde publiek
    # circulerende bespoke-structuur. NAP e.d. = baseline (universeel vanaf R<=5).
    named, _raw, coverage = detect_named_structures(lines)
    if thr.get("inst_public_only", True):
        import re as _re
        msgs = [((m.get("from") or ""), (m.get("text") or ""))
                for d in lines for m in (d.get("messages") or [])]
        pub_named = {}
        for nm, cnt in named.items():
            rx = _re.compile(_re.escape(nm), _re.I)
            occ, senders = 0, set()
            for frm, txt in msgs:
                k = len(rx.findall(txt))
                if k:
                    occ += k
                    senders.add(frm)
            if (occ >= thr.get("inst_min_occurrences", 3)
                    and len(senders) >= thr.get("inst_min_agents", 2)):
                pub_named[nm] = occ
        prive_only = {n: c for n, c in named.items() if n not in pub_named}
        if prive_only:
            detail["named_private_only"] = dict(
                sorted(prive_only.items(), key=lambda kv: -kv[1])[:5])
        named = pub_named
    baseline_names = {n.lower() for n in thr.get("inst_baseline_names", [])}
    bespoke = {n: c for n, c in named.items() if n.lower() not in baseline_names}
    detail["named_bespoke"] = dict(sorted(bespoke.items(), key=lambda kv: -kv[1])[:5])
    detail["named_baseline"] = {n: c for n, c in named.items()
                                if n.lower() in baseline_names}
    # muntmoment (coinage): eerste ronde waarin een bespoke naam valt — een
    # invented naam heeft een aanwijsbare bron + diffusie; baseline-termen niet.
    if bespoke:
        firsts = {}
        for d in lines:
            r = d.get("round") or 0
            texts = [m.get("text") or "" for m in (d.get("messages") or [])]
            texts += [a.get(f) or "" for a in (d.get("agents") or {}).values()
                      for f in ("memory", "thinking")]
            blob = " ".join(texts).lower()
            for nm in bespoke:
                if nm not in firsts and nm.lower() in blob:
                    firsts[nm] = r
        detail["bespoke_first_round"] = firsts

    # ── governance: APARTE AS (resource-orde, niet geneste trede) ───────────
    # Alleen T4; leest of collectieve terughoudendheid de commons levend houdt.
    # Los van de sociale-orde-nesting: een T4-run krijgt een sociaal label EN
    # (indien commons) een governance-label.
    cm = commons_dv.commons_metrics(lines)
    if cm is None:
        governance = None                # geen commons
        detail["commons"] = None
    else:
        governance = bool(cm.get("sustained"))
        detail["commons"] = {k: cm.get(k) for k in
                             ("collapsed", "sustained", "stock_final")}
    gates["governance"] = governance     # gerapporteerd naast de ladder

    # ── nested sociaal-orde-label: hoogste k waarvoor 1..k allemaal passen ──
    nested = 0
    for k, lvl in enumerate(LEVELS[1:], start=1):
        if gates.get(lvl) is True:
            nested = k
        elif gates.get(lvl) is False:
            break
        else:               # None (n.v.t./niet berekenbaar): stopt de klim
            break
    highest_any = max((k for k, lvl in enumerate(LEVELS[1:], start=1)
                       if gates.get(lvl) is True), default=0)
    return dict(name=os.path.basename(path), gates=gates,
                nested_label=LEVELS[nested], nested_level=nested,
                highest_any=LEVELS[highest_any],
                governance=governance, detail=detail)


def print_row(r):
    g = r["gates"]
    def sym(v):
        return {True: "+", False: "-", None: "."}[v]
    vec = " ".join(f"{lvl[:4]}{sym(g[lvl])}" for lvl in LEVELS[1:])
    gov = {True: "sustained", False: "collapsed", None: "n/a"}[r["governance"]]
    print(f"{r['name'][:40]:40s} [{vec}]  nested={r['nested_label']:12s}"
          f" any={r['highest_any']:12s} gov={gov}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--batch", help="map met *_reasoning_live.jsonl")
    ap.add_argument("--frozen", action="store_true",
                    help="pre-reg-mode: geen CLI-overrides toegestaan")
    ap.add_argument("--json", action="store_true", help="volledige JSON-output")
    ap.add_argument("--norm-density-min", type=float, default=None)
    ap.add_argument("--conv-q-min", type=float, default=None)
    args = ap.parse_args()

    thr = load_thresholds()
    overrides = {"norm_density_min": args.norm_density_min,
                 "conv_q_min": args.conv_q_min}
    if any(v is not None for v in overrides.values()):
        if args.frozen:
            sys.exit("--frozen: CLI-overrides geblokkeerd (pre-reg-mode)")
        thr.update({k: v for k, v in overrides.items() if v is not None})

    paths = list(args.paths)
    if args.batch:
        paths += sorted(glob.glob(os.path.join(args.batch, "*_reasoning_live.jsonl")))
    if not paths:
        sys.exit("geen input (paths of --batch)")

    print(f"order-ladder gate  (drempels: {'FROZEN' if args.frozen else 'v0 PROPOSED'})")
    print(f"legenda: + pas, - faal, . n.v.t./onberekenbaar; nested = pre-reg-label\n")
    for p in paths:
        r = gate_run(p, thr)
        if args.json:
            print(json.dumps(r, default=str))
        else:
            print_row(r)


if __name__ == "__main__":
    main()
