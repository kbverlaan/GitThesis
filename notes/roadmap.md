# Thesis Roadmap: The Origins of Order

**Timeline**: Feb 2026 - July 2026
**Submission deadline**: July 15, 2026
**Defence**: Late July 2026
**Weekly meetings**: Fridays with Debraj

---

## How This Document Works

Each **phase** covers ~4-6 weeks. Each week is a **sprint** ending at the Friday meeting.
After each meeting, update the sprint with outcomes and set the next sprint goals.

Rubric reminder (what matters):
- Research Work 35% (theory knowledge, programming, independence, creativity, attitude)
- Thesis Report 50% (literature 20%, methods 20%, results 20%, question 10%, rest split)
- Presentation 15%

---

## Phase 1: Foundation (Feb 1 - Feb 28)
**Focus**: Literature, simulation polish, RL groundwork

### Goals for this phase
- [ ] Read core literature across all areas (see reading list below)
- [ ] LLM simulation stable and producing analyzable results
- [ ] RL agent implementation started (architecture chosen, training loop)
- [ ] Metrics pipeline: can compute Gini, network stats, action distributions from runs
- [ ] Clear picture of experiment design for Phase 2

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
- [ ] Dubey et al. 2018 - Investigating Human Priors (semantic ablation inspiration)

**IR theory** (background, not central):
- [ ] Waltz 1979 - Theory of International Politics
- [ ] Wendt 1992 - Anarchy is What States Make of It

### Sprint 1: Feb 9 - Feb 13
- [ ] Literature deep dive (Mon-Wed)
- [ ] Review simulation runs, identify key patterns (Thu)
- [ ] Prepare meeting (Thu)
- [ ] Meeting with Debraj (Fri Feb 13)

---

## Phase 2: Experimentation (Mar 1 - Apr 30)
**Focus**: Run experiments across all conditions, iterate on design

### Goals for this phase
- [ ] RL agent (LSTM) trained and producing results
- [ ] Systematic experiment runs across all 3 conditions
- [ ] LLM prompt variation experiments (LLM-Control condition)
- [ ] First round of metrics computed and compared across conditions
- [ ] Experiment log documenting all runs, parameters, observations
- [ ] TODO: which of Debraj's experiment ideas to include?

### Key Questions to Resolve Before/During This Phase
- How many runs per condition? (statistical power)
- RL training: convergence criteria, hyperparameter sweep
- Which prompt variations for LLM-Control?
- Do we add semantic ablation experiments? (see semantic_ablation_idea.txt)
- Spatial/partial info variant: core or stretch?

### Stretch Goals (if time allows)
- **Model scale comparison**: Run same conditions across models of increasing capability (e.g. small 8B -> mid-range -> frontier reasoning model). Early runs suggest enormous behavioral differences between Llama-8B and Gemini-3-Flash. Could reveal how model capability interacts with emergent structures. Risk: blows up experiment matrix, keep to 2-3 models max.
- **Reasoning memory ablation**: Give agents persistent memory of their own reasoning across rounds (e.g. summary of previous strategy, stated intentions). Test whether this enables more complex behaviors like coalition formation (arm_other), which currently never occurs. Isolates whether the limitation is reasoning depth or memory/context.

### Sprint Template (copy for each week)
```
### Sprint N: [dates]
**Goal**: [one sentence]
- [ ] task 1
- [ ] task 2
- [ ] task 3
**Meeting notes**:
**Next sprint direction**:
```

---

## Phase 3: Analysis & Early Writing (May 1 - Jun 15)
**Focus**: Analyze results, start writing thesis chapters

### Goals for this phase
- [ ] All experiments complete
- [ ] Statistical analysis across conditions (ANOVA / effect sizes / Mann-Whitney)
- [ ] Key figures and visualizations produced
- [ ] Draft chapters: Methods (Ch 3), Results (Ch 4)
- [ ] Literature Review chapter (Ch 2) drafted
- [ ] Introduction framing refined based on actual results

### Writing Plan (thesis chapters)
| Chapter | Content | Depends On |
|---------|---------|------------|
| 1. Introduction | Motivation, RQ, thesis structure | Final results (to frame correctly) |
| 2. Literature Review | Theory, related work | Phase 1 reading |
| 3. Methods | Game design, agent architectures, experiment design | Phase 2 experiments |
| 4. Results | Findings per condition, cross-condition comparison | Phase 2+3 analysis |
| 5. Discussion | Interpretation, limitations, implications | Ch 4 results |
| 6. Conclusion | Answer to RQ, future work | Ch 5 discussion |

### Suggested Writing Order
1. Methods (you know this best already)
2. Results (write as you analyze)
3. Literature Review (you've read the papers)
4. Discussion (interpret your results)
5. Introduction (frame based on what you found)
6. Conclusion (last)

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

**Next**:

<!--
### Sprint 2: Feb 13 - Feb 20
**Phase**: Foundation
**Goal**: TODO (set after Sprint 1 meeting)
- [ ]
**Outcome**:
**Next**:
-->

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
| | | | |

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| RL agent doesn't converge / learn meaningful policy | High | Start early, try multiple architectures, consult Debraj |
| Prompt sensitivity makes LLM results unreliable | Medium | LLM-Control condition explicitly tests this |
| Not enough time for all experiments | Medium | Prioritize core comparison (RL vs LLM-Comp), cut stretch goals |
| Results show no difference between conditions | Low (still publishable) | "Null result" is a valid finding -- material incentives dominate |
| Scope creep (spatial, language variation, ablation...) | Medium | Core experiments first, extras only if time allows |
| Writing takes longer than expected | High | Start Methods chapter early (Phase 2), don't save all writing for Phase 4 |
