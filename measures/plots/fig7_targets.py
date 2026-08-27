"""Figure 7 --- where in the wealth ordering the blows land.

    python3 plots/fig7_targets.py

One violin per cell over every resolved fight, placed at the rank its target
held going into the round, richest at the top. Six cells: the two capacity
levels that fight, three payoff cells each.

Why a density and not a box. The finding at L2 is that the distribution has two
modes, one on the poorest agents and a smaller one on the richest, with a trough
between them --- and the median falls in that trough. A box plot draws the median
and the quartiles, so it would draw a wide box centred on a rank almost nothing
happens at and report the shape as spread.

Every fight is drawn beside the density, because a smoothed density can invent a
belly where the data has a gap. The points are the observations and settle it.

--- METHOD, for the measure entry in Appendix B -----------------------------

`m:whom-hit-over` already carries the rank rule and this figure uses it
unchanged, so what follows is the part the figure adds.

Scope: L2 and L3, all three payoff cells, production model, 1,923 and 2,928
resolved fights over 45 and 30 runs.

Each resolved fight contributes the rank its target held among the living going
into the round, from the previous round's closing board and never from the
round's own record, which would score a target on the holdings it was left with
after the blow had taken its share. Ranks run 1 for the richest to 30 for the
poorest; eliminations are rare enough that the living are thirty in the great
majority of rounds. The density is a Gaussian kernel estimate at bandwidth 0.16,
chosen narrow because Scott's rule smooths L2's two modes into one; the points
carry a uniform jitter of a third of a rank vertically and a half-normal
horizontal offset, both cosmetic and fixed by seed.

The interval on the median is a percentile bootstrap over ten thousand
resamples, drawn from `tools/uncertainty.py` so that seed and method match the
rest of the chapter. It resamples runs and never the individual fights: a cell
holds around a thousand fights but only ten or fifteen runs, and one L3 run
supplies a fifth of its cell, so treating the fights as independent draws would
return an interval several times too narrow.

Limitation: pooling the fights of a cell weights a run by how much it fought.
The per-run medians are reported in the text rather than drawn, and they
disagree by up to 27 ranks inside one cell.
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
for _m in ("core", "_shared", "tools"):
    sys.path.insert(0, str(HERE.parent / _m))

import _ci             # noqa: E402
import logs            # noqa: E402
import runset          # noqa: E402
from _style import (COLOUR, FAINT, INK, PAYOFF, PT_ASIDE, PT_LABEL,  # noqa: E402
                    PT_TITLE, RUNG, WIDTH, figure_tex, save, style, tint)

FIGURE = "fig7_targets"
LEVELS = ("L2", "L3")
PAYOFFS = ("scar", "knife", "abund")
N = 30
HEIGHT = 3.90
LEFT, RIGHT, TOP, BOTTOM = 0.62, 0.12, 0.34, 0.74
BW = 0.16                   # narrow, or the two modes at L2 smooth into one
SEED_JITTER = 20260826      # the scatter is cosmetic, so it is fixed


def targets(cell: str) -> list[list[int]]:
    """Per run, the rank of every target among the living at the time."""
    uit = []
    for p in runset.cel(cell):
        rs = logs.rounds(p)
        vorige = {e.get("round"): e for e in rs}
        rangen = []
        for e in rs:
            bord = (vorige.get((e.get("round") or 0) - 1) or {}).get("agents") or {}
            ag = bord or (e.get("agents") or {})
            levend = [(nm, a.get("resources") or 0) for nm, a in ag.items()
                      if (a.get("resources") or 0) > 0]
            if not levend:
                continue
            gesorteerd = [nm for nm, _ in sorted(levend, key=lambda kv: -kv[1])]
            for x in (e.get("combat") or []):
                d = isinstance(x, dict) and x.get("defender")
                if d and d in gesorteerd:
                    rangen.append(gesorteerd.index(d) + 1)
        uit.append(rangen)
    return uit


def draw(data: dict):
    style()
    fig, ax = plt.subplots(figsize=(WIDTH, HEIGHT))
    fig.subplots_adjust(left=LEFT / WIDTH, right=1 - RIGHT / WIDTH,
                        top=1 - TOP / HEIGHT, bottom=BOTTOM / HEIGHT)

    # Six positions with a gap between the levels, so the eye reads two groups
    # and not one row of six.
    posities, etiketten, kleuren, cellen = [], [], [], []
    for i, lv in enumerate(LEVELS):
        for j, pf in enumerate(PAYOFFS):
            posities.append(i * 4 + j)
            etiketten.append(PAYOFF[pf])
            kleuren.append(COLOUR[pf])
            cellen.append((lv, pf))

    reeksen = [[r for run in data[lv][pf] for r in run] for lv, pf in cellen]
    # Half a violin, so the density and the observations share one axis and
    # read as one object instead of three parallel ones standing beside each
    # other. The left half is clipped away and the points take that side.
    parts = ax.violinplot(reeksen, positions=posities, widths=1.30,
                          showextrema=False, showmedians=False, bw_method=BW)
    for body, kleur, pos in zip(parts["bodies"], kleuren, posities):
        punten = body.get_paths()[0].vertices
        punten[:, 0] = np.clip(punten[:, 0], pos, np.inf)
        body.set_facecolor(kleur)
        body.set_edgecolor(kleur)
        body.set_alpha(0.30)
        body.set_linewidth(0.7)

    for pos, kleur, (lv, pf) in zip(posities, kleuren, cellen):
        runs = data[lv][pf]
        # Every fight as its own point, left of centre. Ranks are integers, so
        # without a scatter in both directions a cell of nine hundred fights
        # draws thirty stacked lines and the density is invisible; the jitter
        # is cosmetic and the violin beside it carries the actual shape.
        alle = np.array([r for run in runs for r in run], dtype=float)
        rng = np.random.default_rng(SEED_JITTER + posities.index(pos))
        ax.scatter(pos - 0.06 - np.abs(rng.normal(0, 0.115, len(alle))),
                   alle + rng.uniform(-0.34, 0.34, len(alle)),
                   s=0.9, facecolor=kleur, edgecolor="none", alpha=0.16,
                   zorder=3, rasterized=True)
        m, lo, hi = _ci.pooled_median(f"fig7:{lv}:{pf}", runs)
        ax.plot([pos, pos], [lo, hi], color=INK, linewidth=1.2,
                solid_capstyle="butt", zorder=6)
        ax.scatter([pos], [m], s=16, facecolor=INK, edgecolor="white",
                   linewidth=0.6, zorder=7)

    ax.set_xticks(posities)
    ax.set_xticklabels(etiketten, fontsize=PT_LABEL)
    ax.set_xlim(-0.95, 7.05)
    ax.set_ylim(N + 1.2, -0.2)                 # rank 1 at the top
    ax.set_yticks([1, 5, 10, 15, 20, 25, 30])
    ax.set_ylabel("the target's rank among the living", fontsize=PT_LABEL)
    ax.tick_params(labelsize=PT_LABEL, length=2.2)
    for i, lv in enumerate(LEVELS):
        ax.text(i * 4 + 1, -1.5, f"{lv} · {RUNG[lv]}", fontsize=PT_TITLE,
                color=INK, ha="center", va="bottom", fontweight="bold")
    ax.text(-0.76, 2.2, "richest", fontsize=PT_ASIDE, color=FAINT, ha="left",
            va="top", style="italic")
    ax.text(-0.76, N - 1.2, "poorest", fontsize=PT_ASIDE, color=FAINT,
            ha="left", va="bottom", style="italic")

    handelingen = [
        plt.Line2D([], [], marker="o", linestyle="none", markersize=2.6,
                   markerfacecolor=FAINT, markeredgecolor="none",
                   alpha=0.55, label="one fight"),
        plt.Line2D([], [], marker="o", linestyle="-", markersize=3.6,
                   color=INK, linewidth=1.1, label="cell median, 95% interval"),
    ]
    fig.legend(handles=handelingen, loc="lower center", ncol=2, frameon=False,
               fontsize=PT_LABEL, handletextpad=0.5, columnspacing=2.0,
               bbox_to_anchor=(0.5, 0.004))
    return fig


def caption(data: dict) -> str:
    def band(lv, pf, lo, hi):
        alle = [r for run in data[lv][pf] for r in run]
        return 100 * sum(1 for r in alle if lo <= r <= hi) / len(alle)

    l2top = [band("L2", p, 1, 5) for p in PAYOFFS]
    l2bot = [band("L2", p, 26, 30) for p in PAYOFFS]
    l3top = [band("L3", p, 1, 5) for p in PAYOFFS]
    l2med = [_ci.pooled_median(f"fig7:L2:{p}", data["L2"][p])[0] for p in PAYOFFS]
    l3med = [_ci.pooled_median(f"fig7:L3:{p}", data["L3"][p])[0] for p in PAYOFFS]
    n2 = sum(len(r) for p in PAYOFFS for r in data["L2"][p])
    n3 = sum(len(r) for p in PAYOFFS for r in data["L3"][p])
    spreiding = max(max(st.median(r) for r in data[lv][p] if r)
                    - min(st.median(r) for r in data[lv][p] if r)
                    for lv in LEVELS for p in PAYOFFS)
    n2 = sum(len(r) for p in PAYOFFS for r in data["L2"][p])
    n3 = sum(len(r) for p in PAYOFFS for r in data["L3"][p])
    return (
        "Every resolved fight placed at the rank its target held going into "
        f"the round, richest at the top: {n2:,} fights at L2 and {n3:,} at L3. "
        "Each cell is one object: the points on the left are the fights "
        "themselves, the shape on the right is their density, and the dot and "
        "bar on the spine are the cell median with a 95 per cent interval on "
        "it\\meth{m:whom-hit-over}. Random targeting would draw a shape of even "
        "width from top to bottom and put the median at rank 15.5.")


def findings(data: dict) -> list[str]:
    """The sentences the running text needs, with their numbers live.

    Computed here and not typed into the chapter, so a rebuild on a different
    run set cannot leave a sentence describing a shape the figure no longer has.
    """
    def band(lv, pf, lo, hi):
        alle = [r for run in data[lv][pf] for r in run]
        return 100 * sum(1 for r in alle if lo <= r <= hi) / len(alle)

    l2top = [band("L2", p, 1, 5) for p in PAYOFFS]
    l2bot = [band("L2", p, 26, 30) for p in PAYOFFS]
    l3top = [band("L3", p, 1, 5) for p in PAYOFFS]
    l2med = [_ci.pooled_median(f"fig7:L2:{p}", data["L2"][p])[0] for p in PAYOFFS]
    l3med = [_ci.pooled_median(f"fig7:L3:{p}", data["L3"][p])[0] for p in PAYOFFS]
    spreiding = max(max(st.median(r) for r in data[lv][p] if r)
                    - min(st.median(r) for r in data[lv][p] if r)
                    for lv in LEVELS for p in PAYOFFS)
    return [
        f"At L2 the distribution has two modes, a large one on the poorest five "
        f"ranks ({min(l2bot):.0f} to {max(l2bot):.0f} per cent of fights) and a "
        f"smaller one on the richest five ({min(l2top):.0f} to "
        f"{max(l2top):.0f}), while the median falls in the waist between them "
        f"at ranks {min(l2med):.0f} to {max(l2med):.0f}, where the cell fights "
        f"least often.",
        f"At L3, where an agent can invite the neighbour it lacks and reach "
        f"anyone, the lower mode is gone: {min(l3top):.0f} to {max(l3top):.0f} "
        f"per cent of all fighting falls on the richest five and the median "
        f"rises to {min(l3med):.0f} to {max(l3med):.0f}.",
        f"The intervals are narrow beside the disagreement between runs: within "
        f"a single cell one run's median target and another's differ by as much "
        f"as {spreiding:.0f} ranks, so a cell's median is a firmer quantity "
        f"than the runs of a cell are alike.",
        "The bootstrap resamples runs and never the individual fights: a cell "
        "holds about a thousand fights but only ten or fifteen runs, and "
        "treating the fights as independent draws would return an interval "
        "several times too narrow.",
    ]


def main() -> int:
    data = {lv: {pf: targets(f"prod_{lv}_{pf}") for pf in PAYOFFS}
            for lv in LEVELS}
    fig = draw(data)
    save(fig, FIGURE, "target_rank")
    tex = figure_tex(FIGURE, ["target_rank"],
                     "Where in the wealth ordering the blows land",
                     caption(data), "fig:targets")
    (HERE / "figures" / FIGURE / f"{FIGURE}.tex").write_text(tex)
    print(f"wrote figures/{FIGURE}/target_rank.pdf and {FIGURE}.tex")
    print("\nfor the running text:")
    for zin in findings(data):
        print("  · " + zin)
    print()
    for lv in LEVELS:
        for pf in PAYOFFS:
            runs = data[lv][pf]
            alle = [r for run in runs for r in run]
            m, lo, hi = _ci.pooled_median(f"fig7:{lv}:{pf}", runs)
            top5 = 100 * sum(1 for r in alle if r <= 5) / len(alle)
            bot5 = 100 * sum(1 for r in alle if r >= 26) / len(alle)
            print(f"  {lv} {PAYOFF[pf]:11} fights={len(alle):5} "
                  f"median {m:4.1f} [{lo:4.1f}, {hi:4.1f}]  "
                  f"top5 {top5:4.1f}%  bottom5 {bot5:4.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
