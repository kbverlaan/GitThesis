# The Origins of Order: Thesis Repository

**Author**: Koen Verlaan  
**Institution**: Master Computational Science  
**Year**: 2026

## Overview

This repository contains the complete thesis project investigating whether stable power structures emerge from material constraints alone, or require semantic understanding.

## Structure

- **`text/`** — Thesis writing, notes, and specifications (no code)
- **`code/`** — Simulation implementation and analysis scripts (no thesis text)
- **`data/`** — Raw outputs, processed data, experiment runs (gitignored)
- **`figures/`** — Exported figures for thesis inclusion
- **`bibliography/`** — Reference management (BibTeX)
- **`export/`** — LaTeX export artifacts

## Quickstart

### Writing Workflow
1. Draft chapters in `text/chapters/` (Markdown format)
2. Keep running notes in `text/notes/`
3. Export to LaTeX when ready using `export/latex/`

### Code Workflow
1. Environment implementation in `code/env/`
2. Agent architectures in `code/agents/`
3. Run experiments from `code/experiments/`
4. Analysis scripts in `code/analysis/`

## Key Documents

- **Thesis Proposal**: `text/specs/ThesisProposal_Clean.md`
- **Environment Spec**: `text/specs/ENVIRONMENT_OUTLINE.md`

## Git Hygiene

- `/data/` is gitignored (large experiment outputs)
- `/export/` is gitignored (generated LaTeX/PDF artifacts)
- Commit small, focused changes with clear messages
- Keep text and code changes in separate commits where possible
