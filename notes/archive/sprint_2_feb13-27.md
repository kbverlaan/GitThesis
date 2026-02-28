# Sprint 2: Feb 13 - Feb 27
**Phase**: System Characterization
**Meeting**: Friday Feb 27, 14:00
**Goal**: Get baseline running at scale, implement metrics, start theta analysis

---

## Methodology Reminder (Debraj's template)
- Vary ONE parameter at a time
- Track trajectories over time, not just final outcomes
- Look for counterintuitive findings
- Use reasoning traces as data
- Ask: "What would Debraj's paper do here?"

---

## Week 1: Setup & Metrics (Feb 13-19)

### Define theta
- [x] List all actions with their current cost (c) and benefit (b)
- [x] Calculate theta = c/b for each action
- [x] ~~Identify which theta values to sweep~~ → **Decision: dropped theta framing.** Theta only works for invest actions; military actions have context-dependent expected values. Switched to parameter sensitivity analysis, varying individual params one at a time. Spirit of Debraj's instruction preserved.

### Lock baseline
- [x] Pick one objective: maximize_resources (neutral, no social framing)
- [x] invest_self: off (forces interaction, decided Feb 9, confirmed by Run 001 stalemate)
- [x] Pick model for sweeps: **Amazon Nova Micro (nitro)** — 1.8s/round, ~$0.05-0.10/run, valid JSON. Gemini Flash Lite for targeted comparisons.
- [x] Document baseline config:

```yaml
# BASELINE CONFIG (locked Feb 13)
num_agents: 10          # 30 for scale tests
max_rounds: 10
model: google/gemini-2.5-flash-lite  # Nova Micro for sweeps
objective_style: maximize_resources
invest_self: false
invest_self_cost: 0
invest_self_return: 2
invest_other_cost: 0
invest_other_return: 5
arm_cost: 0.0           # zero-cost regime
arm_multiplier: 2.0
arm_duration: 3
arm_other_contribution: 0.5
conflict_cost: 0.0
attack_take_percent: 40
spatial_enabled: true
interaction_radius: 2
action_order: simultaneous
initial_distribution: equal
```

### Implement metrics
- [x] **Gini coefficient per round**: implemented in `analysis/metrics.py`, saved per round
- [x] **Action stability**: % of agents repeating same action, computed per round
- [x] **Action distribution per round**: tracked in round metrics and sweep manifests
- [x] **Palma ratio** (top 10% / bottom 40%): implemented alongside Gini
- [x] Save metrics to output files (`_metrics.json` per run)
- [x] **Sweep validation pipeline**: `validate_sweep.py` with convergence checks, consistency, effect sizes, Mann-Whitney U, Bonferroni correction, diagnostic plots

### Scale testing
- [x] Run with 10 agents — works, 1.6-9.5s/round depending on model
- [x] Run with 30 agents — works (Run 001-002, 126-142). 7-9s/round with Gemini. No rate limit issues with parallel calls.

---

## Week 2: Baseline Runs & Parameter Sweeps (Feb 13-16)

*Note: most of this was done on Feb 13 itself due to fast iteration with Nova Micro.*

### Baseline characterization
- [x] Run 001: 30 agents, invest_self ON → complete stalemate, Gini 0.000, 100% invest_self
- [x] Run 002: 30 agents, invest_self OFF → hegemon emergence, Gini 0.928, tribute system
- [x] Run 126: 30 agents, spatial, invest_self OFF → cooperation (63% invest_other), Gini 0.54
- [x] **Key finding**: invest_self OFF is necessary for interesting dynamics. System produces rich emergent behavior without it.

