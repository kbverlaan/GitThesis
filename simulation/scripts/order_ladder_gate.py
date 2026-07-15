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
from classify_run import detect_named_structures
from order_suite import HAVE_LEIDEN

CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config",
                   "dv_thresholds.yaml")

LEVELS = ["coordination", "cooperation", "convention", "norm",
          "institution", "governance"]


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

    # ── 1 cooperation: volgehouden reciprociteit in het slotvenster ─────────
    late = per_round[-W:]
    n_tr = sum(r["counts"].get("transfer", 0) for r in late)
    n_all = sum(sum(r["counts"].values()) for r in late)
    tshare = n_tr / n_all if n_all else 0.0
    recip = sum(1 for (a, b), v in T.items()
                if a < b and v > 0 and T.get((b, a), 0) > 0)
    gates["cooperation"] = (tshare >= thr["coop_transfer_share"]
                            and recip >= thr["coop_recip_dyads"])
    detail["transfer_share_lastW"] = round(tshare, 3)
    detail["recip_dyads"] = recip

    # ── 2 convention: gekristalliseerde partnerstructuur (achter de Q-gate) ─
    if HAVE_LEIDEN:
        memb, Q, A, Tm, idx = osuite.subgroups(agents, T, Mc, thr["alpha"])
        coh = _cohesion(agents, memb, A, thr["tau"])
        conv = Q >= thr["conv_q_min"] and coh >= thr["conv_cohesion_min"]
        rw = _rewire_rates(lines)
        if rw is not None:  # assoc-rung: structuur moet ook stollen
            early, late_r = rw
            crystallized = (early == 0) or (late_r <= thr["conv_rewire_ratio"] * early)
            conv = conv and crystallized
            detail["rewire_early_late"] = (round(early, 2), round(late_r, 2))
        gates["convention"] = bool(conv)
        detail["Q"] = round(float(Q), 3)
        detail["cohesion"] = round(coh, 2)
    else:
        gates["convention"] = None
        detail["Q"] = detail["cohesion"] = None

    # ── 3 norm: collectieve prescriptie + sanctie-taal (publieke laag) ──────
    deo = deontic.analyze(path)
    gates["norm"] = (deo["norm"] >= thr["norm_density_min"]
                     and deo["sanction"] >= thr["norm_sanction_min"])
    detail["norm_density_pub"] = round(deo["norm"], 4)
    detail["sanctions"] = deo["sanction"]

    # ── 4 institution: benoemde persistente structuur (pre-reg-gate) ────────
    named, _raw, coverage = detect_named_structures(lines)
    gates["institution"] = len(named) >= thr["inst_min_structures"]
    detail["named_structures"] = dict(named.most_common(5))

    # ── 5 governance: commons volgehouden (alleen T4) ───────────────────────
    cm = commons_dv.commons_metrics(lines)
    if cm is None:
        gates["governance"] = None       # niet van toepassing (geen commons)
        detail["commons"] = None
    else:
        # NB drempel-herkomst: commons_dv 'sustained' gebruikt nu nog K/2 —
        # STALE t.o.v. frozen engine (regen x1.5 => engine-anker 2/3*K).
        # Waarde is KOEN-beslissing na de T4-smoke; hier alleen doorgeven.
        gates["governance"] = bool(cm.get("sustained"))
        detail["commons"] = {k: cm.get(k) for k in
                             ("collapsed", "sustained", "stock_final")}

    # ── nested label: hoogste k waarvoor 1..k allemaal passen ───────────────
    nested = 0
    for k, lvl in enumerate(LEVELS[1:], start=1):
        if gates.get(lvl) is True:
            nested = k
        elif gates.get(lvl) is False:
            break
        else:               # None (n.v.t./niet berekenbaar): telt niet mee,
            break           # maar laat hogere treden ook niet passeren
    highest_any = max((k for k, lvl in enumerate(LEVELS[1:], start=1)
                       if gates.get(lvl) is True), default=0)
    return dict(name=os.path.basename(path), gates=gates,
                nested_label=LEVELS[nested], nested_level=nested,
                highest_any=LEVELS[highest_any], detail=detail)


def print_row(r):
    g = r["gates"]
    def sym(v):
        return {True: "+", False: "-", None: "."}[v]
    vec = " ".join(f"{lvl[:4]}{sym(g[lvl])}" for lvl in LEVELS[1:])
    print(f"{r['name'][:44]:44s} [{vec}]  nested={r['nested_label']:12s}"
          f" any={r['highest_any']}")


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
