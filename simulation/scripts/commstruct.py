#!/usr/bin/env python3
"""
commstruct.py — COMMUNICATIE-STRUCTUUR marker (no-LLM, puur telwerk).

De VORM-as van de communicatie-familie, orthogonaal aan de inhoud-markers
(deontic/enforcement/named-institution). Geen lexicon -> de robuustste DV voor
appendix-statistiek. Beantwoordt de oorspronkelijke vraag: hoeveel messagen
agents, en zijn het DM's of groepsberichten?

Hypothese: een INSTITUTIE kondigt publiek af (broadcasts hoog, reach hoog);
een MOB fluistert/smeedt (DM's hoog); een DIALOOG-orde is wederkerig (reciprociteit
hoog) vs. een PROPAGANDA/COMMANDO-orde zendt eenrichtings (hub-concentratie hoog).

Maten per run (alleen niet-verzadigde, discriminerende maten — zie KALIBRATIE):
  - breedte      : gem. # ontvangers per bericht               (targeting-breedte)
  - dm_rate      : fractie berichten met PRECIES 1 ontvanger   (privE/samenzwering)
  - broad_rate   : fractie berichten met >= 5 ontvangers       (publieke afkondiging)
  - reach        : gem. # unieke ontvangers per zender / (n-1) (hoe breed bereikt een agent het veld)
  - in_gini      : gini van RUWE in-degree (# ontvangen berichten/agent)  (ontvang-concentratie)
  - focus_gini   : gini van GERICHTE in-degree (elk bericht 1/k per ontvanger gewogen)
                   -> dempt broadcast-ruis, meet aandacht die ECHT op enkelen is gericht
  - top_recv     : aandeel van de meest-geadresseerde agent (+ naam) (de communicatie-centrale)

KALIBRATIE (2026-06-20): geschrapt omdat verzadigd/artefact onder de "1 bericht/ronde"-
regel: volume (=1.00 overal), hub_gini-zend (~0: iedereen zendt evenveel), reciprociteit
(~0.9 overal: artefact van brede berichten). Behouden maten discrimineren conflict
(breed/broadcast/hoge reach) scherp van bloei (smal/DM/lage reach).

Gebruik:
    python scripts/commstruct.py RUN.jsonl       # 1 run
    python scripts/commstruct.py DIR/            # triage-ranking over een map
"""
import json, sys, glob, os, argparse
from collections import defaultdict


def gini(xs):
    xs = sorted(xs); n = len(xs); s = sum(xs)
    if n == 0 or s <= 0:
        return 0.0
    return (2 * sum((i + 1) * x for i, x in enumerate(xs))) / (n * s) - (n + 1) / n


def analyze(path):
    rounds = [json.loads(l) for l in open(path) if l.strip()]
    nr = len(rounds)
    agents = set()
    n_msg = 0
    recip_counts = []            # # ontvangers per bericht
    dm = broad = 0
    recipients_of = defaultdict(set)   # zender -> set ontvangers (hele run)
    in_raw = defaultdict(float)        # ontvanger -> # ontvangen berichten (ruw)
    in_focus = defaultdict(float)      # ontvanger -> gerichte aandacht (1/k-gewogen)

    for d in rounds:
        agents.update((d.get("agents") or {}).keys())
        for m in d.get("messages", []) or []:
            frm = m.get("from")
            to = m.get("to")
            tos = to if isinstance(to, list) else ([] if to in (None, "all") else [to])
            tos = [t for t in tos if t and t != frm]
            if not frm or not tos:
                continue
            n_msg += 1
            k = len(tos)
            recip_counts.append(k)
            if k == 1:
                dm += 1
            if k >= 5:
                broad += 1
            for t in tos:
                recipients_of[frm].add(t)
                in_raw[t] += 1.0
                in_focus[t] += 1.0 / k         # broadcast naar 10 -> 0.1 per ontvanger

    n = max(len(agents), 1)
    breedte = (sum(recip_counts) / len(recip_counts)) if recip_counts else 0.0
    dm_rate = dm / n_msg if n_msg else 0.0
    broad_rate = broad / n_msg if n_msg else 0.0
    reach = (sum(len(s) for s in recipients_of.values()) / len(recipients_of) / (n - 1)
             if recipients_of and n > 1 else 0.0)
    # centraliteit: concentratie van inkomende aandacht (niet-ontvangers tellen als 0)
    in_gini = gini([in_raw.get(a, 0.0) for a in agents])
    focus_gini = gini([in_focus.get(a, 0.0) for a in agents])
    tot_focus = sum(in_focus.values())
    top_name = max(in_focus, key=in_focus.get) if in_focus else None
    top_recv = (in_focus[top_name] / tot_focus) if tot_focus else 0.0

    return dict(name=os.path.basename(path), nr=nr, n_msg=n_msg, n=n,
                breedte=breedte, dm_rate=dm_rate, broad_rate=broad_rate, reach=reach,
                in_gini=in_gini, focus_gini=focus_gini, top_recv=top_recv, top_name=top_name)


def print_single(r):
    print(f"\n{r['name']}  ({r['nr']} rondes, {r['n']} agents, {r['n_msg']} berichten)")
    print(f"  breedte      : {r['breedte']:.2f} ontvangers/bericht")
    print(f"  DM-rate      : {r['dm_rate']:.3f}  (1 ontvanger = privE/samenzwering)")
    print(f"  broadcast    : {r['broad_rate']:.3f}  (>=5 ontvangers = publieke afkondiging)")
    print(f"  reach        : {r['reach']:.3f}  (gem. fractie van het veld dat een agent bereikt)")
    print(f"  in-gini      : {r['in_gini']:.3f}  (ruwe ontvang-concentratie)")
    print(f"  focus-gini   : {r['focus_gini']:.3f}  (gerichte-aandacht-concentratie, broadcast-gedempt)")
    print(f"  centrale     : {r['top_name']} ({r['top_recv']:.3f} van alle gerichte aandacht)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("path")
    args = p.parse_args()
    if os.path.isdir(args.path):
        files = sorted(glob.glob(os.path.join(args.path, "*_reasoning_live.jsonl")))
        rows = [analyze(f) for f in files]
        print(f"\nTRIAGE — communicatie-structuur  ({len(rows)} runs in {args.path})\n")
        print(f"  {'run':<44} {'breedte':>8} {'DM%':>6} {'broad%':>7} {'reach':>6} {'inG':>6} {'focusG':>7} {'centrale':>12}")
        for r in rows:
            print(f"  {r['name'][:43]:<44} {r['breedte']:8.2f} {r['dm_rate']:6.3f} "
                  f"{r['broad_rate']:7.3f} {r['reach']:6.3f} {r['in_gini']:6.3f} {r['focus_gini']:7.3f} "
                  f"{(r['top_name'] or '-')[:8]:>8}{r['top_recv']:5.2f}")
    else:
        print_single(analyze(args.path))


if __name__ == "__main__":
    main()
