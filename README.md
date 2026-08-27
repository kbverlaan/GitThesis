# The Origins of Order

Code for the MSc thesis *The Origins of Order* — how minimal structure lets
language-based multi-agent LLM systems organise themselves.

**Author:** Koen Verlaan · **Programme:** MSc Computational Science, University
of Amsterdam · **Year:** 2025–2026

## What this is

Generative agents play a repeated resource game. The design varies four things
and watches what social order appears:

- **Capacity level** — give-or-hold (L1), predation (L2), network rewiring (L3),
  a shared commons (L4);
- **Payoff regime** — scarce, knife-edge, abundant;
- **Language channel** — on, or removed;
- **Model family** — two backends, to separate what belongs to the game from
  what belongs to the model.

The engine runs the games and writes a per-turn log for every run. The
`measures/` package turns those logs into the exact figures and tables of the
thesis.

## Layout

```
src/          simulation engine — agents, game, runner, analysis
config/       YAML run configs: one per cell (prod_L{1-4}_{scar,knife,abund}),
              model backends, ladder levels, game parameters
handlabels/   hand-coded label sets used for validation
tests/        engine unit tests
measures/     analysis package: run logs -> figures and tables
  core/         primitives over run logs (no figure-specific logic)
  _shared/      runset loader + shared statistics
  figures/      one function per reported figure; registry.py collects them
  plots/        renderers for the manuscript figures (fig0-fig8)
  tables/       generated LaTeX tables (tab_grid, tab_forms, tab_channel)
  tools/        uncertainty.py — run-level bootstrap + exact binomial intervals
  out/          committed aggregates (figures.json, scalars.json, uncertainty.json)
  registry.py   runs every figure -> out/figures.json  (53 measures)
  make_tables.py regenerates the three LaTeX tables
  tests/        the standards the measures package holds itself to
requirements.txt
repo-audit.sh   hygiene checks (+ --reproduce)
DISCARDED.md    what was removed from the working repo, and why
```

## Data

The raw run logs (~33 GB of per-turn JSONL, one folder per run under
`data/thesis_final/`) are **not** in this repository. What the thesis cites are
the committed aggregates in `measures/out/*.json` and the figures in
`measures/plots/out/`, and those are enough to read the results without the
logs. The full logs are available from the author on request; a fresh clone has
no `data/` directory, so create it first and put the logs there —
`mkdir -p data/thesis_final` — to regenerate everything.

## Running a simulation

```bash
pip install -r requirements.txt
# provide a model key in the environment (OPENROUTER_API_KEY),
# or point --api at a local vLLM server (config/vllm_config.yaml).
python3 src/main.py --game config/game_params.yaml --api config/vllm_config.yaml
```

## Reproducing the figures and tables

With `data/thesis_final/` in place:

```bash
cd measures
python3 registry.py           # -> out/figures.json (the 53 measures)
python3 make_tables.py        # -> tables/tab_*.tex
python3 plots/fig3_wealth.py  # -> plots/out/...  (one script per figure)
```

`./repo-audit.sh --reproduce` regenerates the tables and checks them against the
committed copies.

## Provenance

Each committed aggregate records the commit and date at which it was generated
(`commit` and `generated` in `out/figures.json`; the header comment of each
`tables/*.tex`). This public snapshot is a single squashed commit with the
private development history removed, so that internal hash does not resolve
here — read it as a timestamp, not a link. The guarantee the repository offers
instead is **reproduction**: run the pipeline above and it rebuilds the
committed artifacts from the code in this commit.

## License

Released under the MIT License — see `LICENSE`.
