# Meeting Prep: Mar 14 with Debraj

## Agenda

### 1. Three IVs — Design Decisions (approval needed)
- **IV1: Reasoning depth** L0-L3 — unchanged
- **IV2: Network rewiring** w ∈ {0, 0.05, 0.3, 1.0} — replaces fixed spatial grid
  - Payoff-based rewiring (Zimmermann 2004), ER initial graph ⟨k⟩≈4-6
  - Deep research done: full literature review saved (notes/deep_research_network_rewiring.md)
  - Key refs: Rand et al. 2011 PNAS (human experiments), Pacheco 2006 (phase transition at w*)
  - Risk: LLM agents may not rewire "rationally" — exploratory runs should reveal
- **IV3: Communication scope** no-comm / DM / broadcast / choice — replaces contracts
  - All cheap talk (Crawford & Sobel 1982), no enforcement
  - Choice condition: agent selects DM or broadcast → channel preference as DV
  - Contracts → future work (Discussion)
- **Base defaults**: hidden resources ON, memory ON (not IVs)
- **Hobbes mapping**: two-layered for IV2 (hidden resources = source, w = structural response)

**Question for Debraj**: Does this design make sense? Especially: contracts dropped — is that OK?

### 2. OAT Screening Results
- TODO: analyze nightrun v3 results (jobs 20197381-20197397)
- Which params create genuine dilemmas? Top candidates for factorial

### 3. Exploratory Runs
- Max emergence config ready (experiments/max_emergence_exploratory.yaml)
- 10 agents, 30 rounds, L3, hidden resources, memory ON, high social surplus
- Running on OpenRouter (Qwen 3.5-27B, ~$0.50/run)
- TODO: present results if available

### 4. Examiner: Maik Larooij?
- Dual PhD student UvA (Graus, Marx, Kamps)
- Published "Validation is the central challenge for generative social simulation" (AI Review 2025)
  — systematische review, precies de methodologische kritiek die onze thesis moet adresseren
- Published "Can We Fix Social Media?" met Petter Törnberg — 1000+ LLM agents, haalde Science
- Had eerder mailcontact over mogelijke thesis bij hem
- Sterke fit: LLM × ABM validatie, faithfulness, grote simulaties
- Complement met Debraj: Maik = LLM/ABM validation, Debraj = game theory/mechanism design

**Question for Debraj**: Is Maik Larooij a good choice as second reader? Any other suggestions?

### 5. Network Implementation Plan
- Replace spatial.py with dynamic graph module
- Engine changes: rewiring step after each round
- Prompt changes: show current neighbours (not grid position)
- Timeline: aim to have basic implementation before next meeting (Mar 28)

### 6. Methods Chapter Progress
- All TODO outlines written for §3.1-3.5
- Network topology, information structure, communication scope sections fully designed
- Ready to start writing prose

---

## Deliverables to Show
- [ ] OAT screening analysis (if Snellius results ready)
- [ ] Exploratory run results (if OpenRouter runs done)
- [ ] IV design document (can walk through Methods TODOs)
- [ ] Network rewiring literature summary
- [ ] TextGrad assessment (if job complete)

---

## Questions to Ask
1. Network rewiring design: does payoff-based make sense for 6-action game?
2. Communication: DM vs broadcast vs choice — is 4 levels too many?
3. Contracts dropped — is that acceptable or should we keep it?
4. Maik Larooij as examiner?
5. Timeline: is network implementation before factorial realistic?
