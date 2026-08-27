"""Coined terms with their life span, cached so the drawing can be iterated on.

Reading the logs for six cells takes minutes; redrawing a figure should take
seconds. The cache is keyed on nothing --- delete the file to rebuild it --- and
it is a drawing aid, never a source: the numbers that go in the chapter come
from registry.py, and this exists only so a plot can be nudged twenty times.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _m in ("core", "_shared"):
    sys.path.insert(0, str(HERE.parent / _m))

import text as tekst   # noqa: E402
import runset          # noqa: E402

CACHE = HERE / "out" / "_terms.json"
CELLS = [f"prod_{r}_{p}" for r in ("L2", "L3") for p in ("scar", "knife", "abund")]


def terms(refresh: bool = False) -> dict:
    """{cell: [{term, run, speakers, first, last, life, rounds_said}]}"""
    if CACHE.exists() and not refresh:
        return json.loads(CACHE.read_text())
    out = {}
    for c in CELLS:
        rows = []
        for p in runset.cel(c):
            for naam, v in tekst.named_agreements(p, with_rounds=True).items():
                if not v["rounds"]:
                    continue
                rows.append({"term": naam, "run": p.name.split("__")[1].split("_")[0],
                              "speakers": v["users"],
                              "first": min(v["rounds"]), "last": max(v["rounds"]),
                              "life": max(v["rounds"]) - min(v["rounds"]) + 1,
                              "rounds_said": len(set(v["rounds"])),
                              "by_round": v["speakers_by_round"]})
        out[c] = rows
        print(f"   {c:16} {len(rows):3} terms over {len(runset.cel(c))} runs")
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(uit))
    return out


if __name__ == "__main__":
    terms(refresh="--refresh" in sys.argv)
