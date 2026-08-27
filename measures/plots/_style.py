"""The chapter's figure style, in one place.

Every figure imports this and nothing sets a font, a colour or a page dimension
of its own. Five figures that each carry their own rcParams drift within a
month: one ends up at 7pt labels and the next at 8, one uses the payoff blue for
scarcity and the next for magnitude, and the reader reads the difference as
meaning something.

    from _style import style, COLOUR, WIDTH, save, figure_tex

The page. The chapter is

    \\documentclass[9pt,twocolumn]{article}
    \\usepackage[a4paper,margin=0.75in,columnsep=0.25in]{geometry}

so A4 (8.268in) less two 0.75in margins gives a text width of 6.768in, and a
column is (6.768 - 0.25)/2 = 3.259in. Figures are drawn at exactly one of those
two widths, so `\\linewidth` scales them 1:1 and 7pt in the figure is 7pt on the
page. Drawing at some other width and letting LaTeX resize is how a set of
figures ends up with four type sizes.

Note that `article` has no 9pt option --- it silently gives 10pt --- so the body
text is 10pt and the sizes below are set against that.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import seaborn as sns

HERE = Path(__file__).resolve().parent
FIGURES = HERE / "figures"          # what LaTeX reads; one directory per figure
PREVIEWS = HERE / "out"             # PNGs to look at, kept out of the way

# --- the page ---------------------------------------------------------------

WIDTH = 6.768                       # inches, \the\textwidth
COLUMN = 3.259                      # inches, \the\columnwidth
HEIGHT = 10.19                      # inches of column height (A4 less margins)

# --- colour -----------------------------------------------------------------
#
# Okabe-Ito. Each payoff regime keeps its colour in every figure, so a reader who
# has learnt that blue is scarcity once does not learn it again. Checked pairwise
# under deuteranopia, protanopia and tritanopia by plots/_palette.py; the
# tightest pair is scarce/knife-edge under tritanopia at 9.0 against a
# threshold of 8.

COLOUR = {"scar": "#0072B2", "knife": "#009E73", "abund": "#D55E00"}
PAYOFF = {"scar": "scarce", "knife": "knife-edge", "abund": "abundant"}
# What each rung adds, so a title says what the collective could do rather than
# only which number the rung has.
RUNG = {"L1": "give or hold", "L2": "predation", "L3": "association",
        "L4": "commons"}

INK = "#222222"                     # text
FAINT = "#8a8a8a"                   # axes, secondary labels
GRID = "#ededed"                    # grid lines

# --- type -------------------------------------------------------------------

PT_TITLE = 8.2                      # panel title, bold
PT_LABEL = 7.0                      # axis labels and categories
PT_ASIDE = 6.4                      # what run, how many, and other asides


def style() -> None:
    """Seaborn's grid, then the chapter's typography over it."""
    sns.set_theme(style="whitegrid", context="paper")
    mpl.rcParams.update({
        "font.family": "serif",
        # mathptmx in the chapter is Times; the figures follow it.
        "font.serif": ["Times New Roman", "STIXGeneral", "DejaVu Serif"],
        "font.size": PT_LABEL,
        "axes.edgecolor": FAINT, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": FAINT, "ytick.color": FAINT,
        "xtick.labelcolor": INK, "ytick.labelcolor": INK,
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "axes.facecolor": "white", "figure.facecolor": "white",
        "grid.color": GRID, "grid.linewidth": 0.5,
        "figure.dpi": 200,
        # Not bbox="tight": that trims each panel to its own longest label, so
        # panels of one figure come out at different widths and \linewidth then
        # scales each by a different factor --- one figure, several type sizes.
        # Every figure sets its margins in inches instead.
        "savefig.pad_inches": 0.0,
    })


def tint(hex_colour: str, towards_white: float) -> tuple:
    """The colour mixed with white; 0 is the colour, 1 is white.

    For fills. Desaturating instead turns the blue and the green into two shades
    of the same grey, which reads as dirty rather than as quiet.
    """
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return tuple(c + (1.0 - c) * towards_white for c in (r, g, b))


def save(fig, figure: str, name: str) -> Path:
    """Write the PDF into figures/<figure>/ and a PNG preview into out/.

    One directory per figure, because a figure is rarely one file: this one is
    four panels and a caption, and the next is two networks. Keeping them apart
    means a figure can be rebuilt or dropped without touching another's files.
    """
    target = FIGURES / figure
    target.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(exist_ok=True)
    fig.savefig(target / f"{name}.pdf")
    fig.savefig(PREVIEWS / f"{figure}__{name}.png", dpi=220)
    return target / f"{name}.pdf"


def margins(fig, label_width: float, height: float, top=0.20, bottom=0.40):
    """Fixed margins in inches, so every panel of a figure is exactly as wide.

    `label_width` is the room reserved for the category labels down the left,
    the same in every panel whether or not that panel has a long one.
    """
    fig.subplots_adjust(left=label_width / fig.get_figwidth(), right=0.998,
                        top=1 - top / height, bottom=bottom / height)


def figure_tex(figure: str, files: list[str], short: str, caption: str,
               label: str, span: bool = True, placement: str = "tp") -> str:
    """The LaTeX for one figure, written by the script that drew it.

    A caption that names a run, a seed or a spread has to be rewritten whenever
    the selection changes, and one typed into the chapter by hand will not be.

    Placement is `t` and not `p`. A `[p]` float is held back for a page given
    over to floats, which in practice puts every figure after the discussion,
    a dozen pages from the sentence that introduces it. `[t]` puts it at the
    top of the next page instead.

    A `figure*` in a two-column document cannot land on the page it is declared
    on --- LaTeX defers it to the next one whatever the placement says --- so
    the earliest it can appear is the top of the following page. Getting it any
    closer needs `\\usepackage{dblfloatfix}` or `stfloats` in the preamble,
    which also allows `[b]`.
    """
    environment = "figure*" if span else "figure"
    plates = "\n".join(
        f"\\includegraphics[width=\\linewidth]{{figures/{figure}/{f}.pdf}}\\\\[2pt]"
        for f in files)
    return (f"% generated by plots/{figure}.py --- do not edit the numbers by hand\n"
            + ("% figure* --- the chapter is two-column and this does not fit one\n"
               if span else "")
            + f"\\begin{{{environment}}}[{placement}]\n\\centering\n{plates}\n"
            f"\\caption[{short}]{{%\n\\textbf{{{short}.}} {caption}}}\n"
            f"\\label{{{label}}}\n\\end{{{environment}}}\n")