### Parameter sensitivity sweeps (142 runs total)
- [x] **invest_other_cost** (Runs 003-022, 5 values × 3 reps): high variance, no clean monotonic relationship. Gini 0.57-0.79 across conditions.
- [x] **invest_other_return** (Runs 024-038, 5 values × 3 reps): cooperation flat at 2-4% regardless of return (2→20). War equilibrium behaviorally robust with Nova Micro.
- [x] **attack_take_percent T** (Runs 039-053, 5 values × 3 reps): **Phase transition between T=20 and T=10** (Gini 0.46→0.20). But behavior unchanged — agents fight just as much, just can't accumulate.
- [x] **arm_multiplier** (Runs 056-070, 5 values × 3 reps): no effect. Agents arm at ~27% regardless of multiplier, even at M=1.0 where arming has no benefit.
- [x] **arm_duration** (Runs 071-085, 5 values × 3 reps): mild effect. Short duration acts as "action tax" — more re-arming, less fighting, lower Gini.
- [x] **Gemini Flash Lite T sweep** (Runs 086-100, 5 values × 3 reps): **Architecture determines parameter sensitivity.** Gemini cooperation 14-37% (responsive to T), vs Nova Micro flat at 3%.
- [x] **Initial distribution** (Runs 101-109, 3 distributions × 3 reps): equal most consistently warlike. Unequal/random high variance.
- [x] **Spatial field** (Runs 110-119): **Dramatic cooperation increase.** invest_other 17%→72% with spatial constraints. Phase transition at r=2→r=3.
- [x] **Action order** (Runs 120-125): simultaneous → arms races (56% arm_self). Sequential → more aggression (30% attack) + more inequality.
- [x] **Information factorial** (Runs 127-134, 2×2): **Resource visibility is the dominant cooperation driver, not history.** Hiding resources → paranoid stalemate.
- [x] **Reputation factorial** (Runs 135-142, 2×2): reputation does NOT rescue cooperation when resources hidden. Cooperation is resource-signal-based, not reputation-based.

### Model comparison
- [x] Run 054-055: Gemini Flash vs Nova Micro comparison. Both model architecture AND objective framing independently determine emergent structure.
- [x] Model selection testing: 8 models evaluated. Nova Micro selected for sweeps, Gemini Flash Lite for targeted experiments.

### Infra built (Feb 16)
- [x] Generic sweep runner (`sweep.py`) with factorial/grid support, target routing (game_params, openrouter, prompt_config)
- [x] Run-level metrics: cooperation_ratio, first_attack_round, retaliation_probability, coalition_stability
- [x] Prompt framing system: 5 framings (neutral, cooperative, competitive, strategic, cautious)
- [x] 5 experiment YAML specs for Phase 2 (phase transitions, factorial designs, model sweeps)

---

## Literature (across both weeks)

| Paper | Status | Key takeaway for thesis |
|-------|--------|------------------------|
| Debraj & Kuusela (AAMAS 2024) | read | Methodological template: vary one param, track trajectories, seek counterintuitive findings |
| TextGrad (Zou group) | scanned | Cite, don't integrate. Reduces sensitivity; we want to measure it. |
| Huh - RL Survey | reading | |
| Riedl - Emergent Coordination | reading | |
| Ju et al. 2024 - Sense and Sensitivity | todo | |
| Park et al. 2023 - Generative Agents | todo (re-read) | |
| Leibo et al. 2017 - MARL Social Dilemmas | todo | |
| EGG (Facebook) | todo | |

---

## Deliverables for Debraj (Feb 27)

### From Phase 1 (system characterization)
- [x] Gini trajectory data across multiple sweeps (T sweep, radius sweep, 30-agent runs)
- [x] Action stability data (tracked per round across all 142 runs)
- [x] Action distribution across conditions (documented per sweep in experiment log)
- [x] Parameter sensitivity results (7 parameters swept, phase transitions found)

