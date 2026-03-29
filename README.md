# The Origins of Order

**Author**: Koen Verlaan  
**Programme**: Master Computational Science, University of Amsterdam  
**Year**: 2025-2026

## Research Question

How do strategic reasoning, information structure, and communication scope shape emergent social order in multi-agent LLM systems?

## Repository Structure

This repo contains **code only**. All research notes, roadmap, sprint logs, meeting notes, reading lists, and design docs live in Obsidian (single source of truth).

```
GitThesis/
├── simulation/
│   ├── src/               # Game engine, agents, prompts, analysis
│   ├── config/            # YAML configurations
│   ├── experiments/       # Experiment YAML definitions
│   ├── scripts/           # Utility scripts (UMAP, TextGrad, etc.)
│   ├── snellius/          # SLURM job scripts (SURF HPC)
│   └── archive/           # Archived scripts and old runs
├── text/
│   ├── proposal/          # Submitted proposal (Jan 2026)
│   └── main/              # Thesis chapters (CLS LaTeX template)
├── scripts/               # Zotero helper scripts
├── docs/                  # Reference PDFs (rubric, manual, tips)
├── claude.md              # Agent instructions (for Claude Code)
└── README.md
```

## Quickstart

```bash
cd simulation
python3 src/main.py --game config/game_params.yaml --api config/vllm_config.yaml
```

## Key Links

- **Roadmap + sprint log**: Obsidian → Projecten/Thesis/Roadmap
- **Experiment log**: Obsidian → Projecten/Thesis/Experiment Log
- **Proposal**: `text/proposal/VerlaanProposal_1.pdf`
- **Experiment configs**: `simulation/experiments/`
