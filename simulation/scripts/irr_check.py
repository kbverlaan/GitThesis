#!/usr/bin/env python3
"""IRR-check — order-ladder-classifier vs handmatige labels (fixplan Fase 3).

Vergelijkt het geneste gate-label (order_ladder_gate.py) met Koens hand-labels
en rapporteert Cohen's kappa (ongewogen + lineair gewogen — de labels zijn
ordinaal, dus gewogen is de primaire maat), de confusion matrix en de
disagreement-lijst (input voor drempel-fine-tune vóór de freeze).

Labels-bestand (YAML), zie handlabels/label_template.yaml:
  runs:
    - path: data/runs/rewire_ab/rewactC_reasoning_live.jsonl
      label: institution          # uit LEVELS, of 'skip'
      note: "Growth Circles, 35 rondes vrede"

Gebruik: python3 irr_check.py handlabels/labels.yaml [--frozen]
"""
import argparse, os, sys
from collections import Counter

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from order_ladder_gate import LEVELS, gate_run, load_thresholds

IDX = {lvl: i for i, lvl in enumerate(LEVELS)}


def cohens_kappa(pairs, weighted=False):
    """pairs = [(hand_idx, gate_idx)]. Lineair gewogen kappa voor ordinale labels."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    k = len(LEVELS)
    O = [[0] * k for _ in range(k)]
    for h, g in pairs:
        O[h][g] += 1
    ph = [sum(O[i]) / n for i in range(k)]           # marginalen hand
    pg = [sum(O[i][j] for i in range(k)) / n for j in range(k)]  # marginalen gate
    if weighted:
        w = lambda i, j: 1 - abs(i - j) / (k - 1)
    else:
        w = lambda i, j: 1.0 if i == j else 0.0
    po = sum(w(i, j) * O[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(w(i, j) * ph[i] * pg[j] for i in range(k) for j in range(k))
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("labels", help="YAML met hand-labels (zie template)")
    ap.add_argument("--frozen", action="store_true")
    args = ap.parse_args()

    with open(args.labels) as f:
        spec = yaml.safe_load(f)
    thr = load_thresholds()

    pairs, rows = [], []
    for entry in spec.get("runs", []):
        hand = (entry.get("label") or "").strip().lower()
        if hand in ("", "skip", "todo"):
            continue
        if hand not in IDX:
            sys.exit(f"onbekend label '{hand}' voor {entry['path']} "
                     f"(kies uit: {', '.join(LEVELS)})")
        r = gate_run(entry["path"], thr)
        pairs.append((IDX[hand], r["nested_level"]))
        rows.append((os.path.basename(entry["path"]), hand, r["nested_label"],
                     entry.get("note", "")))

    if not pairs:
        sys.exit("geen gelabelde runs gevonden (alles 'skip'/'todo'?)")

    agree = sum(1 for h, g in pairs if h == g)
    print(f"IRR — order-ladder gate vs hand-labels  (n={len(pairs)})")
    print(f"  exacte overeenstemming : {agree}/{len(pairs)} ({100*agree/len(pairs):.0f}%)")
    print(f"  Cohen's kappa          : {cohens_kappa(pairs):.3f}")
    print(f"  gewogen kappa (lin.)   : {cohens_kappa(pairs, weighted=True):.3f}  <- primair (ordinaal)")

    print("\nConfusion (rij=hand, kolom=gate; alleen bezette rijen/kolommen):")
    cm = Counter(pairs)
    used = sorted({i for p in pairs for i in p})
    hdr = "          " + " ".join(f"{LEVELS[j][:6]:>6s}" for j in used)
    print(hdr)
    for i in used:
        print(f"{LEVELS[i][:10]:10s}" +
              " ".join(f"{cm.get((i, j), 0):>6d}" for j in used))

    dis = [r for r in rows if r[1] != r[2]]
    if dis:
        print(f"\nDisagreements ({len(dis)}):")
        for name, hand, gate, note in dis:
            print(f"  {name[:40]:40s} hand={hand:12s} gate={gate:12s} {note}")
    else:
        print("\nGeen disagreements.")


if __name__ == "__main__":
    main()
