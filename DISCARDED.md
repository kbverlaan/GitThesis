# What was removed, and why

This public snapshot is a clean rebuild of the working thesis repository. Only
the code that produces the manuscript — the engine, and the measures package
pruned to the figures and tables the thesis actually cites — was carried over.
This register records what was left behind, so the omissions are deliberate and
visible rather than silent.

The `simulation/` nesting was dropped: `src/`, `config/`, `measures/`, `tests/`
and `handlabels/` now sit at the top level.

## Development scaffolding (not part of the published work)

- `.claude/`, worktrees, `claude.md` — agent-assistant instructions and scratch.
- `text/`, `docs/Master/` — thesis chapters and drafts (they live in the
  author's notes; the final PDF is added separately).
- `docs/` reference PDFs (rubric, manual, cited papers) — third-party,
  copyrighted, not ours to redistribute.
- Root `scripts/` (Zotero helpers) and `s2.py` — one-off tooling.
- `simulation/scripts/`, `simulation/experiments/`, `simulation/snellius/`,
  `simulation/viewer/` — SLURM job files, UMAP/TextGrad probes, a log viewer,
  and exploratory scripts that no reported figure depends on.
- `config/archive_*` — superseded config snapshots.

## measures/ — pruned to the thesis

The measures package was rebuilt around one function per reported figure
(`figures/`), collected by `registry.py` into `out/figures.json`. Everything
kept here produces a cited figure or table. Removed:

- `check.py` and `tools/{figures_unchanged,stack_check,registered_check}.py` —
  consistency checkers that read the thesis draft from the author's notes; they
  cannot run outside that setup and are not needed to reproduce a figure.
- The pre-rebuild per-measure files, superseded by `figures/`: all of
  `combat/`, `commons/`, `language/`, and every `M*` file in `economy/` and
  `structure/` **except** the three still used to build the LaTeX tables —
  `economy/grid_profile.py`, `M31_channel_off.py`, `structure/M39_form_profile.py`.
- Top-level one-offs `M01_model_swap.py`, `M10_institution_effect.py`,
  `drifted.py`, `note.py`, `unanchored.py`, `unitless.py`.
- Working notes and inventories: `_BRON`, `_INVENTARIS*.md`, `_DECISIONS.md`,
  `_LEDGER.md`, `_LESSONS.md`, `_inventaris_ruw.json`, `measures_out.json`.
- `plots/_parked/` and the regenerable reasoning-trace cache `plots/cache/`.

## Data

The ~33 GB of raw per-turn run logs (`data/thesis_final/`) are not committed;
the reproducible aggregates in `measures/out/` are kept instead. See the README.
