# Practical Experiment Plan
**Created**: 2026-02-16
**Strategy**: Hybrid — Architectures as safe base, Origins phase transition in parallel
**Remaining sprints**: 10 (Feb 27 → Jul 3), meeting every 2 weeks

---

## What exists vs. what needs building

### Already done
- [x] Game engine, spatial field, 30-agent runs working
- [x] Sweep infra: factorial/grid designs, target routing, framing support
- [x] Basic metrics: Gini, Palma, action stability, action distribution
- [x] Run-level metrics: cooperation_ratio, first_attack_round, retaliation_probability, coalition_stability
- [x] Prompt framing system (5 framings: neutral, cooperative, competitive, strategic, cautious)
- [x] 142 exploratory runs with key findings
- [x] Experiment YAML specs for Phase 2

### Needs building — code

| Component | Priority | Effort | Needed for |
|-----------|----------|--------|------------|
| **Extended metrics module** | HIGH | 2-3 days | Both paths |
| Theil T index (decomposable inequality) | | 1hr | All experiments |
| Atkinson index (ε=1) | | 1hr | All experiments |
| Cooperation rate f_C(t) as timeseries | | already have cooperation_ratio, need per-round version | Exp 1 |
| Variance of f_C across replications | | 1hr | Origins Exp 1 |
| **Network analysis module** | MEDIUM | 3-4 days | Arch Exp 1 |
| 5-round sliding window network construction | | 2hrs | |
| Leiden community detection (needs leidenalg package) | | 2hrs | |
| NMI between consecutive partitions | | 1hr | |
| Network metrics (density, reciprocity, clustering, centrality) | | 3hrs | |
| Elo ratings + steepness (de Vries) | | 3hrs | |
| Landau's h' + triangle transitivity | | 2hrs | |
| **Early Warning Signals (EWS) module** | HIGH | 2-3 days | Origins Exp 1 |
| Rolling-window variance, AC-1, skewness | | 3hrs | |
| Kendall's τ trend test | | 1hr | |
| Gaussian kernel detrending | | 1hr | |
| Binder cumulant U calculation | | 1hr | |
| TIPMOC power-law variance fit | | 3hrs | |
| **Trace analysis pipeline** | MEDIUM | 4-5 days | Origins Exp 2 |
| Structured JSON CoT output (beliefs, strategy, intention) | | 2hrs (prompt change) | |
| LLM-based trace coding (LACA pipeline) | | 1-2 days | |
| ToM depth classifier (Level 0/1/2/3) | | 3hrs | |
| BERTopic for emergent themes | | 3hrs | |
| Faithfulness validation (early-answering test) | | 3hrs | |
| **Prompt sensitivity measurement** | LOW | 1-2 days | Arch Exp 2 |
| FormatSpread (3+ equivalent prompt variants) | | 3hrs | |
| PromptSensiScore | | 2hrs | |
| **Statistical analysis module** | HIGH | 2 days | Both paths |
| Two-way ANOVA + partial η² | | 2hrs | |
| Bayes factors (JZS prior) | | 3hrs | |
| ICC calculation | | 1hr | |
| Dominance analysis | | 3hrs | |
| Mixed-effects model (needs statsmodels or R) | | 3hrs | |
| Power analysis via simulation | | 2hrs | |
| **RL baseline agent** | LOW | 3-5 days | Arch Exp 1 (optional) |
| Simple Q-learning or PPO agent | | | |
| Integration with game engine | | | |

### Needs building — experiment configs

