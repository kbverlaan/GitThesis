#!/usr/bin/env python3
"""rewire_baseline.py — L3 netwerk-reciprociteit-baseline (Santos 2006, Rand 2011).

L1/L2/L4 worden tegen een afgeleide verwachting gelezen (stag-hunt, combat,
commons-overshoot); L3 (associatie/rewiring) had er geen. Netwerk-reciprociteit
vult dit: hogere rewiring-rate -> meer cooperatie + meer stabiliteit, CONDITIONEEL
op snel genoeg herbedraden (Rand 2011: fluid ~30%/ronde wel, viscous ~10% niet;
Santos 2006: pas boven een kritische tijdschaal-ratio W). Eigen stance blijft
agnostisch (rewiring voegt vooral complexiteit toe) -> dit is een te TOETSEN
voorspelling, geen aanname; Santos/Rand zijn niet-LLM (structurele analogie).

Per run: rewiring-rate, netto-rewire, cooperatie (transfer-share), instabiliteit
(consensus-std, zelfde maat als batch_suite). Over een L3-sweep-map: rang-correlatie
(Spearman) van rewiring-rate met cooperatie en met stabiliteit + een drempel(knik)-
check (mediaan-split) -- want de voorspelling is niet-lineair, niet monotoon.

Gebruik:
    python scripts/rewire_baseline.py RUN.jsonl          # per-run maten
    python scripts/rewire_baseline.py L3_SWEEP_DIR/       # + Santos/Rand-correlatie
"""
import json, glob, os, argparse
import numpy as np


def cat(a):
    """Categoriseer de primaire actie (zelfde mapping als batch_suite.py)."""
    if a is None:
        return 'hold'
    a = str(a).lower()
    if a.startswith('invest') or a == 'transfer':
        return 'transfer'
    if a.startswith('take') or a == 'attack':
        return 'take'
    if 'arm_self' in a or 'strengthen_self' in a:
        return 'strengthen_self'
    if 'arm' in a or 'strengthen' in a:
        return 'strengthen_other'
    return 'hold'


def analyze(path):
    rounds = [json.loads(l) for l in open(path) if l.strip()]
    nr = len(rounds)
    if nr < 2:
        return None
    drops = invites = n_act = n_transfer = 0
    cons = []
    for d in rounds:
        ag = d.get('agents') or {}
        cc = {}
        for aid, info in ag.items():
            c = cat(info.get('action'))
            cc[c] = cc.get(c, 0) + 1
            n_act += 1
            if c == 'transfer':
                n_transfer += 1
            ri = info.get('rewire_intent') or {}
            if ri.get('drop'):
                drops += 1
            if ri.get('invite'):
                invites += 1
        n = sum(cc.values()) or 1
        cons.append(max(cc.values()) / n if cc else 0)      # consensus = modale actie-share
    return dict(name=os.path.basename(path), nr=nr,
                rewiring_rate=(drops + invites) / nr,
                net_rewire=(invites - drops) / nr,
                transfer_share=n_transfer / n_act if n_act else 0.0,
                cons_std=float(np.std(cons)))                # instabiliteit (golf)


def spearman(x, y):
    """Rang-correlatie zonder scipy (Pearson op de rangen).
    Guard op de variantie van de ORIGINELE waarden: bij een constante reeks
    (bv. coop=0.00 in een pure-conflict-cel) levert argsort een spurieuze rangorde
    met niet-nul std -> dat zou een valse rho=+/-1.0 geven. Dan: nan."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < 3 or x.std() == 0 or y.std() == 0:
        return float('nan')
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    return float(np.corrcoef(rx, ry)[0, 1])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", help="een RUN.jsonl of een L3-sweep-map met *_reasoning_live.jsonl")
    args = p.parse_args()

    if os.path.isdir(args.path):
        files = sorted(glob.glob(os.path.join(args.path, "*_reasoning_live.jsonl")))
        rows = [r for r in (analyze(f) for f in files) if r]
        if not rows:
            print("geen runs gevonden")
            return
        print(f"\nL3 netwerk-reciprociteit-baseline  ({len(rows)} runs in {args.path})\n")
        print(f"  {'run':<50} {'rewire/r':>9} {'netto':>7} {'coop':>6} {'instab':>7}")
        for r in sorted(rows, key=lambda r: -r['rewiring_rate']):
            print(f"  {r['name'][:49]:<50} {r['rewiring_rate']:9.2f} {r['net_rewire']:+7.2f} "
                  f"{r['transfer_share']:6.2f} {r['cons_std']:7.3f}")
        rw = np.array([r['rewiring_rate'] for r in rows])
        coop = np.array([r['transfer_share'] for r in rows])
        instab = np.array([r['cons_std'] for r in rows])
        print(f"\n  Santos/Rand-voorspelling (rang-correlatie over de sweep):")
        # Spreidings-guard: de correlatie is alleen zinvol als coop EN rewire echt
        # varieren over de runs. Bij te weinig spreiding (bv. replicates van EEN
        # cel, of een pure-conflict-regime met coop~0) is de rho ruis op stof.
        if np.ptp(coop) < 0.03 or np.ptp(rw) < 0.10:
            print(f"    (!) te weinig spreiding: coop-range {np.ptp(coop):.3f}, rewire-range {np.ptp(rw):.2f}")
            print(f"        -> waarschijnlijk EEN cel/replicates of een coop~0-regime, GEEN payoff-sweep;")
            print(f"           correlatie niet zinvol. Draai op een echte L3 g_inv-sweep.")
        else:
            print(f"    rewiring-rate vs cooperatie  : rho = {spearman(rw, coop):+.2f}  (voorspeld: +)")
            print(f"    rewiring-rate vs stabiliteit : rho = {spearman(rw, -instab):+.2f}  "
                  f"(voorspeld: +; hoge rewire -> lage instab)")
            med = float(np.median(rw))
            hi = coop[rw >= med]; lo = coop[rw < med]
            if len(hi) and len(lo):
                print(f"    drempel-knik (mediaan rewire={med:.2f}): coop hoog-rewire {hi.mean():.2f} "
                      f"vs laag-rewire {lo.mean():.2f}")
                print(f"      -> Santos/Rand: het effect zit bij de knik (niet-lineair), niet in een monotone lijn.")
        print(f"\n  NB: te toetsen voorspelling, geen aanname; Santos/Rand = niet-LLM (analogie).")
    else:
        r = analyze(args.path)
        if not r:
            print("run te kort")
            return
        print(f"\n{r['name']}  ({r['nr']} rondes)")
        print(f"  rewiring-rate   {r['rewiring_rate']:.2f}/ronde   netto {r['net_rewire']:+.2f}/ronde")
        print(f"  cooperatie (transfer-share)   {r['transfer_share']:.2f}")
        print(f"  instabiliteit (consensus-std) {r['cons_std']:.3f}")
        print(f"  (de Santos/Rand-correlatie vereist een sweep-map met meerdere L3-runs)")


if __name__ == "__main__":
    main()
