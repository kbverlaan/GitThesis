# Five figures for Chapter 4 — design

**What a figure here is for, and the test each has to pass.** A figure in this
chapter does not restate a statistic. It shows what happened: names the agents
coined themselves, who attacked whom, who grew rich and who sank. If a figure can
be summarised in a sentence, that sentence belongs in the text and the figure
nowhere.

That means all five show **individual agents**, not cell means. It also means each
needs a caption saying how representative it is — a single run illustrates, it
does not establish.

---

## The shared visual language

Five figures standing beside each other in one chapter have to speak the same
grammar, or the reader learns the axes again every time.

**Time runs to the right.** Sixty rounds, always the same width, always the same
scale. That holds for the name timeline, the wealth map and the rota.

**Agents run vertically, always alphabetical, always in the same order.** Row
twelve is the same agent in every figure. It costs something — sorting the wealth
map by final holdings would be more informative — but it buys more: the reader can
follow an agent from figure to figure, and it makes the rota's finding (that the
alphabet *is* the ordering) visible instead of something to take on trust.

**One tint for magnitude, three for the payoff cells.** Where a cell carries a
magnitude — holdings, messages, harvests — the colour is one hue from light to
dark. Where three payoff cells stand together they carry three fixed colours that
keep the same meaning in every figure.

### The palette

Okabe-Ito, the standard colourblind-safe palette. The three payoff colours are the
maximally separable three from it:

| role | colour | |
|---|---|---|
| scarce | `#0072B2` | blue |
| knife-edge | `#009E73` | blue-green |
| abundant | `#D55E00` | vermilion |
| magnitude ramp | white → `#0072B2` | holdings, messages, harvests |
| target (network) | `#D55E00` | the agent attacked |
| attacker | `#0072B2` | who joined in |
| abstainer | `#FFFFFF` with a stroke | who could and did not |

**Machine-checked** by `plots/_palette.py`. Each pair is simulated under
deuteranopia, protanopia and tritanopia (Viénot/Brettel) and the distance measured
in OKLab. All three pairs clear the threshold of 8; the tightest is
scarce/knife-edge under tritanopia at 9.0, and all three stay well above the
normal-vision floor of 15. Re-run the script whenever a colour changes.

### The page, and why the figures are drawn at exact widths

The chapter is `\documentclass[9pt,twocolumn]{article}` on A4 with 0.75in margins
and a 0.25in column separation, so `\textwidth` is 6.768in and a column is
3.259in. (`article` has no 9pt option and silently gives 10pt, so the body text is
10pt.) Every figure is drawn at exactly one of those two widths, so `\linewidth`
scales it 1:1 and 7pt in the figure is 7pt on the page. Letting LaTeX resize is
how a set of figures ends up with four type sizes — which happened here, when four
panels saved with a tight bounding box came out at four widths.

The column is 737pt tall. A figure and its caption have to fit inside that or the
float is silently pushed off the page.

### The style module

Everything above lives in `plots/_style.py` and no figure sets a font, a colour or
a page dimension of its own:

| | |
|---|---|
| `style()` | seaborn `whitegrid`, then the chapter's Times at 7/8.2pt |
| `COLOUR`, `PAYOFF`, `RUNG` | the payoff colours and the names of the rungs |
| `WIDTH`, `COLUMN`, `HEIGHT` | the page, in inches |
| `tint(colour, towards_white)` | pale fills; desaturating instead reads as dirty |
| `save(fig, figure, name)` | PDF into `figures/<figure>/`, PNG preview into `out/` |
| `margins(fig, label_width, height)` | fixed margins in inches, so panels match |
| `figure_tex(...)` | the `figure*` wrapper and caption, written by the script |

**Technique.** Matplotlib with seaborn's `whitegrid` underneath. Hand-written SVG
was the first attempt and was abandoned: full control over every coordinate
produces a figure that looks hand-made, and a reader who notices that is looking
at the drawing instead of at the data.