| Experiment | YAML exists? | Runs | Status |
|------------|-------------|------|--------|
| Origins Exp 1: radius sweep (extended) | `phase_transition_radius.yaml` — needs update to 20 reps, wider range | ~200 | TODO |
| Origins Exp 1: agent count sweep | `phase_transition_agents.yaml` — needs update for Binder cumulant (N=15,20,30,45,60) | ~200 | TODO |
| Origins Exp 1: information visibility sweep | needs new YAML | ~100 | TODO |
| Origins Exp 3: necessary/sufficient | `necessary_sufficient.yaml` — needs update to 20 reps | ~120 | TODO |
| Arch Exp 1: fingerprinting | `architectural_fingerprint.yaml` — update to 20 reps | ~80 | TODO |
| Arch Exp 2: model × framing factorial | `prompt_framing_factorial.yaml` — update to 20 reps | ~300 | TODO |
| Arch Exp 3: robustness | needs new YAML | ~120 | TODO |

---

## Sprint-by-sprint plan

### Sprint 3: Feb 27 - Mar 13
**Theme**: Metrics foundation + first production sweeps
**Meeting deliverable**: Extended metrics on existing data, first Arch Exp 1 results

- [ ] Build extended metrics module (Theil T, Atkinson, per-round f_C, variance of f_C)
- [ ] Build EWS module (rolling variance, AC-1, skewness, Kendall's τ)
- [ ] Update experiment YAMLs to production reps (20 per condition)
- [ ] Run Arch Exp 1: architectural fingerprinting (3 models × 20 runs = 60 runs)
- [ ] Run Origins Exp 1a: radius sweep (8-10 values × 20 runs = 160-200 runs)
- [ ] Compute EWS on radius sweep — is there a phase transition signal?
- [ ] Literature: Perc et al. (2017), Scheffer et al. (2009), Akata et al. (2025)

### Sprint 4: Mar 13 - Mar 27
**Theme**: Factorial experiment + network analysis
**Meeting deliverable**: Model × framing results, network metrics

- [ ] Build network analysis module (Leiden, NMI, centrality, Elo steepness)
- [ ] Run Arch Exp 2: model × framing factorial (15 cells × 20 runs = 300 runs)
- [ ] Apply network metrics to Arch Exp 1 data — do architectures produce different network signatures?
- [ ] Statistical analysis: two-way ANOVA, η², dominance analysis on Exp 2 data
- [ ] Run Origins Exp 1b: agent count sweep for Binder cumulant (5 sizes × 20 runs = 100 runs)
- [ ] Literature: Lorè & Heydari (2024), Traag et al. (2019), de Vries et al. (2006)

### Sprint 5: Mar 27 - Apr 10
**Theme**: Phase transition verdict + necessary/sufficient
**Meeting deliverable**: Phase transition analysis, necessary/sufficient matrix

- [ ] Analyze: is the phase transition real? EWS signals + Binder cumulant crossing?
- [ ] **Decision point**: Origins framing viable? Or stay with Architectures?
- [ ] Run Origins Exp 3: necessary/sufficient factorial (6 cells × 20 runs = 120 runs)
- [ ] Run Arch Exp 3: robustness checks (top-2 contrasts × varied params × 10 runs = ~120 runs)
- [ ] Build statistical analysis module (mixed-effects, Bayes factors, ICC)
- [ ] Literature: Hofer et al. (2018), arXiv:2601.17311

### Sprint 6: Apr 10 - Apr 24
**Theme**: Trace analysis (if Origins) or deep statistical analysis (if Architectures)

**If Origins path:**
- [ ] Build trace analysis pipeline (structured CoT output, LACA coding)
- [ ] Run Origins Exp 2: 30 runs at 3 phase points with full trace logging
- [ ] Code traces: strategic orientation, ToM depth, temporal reasoning
- [ ] Faithfulness validation on subset

**If Architectures path:**
- [ ] Prompt sensitivity measurement (FormatSpread, PSS) on key conditions
- [ ] Power analysis on pilot data
- [ ] Additional robustness runs if needed
- [ ] Deeper network analysis: temporal evolution of communities

- [ ] Literature: Turpin et al. (2023), Lanham et al. (2023), faithfulness papers

### Sprint 7: Apr 24 - May 8
**Theme**: Analysis completion + start writing Methods
- [ ] All experiments complete by end of this sprint
- [ ] Finalize all metrics computation across all runs
- [ ] Generate publication-quality figures
- [ ] Start writing Methods chapter (game design, agent architectures, metrics, experimental design)
- [ ] Literature review outline

### Sprints 8-10: May 8 - Jul 3
**Theme**: Writing (see existing roadmap Phase 3-4)
- Methods → Results → Literature Review → Discussion → Introduction → Conclusion
- Iterate with Debraj feedback

---

## Run budget

| Experiment | Runs | Est. cost (Nova Micro) | Est. time |
|------------|------|----------------------|-----------|
| Arch Exp 1: fingerprinting | 60 | ~$5 | ~2hrs |
| Arch Exp 2: factorial | 300 | ~$25 | ~10hrs |
| Arch Exp 3: robustness | 120 | ~$10 | ~4hrs |
| Origins Exp 1a: radius sweep | 200 | ~$15 | ~6hrs |
| Origins Exp 1b: agent count | 100 | ~$8 | ~3hrs |
| Origins Exp 1c: info visibility | 100 | ~$8 | ~3hrs |
| Origins Exp 2: traces | 30 | ~$5 (Gemini) | ~5hrs |
| Origins Exp 3: nec/suf | 120 | ~$10 | ~4hrs |
| **Total** | **~1030** | **~$85** | **~37hrs** |

NB: kosten zijn voor Nova Micro ($0.06/$0.25 per M tokens). Gemini Flash Lite runs ~10x duurder. Runs draaien onbeheerd, dus wandklok ≠ werktijd.

---

## Decision points

| When | Decision | Criteria |
|------|----------|---------|
| **Sprint 5 (Mar 27)** | Origins or Architectures framing? | EWS shows significant trend (τ > 0.4)? Binder curves cross? Variance peak visible? |
| **Sprint 4 (Mar 13)** | Include RL baseline? | Is there time? Does it add enough to justify 3-5 days implementation? |
| **Sprint 6 (Apr 10)** | Trace analysis depth? | Faithfulness validation results — are traces usable as data? |
| **Sprint 7 (Apr 24)** | Scope cut if behind | Drop: RL baseline, prompt sensitivity measurement, equation-free analysis, TIPMOC |

---

## What to drop if time is short

**Cut first (nice-to-have):**
- RL baseline agent (3-5 days saved)
- Equation-Free bifurcation analysis
- TIPMOC parametric detection
- Topological change-point detection (Gu et al.)
- FormatSpread / PromptSensiScore prompt sensitivity
- BERTopic on traces

**Cut second (weakens but doesn't kill):**
- Elo steepness + Landau's h' (keep simpler hierarchy metrics)
- Binder cumulant (keep EWS as primary phase transition method)
- Faithfulness validation (acknowledge limitation instead)
- Information visibility sweep (already have data from runs 127-134)

**Never cut:**
- Extended inequality metrics (Theil T, Atkinson) — 2hrs, high value
- EWS on radius sweep — core of Origins path
- Model × framing factorial — core of Architectures path
- Network analysis basics (Leiden, NMI) — needed for "emergent structure" claim
- Mixed-effects statistical model — needed for any publication-worthy analysis

---

## Immediate next actions (this week, Feb 16-20)

1. [ ] Build `simulation/src/analysis/ews.py` — EWS module (rolling variance, AC-1, skewness, Kendall's τ)
2. [ ] Add Theil T, Atkinson index to `metrics.py`
3. [ ] Add per-round cooperation rate f_C(t) to sweep output
4. [ ] Update experiment YAMLs: radius sweep to 20 reps, 50 rounds, extended range
5. [ ] Start running Arch Exp 1 (fingerprinting) overnight — 60 runs, ~2hrs
6. [ ] Read Perc et al. (2017) — foundational for phase transition framing
7. [ ] Read Akata et al. (2025) — methodological template for factorial LLM experiments
