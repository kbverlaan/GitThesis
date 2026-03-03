# Thesis Roadmap: The Origins of Order

**RQ**: How do strategic reasoning, information structure, and communication scope each shape the emergence of social order in multi-agent LLM systems?

**Three IVs** — formally: the three inputs of mechanism design (Hurwicz, 1960). Narratively: Hobbes's three causes of conflict in the state of nature (*Leviathan*, 1651).

| IV | Manipulation | Mechanism Design | Hobbes | Mapping quality |
|----|-------------|-----------------|--------|----------------|
| 1. **Reasoning depth** (L0-L3) | K-level prompts | Solution concept | "Competition" — rational self-interest | Strong |
| 2. **Network rewiring** (w ∈ {0, 0.05, 0.3, 1.0}) | Payoff-based rewiring probability | Type space | "Diffidence" — two-layered (see below) | Moderate |
| 3. **Communication scope** (no-comm / DM / broadcast / choice) | Pre-action messaging phase | Message space | "Lack of common power" — can words alone create order? | Strong |

**IV2 two-layer nuance:**
- Layer 1: Hidden resources (base default, always ON) = direct Hobbes diffidence. Agents face genuine type uncertainty.
- Layer 2: Network rewiring w (the IV) = structural RESPONSE to diffidence. Higher w gives EXIT OPTION from bad neighbours.
- MD mapping is cleaner: w directly manipulates the type space (who you observe/interact with).

**Base defaults (not IVs):** hidden resources ON, memory ON (window 10), 6 actions (invest_self/other, arm_self/other, attack, do_nothing), %-based economy.

**Framing note**: mechanism design mapping is the formal backbone. Hobbes mapping is narrative — used for intro/discussion with caveats.

**Timeline**: Feb 2026 - July 2026
**Submission deadline**: July 15, 2026
**Defence**: Late July 2026
**Biweekly meetings**: Fridays at 14:00 with Debraj (Feb 27, Mar 13, Mar 27, Apr 10, Apr 24, May 8, May 22, Jun 5, Jun 19, Jul 3)
**Sprint cadence**: 2-week sprints, each ending at the Friday meeting

---

## How This Document Works

Each **phase** covers ~4-6 weeks. Each **sprint** is 2 weeks, ending at the biweekly Friday meeting.
After each meeting, update the sprint with outcomes and set the next sprint goals.

Rubric reminder (what matters):
- Research Work 35% (theory knowledge, programming, independence, creativity, attitude)
- Thesis Report 50% (literature 20%, methods 20%, results 20%, question 10%, rest split)
- Presentation 15%

---

## Phase 1: System Characterization (Feb 1 - Feb 18) ✅ COMPLETE
**Focus**: Understand the simulation as a system before varying prompts

Per Debraj (Feb 13): "Without understanding the system, it's impossible to say anything about changing the prompting later."

### Goals for this phase
- [x] Pick ONE metric: hierarchy (Gini coefficient, top 10% vs bottom 50%)
- [x] Pick ONE baseline prompt + parameter set
- [x] Measure agent action stability over time: do they converge on optimal actions?
- [x] Define theta = cost/benefit for each action, systematically vary it → pivoted to parameter sensitivity analysis
- [x] Determine how theta affects game stability (should be sensitive + indicative)
- [x] Scale to 30 agents (research suggests significant distribution changes)
- [x] If time: vary initial wealth distribution, vary simultaneous vs random action order
- [ ] Read core literature across all areas (see reading list below) — ongoing
- [x] Metrics pipeline: can compute Gini, action stability, distributions from runs

### Reading List (core papers -- TODO: prioritize and track)
**RL + emergent social structures**:
- [ ] Leibo et al. 2017 - Multi-agent RL in Sequential Social Dilemmas
- [ ] Baker et al. 2019 - Emergent Tool Use (hide and seek)
- [ ] Lowe et al. 2017 - MADDPG
- [ ] Silver et al. 2021 - Reward is Enough

**LLM agents**:
- [ ] Park et al. 2023 - Generative Agents
- [ ] Ju et al. 2024 - Sense and Sensitivity (prompt sensitivity)
- [ ] Zarz et al. 2023 - Emergent Cooperation with LLMs
- [ ] TODO: Moltbok reference you mentioned in ideas.txt

**Foundations / ABM**:
- [ ] Axelrod 1984 - Evolution of Cooperation
- [ ] Epstein & Axtell - Sugarscape (Growing Artificial Societies)
- [ ] Schelling - segregation model (background)

**Validation / methodology**:
- [ ] Larooij & Tornberg 2025 - LLM agent validation critique
- [x] Dubey et al. 2018 - Investigating Human Priors (semantic ablation inspiration)

**From Debraj (Feb 13)**:
- [x] Debraj's paper with master student - RL in similar game (MUST READ): https://dl.acm.org/doi/10.5555/3635637.3662962
- [x] TextGrad (Zou group) - prompt sensitivity tool: https://github.com/zou-group/textgrad
- [ ] EGG (Facebook) - emergence of language framework: https://github.com/facebookresearch/EGG

**Debraj's other papers (added Feb 17)**:
- [ ] Mengesha & Roy 2025 - "Evolutionary Game Selection Leads to Emergent Inequality" (ICCS 2025). Game selection co-evolves with strategies → inequality. Connects to our finding that architectures "select" different equilibria. https://link.springer.com/chapter/10.1007/978-3-031-97557-8_21
- [ ] Mengesha & Roy 2025 - "Carbon pricing drives critical transition to green growth" (Nature Communications). ABM with critical transitions — methodological reference for phase transition analysis.
- [ ] Dupont & Roy 2025 - "Emergent poverty traps at multiple levels impede social mobility" (Humanities & Social Sciences Communications). Multi-level emergence and poverty traps — connects to our Matthew Effect finding.
- [ ] Bazyleva, Garibay & Roy 2024 - "Trajectory-based global sensitivity analysis in multiscale models" (Scientific Reports). GSA methodology for ABMs — could inform parameter sensitivity analysis.

