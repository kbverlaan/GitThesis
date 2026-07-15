#!/usr/bin/env python3
"""Naming-baseline — empirische nulverwachting voor de named-institution-gate.

Vraag: hoe vaak vuurt de named-structure-detector op runs waar GEEN
institutionele orde zou moeten zijn (controle-corpus: bv. oorlogs-runs,
comms-off-runs, vroege vensters)? Dat is de baseline waartegen de
institution-poort (order_ladder:inst_min_structures) gelezen wordt: een
detector-hit telt pas als bewijs als het aantal boven deze baseline ligt.

KOEN wijst het controle-corpus aan (welke runs "geen institutie" zijn is een
inhoudelijk oordeel — hand-label-territorium, geen Claude-keuze).

Gebruik:
  python3 naming_baseline.py <dir-of-paths...> [--early N]
  --early N: tel alleen de eerste N rondes mee (pre-institutie-venster als
             binnen-run-controle, naast het tussen-run-corpus).
"""
import argparse, glob, json, os, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify_run import detect_named_structures


def load(path, early=0):
    lines = [json.loads(l) for l in open(path) if l.strip()]
    if early:
        lines = [d for d in lines if (d.get("round") or 0) <= early]
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--early", type=int, default=0, metavar="N",
                    help="alleen rondes <= N (binnen-run pre-institutie-controle)")
    args = ap.parse_args()

    paths = []
    for p in args.paths:
        paths += (sorted(glob.glob(os.path.join(p, "*_reasoning_live.jsonl")))
                  if os.path.isdir(p) else [p])
    if not paths:
        sys.exit("geen runs gevonden")

    counts = []
    tag = f" (rondes <= {args.early})" if args.early else ""
    print(f"naming-baseline over {len(paths)} runs{tag}\n")
    for p in paths:
        named, _raw, coverage = detect_named_structures(load(p, args.early))
        counts.append(len(named))
        top = ", ".join(f"{n} ({c}x/{coverage[n]}ag)" for n, c in named.most_common(3))
        print(f"  {os.path.basename(p)[:48]:48s} #structuren={len(named):2d}  {top}")

    print(f"\n  baseline: mean {statistics.fmean(counts):.1f} | "
          f"median {statistics.median(counts):.0f} | max {max(counts)} | "
          f"runs met >=1: {sum(1 for c in counts if c)}/{len(counts)}")
    print("  lezing: de institution-poort is pas informatief als de te toetsen")
    print("  runs BOVEN deze verdeling zitten (drempel-beslissing: Koen).")


if __name__ == "__main__":
    main()
