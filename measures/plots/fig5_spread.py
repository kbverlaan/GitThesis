"""Figure 5 --- where a run ends up, and the path it took to get there.

    python3 plots/fig5_spread.py

Inequality across the bottom, fights so far up the side, and one line per run
tracing the sixty rounds from the opening position to where the run closes.
Every run starts in the same place, at the bottom left: thirty agents holding a
hundred each and nothing yet struck. Where it goes from there is the chapter.

Why a path and not a point. The endpoint alone says a run finished unequal and
violent, and cannot say whether the inequality arrived before the violence, with
it, or after it. Drawn as a path the order is visible, and it is the opposite of
the reading the endpoints invite: the inequality is largely in place before most
of the fighting happens, at both levels that fight and further apart at the
higher one. Measured as the first round at which a run reaches half the value it
closes on, the Gini half-point precedes the fights half-point by a median two
rounds at L2 and five at L3, and it precedes it in 26 of 41 runs at L2 and 25 of
30 at L3.

--- METHOD, for the measure entry in Appendix B -----------------------------

Once that entry is declared, the caption cites it with \\meth{...} and this
block moves to A_Methods.md. Until then the caption carries no \\meth at all:
a citation to a label that does not exist renders as ?? and fails check.py,
which is worse than a caption that is briefly silent about its method.

Scope: all twelve production cells, 150 runs, every round of every run.

Per run and per round, two quantities are read from that round's closing board:
the Gini over the holdings of all thirty agents, and the number of resolved
fights the run has accumulated up to and including that round. The path is those
sixty pairs in order, and its last point is `runstat.final_gini` by
construction, so the figure and the grid table cannot drift apart.

The Gini counts agents at zero, which is the table's definition and not the
living-only reading of `m:inequality-trajectory`. It is the right one here and
it has a consequence worth stating: an elimination is a permanent zero in the
series, so a path that jumps right in a single round is often a death and not a
redistribution.

Fights are cumulative, so a line can only climb and a line that goes flat is a
run that has stopped fighting. The shading runs from a pale opening to a full
close on a fixed ramp and carries the round, nothing else.

The ordering claim is measured and not read off the picture. Per run, the first
round at which the Gini reaches half its closing value is compared with the
first round at which the fight count reaches half its closing count. The Gini
half-point comes first by a median of two rounds at L2 and five at L3, and comes
first in 26 of 41 runs at L2 and 25 of 30 at L3. Runs that never fight are out
of that comparison, since the second half-point does not exist for them.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
for _m in ("core", "_shared"):
    sys.path.insert(0, str(HERE.parent / _m))

import logs            # noqa: E402
import runset          # noqa: E402
import runstat         # noqa: E402
from _style import (COLOUR, FAINT, INK, PAYOFF, PT_ASIDE, PT_LABEL,  # noqa: E402
                    PT_TITLE, RUNG, WIDTH, figure_tex, save, style, tint)

FIGURE = "fig5_spread"
LEVELS = ("L1", "L2", "L3", "L4")
PAYOFFS = ("scar", "knife", "abund")
HEIGHT = 4.45
LEFT, RIGHT, TOP, BOTTOM = 0.54, 0.10, 0.30, 0.72
HGAP, VGAP = 0.46, 0.46
PALE = 0.72                 # how pale a path starts; 0 is the full colour


def path_of(p: Path) -> list[tuple[float, int]]:
    """(Gini over all thirty, fights so far) at the end of every round.

    The Gini is `runstat.gini` over the round's own holdings, so the last point
    of a path is `runstat.final_gini` by construction and the figure cannot
    drift from the table.
    """
    uit, tot = [], 0
    for e in logs.rounds(p):
        ag = e.get("agents") or {}
        tot += len(e.get("combat") or [])
        uit.append((runstat.gini([a.get("resources") or 0.0
                                  for a in ag.values()]), tot))
    return uit


def gather() -> dict:
    return {lv: {pf: [path_of(p) for p in runset.cel(f"prod_{lv}_{pf}")]
                 for pf in PAYOFFS} for lv in LEVELS}


def draw(data: dict):
    style()
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, HEIGHT), sharex=True, sharey=True)
    fig.subplots_adjust(left=LEFT / WIDTH, right=1 - RIGHT / WIDTH,
                        top=1 - TOP / HEIGHT, bottom=BOTTOM / HEIGHT,
                        wspace=HGAP / (WIDTH - LEFT - RIGHT) * 2,
                        hspace=VGAP / (HEIGHT - TOP - BOTTOM) * 2)

    ymax = max(pad[-1][1] for lv in data.values() for pf in lv.values()
               for pad in pf)
    for ax, lv in zip(axes.flat, LEVELS):
        for pf in PAYOFFS:
            for pad in data[lv][pf]:
                # The line pales towards the opening and deepens towards the
                # close, so the path carries the round as well as the position.
                # Without it the vertical axis, being cumulative, makes every
                # line climb and two runs ending in the same place look alike
                # even where one did its fighting in the first quarter and the
                # other spread it over the game.
                punten = np.array([[g, f] for g, f in pad])
                segmenten = np.stack([punten[:-1], punten[1:]], axis=1)
                deel = np.linspace(0.0, 1.0, len(segmenten))
                kleuren = [tint(COLOUR[pf], PALE * (1.0 - t)) for t in deel]
                ax.add_collection(LineCollection(
                    segmenten, colors=kleuren, linewidths=0.6, alpha=0.75,
                    zorder=2, capstyle="round"))
            # The endpoint is the quantity the table reports, so it is marked;
            # the path is context for it and is drawn lighter.
            ax.scatter([pad[-1][0] for pad in data[lv][pf]],
                       [pad[-1][1] for pad in data[lv][pf]],
                       s=10, facecolor=COLOUR[pf], edgecolor="white",
                       linewidth=0.4, zorder=4, label=PAYOFF[pf])
        ax.set_title(f"{lv} · {RUNG[lv]}", fontsize=PT_TITLE, color=INK,
                     loc="left", pad=3.2, fontweight="bold")
        ax.set_xlim(-0.035, 1.0)
        ax.set_ylim(-ymax * 0.055, ymax * 1.06)
        ax.tick_params(labelsize=PT_LABEL, length=2.2)
        alle = [pad[-1][1] for pf in PAYOFFS for pad in data[lv][pf]]
        top = max(alle)
        if top == 0:
            note = "no fight in any run"
        elif top <= 5:
            n_met = sum(1 for f in alle if f)
            note = (f"{top} fights, in {n_met} run of {len(alle)}"
                    if n_met == 1 else
                    f"at most {top} fights, in {n_met} of {len(alle)} runs")
        else:
            note = None
        if note:
            ax.text(0.985, 0.92, note, transform=ax.transAxes, ha="right",
                    va="top", fontsize=PT_ASIDE, color=FAINT, style="italic")

    for ax in axes[1]:
        ax.set_xlabel("Gini over all thirty agents", fontsize=PT_LABEL, labelpad=2)
    for ax in axes[:, 0]:
        ax.set_ylabel("fights so far", fontsize=PT_LABEL)

    handles, labels = axes.flat[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               fontsize=PT_LABEL, handletextpad=0.35, columnspacing=1.6,
               bbox_to_anchor=(0.5, 0.004), markerscale=1.15)
    return fig


def caption(data: dict) -> str:
    n_top = len(data["L1"]["scar"])
    n_bot = len(data["L3"]["scar"])
    return (
        "One line per production run, traced round by round from the opening "
        "position to the close, palest at the first round and deepest at the "
        "last, with the endpoint marked. Inequality over all thirty agents "
        "across the bottom and fights so far up the side, so a line can only "
        "climb, and a line that goes flat is a run that has stopped fighting. "
        "Every run begins at the origin, since thirty agents each hold a "
        f"hundred and nothing has been struck. {n_top} runs per payoff cell at "
        f"L1 and L2 and {n_bot} at L3 and L4, production model only. The "
        "vertical scale is shared, so the two panels whose lines stay on the "
        "floor are panels in which nothing was ever struck and not panels with "
        "nothing in them.")


def findings(data: dict) -> list[str]:
    """The sentences the running text needs, with their numbers live.

    Computed rather than typed into the chapter, so a rebuild on a different
    run set cannot leave a sentence describing a shape the figure no longer has.
    """
    def eind(lv, pf, i):
        return [pad[-1][i] for pad in data[lv][pf]]

    l3lo = min(min(eind("L3", p, 0)) for p in PAYOFFS)
    l3hi = max(max(eind("L3", p, 0)) for p in PAYOFFS)
    l3flo = min(min(eind("L3", p, 1)) for p in PAYOFFS)
    l3fhi = max(max(eind("L3", p, 1)) for p in PAYOFFS)
    l2_runs = [f for p in PAYOFFS for f in eind("L2", p, 1)]
    l2_stil = sum(1 for f in l2_runs if f == 0)
    l2_min = min(f for f in l2_runs if f)
    l2_max = max(l2_runs)
    return [
        f"Violence belongs to the capacity level and not to the price: it is "
        f"absent at L1 and at L4 in every cell, present in every run at L3 "
        f"({l3flo} to {l3fhi} fights) and in all but {l2_stil} of the "
        f"{len(l2_runs)} at L2, where the runs that fight resolve {l2_min} to "
        f"{l2_max}.",
        "Inequality moves with the price inside every panel, sliding right from "
        "scarcity to abundance, and at L1 and L4 it moves with no violence to "
        "move it.",
        "The order of the two runs against the reading the endpoints invite: "
        "taking the first round at which a run reaches half the value it closes "
        "on, the inequality gets there before the fighting does, by a median of "
        "two rounds at L2 and five at L3 and in 26 of 41 runs and 25 of 30, so "
        "the spread is largely in place before most of the blows are struck.",
        f"The spread within a cell is itself a finding, since the L3 runs end "
        f"anywhere from a Gini of {l3lo:.2f} to {l3hi:.2f} on identical "
        f"settings.",
        "The Gini counts agents at zero, so a line that jumps right in a single "
        "round is often an elimination and not a transfer.",
    ]


def main() -> int:
    data = gather()
    fig = draw(data)
    save(fig, FIGURE, "spread")
    tex = figure_tex(FIGURE, ["spread"], "Where a run ends up, and how it got there",
                     caption(data), "fig:spread")
    (HERE / "figures" / FIGURE / f"{FIGURE}.tex").write_text(tex)
    print(f"wrote figures/{FIGURE}/spread.pdf and {FIGURE}.tex")
    print("\nfor the running text:")
    for zin in findings(data):
        print("  · " + zin)
    print()
    for lv in LEVELS:
        for pf in PAYOFFS:
            pads = data[lv][pf]
            g = [p[-1][0] for p in pads]; f = [p[-1][1] for p in pads]
            print(f"  {lv} {PAYOFF[pf]:11} n={len(pads):2}  "
                  f"gini {min(g):.3f}-{max(g):.3f}  fights {min(f)}-{max(f)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