**Reasoning depth & faithfulness** (added Feb 18):
- [ ] Zhang et al. 2025 - "K-Level Reasoning: Establishing Higher Order Beliefs in LLMs for Strategic Reasoning" (NAACL 2025). K-Level framework for varying reasoning depth. https://arxiv.org/abs/2402.01521
- [ ] Turpin et al. 2023 - "Language Models Don't Always Say What They Think: Unfaithful Explanations in CoT Prompting" (NeurIPS 2023). CoT can be systematically biased without model acknowledging it. https://arxiv.org/abs/2305.04388
- [ ] Lanham et al. 2023 - "Measuring Faithfulness in Chain-of-Thought Reasoning" (Anthropic). Faithfulness varies by task; larger models = less faithful. https://arxiv.org/abs/2307.13702
- [ ] Chen et al. 2025 - "Reasoning Models Don't Always Say What They Think" (Anthropic). Reasoning models construct fake rationales, <2% admit to using hints. https://arxiv.org/abs/2505.05410
- [ ] arXiv:2502.20432 - "LLM Strategic Reasoning: Agentic Study through Behavioral Game Theory". CoT not universally effective — interacts with model capability.
- [ ] arXiv:2601.15047 - "Game-Theoretic Lens on LLM-based Multi-Agent Systems". Formalizes reasoning equilibria — reasoning strategy changes the game's equilibrium.
- [ ] Abdelnabi et al. 2024 - "Cooperation, Competition, and Maliciousness: LLM-Stakeholders Interactive Negotiation" (NeurIPS 2024). Structured CoT in multi-agent negotiation.

**IR theory** (background, not central):
- [ ] Waltz 1979 - Theory of International Politics
- [ ] Wendt 1992 - Anarchy is What States Make of It

### Sprint 1: Feb 9 - Feb 13
- [ ] Literature deep dive (Mon-Wed)
- [ ] Review simulation runs, identify key patterns (Thu)
- [ ] Prepare meeting (Thu)
- [ ] Meeting with Debraj (Fri Feb 13)

---

## Phase 2a: Architecture & Framing Experiments (Feb 17 - Feb 18) ✅ COMPLETE
**Focus**: Do different LLM architectures produce distinct behavioral signatures? How does prompt framing interact?