### From Phase 2a (architecture + framing)
- [x] Gemma 2 27B: 100 runs, η²=0.901 for framing→Gini
- [x] 6 meeting plots (boxplot, trajectories, action dist, Cohen's d heatmap, keyword table, scatter)
- [x] Trace analysis: reasoning vocabulary predicts outcomes

### From Phase 2b (reasoning depth) — THE MAIN EVENT
- [x] Reasoning depth pilot results (4 levels × 3 reps): non-monotonic pattern
- [x] arm_cost × reasoning interaction effect: L0 insensitive, L2 hyper-responsive (Δ Gini = +0.23)
- [ ] Full parameter sweep results (awaiting L3 data + invest_self/invest_return)
- [ ] Proposal: Origins factorial design (reasoning × radius, 480 runs)
- [ ] Discussion: base parameter selection for production runs

### Presentation narrative for meeting
1. "Phase 1 showed spatial radius is the strongest cooperation driver (phase transition at r=2→3)"
2. "Phase 2a showed framing explains 90% of Gini variance on Gemma 2"
3. "I pivoted to reasoning depth on single model — cleaner than cross-model comparison"
4. "Pilot result: non-monotonic pattern. NOT more reasoning = more conflict (as Kuusela & Roy found)"
5. "The interaction effect is the real finding: L0 doesn't notice game structure changes, L2 is hyper-responsive"
6. "Next: Origins factorial — does reasoning depth shift phase transitions?"
7. "I'm aiming for publishable quality" → show checklist

---

## Daily Log

### Feb 13 (Fri) - after meeting
- Read Debraj's paper, analyzed TextGrad
- Updated roadmap with new phase structure
- Created this sprint document
- Ran 142 experiments: baseline, model selection, 7 parameter sweeps, spatial field, information/reputation factorials
- Key decisions: dropped theta framing, zero-cost regime as default, Nova Micro for sweeps

### Feb 14-15
- (weekend)

### Feb 16
- Built sweep infra: factorial/grid sweeps, target routing, prompt framing system
- Added 4 run-level metrics (cooperation_ratio, first_attack_round, retaliation_probability, coalition_stability)
- Created 5 Phase 2 experiment YAML specs
- Updated validate_sweep.py with new metrics and cooperation ratio plots

---

## Key Findings (for meeting prep)

### Phase 1 (system characterization — 142 runs)
1. **Spatial constraints are the strongest cooperation driver.** invest_other 17% → 72% with spatial field. Phase transition at r=2→r=3.
2. **Resource visibility drives cooperation, not reputation or history.** Agents invest based on "who is richest", not "who has been nicest".
3. **War equilibrium is robust to payoff changes.** Cooperation requires structural change, not just payoff tuning.
4. **Objective framing flips equilibria.** "maximize resources" → war. "avoid last" → 83% cooperation.

### Phase 2a (architecture + framing — 100 runs)
5. **Framing explains 90% of Gini variance** on Gemma 2 27B (η²=0.901).
6. **Counterintuitive**: cautious framing produces LESS inequality than cooperative framing.
7. **Trace analysis**: reasoning vocabulary predicts outcome within identical action distributions.

### Phase 2b (reasoning depth — 12 pilot + 96 sweep runs = 108 total)
8. **Non-monotonic reasoning effect confirmed (n=24 per level)**: L0 (Gini 0.535, cooperative) → L1 (0.620, strategic) → L2 (0.608, defensive) → L3 (0.693, exploitative). NOT Kuusela & Roy's "more reasoning = more conflict" — it's mechanism-dependent.
9. **arm_cost × reasoning interaction**: L0 insensitive (delta -0.045). L2 explodes (+0.226). L3 starts high, modest increase (+0.056). **Deeper reasoning AMPLIFIES structural incentives.**
10. **invest_self is the strongest structural lever**: collapses L0 to Gini 0.184 with invest_self ON. But L3 maintains 0.526 — exploitative even in safe regime.
11. **Each level has a qualitatively distinct behavioral profile**: L0=naive cooperator (65% coop, 0% arm), L1=strategic calculator (57% coop, 4% arm, 6% atk), L2=defensive hoarder (34% coop, 37% arm, 2% atk), L3=selective predator (47% coop, 16% arm, 8% atk).
12. **L3 cooperates more than L2 but attacks 4× more.** Cooperate-then-strike strategy. L2 arms obsessively but rarely attacks.
13. **conflict_cost has weak effect across all levels.** L3 especially insensitive (delta -0.012) — attacks regardless of cost.

### The story for Debraj
- His finding: more reasoning → more conflict (Level-0 < Level-2 in RL)
- Our finding: it's more nuanced — non-monotonic AND conditional on game structure
- Each level produces a qualitatively different behavioral profile, not just more/less conflict
- The interaction effect is the real contribution: reasoning depth × structure → emergent order
- invest_self sweep shows L3 maintains exploitative behavior even when "safe" options exist
- This sets up the Origins factorial: does the phase transition SHIFT with reasoning depth?

---

## Observations & Questions

- System characterization is model-dependent — but now locked to Gemma 2 27B for all remaining experiments
- Coalition formation (arm_other) still nearly absent — agents lack multi-step strategic planning
- invest_self OFF confirmed as correct baseline choice (invest_self ON → stalemate for L0)
- L0 agents are "structurally blind" — Gini barely changes across ANY parameter manipulation
- L2 agents arm even when it's irrational (31% arm_self with invest_self ON)
- L3's cooperate-then-strike is genuinely emergent — not prompted for, but consistent across 24 runs
- **Open question**: base parameter selection — arm_cost=2 creates the strongest L2 interaction but invest_self=OFF is necessary
- **Open question for Debraj**: is the non-monotonic pattern + interaction effect + qualitative profiles strong enough for a publishable contribution?
- **Resolved**: "what base parameters create a genuine dilemma?" — arm_cost > 0 makes arming non-trivial, invest_self OFF forces social interaction

---

## End of Sprint Review (to be completed Feb 27)

**What went well:**
- Massive throughput: 142 Phase 1 runs + 100 Gemma 2 Arch runs + 12 pilot runs + 48 sweep runs = ~300 total
- Clear pivot from cross-model to reasoning depth — cleaner science
- Non-monotonic pattern is genuinely surprising and novel
- arm_cost × reasoning interaction is the strongest result so far
- Thesis chapter outlines done, publishable checklist created
- Infrastructure for sweeps, auto-submission, analysis all built

**What didn't happen:**
- Literature reading fell behind — faithfulness papers not yet read (Turpin, Lanham, Chen)
- No formal power analysis from pilot data yet
- Production runs not started (waiting for sweep base parameter selection)
- Origins factorial not started

**Remaining this sprint (Feb 19-27):**
- [x] Complete parameter sweeps: arm_cost ✅, conflict_cost ✅, invest_self ✅
- [ ] Complete invest_return sweep (waiting for SLURM maintenance to end)
- [x] Analyze full sweep results (96/132 runs analyzed, see Feb 19 log)
- [ ] Select base parameters for production runs
- [ ] Power analysis from pilot ICC + effect sizes
- [ ] Read core papers (Debraj's paper, Zhang K-Level, Pfau, Turpin, Lanham — see reading list)
- [ ] Prepare meeting presentation for Debraj (Feb 27)
- [ ] Start writing Methods chapter (game design section)

### Decision Log — Feb 17-18 (Arch Exp 1+2 Nightrun)

**Decision: Drop Qwen3-235B-A22B-FP8.**
Reason: Too slow for budget. 60 min loading + ~22h per run (30 agents, thinking model on 4 GPUs). 100 runs would cost ~9,600 SBU (19% budget). Not worth it for a third model when two already provide good contrast.

**Decision: Drop QwQ-32B, replace with Qwen3-32B.**
Reason: QwQ-32B is an "always-think" model with no way to control thinking length. No `max_thinking_tokens`, no `/no_think` tag. Result: 96.5% of API calls timed out (30s timeout too short for 4000+ token thinking chains). All 7 completed QwQ runs are invalidated (96% do_nothing from timeouts, not genuine behavior). Qwen3-32B supports `enable_thinking`, `/think`/`/no_think` tags, and adjustable thinking budgets. Same model family, same size, but controllable. Preserves the Level-2 reasoning narrative.

**Decision: Gemma 2 27B stays.** 100/100 runs completed successfully. Fast, cooperative, good contrast with thinking model.

**Updated roadmap?** [ ] yes / [ ] no

### Feb 18 (morning) — Gemma 2 analysis complete, Qwen3 feasibility issue

**Gemma 2 27B analysis (100 runs):**
- Synced 400 files from Snellius, all 100 runs validated (5 framings × 20 reps)
- Created `src/analysis/arch_analysis.py` and `src/analysis/trace_analysis.py`
- Created `notebooks/arch_exp_gemma2.ipynb` with 6 meeting plots
- **Key result**: η²=0.901 — framing explains 90% of Gini variance
- Counterintuitive: cautious (0.549) < cooperative (0.581) on Gini
- Trace analysis: near-identical actions in high vs low Gini runs, but different reasoning vocabulary

**Qwen3-32B feasibility problem:**
- 8× slower due to KV cache saturation, walltime insufficient
- **Decision**: pivot to reasoning depth on single model (Gemma 2)

### Feb 18 (afternoon) — Reasoning depth pivot: implementation + pilot

**Implemented reasoning depth in `src/agents/prompts.py`:**
- `REASONING_LEVELS` dict: level0 (reactive), level1 (strategic), level2 (opponent modeling), level3 (recursive)
- Dynamic reasoning instruction in JSON prompt template
- Backwards compatible with existing configs

**Pilot launched on Snellius (12 runs: 4 levels × 3 reps):**
- Job completed successfully (~5h)
- **Non-monotonic pattern discovered**: L0 (cooperative, Gini 0.566) → L1 (aggressive, 0.632) → L2 (defensive/arming, 0.624) → L3 (exploitative, 0.712)
- L2 agents arm_self 40% of the time — defensive buildup
- L3 agents attack 7% — exploitation
- Token counts validate manipulation: L0=6, L1=31, L2=40, L3=44

### Feb 18 (evening) — Parameter sweeps + thesis outline + publishable standard

**Nightrun sweeps launched (132 runs across 4 experiments):**
- arm_cost [0,2,5] × reasoning [L0-L3] × 3 reps = 36 runs
- conflict_cost [0,3,5] × reasoning [L0-L3] × 3 reps = 36 runs
- invest_self [true,false] × reasoning [L0-L3] × 3 reps = 24 runs (waiting for GPU slots)
- invest_return [2,5,20] × reasoning [L0-L3] × 3 reps = 36 runs (waiting for GPU slots)
- Auto-submit script manages GPU allocation (max 3 sweep GPUs, 2 reserved for training)

**Partial arm_cost results (24/36 runs — L0/L1/L2 complete):**
- **STRONG interaction effect**: L0 Gini insensitive to arm_cost (~0.58 always). L2 Gini explodes: 0.58 → 0.82 as arm_cost increases.
- Deeper reasoning AMPLIFIES structural incentives, doesn't dampen them.

**Thesis chapter outlines created:**
- Updated 4 chapters (Introduction, Literature Review, Methods, Discussion) with TODO structure + literature placement
- Reflects evolved focus: reasoning depth × game structure, not RL vs LLM

**Publishable thesis standard adopted:**
- Created `notes/publishable_checklist.md` — comprehensive quality requirements
- Updated `CLAUDE.md` with publishable standard section
- Key requirements: mixed-effects models, effect sizes + CIs + Bayes factors, faithfulness validation, LACA trace coding, FormatSpread analysis

### Feb 19 (night/morning) — Sweep results complete (3/4), full L3 analysis

**Overnight sweep completion:**
- arm_cost: 36/36 ✅ (was 24/36 yesterday)
- conflict_cost: 36/36 ✅ (was 24/36 yesterday)
- invest_self: 24/24 ✅ (was 0/24 yesterday)
- invest_return: 0/36 — SLURM went down for maintenance before auto-submit could launch this
- Total completed: 96/132 sweep runs + 12 pilot = 108 reasoning depth runs

**SLURM maintenance:** Controller offline, SSH IP-restricted temporarily (resolved by waiting). Added ServerAliveInterval/ServerAliveCountMax to SSH config to prevent future connection spam.

**Full L3 results (n=24 across all sweeps) — The Selective Predator:**

| Level | n | Gini | Coop% | Arm% | Atk% | Character |
|-------|---|------|-------|------|------|-----------|
| L0 | 24 | 0.535 | 65% | 0% | 3% | Naive cooperator |
| L1 | 24 | 0.620 | 57% | 4% | 6% | Strategic calculator |
| L2 | 24 | 0.608 | 34% | 37% | 2% | Defensive hoarder |
| L3 | 24 | **0.693** | 47% | 16% | **8%** | Selective predator |

**Key finding confirmed with full data: each level has a qualitatively distinct behavioral profile.**
- L0: doesn't notice game structure changes (Gini delta ≤0.05 across all sweeps)
- L2: hyper-reactive to arm_cost (+0.226 Gini delta) — defensive arming spirals
- L3: consistently highest inequality, cooperates AND attacks, relatively insensitive to costs

**invest_self sweep — strongest structural lever:**
- invest_self ON collapses all levels toward low inequality
- But L3 maintains highest Gini even with invest_self ON (0.526 vs L0's 0.184)
- L0 with invest_self ON: 89% invest_self → complete stalemate
- L2 with invest_self ON: 62% invest_self + 31% arm — arms even when it's pointless
- L3 with invest_self ON: 78% invest_self + 9% attack — self-invests then strikes

**conflict_cost: L3 is insensitive (corrected from preliminary):**
- With only 1 rep yesterday, L3 appeared sensitive to conflict_cost (0.734→0.628)
- With 3 reps: 0.691→0.679 (delta = -0.012). L3 attacks regardless of cost.

**Thesis chapter outlines + Zotero:**
- Cross-referenced all Zotero papers against thesis chapter outlines
- Added 16 missing papers to chapter outlines (Lit Review, Methods, Discussion)
- Created Zotero import script (`notes/add_missing_to_zotero.js`) for 12 papers not yet in library
- Created AI usage disclosure section in Ethics chapter + Appendix Manifesto

**Reading list compiled for Sprint 3:**
- 15 papers prioritized in 4 tiers
- Tier 1 (before Feb 27): Debraj's paper, Zhang K-Level, Pfau Dot-by-Dot, Turpin faithfulness
