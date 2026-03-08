# The Origins of Order

**Author**: Koen Verlaan
**Programme**: Master Computational Science, University of Amsterdam
**Year**: 2025-2026

## Research Question

How do strategic reasoning, information structure, and communication scope shape emergent social order in multi-agent LLM systems?

## Repository Structure

```
GitThesis/
├── text/
│   ├── proposal/          # Submitted proposal (Jan 2026)
│   └── main/              # Thesis chapters (CLS template)
├── notes/                 # Research notes, meeting prep, reading lists
│   └── archive/           # Older notes (Feb 2026 bulk archival)
├── simulation/
│   ├── src/               # Game engine, agents, prompts, analysis
│   ├── config/            # YAML configurations
│   ├── experiments/       # Experiment YAML definitions
│   ├── scripts/           # Utility scripts
│   ├── snellius/          # SLURM job scripts (SURF HPC)
│   ├── data/              # Active run data, showcase, figures
│   └── archive/           # Archived scripts and old runs
├── data/experiment_log/   # Phase 1 experiment logs
├── docs/                  # Reference PDFs, archived plans
└── scripts/               # Paper search utilities
```

## Quickstart

```bash
cd simulation
python3 src/main.py --game config/game.yaml --api config/api.yaml
```

## Key Documents

- **Roadmap**: `notes/roadmap.md`
- **Proposal**: `text/proposal/VerlaanProposal_1.pdf`
- **Experiment configs**: `simulation/experiments/`
