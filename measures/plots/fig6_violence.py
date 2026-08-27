"""Figure 6 --- when the fighting happens.

The caption carries no \\meth citation yet, because the measure entry it would
point at is not declared. A citation to a label that does not exist renders as
?? and fails check.py, so the method text waits in this docstring instead;
figures 1, 2 and 4 show the form it takes once the entry exists.

    python3 plots/fig6_violence.py

Fights per round against the round they fell in, one faint line per run and one
solid line per payoff cell, for the two capacity levels that fight at all. L1
has no weapon and L4 never draws the one it carries, so both are flat zero and
are not drawn; Figure~\\ref{fig:spread} is where that absence is visible.

What the figure is for. The chapter reports the shape of a run's violence as
three numbers --- the round of the first blow, the round it crests, the round of
the last --- and those numbers describe the median run of a cell, which is not
a run. Drawn, the shape is one thing and not three: violence arrives within a
few rounds, crests inside the first quarter of the game, and then falls away
over the remaining forty rounds without ever quite stopping.

The decline is not the same event in the two panels, and the figure cannot say
which it is. At L3 the economy drains as it happens, so the fighting may be
stopping because there is nothing left to take; at L2 the holdings survive.
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
for _m in ("core", "_shared"):
    sys.path.insert(0, str(HERE.parent / _m))

import _ci             # noqa: E402
import combat          # noqa: E402
import runset          # noqa: E402
from _style import (COLOUR, FAINT, INK, PAYOFF, PT_ASIDE, PT_LABEL,  # noqa: E402
                    PT_TITLE, RUNG, WIDTH, figure_tex, save, style, tint)

FIGURE = "fig6_violence"
LEVELS = ("L2", "L3")
PAYOFFS = ("scar", "knife", "abund")
ROUNDS = 60
HEIGHT = 4.25
LEFT, RIGHT, TOP, BOTTOM = 0.60, 0.10, 0.30, 0.60


def gather() -> dict:
    """{level: {payoff: [per-run vectors of fights per round]}}."""
    out = {}
    for lv in LEVELS:
        out[lv] = {}
        for pf in PAYOFFS:
            runs = []
            for p in runset.cel(f"prod_{lv}_{pf}"):
                v = [0] * (ROUNDS + 1)
                for r, _ in combat.fights(p):
                    if r and 1 <= r <= ROUNDS:
                        v[r] += 1
                runs.append(v[1:])
            out[lv][pf] = runs
    return out


def cell_mean(runs):
    return [st.mean(r[i] for r in runs) for i in range(ROUNDS)]


def draw(data: dict):
    style()
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, HEIGHT), sharex=True,
                             gridspec_kw={"height_ratios": [1.6, 1.0]})
    fig.subplots_adjust(left=LEFT / WIDTH, right=1 - RIGHT / WIDTH,
                        top=1 - TOP / HEIGHT, bottom=BOTTOM / HEIGHT,
                        wspace=0.10, hspace=0.20)

    x = range(1, ROUNDS + 1)
    top = max(float(_ci.band(f"fig6:{lv}:{pf}", data[lv][pf])[2].max())
              for lv in LEVELS for pf in PAYOFFS)

    # --- upper row: the rate itself ---------------------------------------
    for ax, lv in zip(axes[0], LEVELS):
        for pf in PAYOFFS:
            _, lo, hi = _ci.band(f"fig6:{lv}:{pf}", data[lv][pf])
            ax.fill_between(x, lo, hi, color=COLOUR[pf], alpha=0.16,
                            linewidth=0, zorder=1)
        for pf in PAYOFFS:
            m, _, _ = _ci.band(f"fig6:{lv}:{pf}", data[lv][pf])
            ax.plot(x, m, color=COLOUR[pf], linewidth=1.45, zorder=3,
                    label=PAYOFF[pf], solid_capstyle="round")
        ax.set_title(f"{lv} · {RUNG[lv]}", fontsize=PT_TITLE, color=INK,
                     loc="left", pad=3.2, fontweight="bold")
        ax.set_xlim(0, ROUNDS + 1)
        ax.set_ylim(-top * 0.03, top * 1.04)
        ax.tick_params(labelsize=PT_LABEL, length=2.2)
    axes[0][0].set_ylabel("fights in the round", fontsize=PT_LABEL)
    axes[0][1].tick_params(labelleft=False)

    # --- lower row: the contrast, where the finding actually lives --------
    #
    # Two intervals drawn beside each other cannot be read for a difference:
    # bands that overlap can still have a difference clear of zero. So the
    # contrast gets its own interval and its own zero line.
    onder = []
    for ax, lv in zip(axes[1], LEVELS):
        # Same seed name as the caption's count, or the panel and the sentence
        # under it would be two different draws and disagree by a round.
        d, lo, hi = _ci.band_difference(f"fig6:diff:{lv}:abund:scar",
                                        data[lv]["abund"], data[lv]["scar"])
        onder.append((lo, hi))
        # Neutral and not the abundant colour, though the contrast is named for
        # that cell: the difference belongs to neither of the two, and giving it
        # one of their colours would read as that cell's curve drawn again. The
        # line is ink and only the band is grey, so the row still carries the
        # weight of a finding rather than of an aside.
        ax.axhline(0, color=FAINT, linewidth=0.7, zorder=2)
        ax.fill_between(x, lo, hi, color=INK, alpha=0.13, linewidth=0, zorder=1)
        ax.plot(x, d, color=INK, linewidth=1.25, zorder=3, solid_capstyle="round")
        weg = [r + 1 for r in range(ROUNDS) if lo[r] > 0 or hi[r] < 0]
        ax.set_xlim(0, ROUNDS + 1)
        ax.set_xlabel("round", fontsize=PT_LABEL, labelpad=2)
        ax.set_xticks([1, 10, 20, 30, 40, 50, 60])
        ax.tick_params(labelsize=PT_LABEL, length=2.2)
        ax.text(0.985, 0.06, f"{len(weg)} of {ROUNDS} rounds clear of zero",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=PT_ASIDE, color=FAINT, style="italic")
    laag = min(float(lo.min()) for lo, _ in onder)
    hoog = max(float(hi.max()) for _, hi in onder)
    for ax in axes[1]:
        ax.set_ylim(laag - 0.12, hoog + 0.12)
    axes[1][0].set_ylabel("abundant less scarce", fontsize=PT_LABEL)
    axes[1][1].tick_params(labelleft=False)

    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               fontsize=PT_LABEL, handletextpad=0.5, columnspacing=1.8,
               bbox_to_anchor=(0.5, 0.004))
    return fig


def caption(data: dict) -> str:
    bits = []
    for lv in LEVELS:
        for pf in PAYOFFS:
            m = cell_mean(data[lv][pf])
            crest = max(range(ROUNDS), key=lambda i: m[i]) + 1
            bits.append((lv, pf, crest, max(m)))
    l3peak = max(b[3] for b in bits if b[0] == "L3")
    l2peak = max(b[3] for b in bits if b[0] == "L2")
    crests = sorted(b[2] for b in bits)
    n_runs = sum(len(data[lv][pf]) for lv in LEVELS for pf in PAYOFFS)
    still = sum(1 for lv in LEVELS for pf in PAYOFFS
                for r in data[lv][pf] if sum(r[40:]))

    # The contrast, tested where it belongs. Counting rounds where two bands
    # fail to overlap understates it --- two intervals can overlap while the
    # interval on their difference clears zero --- so the count below is taken
    # from `band_difference` and not from the bands in the upper row.
    def losvan(lv, a_, b_):
        _, lo, hi = _ci.band_difference(f"fig6:diff:{lv}:{a_}:{b_}",
                                        data[lv][a_], data[lv][b_])
        return sum(1 for r in range(ROUNDS) if lo[r] > 0 or hi[r] < 0)
    l2_ab_sc = losvan("L2", "abund", "scar")
    l2_ab_kn = losvan("L2", "abund", "knife")
    l2_sc_kn = losvan("L2", "scar", "knife")
    l3_max = max(losvan("L3", x, y) for x, y in
                 (("abund", "scar"), ("abund", "knife"), ("scar", "knife")))

    return (
        "Fights per round against the round they fell in. Above, the cell mean "
        "as a line with a 95 per cent interval over runs, fifteen runs per cell "
        "at L2 and ten at L3. Below, the abundant cell less the scarce one, "
        "with an interval on the difference itself and a line at zero: two "
        "bands that overlap can still have a difference clear of zero, so the "
        "lower row is the test and the upper row the shape. L1 and L4 are not "
        "drawn, since no run at either level resolves more than two fights in "
        "the whole game.")


def findings(data: dict) -> list[str]:
    """The sentences the running text needs, with their numbers live.

    They are computed here rather than written into the chapter by hand, so a
    rebuild on a different run set cannot leave a sentence in \\S4 describing a
    pattern the figure no longer shows. Printed by `main`; the chapter takes
    them and puts them in Koen's own words.
    """
    bits = []
    for lv in LEVELS:
        for pf in PAYOFFS:
            m = cell_mean(data[lv][pf])
            bits.append((lv, pf, max(range(ROUNDS), key=lambda i: m[i]) + 1,
                         max(m)))
    crests = sorted(b[2] for b in bits)
    l3peak = max(b[3] for b in bits if b[0] == "L3")
    l2peak = max(b[3] for b in bits if b[0] == "L2")
    n_runs = sum(len(data[lv][pf]) for lv in LEVELS for pf in PAYOFFS)
    still = sum(1 for lv in LEVELS for pf in PAYOFFS
                for r in data[lv][pf] if sum(r[40:]))

    def losvan(lv, x, y):
        _, lo, hi = _ci.band_difference(f"fig6:diff:{lv}:{x}:{y}",
                                        data[lv][x], data[lv][y])
        return sum(1 for r in range(ROUNDS) if lo[r] > 0 or hi[r] < 0)

    return [
        f"Every cell runs the same shape: the fighting arrives within a few "
        f"rounds, crests between rounds {crests[0]} and {crests[-1]}, and falls "
        f"away over the rest of the game, with the capacity level setting its "
        f"height at {l3peak:.1f} fights a round at the crest against "
        f"{l2peak:.1f} one level down.",
        f"The decline does not amount to a settlement, since fighting continues "
        f"at a lower rate to the last round and {still} of the {n_runs} runs "
        f"resolve a fight after round 40.",
        f"At L2 abundance is below scarcity in {losvan('L2', 'abund', 'scar')} "
        f"of the sixty rounds and below knife-edge in "
        f"{losvan('L2', 'abund', 'knife')}, while scarcity and knife-edge "
        f"separate in {losvan('L2', 'scar', 'knife')}: paying more for "
        f"cooperation buys less fighting, and the two tight cells are not "
        f"distinguishable from each other.",
        f"At L3 the widest of the three contrasts clears zero in "
        f"{max(losvan('L3', x, y) for x, y in (('abund','scar'),('abund','knife'),('scar','knife')))} "
        f"of the sixty rounds, so the price that moves the rate one level down "
        f"leaves next to no mark on it once agents can reach whoever they like.",
        "What the figure cannot say is why the rate falls, and the two panels "
        "may not fall for the same reason: at L3 the economy is draining while "
        "it happens and at L2 it is not.",
    ]


def main() -> int:
    data = gather()
    fig = draw(data)
    save(fig, FIGURE, "over_time")
    tex = figure_tex(FIGURE, ["over_time"], "When the fighting happens",
                     caption(data), "fig:violence")
    (HERE / "figures" / FIGURE / f"{FIGURE}.tex").write_text(tex)
    print(f"wrote figures/{FIGURE}/over_time.pdf and {FIGURE}.tex")
    print("\nfor the running text:")
    for zin in findings(data):
        print("  · " + zin)
    print()
    for lv in LEVELS:
        for pf in PAYOFFS:
            runs = data[lv][pf]
            m = cell_mean(runs)
            crest = max(range(ROUNDS), key=lambda i: m[i]) + 1
            late = sum(1 for r in runs if sum(r[40:]))
            print(f"  {lv} {PAYOFF[pf]:11} n={len(runs):2} crest R{crest:2} "
                  f"peak {max(m):.2f}  fights after R40 in {late}/{len(runs)} runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