### Key Results
- **Gemma 2 27B**: 100 runs complete (5 framings × 20 reps). η²=0.901 — framing explains 90% of Gini variance
- **Counterintuitive finding**: cautious framing (Gini 0.549) < cooperative (0.581)
- **Trace analysis**: reasoning vocabulary predicts outcome within identical action distributions
- Architecture comparison (cross-model) deprioritized: Qwen3-32B 8× slower, comparing models confounded
- **Decision**: pivot to reasoning depth on single model (cleaner science, maps to Debraj's Level-0/1/2)

### Artifacts
- Analysis: `arch_analysis.py`, `trace_analysis.py`, `notebooks/arch_exp_gemma2.ipynb`
- 6 meeting plots: boxplot, trajectories, action dist, Cohen's d heatmap, keyword table, scatter

---

## Phase 2b: Reasoning Depth Experiments (Feb 18 - ongoing) ✅ EXPLORATORY COMPLETE
**Focus**: Isolate reasoning depth as the key variable. Vary reasoning instruction on ONE model (Gemma 2 27B) to test: does deeper reasoning change emergent social structure?
**Status after Feb 27 meeting**: All exploratory work complete. Must rerun everything on Qwen 3.5-27B (dense) (Debraj: "one model, rerun everything"). Reasoning depth becomes one thesis chapter.

**Rationale for pivot** (decided Feb 18):
- Comparing different models (Gemma vs Qwen) is confounded — they differ on 100 dimensions
- Debraj's template: vary ONE parameter at a time on the same architecture
- Cleaner science: isolate reasoning depth while holding model constant

### Literature grounding
- Kuusela & Roy (AAMAS 2024): Level-0 (heuristic) vs Level-2 (recursive) → more reasoning = more conflict
- Zhang et al. (NAACL 2025): K-Level Reasoning framework for LLMs — recursive belief modeling
- Pfau et al. (2024): "Let's Think Dot by Dot" — even filler tokens improve performance (computational depth matters independent of content)
- Turpin et al. (NeurIPS 2023), Lanham et al. (2023): CoT not always faithful — frame as computational depth manipulation

### Implementation
- Reasoning levels implemented in `src/agents/prompts.py` via `REASONING_LEVELS` dict
- JSON prompt template dynamically inserts reasoning instruction based on level
- Backwards compatible: `reasoning_level='default'` preserves original behavior

| Level | Label | Reasoning instruction | Observed tokens |
|-------|-------|----------------------|-----------------|
| 0 | Reactive | "State your choice briefly. Do not deliberate." | ~6 |
| 1 | Strategic | "Calculate the expected value of each available action..." | ~31 |
| 2 | Opponent modeling | "First predict what each nearby agent is likely to do..." | ~40 |
| 3 | Recursive | "Consider that nearby agents are also reasoning about your likely actions..." | ~44 |

### Experiment 3: Reasoning Depth Pilot ✅ COMPLETE
**Design**: 4 reasoning levels × 3 reps = 12 runs, Gemma 2 27B, 30 agents, 50 rounds, spatial (r=2), zero costs
**Config**: `experiments/reasoning_depth_pilot.yaml`

**Results** (non-monotonic pattern — the key finding):

| Level | Gini (mean±std) | Coop ratio | Top actions | Tokens |
|-------|-----------------|------------|-------------|--------|
| L0 | 0.566 ± 0.034 | 70% | invest_other 54%, do_nothing 25% | 6 |
| L1 | 0.632 ± 0.064 | 63% | invest_other 47%, do_nothing 26% | 31 |
| L2 | 0.624 ± 0.079 | 39% | arm_self 40%, invest_other 32% | 40 |
| L3 | 0.712 ± 0.066 | 52% | invest_other 39%, attack 7% | 44 |

- NOT "more reasoning = more cooperation" (naive expectation)
- NOT "more reasoning = more conflict" (Kuusela & Roy's finding)
- It's **non-monotonic and mechanism-dependent**: L0 cooperative, L1 strategic, L2 defensive/arming, L3 exploitative

### Experiment 3b: Parameter Sweeps × Reasoning Depth
**Question**: Does reasoning depth interact with game structure parameters?
**Design**: 4 parameter sweeps × 4 reasoning levels × 3 reps each
**Configs**: `experiments/sweep_{arm_cost,conflict_cost,invest_self,invest_return}_reasoning.yaml`

| Sweep | Values | Status | Key finding |
|-------|--------|--------|-------------|
| arm_cost | 0, 2, 5 | ✅ 36/36 | **STRONG interaction**: L0 insensitive (Gini delta -0.045), L2 explodes (+0.226). L3 starts high, modest increase (+0.056) |
| conflict_cost | 0, 3, 5 | ✅ 36/36 | Weak effect across all levels. L3 insensitive (delta -0.012) — attacks regardless of cost |
| invest_self | true, false | ✅ 24/24 | **Strongest structural lever**: L0 collapses to 0.184 Gini with invest_self ON. L3 maintains 0.526 — highest even in safe regime |
| invest_return | 2, 5, 20 | 0/36 (waiting for SLURM maintenance to end) | — |

**Behavioral fingerprints confirmed across 96 runs (n=24 per level):**

| Level | Gini | Coop% | Arm% | Atk% | Character |
|-------|------|-------|------|------|-----------|
| L0 | 0.535 | 65% | 0% | 3% | Naive cooperator |
| L1 | 0.620 | 57% | 4% | 6% | Strategic calculator |
| L2 | 0.608 | 34% | 37% | 2% | Defensive hoarder |
| L3 | 0.693 | 47% | 16% | 8% | Selective predator |

**Key insights from full sweep analysis:**
- **arm_cost interaction** is the strongest: deeper reasoning AMPLIFIES structural incentives
- **invest_self** is the strongest structural lever overall (delta up to 0.411)
- **L3 is qualitatively different** from L2: cooperates more (47% vs 34%) but attacks 4× more (8% vs 2%). Cooperate-then-strike strategy.
- **L0 is structurally blind**: Gini barely changes across any parameter manipulation
- **L2 arms even when it's pointless** (31% arm_self with invest_self ON, where self-investment dominates)

### Experiment 3c: Reasoning Depth Production (PLANNED)
**Design**: 4 levels × 20 reps at optimized base params (selected from sweep results)
**Config**: `experiments/reasoning_depth_production.yaml` (needs base param update after sweeps)
**Purpose**: Statistical power for ANOVA, pairwise comparisons, Bayes factors

### Next steps
- [x] Complete parameter sweeps: arm_cost ✅, conflict_cost ✅, invest_self ✅
- [ ] Complete invest_return sweep (SLURM maintenance, auto-submit will pick up)
- [x] Analyze full sweep results (96/132 runs)
- [ ] Select base parameters for production runs (genuine dilemmas)
- [ ] Update production config with selected base params
- [ ] Run production (80 runs) + power analysis from pilot ICC/effect sizes
- [ ] Implement faithfulness validation (Lanham early-answering test on subset)

---

## Phase 2c: Origins — Parameter Characterisation + Factorial (~Mar 1 - Apr 15)
**Focus**: Find game parameters that create genuine dilemmas, then test reasoning depth × structure interactions.

**Update after Feb 27 meeting**: All experiments on Qwen 3.5-27B (dense, all 27B params active). Use native `<think>` reasoning traces. Debraj wants utility-based movement (Schelling-type) instead of random walk.

### Two-Stage Sweep Design

**Stage 1: OAT Screening** (submitted Feb 28 night, 116 runs, ~12K SBU)
Quick mode: 10 agents, 10 rounds, L1+L3, 2 reps per condition. invest_self OFF (default).
Goal: identify which parameters produce richest dynamics (diverse actions, Gini variation, L1≠L3).
Focus metrics: **cooperation ratio**, **Gini**, **E-I index**.
Prompt shows explicit theta ratios (e.g., "cost-to-benefit ratio 1:1.5") per Debraj.

| Category | Sweep | Values | Runs |
|----------|-------|--------|------|
| Conflict theta | conflict_cost_pct | [2, 5, 10, 20] | 16 |
| Conflict theta | attack_take_pct | [20, 40, 60, 80] | 16 |
| Arming theta | arm_cost_pct (self) | [5, 10, 20] | 12 |
| Arming theta | arm_other_cost_pct | [5, 10, 20] | 12 |
| Cooperation theta | invest_other_return_pct | [10, 15, 25] | 12 |
| Cooperation theta | invest_other_cost_pct | [5, 10, 20] | 12 |
| Spatial | interaction_radius | [1, 2, 3] | 12 |
| Toggle | invest_self on/off | [on, off] | 8 |
| Toggle | memory on/off | [on, off] | 8 |

Configs: `experiments/qwen_sweep_*.yaml`
Submit: `snellius/submit_qwen_nightrun.sh`

**Stage 2: Focused Factorial** (planned, after Stage 1 analysis)
Production scale: 30 agents, 50 rounds, 20 reps per condition.
Pick top 2-3 most dynamic parameters from Stage 1 → cross with reasoning depth (L0-L3).
Design depends on Stage 1 results.

### Engine Design (unified %-based economy, implemented Feb 28)
All costs/returns are percentages of the acting agent's current resources.
- invest_self: pay cost_pct%, gain return_pct% (default: 10%/12%, net +2%)
- invest_other: pay cost_pct%, target gets return_pct% (default: 10%/15%, ratio 1:1.5)
- arm_self/arm_other: pay cost_pct%, that amount becomes additive combat bonus
- Combat: strength = resources + arm_bonus. Win prob = your_strength / total.
- Arm decay: ×0.5 per round (exponential, not fixed duration)
- Attack: winner takes attack_take_pct% of loser. Both pay conflict_cost_pct%.

### Origins Factorial: Spatial Radius × Reasoning Depth
**Config**: `experiments/origins_radius_reasoning.yaml` (needs update after Stage 2)
**Design**: radii × 4 levels × 20 reps (exact radii from Stage 1 results)
- Levels: L0, L1, L2, L3

**Key questions**:
- Does the cooperation→conflict phase transition shift with reasoning depth?
- Do deeper-reasoning agents need stronger structural constraints to cooperate?
- Is there a "cooperation frontier" in reasoning × structure space?

### Analysis Plan
- **Per reasoning level**: Gini vs radius curve (phase transition plot — the "hero figure")
- **Two-way ANOVA**: reasoning_level × interaction_radius → Gini, cooperation_ratio, E-I index
- **Interaction effect**: partial η² for the reasoning × radius term
- **Phase transition detection**: variance peak (susceptibility analogue), rolling-window EWS
- **Mixed-effects**: `Gini ~ reasoning_level * radius + (1|RunID)` with Satterthwaite df
- **Bayes factors** for key pairwise comparisons (following Akata et al., 2025)
- **Coalition metrics**: Leiden communities, ingroup/outgroup rates, hierarchy (David's scores, Landau's h)

### Stretch experiments (if time/compute)
- Information architecture × reasoning depth (resource visibility, history)
- Scale effects (10, 20, 30 agents × reasoning level)

### Deliverables
- 4 phase transition curves (one per level) in single plot
- Interaction effect sizes with CIs
- Gini + cooperation trajectory plots per condition (mean + CI bands)
- Mixed-effects model output table

---

## Phase 2d: Communication Scope (~Apr 1 - Apr 30)
**Focus**: Can cheap talk — without enforcement — create social order? Does it matter who hears you?

Approved by Debraj as **separate thesis chapter** alongside reasoning depth.

### Core Design: 3-Condition Communication Scope Sweep

| Condition | Mechanism | Who hears | Game-theoretic prediction | LLM prediction |
|-----------|-----------|-----------|--------------------------|----------------|
| No-comm | No messaging phase | Nobody | Hobbesian trap | Same |
| DM only | 1 private message to 1 neighbour | Recipient only | Minimal effect (bilateral) | Secret deals, conspiracies |
| Broadcast only | 1 public message to all neighbours | All neighbours | Partial effect (coordination) | Public commitments, norms, shaming |
| Choice | Agent selects DM or broadcast | Depends on choice | Full capability | Channel preference becomes DV |

**The key question**: Do WORDS alone create order, and does it matter who hears them?
- DM enables HIDDEN coordination (conspiracies, bilateral deals)
- Broadcast enables PUBLIC coordination (norms, collective action, shaming)
- All messages are cheap talk (Crawford & Sobel 1982): non-binding, potentially deceptive

### Communication Mechanism
- Each round has 2 phases: **message phase** → **action phase**
- No-comm: skip messaging phase entirely
- DM only: LLM outputs `{"message": "...", "to": "Agent_X"}` before action choice
- Broadcast only: LLM outputs `{"message": "...", "to": "all"}` before action choice
- Choice: LLM outputs `{"message": "...", "to": "Agent_X" OR "all"}` — agent decides channel per round. Channel choice logged as DV (% DM vs broadcast by level/round/position)
- Messages stored in memory system alongside action observations
- No structure imposed on message content — agents write what they want

### Interaction with Network Rewiring (w)
- Static (w=0) + DM = stable bilateral relationships, long-term deals
- Static + broadcast = fixed public sphere, stable audience
- Fluid (w=1) + DM = fragile deals (partner may rewire away)
- Fluid + broadcast = changing audience each round

### Full Experimental Design
- 4 comm × 4 reasoning × 4 network = 64 cells (full factorial)
- May reduce: fix w at 2 levels (static, fluid) → 4 × 4 × 2 = 32 cells × 20 reps = 640 runs
- Or: run choice condition only at L1+L3 (most informative contrast)
- Or: prioritize comm × reasoning first, add network interaction later

### Hypotheses (counterintuitive predictions)
1. **Cheap talk works for LLMs** — cooperation increases even without enforcement, violating game-theoretic rationality (Sally 1995 predicts ~40% boost in humans)
2. **Broadcast > DM** — public commitment enables coordination that private deals cannot. If so: coordination mechanism > bilateral commitment mechanism
3. **L3 weaponizes communication** — uses messages to manipulate (false promises, threats) while L1 uses them honestly
4. **Concordance varies by level** — L0 ignores messages, L1 honors promises, L3 lies strategically
5. **Communication × network interaction** — cheap talk more effective on static networks (stable relationships) than fluid ones

### Message Analysis (messages as data)
- What do agents say? Threats, promises, proposals, information sharing?
- Concordance: message content vs actual action (promise to cooperate → did they?)
- By reasoning level: who lies, who keeps promises, who threatens?
- Emergent communication patterns: do agents develop norms? ("I'll invest if you invest")
- DM vs broadcast: do agents use DMs for conspiracies and broadcasts for norms?

### Future Work (Discussion section)
- Binding contracts with enforcement (Hobbes's Leviathan, Conitzer 2024 program equilibria)
- Multi-party contracts, conditional contracts
- Heterogeneous model mix (different reasoning levels in same game)

### Robustness & Validation

### Prompt sensitivity
- Report FormatSpread (Sclar et al., 2024) or PromptSensiScore (Zhuo et al., 2024)
- Test semantically equivalent reformulations of L0-L3 prompts
- **TextGrad Option B**: Run both original + TextGrad-optimized prompts as robustness check

### Faithfulness validation
- Implement Lanham et al.'s early-answering test on subset of runs
- If compute allows: Thought Anchors resampling (Bogdan et al., 2025) on critical rounds
- Report concordance: stated reasoning vs actual action choice

### Trace coding
- LACA framework (Chew et al., 2023): codebook → LLM coding → human verification
- Inter-rater reliability with Gwet's AC1
- Theory-of-mind depth coded per trace
- Track prompted vs observed reasoning level divergence

### Deliverables
- **Hero finding**: cheap talk effect size by reasoning level (does language alone break the trap?)
- Cooperation trajectories: no-comm vs cheap talk vs contracts, per reasoning level
- Message analysis: concordance, threats, lies by level
- Prompt sensitivity analysis
- Faithfulness validation results

---

---

## Phase 3: Analysis & Writing (May 1 - Jun 15)
**Focus**: Full statistical analysis to publishable standard, write thesis chapters

### Analysis (publishable standard — see `notes/publishable_checklist.md`)
- [ ] All experiments complete (Phase 2b production + 2c Origins factorial + 2d robustness)
- [ ] Mixed-effects models with proper nesting: `Gini ~ reasoning_level * param + Round + (1|RunID)`
- [ ] Effect sizes (Cohen's d, partial η²) + 95% CIs for everything
- [ ] Bayes factors for key comparisons
- [ ] Phase transition detection: EWS, variance peaks, critical point estimation
- [ ] Trace coding with LACA framework, inter-rater reliability
- [ ] All figures: colorblind-safe, vector format, error bars, individual trajectories visible

### Writing Plan
| Chapter | Content | Depends On | Outline status |
|---------|---------|------------|----------------|
| 1. Introduction | MD × Hobbes framing → three IVs → gap → contribution | Final results | Needs update |
| 2. Literature Review | MD (3 inputs), LLM agents, reasoning depth, co-evolutionary networks, communication, phase transitions, gap | Reading | TODO structure done (Mar 2) |
| 3. Methods | Game design, three IVs (reasoning L0-L3, network w, comm scope), experimental design, metrics | Phase 2 experiments | TODO outline done (Mar 2) |
| 4. Reasoning Depth | L0-L3 × game structure on Qwen 3.5-27B | Phase 2c | Not started |
| 5. Network & Communication | Network rewiring (w) + communication scope (no-comm/DM/broadcast) | Phase 2c+2d | Not started |
| 6. Discussion | Three IVs synthesized, interactions, faithfulness caveats, limitations, Hobbes revisited | Ch 4+5 results | Needs update |
| 7. Conclusion | Answer to RQ, contracts as future work | Ch 6 | Not started |

### Suggested Writing Order
1. Methods (know this best, write while running experiments)
2. Results (write as you analyze)
3. Literature Review (papers read)
4. Discussion (interpret results)
5. Introduction (frame based on findings)
6. Conclusion (last)

### Claims calibration reminder
- Strong evidence → "We find that..."
- Moderate evidence → "Our results suggest..."
- Weak/exploratory → "We observe preliminary evidence that..."
- Frame reasoning depth as "computational depth manipulation", not cognitive claims

---

## Phase 4: Writing & Polish (Jun 15 - Jul 15)
**Focus**: Complete thesis draft, iterate, polish

### Goals for this phase
- [ ] Complete first draft of all chapters
- [ ] Feedback round with Debraj on full draft
- [ ] Revise based on feedback
- [ ] Final figures, formatting, references
- [ ] Abstract written
- [ ] Proofread
- [ ] Submit by July 15

### Milestones
- [ ] Jun 15: First complete draft to Debraj
- [ ] Jun 30: Revised draft after feedback
- [ ] Jul 10: Final polish
- [ ] Jul 15: Submission

---

## Phase 5: Defence Prep (Jul 15 - late Jul)
**Focus**: Prepare and deliver oral defence

- [ ] Presentation slides (15% of grade)
- [ ] Practice defence questions
- [ ] Know every detail of your thesis cold
- [ ] Defence

---

## Sprint Log

Track each week here. After each Friday meeting, add an entry.

### Sprint 1: Feb 9 - Feb 13
**Phase**: Foundation
**Goal**: Literature start + meeting prep
Reading list:
- [x] Dubey et al. 2018 - Investigating Human Priors (already read -- semantic ablation methodology)
- [ ] Huh - Comprehensive Survey of RL (already reading)
- [ ] Riedl - Emergent Coordination (already reading)
- [ ] Ju et al. 2024 - Sense and Sensitivity (prompt sensitivity)
- [ ] Park et al. 2023 - Generative Agents (re-read, foundational inspiration)
- [ ] Leibo et al. 2017 - Multi-agent RL in Sequential Social Dilemmas
Other:
- [x] Review simulation runs, document patterns
- [ ] Prepare meeting agenda (Thu)
- [ ] Friday meeting with Debraj

**Simulation Run Analysis (28 runs, Feb 4)**:

Key findings:
1. **Objective framing is the strongest behavioral lever.** Same game, same model, completely different emergent structures from changing the goal sentence:
   - "shared win" → perfect reciprocal cooperation, zero inequality
   - "avoid last" → cautious/defensive, low inequality, moderate conflict
   - "finish first" → aggressive, frequent attacks
   - "maximize absolute" → bandwagoning toward the leader, HIGH inequality
   - "accumulate" / default → invest_self stalemate
2. **Nobody ever used arm_other.** Coalition formation mechanic is completely unused across all 28 runs. Likely a reasoning limitation -- agents can't plan multi-agent coalition strategies. Could also be cost/benefit issue (arm_other has no direct return for the supporter).
3. **invest_self dominates when available.** Safest option, agents default to it. Turning it off forces social interaction and richer dynamics.
4. **Model choice matters.** Llama-8B: minimal reasoning, accidental hierarchies via "sycophancy" (investing in the leader). Gemini-3-Flash: explicit probability calculations, adaptive strategy. DeepSeek: strategic reasoning but falls into appeasement traps.
5. **36% of runs ended in perfect equality** -- either boring stalemates (all invest_self) or interesting reciprocal cooperation (shared_win pairs).
6. **End-game conflict** emerges when agents know when the game ends (backward induction -- classical game theory prediction).
7. **invest_other creates the most extreme outcomes both ways** -- perfect equality when reciprocal, extreme hierarchy when asymmetric (bandwagoning).
8. **Parameters varied across runs** -- need to standardize before systematic experiments.

**Decisions**:
- Disable invest_self for main experiments (forces social dynamics)
- Be careful attributing differences to "semantic priors" -- thesis is descriptive, not explanatory
- Model scale comparison is a stretch goal, not core
- Reasoning memory ablation is a stretch goal (test if memory enables coalition formation)
- Coalition parameter tuning (arm_other cost/benefit) for next sprint, after Debraj discussion
- Focus this sprint on literature, not new experiments -- lock parameters after direction is confirmed

**Open questions for Debraj**:
- Thesis direction: RL comparison vs LLM-only ablation vs middle ground
- What parameter regime to standardize on
- Is coalition formation (arm_other) worth pursuing through parameter tuning?

**Outcome**: Meeting shifted thesis direction. Phase 1 = understand the system first. Phase 2 = prompt variation. RL is optional/lightweight.
**Next**: Sprint 2 -- system characterization begins

### Sprint 2: Feb 13 - Feb 27
**Phase**: System Characterization
**Goal**: Get baseline running at scale, implement metrics, start theta analysis

**Context from Debraj's paper (Kuusela & Roy, AAMAS 2024):**
- Paper: 2 civilizations, Stag Hunt under uncertainty, I-POMDP with reasoning levels
- Key finding: more reasoning → MORE conflict (counterintuitive). Fear spiral reinforces itself.
- His method: systematically vary one parameter at a time, track action distributions + trajectories, connect to theory
- His reasoning levels (0→1→2) map to our prompt variations (minimal → history → social CoT)
- His "morality parameter" maps to our objective framing
- He tracks action quality (WHY agents choose), not just WHAT they choose → use our reasoning traces as data
- **This paper is our methodological template. Follow the same structure.**

**TextGrad (Zou group, Nature 2025):**
- Automatic prompt optimization via "textual backpropagation"
- Verdict: cite it, don't integrate it. It reduces sensitivity; we want to measure and understand it.
- Reference for literature review / future work section

#### Week 1 (Feb 13-19): Setup & Metrics
- [x] Read Debraj's paper
- [x] Check TextGrad repo
- [ ] Define theta = c/b for each action in current game design
- [ ] Pick baseline: one objective (maximize_resources), minimal prompt, locked parameters
- [ ] Implement Gini coefficient calculation over time (per round, not just final)
- [ ] Implement action stability metric: what % of agents switch action between rounds?
- [ ] Test scaling: run with 10, 15, 30 agents -- does it work? API costs? Runtime?

#### Week 2 (Feb 20-26): Baseline Runs & Theta Sweep
- [ ] Run baseline at 30 agents: multiple runs with same config, measure variance
- [ ] Do agents stabilize? Plot action distribution per round over time
- [ ] Plot Gini trajectory over time -- does hierarchy emerge or stay flat?
- [ ] Start theta sweep: vary c/b ratio for one action at a time, measure effect on stability
- [ ] Check EGG repo (Facebook, emergence of language)

#### Literature (across both weeks)
- [ ] Huh - Comprehensive Survey of RL
- [ ] Riedl - Emergent Coordination
- [ ] Ju et al. 2024 - Sense and Sensitivity
- [ ] Park et al. 2023 - Generative Agents (re-read)
- [ ] Leibo et al. 2017 - Multi-agent RL in Sequential Social Dilemmas

#### Deliverables for Debraj (Feb 27)
- Gini trajectory plot for baseline (30 agents, multiple runs)
- Action stability plot (do agents converge?)
- First theta sweep results: how does c/b ratio affect game dynamics?
- Report on what you learned from the system characterization
- Literature progress update

**Outcome (updated Feb 18)**: Phase 1 complete (142 runs). Phase 2a complete (100 Gemma 2 runs, η²=0.901). Pivoted to reasoning depth on single model. Phase 2b pilot complete: non-monotonic pattern (L0 coop → L1 aggressive → L2 defensive → L3 exploitative). Parameter sweeps running. arm_cost × reasoning interaction effect is the strongest finding. Publishable thesis standard adopted.
**Decisions**: Reasoning depth on single model (Gemma 2) over cross-model comparison. 4 reasoning levels (L0-L3). Parameter sweeps to find genuine dilemma parameters. Publishable quality standard.

**Outcome (updated Feb 27)**: Presented all results to Debraj. He said "very publishable" — first time. Major decisions:
- **Both directions approved**: reasoning depth (chapter) + credible commitment (chapter)
- **One model strictly**: switch to Qwen 3.5-27B (dense), rerun ALL characterisation
- **Reasoning model traces**: use model's own CoT, not instructed reasoning field
- **Utility-based movement**: replace random walk with Schelling-type movement
- **Stabilisation**: metrics must be shown as time plots or after stabilisation, not just end-values
- **invest_self ON as baseline**: show stalemate as reference point
- **TextGrad**: investigate for prompt engineering + uncertainty quantification
- **K-instructed prompting is defensible** as method
See `notes/meeting_prep_27_feb.md` for full meeting notes.
Slides archived: `notes/archive/slides/meeting27slidedeck.key`

### Sprint 3: Feb 27 - Mar 14
**Phase**: Model transition + design decisions + Qwen characterisation
**Goal**: Deploy Qwen 3.5-27B, finalize IV design, exploratory runs, start Methods writing
**Sprint log**: `notes/sprint_3_feb27-mar14.md`

#### Plan (updated Mar 2)

**Phase 1 — Qwen deployment + OAT screening (done/running)**
- [x] Deploy Qwen 3.5-27B (dense) on Snellius + validation test
- [x] OAT screening sweeps submitted (116 runs, 9 param sweeps × L1+L3)
- [x] Engine rewrite: unified %-based economy
- [x] Persistent agent memory implemented
- [x] Early stopping implemented (two-phase adaptive)

**Phase 2 — Design decisions (done Mar 2)**
- [x] Hidden resources as base default (implemented)
- [x] Dynamic network with payoff-based rewiring (w as IV) — design finalized
- [x] Communication scope (no-comm/DM/broadcast) — design finalized
- [x] Memory always ON — decided
- [x] Literature review TODOs updated with network co-evolution papers
- [x] Methods TODOs updated for all three IVs

**Phase 3 — Week 2: Exploratory runs + implementation (Mar 3-14)**
- [ ] Run max emergence exploratory runs on OpenRouter (config ready)
- [ ] Analyze OAT screening results from Snellius
- [ ] Start network rewiring implementation (replace spatial.py)
- [ ] Methods chapter writing (TODOs → prose)
- [ ] Discuss network + communication design with Debraj (Mar 14)

#### Done
- [x] Stabilisation metrics implemented
- [x] Network analysis + Leiden + ingroup/outgroup integrated
- [x] Qwen 3.5-27B tested + benchmarked (5.8x speedup concurrent)
- [x] TextGrad pipeline built + submitted
- [x] L3 prompt rewritten (recursive reasoning)
- [x] Memory system: local observations, stale entries, hide_resources support
- [x] Three IVs finalized: reasoning L0-L3, network w, communication scope
- [x] Deep research: network rewiring literature reviewed and saved

#### Still TODO
- [ ] Network rewiring implementation
- [ ] Communication mechanism implementation
- [ ] Methods chapter prose (write from TODOs)
- [ ] Analyze Snellius OAT results
- [ ] TextGrad analysis

---

## Decision Log

Track major decisions and WHY you made them. (Rubric: independence, creativity)

| Date | Decision | Reasoning | Debraj's Input |
|------|----------|-----------|----------------|
| Jan 28 | Switched from IR theory framing to emergent social structures | Avoids circularity, captures full game richness | - |
| Jan 29 | Descriptive, not explanatory thesis | Can't isolate mechanisms, only compare outcomes | - |
| Jan 30 | Three-condition design (RL, LLM-Comp, LLM-Control) | Debraj agreed, said setup is good enough | "Biggest value is in experiments" |
| Feb 4 | First simulation runs with varying configs | Testing prompt sensitivity, objective effects | - |
| Feb 9 | Disable invest_self for main experiments | With invest_self on, most agents default to self-investment every round -- safe but boring. Turning it off forces social interaction, which is what the thesis investigates. | - |
| Feb 9 | Be careful with "semantic priors" as explanation | Can observe THAT architectures differ, not claim WHY. Architecture + pretraining + inference all differ. Thesis is descriptive, not explanatory. Already in forbidden terms list. | - |
| Feb 13 | Phase 1 = characterize the system before varying prompts | Can't interpret prompt effects without understanding baseline system behavior | Debraj: "Without that, it's impossible to say anything about changing the prompting later" |
| Feb 13 | RL is optional/lightweight, not core | LLM prompt variation is the main investigation. RL as simple baseline if used at all. | Debraj: "RL might not be needed, but we'll see. Keep it simple." |
| Feb 13 | Scale to 30 agents | Research suggests significant distribution changes at scale | Debraj's recommendation |
| Feb 13 | Vary theta (cost/benefit ratio) as the key parameter | Single systematic parameter to understand system sensitivity | Debraj: "This is the only parameter we vary at this point" |
| Feb 13 | Drop theta framing, do parameter sensitivity analysis | Theta (c/b) only works for invest actions. Military actions have context-dependent expected values (depends on opponent, arms, coalitions). Vary individual params one at a time instead. Spirit of Debraj's instruction preserved. | - |
| Feb 13 | Confirmed: invest_self off for baseline | 30-agent run with invest_self on = 100% stalemate (Gini=0.000). invest_self off = hegemon emergence (Gini=0.928). Need dynamics to characterize. | - |
| Feb 16 | Launch Architecture Experiments as Phase 2a | Phase 1 showed architecture is dominant variable (Cohen's d > 3). Maps to Debraj's Level-0/Level-2 framework. Must characterize architectures before Origins experiments (need to know which models produce dynamics). | - |
| Feb 16 | 50-round games for Arch experiments | 10 rounds too short for trajectory analysis — cooperation dynamics and hegemon formation need 30+ rounds to stabilize. 50 rounds captures full trajectory. | - |
| Feb 16 | Llama 3.3 70B unsuitable for Origins | 100% do_nothing across all 20 runs, zero variance. Cannot produce the dynamics needed for Origins experiments. Need alternative open-weight model from Snellius tests. | - |
| Feb 17 | Combined Exp 1+2 on Snellius per model | Running fingerprint (neutral × 20 reps) + framing factorial (5 framings × 20 reps) in single job per model. Efficient use of Snellius GPU time. | - |
| Feb 18 | Pivot from cross-model comparison to reasoning depth on single model (Gemma 2 27B) | Cleaner science: isolates ONE variable (reasoning depth). Cross-model comparison confounded by 100+ differences. Maps to Debraj's Level-0/1/2 framework. Computationally feasible. | Anticipated approval — will present Feb 27 |
| Feb 18 | 4 reasoning levels (L0-L3), not 3 | L3 (recursive) added after pilot showed non-monotonic L0→L2 pattern. L3 tests whether recursive reasoning cooperates again or escalates further. Answer: L3 is most exploitative (Gini 0.712, 7% attack). | - |
| Feb 18 | Parameter sweeps before production runs | Zero-cost regime makes arm_self trivially dominant. Must find base params that create genuine strategic dilemmas. 4 sweeps launched: arm_cost, conflict_cost, invest_self, invest_return. | - |
| Feb 18 | Adopt publishable thesis standard | Created `notes/publishable_checklist.md` with comprehensive quality requirements. Updated CLAUDE.md to enforce standards. Key: mixed-effects models, effect sizes + CIs + Bayes factors, faithfulness validation, LACA trace coding. | - |
| Feb 18 | Frame reasoning depth as computational depth manipulation | Not claiming agents "reason" or have ToM. Prompts change computational depth (supported by Pfau et al., 2024). Traces are behavioral data, not mechanistic explanations. | - |
| Feb 27 | Both directions: reasoning depth + credible commitment | Debraj approved both as separate thesis chapters. Reasoning depth is the "agent" chapter, credible commitment is the "environment" chapter. | "Do both! Nobody has done this before." |
| Feb 27 | Switch to Qwen 3.5-27B (dense) as sole model | All prior work was exploratory on multiple models. Production must use one model only. Qwen 3.5-27B chosen: dense (all 27B params active), reasoning model, strong performance (SWE-bench 72.4, IFEval 95.0). MoE variant (35B-A3B) had vLLM compat issues. | "One model! Rerun everything!" |
| Feb 27 | Use model's own reasoning traces, not instructed reasoning | Qwen 3.5 is a reasoning model — its own CoT is the data. The instructed "reasoning" JSON field is not the same as the model's actual reasoning process. | "Use THEIR reasoning traces as object of observation" |
| Feb 27 | Replace random walk with utility-based movement | Random walk prevents relationship formation (agents see new neighbors every round). Schelling-type movement enables ingroup/outgroup dynamics. | "In real life, movement is utility-based, never random" |
| Feb 27 | K-instructed prompting is defensible | Even though we now use a reasoning model, instructed K-level prompting remains a valid methodology for varying reasoning depth. | Explicit approval |
| Feb 27 | Invest_self ON as baseline, not excluded condition | Stalemate (Gini 0.000) is itself an interesting result and provides context for all other conditions. | "Show it as a baseline" |
| Feb 28 | %-based economy (percentage_costs) | All costs/returns scale with agent's current resources. invest_self: -10%/+20%, invest_other: -10%/+15%, arm: -10%, conflict: -5%. Ensures actions stay meaningful at any wealth level. Backward compat via flag. | - |
| Feb 28 | Two-stage screening sweeps (OAT then factorial) | Stage 1: 9 OAT sweeps × L1+L3 × 2 reps = 116 runs (invest_self OFF default). Stage 2: focused factorial on top params at production scale. Standard screening approach. | - |
| Feb 28 | invest_self OFF as default in all param sweeps | Even +2% net gain causes L1 agents to choose invest_self 100%. Must be OFF to force social dynamics. invest_self ON tested only in dedicated toggle sweep. | Fixed after first nightrun showed 100% invest_self |
| Feb 28 | No zero-cost values in sweeps | 0-cost arming = free arming (no dilemma). 0-cost conflict = free attacks. Removed: arm [0,5,10,20]→[5,10,20], conflict [0,5,10,20]→[2,5,10,20]. | Fixed after first nightrun |
| Mar 1 | Publishable checklist rewritten for AAMAS | Restructured from generic quality list to AAMAS-targeted paper guide. OCAR story structure, Kuusela's patterns, 8-page budget, declarative section titles, 3 focus metrics. | - |
| Mar 1 | Communication via cheap talk in credible commitment chapter | LLMs not communicating wastes their core capability. Initially: no-comm → cheap talk → contracts. **Updated Mar 2**: contracts dropped, replaced by communication SCOPE (no-comm → DM → broadcast). See Mar 2 decisions. | - |
| Mar 1 | RQ updated: three IVs grounded in mechanism design + Hobbes | Three IVs = mechanism design's three formal inputs (exact mapping). Hobbes's three causes of conflict used as narrative frame with caveats: reasoning→competition (strong, empirical), info→diffidence (moderate, causal chain), communication→common power (strong, Baliga & Sjöström 2004). MD mapping is the formal backbone; Hobbes is the intro/discussion story. | - |
| Mar 1 | Memory default ON, god-view removed | Without memory, do_nothing is Nash equilibrium (invest_other costs 10%, returns 0 to investor). God-view profiles leaked omniscient info. Memory OFF = no history (clean IV). | - |
| Mar 1 | vLLM reasoning field = `msg.reasoning` not `msg.reasoning_content` | 4000+ thinking tokens generated but not saved. Fix: check both attrs. | - |
| Mar 1 | Wall time 4h→8h for screening sweeps | L1 ~37min/run + L3 ~67min/run. 6-8 runs/task = up to 7h. | - |
| Mar 2 | Hidden resources as base default (not IV) | Agents see only own resources, neighbours show `???`. Creates genuine type uncertainty (Harsanyi). Implemented in prompts.py + memory.py. May test in OAT pilots. | - |
| Mar 2 | Dynamic network with payoff-based rewiring replaces fixed grid | ER initial graph ⟨k⟩≈4-6, break-one-make-one, min degree≥1. w as IV: {0, 0.05, 0.3, 1.0}. Literature: Zimmermann 2004, Pacheco 2006, Rand 2011. Solves Debraj's "random movement" objection. | Debraj said utility-based movement needed (Feb 27) |
| Mar 2 | Communication scope (no-comm/DM/broadcast) replaces contracts | Contracts felt arbitrary — enforcement engine is a design choice, not emergence. DM vs broadcast = clean manipulation of communication SCOPE (private vs public cheap talk). Contracts → future work. | - |
| Mar 2 | Memory always ON (not IV) | Memory is prerequisite for meaningful social dynamics (reciprocity, reputation). Without it, do_nothing dominates. Not an experimental variable — a base requirement. | - |
| Mar 2 | bf16 over FP8 for Qwen 3.5-27B | FP8 benchmark: 26% slower due to DeepGEMM overhead at 27B scale. VRAM saving (28 vs 52 GiB) not worth the speed loss. | - |
| Mar 2 | Communication scope: 4th level "choice" added | Agent selects DM or broadcast per round. Channel preference becomes a DV. Tests not just effect of communication but agent preference for private vs public coordination. | - |
| Mar 3 | Coalition attacks (shared combat) | Multiple agents attacking the same target combine strengths. Snapshot-based simultaneous resolution (no order dependence). Spoils proportional to strength contribution. Enables emergent coalitions without explicit coordination. arm_other = mechanism for strengthening coalition partners. Interesting interaction with communication scope (coordinate attacks via DM/broadcast). | - |
| Mar 3 | Methods §3.1 restructurering: follow formal tuple | §3.1 now structured as N → S → A → O → T → u, following the formal game tuple. Transition function T was nowhere explicitly described — now fully specified (6-step resolution including coalition attacks, snapshot combat, simultaneous resolution). | - |

---

## Risk Register

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| System doesn't stabilize / no clear baseline behavior | High | Vary theta systematically, try different parameter regimes | ✅ Resolved — system well-characterized |
| Scaling to 30 agents: API costs, runtime, context window limits | Medium | Test incrementally (6 -> 15 -> 30), monitor costs | ✅ Resolved — 30 agents works fine |
| Prompt sensitivity makes LLM results unreliable | Medium | FormatSpread analysis, semantically equivalent reformulations | Active — Phase 2d |
| Compute budget exceeded before Origins factorial | Low | 75K extra SBU goedgekeurd (totaal ~77.4K). Ruim voldoende. | ✅ Resolved |
| Results show no difference across reasoning levels | Low (moot) | "Null result" = publishable. But pilot shows strong effects. | ✅ Moot — strong effects found |
| Faithfulness objection undermines trace analysis | High | Frame as computational depth, not cognitive claims. Implement Lanham/Thought Anchors validation. | Phase 2d |
| Single-model limitation weakens generalizability claim | Medium | Using Qwen 3.5 only. Acknowledge in limitations. Credible commitment chapter generalizes across models by design. | Accepted |
| Non-monotonic pattern not robust to base parameter change | Medium | Parameter sweeps running now to check. arm_cost interaction effect survives across values. | Must revalidate on Qwen 3.5 |
| Writing takes longer than expected | High | Chapter outlines already created. Start Methods early. | Outlines done |
| Scope creep (two chapters + extensions) | **High** | Debraj approved both directions but risk of spreading too thin. Prioritize: (1) Qwen deploy, (2) characterisation rerun, (3) reasoning depth, (4) credible commitment. Extensions are stretch goals. | **Active — monitor closely** |
| Model transition delays | Medium | All prior results are exploratory. Qwen 3.5 may behave differently. Budget time for re-characterisation. | New |
| Qwen 3.5-27B reasoning depth effects differ from Gemma 2 | Medium | 27B dense (all params active). Pilot first, compare behavioral fingerprints with Gemma 2 results. | New |
| SBU budget for double experiments | Low | 75K extra SBU goedgekeurd. Ruim budget voor beide chapters + extensies. | ✅ Resolved |
| Network rewiring: LLM agents may not rewire "rationally" | Medium | Co-evolutionary literature (Zimmermann 2004, Rand 2011) uses evolutionary strategy updating (imitate-the-best). Our agents REASON about rewiring. Risk: prompt artifacts cause irrational neighbor retention/dropping, breaking comparison to theoretical baselines. Mitigation: (1) exploratory runs to verify agents actually drop low-payoff neighbors, (2) compare rewiring patterns to evolutionary GT predictions, (3) if agents don't rewire sensibly, rewiring could be made automatic (payoff-based rule) rather than agent-chosen — but this weakens the "reasoning about structure" claim. | New |