**One directory per figure** under `plots/figures/`, since a figure is rarely one
file. The draft's own `figures/` is a symlink to that directory, so a rebuild is
in the thesis with no copying step to forget. (Syncthing does not follow symlinks,
so the vault's copy is local to this machine.)

---

## Figure 1 · The rise and fall of names — **built**

**What the reader sees.** Four panels stacked — L2 scarce, L2 knife-edge, L3
scarce, L3 knife-edge — one run each. One horizontal violin per coined name: every
time an agent says that name is one observation at the round it was said. A violin
is wide where the name was in many mouths at once and long where it stayed in the
language; the dots are the utterances, and the bar inside is the median round and
the middle half.

**How it is built.** Seaborn `violinplot` + `stripplot`, horizontal, names in order
of first appearance. `density_norm="width"` so every violin is the same width —
otherwise one name with three hundred utterances flattens its neighbours and the
succession is lost. Four separate PDFs at a fixed row height, stacked in LaTeX, so
a row is the same size in every panel. The script writes its own caption, with
seeds and cell spread, so figure and caption cannot come apart.

**What the reader takes from it.** A diagonal: each name arrives later than the
last. Under scarcity at L2 thirteen names in succession — *Inner Circle*, *Allied
Group*, *Rotating Council*, *Debt Registry*, *Total Halt* — where at knife-edge the
early ones are still being said at the end. Median life 17 rounds against 32.

**What it gives the section.** §4.2 counts coined terms per cell and says nothing
about what became of them. That the scarce cell coins more and holds each half as
long is invisible in a count and immediate here.

**What the measure counts.** One arrangement, one term: wordings are merged on
content-word overlap (*Core NAP* / *Core Local NAP* / *Local NAPs* is one pact),
and sentence fragments carrying a finite verb or a negation do not count (*IS
DEPLETED* is not a name). Both live in `core/text.py`, not in the drawing — a
figure that has to hide what its measure counts is arguing against that measure.

**Three abandoned forms.** Bands, a grid and a raincloud sit in `_parked/` with
their reasons. Briefly: the first two showed *that* a name was used but not how,
and the third was a distribution in a chapter that already has enough of them.

---

## Figure 2 · The largest attack — **built**

**What the reader sees.** Two networks side by side. On the left the largest
coalition at L2 — seven attackers — on the right the one at L3, with twenty-nine.
The target at the centre in vermilion, the attackers around it in blue with their
names, and the target's neighbours who did *not* join as open circles with only a
stroke.

**How it is built.** `combat.fights(path)` gives the attackers and the defender per
fight; the round's own graph gives the target's neighbours. The scene is the largest
coalition the rung produced anywhere, ties broken by the target's neighbourhood so
the room left unused is at its clearest. Attackers are placed on the ring first and
abstainers after them, so the coalition sits together; that is a readability choice
and the caption says so, because the ring is not the graph's own layout and ties
between two neighbours are not drawn.

A faint circle is drawn through the positions. Without it the empty markers read as
scattered points; with it they read as gaps in something, which is the claim.

**What the reader takes from it.** Six gaps in the ring on the left, none on the
right. Seven of Cobalt's thirteen neighbours strike it in round 6 of an L2 abundant
run; twenty-nine of Blue's twenty-nine strike it in round 30 of an L3 scarce run.
Seven is the largest coalition in all three L2 payoff cells, which is why the two
panels are drawn from different payoffs: the ceiling is a property of the rung.

**What it gives the section.** §4.2 claims the ceiling of seven is behavioural and
not structural, and supports it with "the agents it struck had nine, ten and
thirteen neighbours". That asks the reader to hold three numbers and build a
picture. This *is* that picture.

---

## Figure 3 · What each round does to what an agent holds — **built**

**What the reader sees.** Four panels, one run per rung: thirty agents down the
side in alphabetical order, sixty rounds across, a cell coloured by the *change*
in that agent's holdings over that round. Blue for a gain, vermilion for a loss,
pale where little happened. A cross marks the agent a coalition attacked that
round, an open dot each agent that joined.

**How it is built.** `logs.rounds(path)` for holdings, differenced along the round
axis; `combat.fights(path)` for the crosses and dots. One run per rung, each the
run whose final Gini is its cell's median. The scale is symmetric and logarithmic
on both sides of zero (`SymLogNorm`, linthresh 2): the median round is a loss of
one resource and the worst a loss of a hundred, so a linear scale renders the
first as nothing and a log scale cannot cross zero.

**Why the change and not the level.** The level map was built five ways and
abandoned (see `_parked/`). A magnitude grid says a row is brighter than its
neighbours and not how it got that way, and since everything drains slowly it
reduces to four panels of gradual fading. The change separates the two things that
are actually happening: the fee, which is the pale wash over everything, and the
combat, which is the few cells that are not pale. The crosses then separate a
loss from a bleed — without them the panel says an agent ended lower and leaves
the reader to guess which.

**What the reader takes from it.** Four economies on one instrument. At L1 pairs
are broad blue bands with a dotted orange line through the givers, who pay every
round. At L2 the wash is nearly uniform with clusters between rounds ten and
twenty. At L3 the first thirty rounds are dense with both colours and the last
thirty are empty. At L4 the marks are small, mixed and spread — and there is not
one cross, though the capacity to attack is carried up the ladder.

The rungs differ in the *speed* of a loss, not its size: the steepest fall is
97 to 15 at L1 and 97 to 39 at L4, over fifty-nine and twenty-three rounds, and
274 to nothing in five at L3.

**No names in this panel.** Figures 1 and 2 are about individuals and carry names.
This one is about a regime, and an arrow reading "Amber 274 → 0" turns four
economies into one agent's story. The fall is computed and reported in the text
instead.

---

## Figure 4 · The rota nobody agreed — **built**

**What the reader sees.** Two panels, both the L4 scarce cell: thirty agents in
alphabetical order against sixty rounds, a mark where that agent harvested. Rounds
whose harvesters form a contiguous alphabetical block are coloured, the rest grey.
The upper panel walks down the alphabet in fives and starts again; the lower one
rotates just as strictly on some other assignment and is grey throughout.

**How it is built.** The action per agent per round from the round logs. The block
test is Measure~`m:commons-capacity-level`'s, verbatim.

**What the reader takes from it, and what it changed.** This figure was drawn to
illustrate a claim and ended up correcting it. The chapter reported 42.7% of
harvest rounds as alphabetical blocks against a chance level of 0.12%, which reads
as a tendency present everywhere. It is a mixture: four of the ten scarce runs score
zero and six score half to nine tenths. Drawing one from each half made the reason
plain --- both are rotas. The zero-scoring run harvests ten agents a round on a
three-round cycle in which every agent keeps its slot for fifty rounds. The block
test cannot see it, because those cohorts are not alphabetical blocks.

That produced a new measure, `m:harvest-rhythm`, and a rewritten passage in §4.2:

- A rota forms in **all ten** scarce runs. The period is six rounds at the median
  and **every interval** in the run sits at it, against 22.1% for the same harvests
  scattered at random.
- Harvesters per round times the period equals the population exactly: the thirty
  divide into cohorts with nobody left over and nobody in two.
- Under the same rung **without a channel** the period is one round in both control
  runs --- everyone harvesting every round, which is no schedule at all.
- Whether the cohorts follow the alphabet is a second, weaker question: 76.7% of
  scarce agents fall in contiguous blocks against a chance level of 16.7%, ranging
  from 23 to 100% across runs.

The schedule is what the channel buys. The alphabet is one way of filling it in.

---

## Figure 5 · Who writes to whom — **built**

**What the reader sees.** Four thirty-by-thirty matrices: sender down the side,
addressee across, both alphabetical, a cell darkening on a log scale with the
number of messages that pair exchanged. Gemma on the top row, Qwen on the bottom,
L2 left and L3 right. A bar along the top of each matrix gives how much each agent
was written to, and one down the right how much it wrote.

**How it is built.** The `to` fields of the messages, the same source as
`m:address-each-other`. One run per panel, with the seed held fixed down each
column, so the two arms open on the same graph and the difference between the rows
belongs to the model.

**What the design got wrong, and what replaced it.** The plan was a band around the
diagonal at L2 — you can only reach your neighbours — opening out at L3. There is
no such band and there cannot be: the starting graph is not alphabetical, and
connected agents sit a median of nine apart in the list, so adjacency is scattered
across the square by construction. What the panels differ in is not shape but
coverage: Gemma writes into 23% of the 870 ordered pairs at L2 and 53% at L3, while
Qwen goes from 19% to 25% and barely moves between the rung where it can reach only
its neighbours and the rung where it can reach anyone.

The margin bars were added for the same reason. Without them the square is a
scatter of cells with nothing for the eye to hold; with them a panel says whether
the traffic is spread over the population or piled onto a few agents.

**What it gives the section.** §4.5 rests on 9.1 recipients a message against 2.5,
which asks the reader to believe what a matrix shows. It also covers the arm
comparison, which otherwise has no figure.

---

## What this set does not do

None of the five shows a mean over cells, and that is deliberate. The load-bearing
numbers stay in the text; the figures show where those numbers come from. Every
caption therefore says which run is shown and how it was chosen.

Two of the five are a single run (4, and 1 per panel). Three show several side by
side. Where one run is shown, the caption carries the spread it came from.
