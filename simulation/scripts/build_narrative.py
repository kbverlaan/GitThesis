#!/usr/bin/env python3
"""
build_narrative.py — zet een reasoning_live.jsonl om in een LEESBAAR transcript.

Doel: uit de ruwe per-ronde JSONL alle BERICHTGEVING + ACTIES (+ optioneel de
memory-notes) halen, zodat een mens of een LLM-subagent het volledige verhaal
van een run kan reconstrueren. De `thinking`-velden worden bewust WEGGELATEN
(te groot: ~4k tokens x 30 agents x 30 rondes).

Gebruik:
    python scripts/build_narrative.py RUN.jsonl                 # -> stdout
    python scripts/build_narrative.py RUN.jsonl -o out.md       # -> bestand
    python scripts/build_narrative.py RUN.jsonl --no-notes      # zonder memory-notes
    python scripts/build_narrative.py RUN.jsonl --no-messages   # alleen acties

Per ronde toont het transcript:
  - kop met totale resources + #agents die nog 'mee doen' (R >= 10% van start)
  - ACTIES: agent: action(->target)  [R: resources, delta t.o.v. vorige ronde]
  - MESSAGES: from -> [to]: "text"
  - NOTES (optioneel): agent: "memory-note van die ronde"
"""
import json, argparse, sys
from collections import defaultdict


def act_str(info):
    """Compacte actie-omschrijving: 'take->Pearl' / 'transfer->Cyan' / 'hold'."""
    a = (info.get("action") or "hold")
    tg = info.get("target")
    return f"{a}->{tg}" if tg else a


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def build(rounds, with_messages=True, with_notes=True):
    out = []
    # start-resources per agent (ronde 1) voor de 'meedoen'-drempel + delta's
    initR = {a: i.get("resources") for a, i in rounds[0].get("agents", {}).items()}
    prevR = dict(initR)

    for d in rounds:
        rnum = d.get("round")
        ag = d.get("agents", {})
        Rs = {a: i.get("resources") for a, i in ag.items()}
        tot = sum(v for v in Rs.values() if v is not None)
        # 'meedoen' = nog >= 10% van eigen start-resources (lethal pot plukt kaal i.p.v. doodt)
        ndoen = sum(1 for a, v in Rs.items()
                    if v is not None and initR.get(a) and v >= 0.10 * initR[a])

        out.append(f"\n{'='*70}\n## Ronde {rnum}   (totaal R {tot:.0f} | meedoen {ndoen}/{len(ag)})\n")

        # ── ACTIES (gesorteerd op resources, rijkste eerst — zo lees je de hiërarchie) ──
        out.append("ACTIES:")
        for aid, info in sorted(ag.items(), key=lambda kv: -(kv[1].get("resources") or 0)):
            R = info.get("resources")
            d_ = (R - prevR[aid]) if (R is not None and prevR.get(aid) is not None) else 0.0
            arm = info.get("arm_bonus") or 0.0
            armtxt = f" arm+{arm:.0f}" if arm > 0.5 else ""
            out.append(f"  {aid:<9} {act_str(info):<18} [R {R:.1f}{f', d{d_:+.1f}' if abs(d_)>=0.1 else ''}{armtxt}]")

        # ── MESSAGES ──
        if with_messages:
            msgs = d.get("messages", []) or []
            out.append("\nMESSAGES:" if msgs else "\nMESSAGES: (geen)")
            for m in msgs:
                to = m.get("to")
                to_s = ",".join(to) if isinstance(to, list) else (to or "all")
                txt = (m.get("text") or "").replace("\n", " ").strip()
                out.append(f"  {m.get('from')} -> [{to_s}]: \"{txt}\"")

        # ── MEMORY-NOTES (de 'running understanding' van elke agent) ──
        if with_notes:
            out.append("\nNOTES:")
            for aid, info in sorted(ag.items(), key=lambda kv: -(kv[1].get("resources") or 0)):
                note = (info.get("memory") or "").replace("\n", " ").strip()
                if note:
                    out.append(f"  {aid}: \"{note}\"")

        prevR = {a: (v if v is not None else prevR.get(a)) for a, v in Rs.items()}

    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("jsonl")
    p.add_argument("-o", "--out")
    p.add_argument("--no-messages", action="store_true")
    p.add_argument("--no-notes", action="store_true")
    p.add_argument("--from", dest="rfrom", type=int, default=None, help="alleen rondes >= dit nummer")
    p.add_argument("--to", dest="rto", type=int, default=None, help="alleen rondes <= dit nummer")
    args = p.parse_args()

    rounds = load(args.jsonl)
    if args.rfrom is not None:
        rounds = [d for d in rounds if (d.get("round") or 0) >= args.rfrom]
    if args.rto is not None:
        rounds = [d for d in rounds if (d.get("round") or 0) <= args.rto]
    cfg = rounds[0].get("config", {}) if rounds else {}
    header = (f"# Narratief-transcript: {args.jsonl.split('/')[-1]}\n"
              f"# rondes: {len(rounds)} | agents: {len(rounds[0].get('agents', {}))}\n"
              f"# config: {json.dumps(cfg)[:300]}\n")
    body = build(rounds, with_messages=not args.no_messages, with_notes=not args.no_notes)
    text = header + body

    if args.out:
        open(args.out, "w").write(text)
        print(f"geschreven: {args.out} ({len(text):,} tekens, ~{len(text)//4:,} tokens)", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
