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

- [x] Gini trajectory data across multiple sweeps (T sweep, radius sweep, 30-agent runs)
- [x] Action stability data (tracked per round across all 142 runs)
- [x] Action distribution across conditions (documented per sweep in experiment log)
- [x] Parameter sensitivity results (7 parameters swept, phase transitions found)
- [ ] Formal plots via validate_sweep.py (run on completed sweep data)
- [ ] Verbal: what I learned about the system's behavior
- [ ] Verbal: literature progress

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

1. **Spatial constraints are the strongest cooperation driver.** invest_other goes from 17% to 72% with spatial field. Phase transition between r=2 and r=3.
2. **Resource visibility drives cooperation, not reputation or history.** Agents invest based on "who is richest", not "who has been nicest".
3. **Architecture determines parameter sensitivity.** Nova Micro is behaviorally rigid (65% attack regardless of params). Gemini Flash Lite responds to parameter changes.
4. **War equilibrium is robust to payoff changes.** Reducing attack spoils reduces inequality but NOT aggression. Cooperation requires structural change (spatial, model, objective) not just payoff tuning.
5. **Matthew Effect from cooperation.** In spatial mode, "invest in the richest" creates emergent hierarchy from cooperation, not conflict.
6. **Objective framing flips equilibria.** "maximize resources" → war. "avoid last" → 83% cooperation. Independent of model.

---

## Observations & Questions

- System characterization is model-dependent — can't describe "the system" without specifying the model
- Coalition formation (arm_other) still nearly absent — agents lack multi-step strategic planning
- Zero-cost regime eliminates bankruptcy stalemate but creates pure war game with Nova Micro
- 10-round games may be too short for stable cooperation to emerge via reputation
- Question for Debraj: is 142 runs enough for Phase 1, or do we need more controlled sweeps with higher n?

---

## End of Sprint Review

**What went well:**
- Massive experiment throughput on day 1 (142 runs)
- Found multiple phase transitions and interaction effects
- Built reusable sweep infrastructure for Phase 2
- Clear findings that map to both thesis paths

**What didn't happen:**
- Literature reading fell behind — only Debraj's paper and TextGrad scanned
- Sprint doc and daily log not maintained during the week
- No formal theta analysis (dropped in favor of parameter sensitivity)
- EGG repo not checked yet

**Decisions for next sprint:**
- TODO (awaiting new directive)

**Updated roadmap?** [ ] yes / [ ] no
