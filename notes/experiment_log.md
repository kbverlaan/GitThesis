# Experiment Log

Structured log of all simulation runs with config, results, and observations.

---

## Run 001: Baseline with invest_self ON (30 agents)
- **Run ID**: `20260213_134944`
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: First 30-agent run, baseline with invest_self enabled

### Config
| Parameter | Value |
|-----------|-------|
| num_agents | 30 |
| initial_resources | 25.0 |
| max_rounds | 10 |
| model | google/gemini-3-flash-preview |
| allow_invest_self | true |
| invest_self_cost / return | 0 / 2 |
| invest_other_cost / return | 0 / 5 |
| arm_cost | 5.0 |
| arm_multiplier | 2.0 |
| conflict_cost | 3.0 |
| attack_take_percent | 40% |

### Results
| Metric | Value |
|--------|-------|
| Final Gini | 0.000 |
| Final Palma | 0.25 |
| Action stability | 100% (from round 2) |
| Runtime | 71.7s (7.2s/round) |

### Action Distribution
| Action | Count | % |
|--------|-------|---|
| invest_self | 300 | 100% |

### Observations
- Complete stalemate. All 30 agents chose invest_self every single round.
- Gini = 0.000 throughout. No inequality emerged.
- All agents ended at exactly 45.0 resources (25 + 10*2).
- invest_self is a dominant strategy: guaranteed +2, zero cost, zero risk.
- Agents explicitly reason: "attacking is a 50/50 risk", "invest_self is guaranteed gain".
- **Conclusion**: invest_self must be disabled or made costlier for interesting dynamics.

### Files
- `data/runs/20260213_134944_history.json`
- `data/runs/20260213_134944_traces.json`
- `data/runs/20260213_134944_metrics.json`

---

## Run 002: invest_self OFF (30 agents)
- **Run ID**: `20260213_140818`
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Force social interaction by disabling invest_self

### Config
| Parameter | Value |
|-----------|-------|
| num_agents | 30 |
| initial_resources | 25.0 |
| max_rounds | 10 |
| model | google/gemini-3-flash-preview |
| allow_invest_self | **false** |
| invest_other_cost / return | 0 / 5 |
| arm_cost | 5.0 |
| arm_multiplier | 2.0 |
| conflict_cost | 3.0 |
| attack_take_percent | 40% |

### Results
| Metric | Value |
|--------|-------|
| Final Gini | 0.928 |
| Final Palma | 69.27 |
| Action stability | 63% (round 10) |
| Runtime | 94.5s (9.5s/round) |

### Action Distribution
| Action | Count | % |
|--------|-------|---|
| invest_other | 122 | 40.7% |
| attack | 105 | 35.0% |
| no_action | 40 | 13.3% |
| arm_self | 33 | 11.0% |

### Final Resources (top 5 / bottom 5)
| Rank | Agent | Resources |
|------|-------|-----------|
| 1 | agent_21 | 535.7 |
| 2 | agent_14 | 2.3 |
| 3 | agent_5 | 2.3 |
| ... | ... | ... |
| 28 | agent_9 | 0.6 |
| 29 | agent_2 | 0.4 |
| 30 | agent_25 | 0.0 |

### Observations
- **Hegemon emerged**: agent_21 accumulated 535.7 resources (95% of total system resources).
- **Tribute system**: by round 9, almost all agents investing in agent_21 "to avoid being targeted".
- Agents reasoning: "agent_21 has recently attacked those who didn't invest" -- fear-driven cooperation.
- **End-game revolt attempts**: in round 10, ~10 agents tried attacking agent_21 but couldn't afford it (resources < conflict_cost).
- agent_21 armed itself in round 9 and attacked the strongest remaining agent (agent_25).
- Gini trajectory: 0.000 → 0.928 over 10 rounds. Sharp increase.
- arm_other still unused (0 instances). Coalition formation still doesn't happen.
- 13.3% no_action = agents too broke to do anything.
- **Conclusion**: without invest_self, rich dynamics emerge. Single hegemon outcome with tribute extraction. Need multiple runs to see if this is consistent or if different structures emerge.

### Files
- `data/runs/20260213_140818_history.json`
- `data/runs/20260213_140818_traces.json`
- `data/runs/20260213_140818_metrics.json`

---

## Model Selection Testing (Feb 13)

Tested models for 30-agent parameter sweeps. Requirements: fast, valid JSON output, cheap.

| Model | Cost (in/out $/M) | Speed | JSON? | Behavior | Verdict |
|-------|-------------------|-------|-------|----------|---------|
| Gemini 3 Flash | $0.50/$3.00 | 7.2s/round | Yes | Rich, strategic | Too expensive for sweeps |
| Trinity (free) | Free | 9.2s/round | Yes | Docile, bandwagon | Works but boring |
| **Nova Micro (nitro)** | **$0.06/$0.25** | **1.8s/round** | **Yes** | **Diverse, aggressive** | **SELECTED** |
| Liquid LFM 1.2B (free) | Free | 6.4s/round | Yes | Random, arm_other | 20 RPM limit kills it |
| Qwen3-32B (nitro) | $0.12/$0.18 | - | No (fallback) | - | Can't parse JSON |
| Nemotron nano (nitro) | $0.07/$0.03 | - | No (fallback) | - | Can't parse JSON |
| DeepSeek R1T2 (free) | Free | Timeout | - | - | Reasoning tokens too slow |
| GPT-OSS-120B | $0.04/$0.19 | Timeout | - | - | Mandatory CoT too slow |

**Decision**: Use Amazon Nova Micro (nitro) for parameter sweeps. 1.8s/round, ~$0.05-0.10 per run, valid JSON, diverse actions.

---

## Decisions from today's runs

- **Drop theta (c/b) framing.** Theta works for invest actions (cost/return ratio) but not for military actions where expected benefit is context-dependent (depends on opponent resources, arms, coalitions). Instead: parameter sensitivity analysis, varying one parameter at a time.
- **invest_self off as default for experiments.** With invest_self on, it dominates and produces stalemates. Disabling it forces social interaction.

---

## Runs 003-022: invest_other_cost sweep (3 runs per value)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Parameter sensitivity -- how does invest_other cost affect dynamics?
- **Model**: amazon/nova-micro-v1:nitro
- **Config**: 10 agents, 10 rounds, invest_self OFF, invest_other_return=5, all other params default
- **Runs**: 15 total (3 per parameter value)

### Individual Run Results

| invest_other_cost | Run | Final Gini | invest_other % | attack % | arm_self % | no_action % |
|-------------------|-----|-----------|----------------|----------|------------|-------------|
| 0 (free) | 1 | 0.851 | 11.0% | 24.0% | 28.0% | 37.0% |
| 0 (free) | 2 | 0.819 | 6.0% | — | — | — |
| 0 (free) | 3 | 0.566 | 1.0% | — | — | — |
| 2 | 1 | 0.886 | 9.0% | 29.0% | 19.0% | 43.0% |
| 2 | 2 | 0.684 | 5.0% | — | — | — |
| 2 | 3 | 0.800 | 2.0% | — | — | — |
| 5 | 1 | 0.900 | 2.0% | 33.0% | 14.0% | 51.0% |
| 5 | 2 | 0.894 | 0.0% | — | — | — |
| 5 | 3 | 0.553 | 0.0% | — | — | — |
| 8 | 1 | 0.527 | 2.0% | 24.0% | 20.0% | 54.0% |
| 8 | 2 | 0.717 | 4.0% | — | — | — |
| 8 | 3 | 0.474 | 3.0% | — | — | — |
| 12 | 1 | 0.562 | 1.0% | 27.0% | 17.0% | 55.0% |
| 12 | 2 | 0.900 | 6.0% | — | — | — |
| 12 | 3 | 0.677 | 4.0% | — | — | — |

### Summary Statistics (n=3 per value)

| invest_other_cost | Mean Gini | Std Gini | Mean invest_other % |
|-------------------|-----------|----------|---------------------|
| 0 (free) | 0.745 | 0.156 | 6.0% |
| 2 | 0.790 | 0.101 | 5.3% |
| 5 (break-even) | 0.782 | 0.199 | 0.7% |
| 8 | 0.573 | 0.128 | 3.0% |
| 12 | 0.713 | 0.172 | 3.7% |

### Observations
- **High variance across all conditions** (std 0.10–0.20). n=3 is insufficient for confident conclusions.
- **Cooperation is low everywhere**: even at cost=0, mean invest_other is only 6%. Nova Micro agents are aggressive.
- **Gini consistently high** (0.57–0.79 mean) -- hegemon formation appears robust across cost levels.
- **No clean monotonic relationship** between cost and Gini when including repeats. The apparent Gini peak at cost=5 from single runs does NOT replicate cleanly.
- **cost=8 has lowest mean Gini** (0.573) -- possible sweet spot where cooperation cost discourages tribute extraction but doesn't bankrupt agents.
- **cost=12 has surprising variance** (0.562 to 0.900) -- one run produced near-maximum inequality despite highest cooperation cost.
- **Palma = infinity in most runs** -- bottom 40% reach 0 resources. Edge case to handle in metrics.
- **Key takeaway**: With Nova Micro, the system is highly stochastic. Need either (a) more repeats (5-10+) or (b) 30-agent runs where law of large numbers smooths outcomes.

### Files
- `data/runs/20260213_14493*` through `20260213_*` (15 run files)

---

## Run 023: Zero-cost baseline (all costs = 0)
- **Run ID**: `20260213_151132`
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Eliminate bankruptcy stalemate by removing all action costs

### Config
| Parameter | Value |
|-----------|-------|
| num_agents | 10 |
| initial_resources | 25.0 |
| max_rounds | 10 |
| model | amazon/nova-micro-v1:nitro |
| allow_invest_self | false |
| invest_other_cost / return | **0** / 5 |
| arm_cost | **0.0** |
| conflict_cost | **0.0** |
| attack_take_percent | 40% |

### Results
| Metric | Value |
|--------|-------|
| Final Gini | 0.691 |
| Final Palma | 84.39 |
| Action stability | 70% (round 10) |
| Runtime | 15.9s (1.6s/round) |
| Total resources | 270.0 (grew from 250) |

### Action Distribution
| Action | Count | % |
|--------|-------|---|
| attack | 74 | 74.0% |
| arm_self | 22 | 22.0% |
| invest_other | 4 | 4.0% |
| no_action | 0 | 0.0% |

### Observations
- **Bankruptcy stalemate eliminated.** no_action dropped from 37-55% (with costs) to 0%.
- Phase transition from "cost-constrained stalemate" to "pure war game".
- Round 1: 8/10 agents arm (free arming = obvious first move), then fighting from round 2+.
- Three hegemons (107, 84, 57) rather than single hegemon -- more distributed power.
- Resources grew from 250→270 (invest_other creates +5 per use, 4 uses = +20).
- Agents at near-zero still attack (nothing to lose) -- no forced passivity.
- **Cooperation still negligible** (4%). invest_other_return=5 not attractive enough vs. attacking.
- **Next**: sweep invest_other_return to find cooperation threshold.

### Files
- `data/runs/20260213_151132_history.json`
- `data/runs/20260213_151132_traces.json`
- `data/runs/20260213_151132_metrics.json`

---

## Runs 024-038: invest_other_return sweep (zero-cost regime, 3 runs per value)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Find cooperation threshold -- at what invest_other_return do agents start cooperating?
- **Model**: amazon/nova-micro-v1:nitro
- **Config**: 10 agents, 10 rounds, invest_self OFF, ALL COSTS = 0, attack_take_percent=40%

### Summary Statistics (n=3 per value)

| invest_other_return | Mean attack % | Mean arm_self % | Mean invest_other % | arm_other instances |
|---------------------|--------------|-----------------|---------------------|---------------------|
| 2 | 69.3% | 28.3% | 2.0% | 1 |
| 5 | 68.3% | 29.7% | 2.0% | 0 |
| 10 | 63.0% | 32.7% | 4.0% | 1 |
| 15 | 62.3% | 33.7% | 3.3% | 3 |
| 20 | 74.7% | 21.7% | 3.7% | 0 |

### Observations
- **Cooperation is flat.** invest_other stays at 2-4% regardless of return value (2 to 20). No phase transition found.
- **Agents are stuck in a war equilibrium.** ~65% attack, ~30% arm, ~3% cooperate. The return value barely matters.
- **Even at return=20** (giving someone 20 free resources), agents prefer attacking. Fear dominates over value creation.
- **arm_other is rare but present** (5 total instances across 15 runs) -- proto-coalition behavior?
- **No coalitions formed.** invest_other is always one-off, never reciprocated.
- **Possible explanation**: Nova Micro agents may lack strategic depth to reason about cooperation benefits. They see "attack = take 40% of someone's resources" as immediately more attractive than "give someone +N resources hoping for future reciprocity".
- **Implication**: Cooperation might need to be structurally incentivized (e.g., mutual gains, repeated-game signaling) rather than just made more valuable. Or: test with smarter model (Gemini Flash) to see if reasoning ability changes the equilibrium.

---

## Runs 039-053: attack_take_percent (T) sweep (zero-cost, invest_other_return=20)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Find cooperation transition by reducing spoils of conflict
- **Model**: amazon/nova-micro-v1:nitro
- **Config**: 10 agents, 10 rounds, invest_self OFF, ALL COSTS = 0, invest_other_return=20

### Summary Statistics (n=3 per value)

| T (attack_take_%) | Mean Gini | Mean attack % | Mean arm_self % | Mean invest_other % |
|--------------------|-----------|--------------|-----------------|---------------------|
| 40 | 0.523 | 65.3% | 31.7% | 3.0% |
| 30 | 0.533 | 63.3% | 33.0% | 3.7% |
| 20 | 0.461 | 69.3% | 27.0% | 3.3% |
| 10 | 0.200 | 66.0% | 32.0% | 2.0% |
| 5 | 0.208 | 65.3% | 30.7% | 4.0% |

### Key Finding: Behavioral Robustness of War Equilibrium
- **Gini phase transition between T=20 and T=10** (0.46 → 0.20). Inequality drops sharply.
- **But behavior does NOT change.** Attack rate stays ~65%, cooperation ~3% across ALL values of T.
- Agents fight just as much at T=5% as at T=40%. They just can't accumulate as much from winning.
- **Reducing spoils of war reduces inequality but does NOT produce cooperation.**
- The war equilibrium is behaviorally robust: agents don't reason "war is less profitable → cooperate instead."
- **Implication**: Cooperation may require structural game changes (mutual gains, signaling mechanisms) or smarter models that can reason about long-term reciprocity. Simply adjusting payoff magnitudes is insufficient with Nova Micro.

---

## Runs 054-055: Gemini Flash -- model & objective comparison
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Test whether smarter model and/or different objective produces cooperation
- **Model**: google/gemini-3-flash-preview
- **Config**: 10 agents, 10 rounds, invest_self OFF, ALL COSTS = 0, invest_other_return=20, T=10%

### Run 054: Gemini Flash, maximize_resources
| Metric | Value |
|--------|-------|
| Final Gini | 0.731 |
| Runtime | 94.9s (9.5s/round) |
| invest_other | 33.0% |
| attack | 55.0% |
| arm_self | 12.0% |
| Total resources | 910 (from 250) |

### Run 055: Gemini Flash, avoid_last
| Metric | Value |
|--------|-------|
| Final Gini | 0.103 |
| Runtime | 55.2s (5.5s/round) |
| invest_other | **83.0%** |
| attack | 6.0% |
| arm_self | 11.0% |
| Total resources | **1910** (from 250) |

### Cross-comparison (same game params: T=10%, invest_other_return=20, zero costs)

| Condition | invest_other % | attack % | Gini | Total resources |
|-----------|---------------|----------|------|-----------------|
| Nova Micro, maximize | 3% | 66% | 0.200 | ~270 |
| Gemini Flash, maximize | 33% | 55% | 0.731 | ~910 |
| Gemini Flash, avoid_last | 83% | 6% | 0.103 | ~1910 |

### Key Findings
- **Model architecture matters**: Gemini Flash cooperates 10x more than Nova Micro under identical game conditions (33% vs 3%). Smarter models find cooperative strategies.
- **Objective framing matters even more**: Switching from "maximize resources" to "avoid finishing last" flips the equilibrium from war (55% attack) to cooperation (83% invest_other).
- **Both effects interact**: Nova Micro + maximize = pure war. Gemini + avoid_last = cooperative society.
- **Value creation**: Cooperation is massively positive-sum. The cooperative run created 7.6x more total resources than the war run (1910 vs 270).
- **Inequality**: War with smart model paradoxically produces MORE inequality (Gini 0.731) than war with dumb model (0.200) -- because Gemini creates a clear hegemon through strategic tribute. Cooperation produces near-equality (0.103).
- **Thesis implication**: Both the reasoning architecture AND the objective function are independent variables that determine emergent social structure. This maps directly to the RQ about architecture-dependent emergence.

---

## Runs 056-070: arm_multiplier sweep (zero-cost regime, 3 runs per value)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Does arming advantage affect structure?
- **Model**: amazon/nova-micro-v1:nitro
- **Config**: 10 agents, 10 rounds, invest_self OFF, ALL COSTS = 0, invest_other_return=5, T=40%

### Summary Statistics (n=3 per value)

| arm_multiplier | Mean Gini | Mean attack % | Mean arm_self % | Mean invest_other % |
|----------------|-----------|--------------|-----------------|---------------------|
| 1.0 (no effect) | ~0.728 | 70.3% | 25.7% | 3.7% |
| 1.5 | 0.703 | 68.0% | 28.3% | 3.7% |
| 2.0 (default) | 0.748 | 69.3% | 27.3% | 3.3% |
| 3.0 | 0.644 | 69.3% | 25.3% | 5.3% |
| 5.0 | 0.690 | 70.0% | 28.3% | 1.7% |

### Observations
- **No phase transition.** All metrics flat across multiplier values.
- Agents arm at ~27% and attack at ~69% regardless of multiplier.
- Even at M=1.0 (arming has NO combat benefit), agents still arm 26% of the time -- they don't adapt.
- **Conclusion**: arm_multiplier does not drive structural change with Nova Micro. Agents don't reason about multiplier value.

---

## Runs 071-085: arm_duration sweep (zero-cost regime, 3 runs per value)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Does arming duration affect structure?
- **Model**: amazon/nova-micro-v1:nitro
- **Config**: 10 agents, 10 rounds, invest_self OFF, ALL COSTS = 0, invest_other_return=5, T=40%

### Summary Statistics (n=3 per value)

| arm_duration | Mean Gini | Mean attack % | Mean arm_self % | Mean invest_other % |
|--------------|-----------|--------------|-----------------|---------------------|
| 1 round | 0.562 | 61.7% | 35.3% | 3.0% |
| 2 rounds | ~0.553 | 64.7% | 32.7% | 2.3% |
| 3 rounds (default) | 0.691 | 71.0% | 27.0% | 2.0% |
| 5 rounds | 0.622 | 65.0% | 34.0% | 1.0% |
| 8 rounds | 0.732 | 67.7% | 31.7% | 0.7% |

### Observations
- **Mild structural effect.** Shorter arm duration → lower Gini and more arming.
- At D=1, agents must re-arm every round, spending 35% of actions on arm_self vs 27% at D=3. This crowds out attacking (62% vs 71%).
- **Less fighting → less inequality**: D=1 Gini 0.56 vs D=8 Gini 0.73.
- The trend isn't perfectly monotonic (D=5 dips) but the endpoints are clear.
- **Mechanism**: Short arm duration acts as an "action tax" -- agents waste turns re-arming instead of fighting, which dampens inequality.
- Not a clean phase transition like T sweep, but a gradual structural effect.

---

## Runs 086-100: Gemini Flash Lite T sweep (zero-cost, invest_other_return=5)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Compare parameter sensitivity of Gemini Flash Lite vs Nova Micro
- **Model**: google/gemini-2.5-flash-lite
- **Config**: 10 agents, 10 rounds, invest_self OFF, ALL COSTS = 0, invest_other_return=5

### Summary Statistics (n=3 per value)

| T | Mean Gini | Mean attack % | Mean arm_self % | Mean invest_other % |
|---|-----------|--------------|-----------------|---------------------|
| 5% | 0.342 | 28.3% | 27.7% | **33.0%** |
| 10% | 0.274 | 32.7% | 25.3% | 13.7% |
| 20% | 0.393 | 21.7% | 24.0% | **37.0%** |
| 30% | 0.522 | 28.7% | 38.7% | 17.3% |
| 40% | 0.512 | 17.0% | 26.7% | **32.0%** |

### Cross-model comparison (same game, same parameters)

| T | Nova Micro attack % | Gemini attack % | Nova Micro invest_other % | Gemini invest_other % |
|---|--------------------|-----------------|--------------------------|-----------------------|
| 5% | 65.3% | 28.3% | 4.0% | 33.0% |
| 10% | 66.0% | 32.7% | 2.0% | 13.7% |
| 20% | 69.3% | 21.7% | 3.3% | 37.0% |
| 30% | 63.3% | 28.7% | 3.7% | 17.3% |
| 40% | 65.3% | 17.0% | 3.0% | 32.0% |

### Key Findings
- **Gemini Flash Lite IS parameter-sensitive.** Cooperation ranges 14-37%, attack 17-33%. Nova Micro was flat at 65%/3%.
- **Architecture determines parameter sensitivity.** The game has a rich parameter landscape, but only a capable model can navigate it.
- **Cooperation is substantial.** Even at T=40% (highest war spoils), Gemini cooperates 32% of the time vs Nova Micro's 3%.
- **The pattern is not monotonic.** High variance across runs, cooperation doesn't simply increase as T decreases. Suggests complex strategic dynamics.
- **System characterization IS model-dependent.** This confirms that Phase 1 findings depend on which model you use. The game supports different equilibria; the model determines which one emerges.

---

## Runs 101-109: Distribution Sweep (Gemini Flash Lite, zero-cost)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Test whether initial wealth distribution affects emergent behavior
- **Model**: google/gemini-2.5-flash-lite
- **Config**: 10 agents, 10 rounds, invest_self OFF, ALL COSTS = 0, T=40%, invest_other_return=5

### Summary Statistics (n=3 per value, random rep 2 contaminated — 5 agents/3 rounds leaked from smoke test)

| Distribution | Rep | Final Gini | Attack % | Arm_self % | Invest_other % | Notes |
|---|---|---|---|---|---|---|
| equal | 1 | 0.718 | 31% | 33% | 16% | |
| equal | 2 | 0.744 | 26% | 44% | 18% | |
| equal | 3 | 0.644 | 38% | 30% | ~0% | |
| unequal | 1 | 0.651 | 51% | 25% | 14% | |
| unequal | 2 | 0.703 | 28% | 27% | 26% | |
| unequal | 3 | 0.230 | ~0% | 33% | ~0% | Peaceful/equalizing |
| random | 1 | 0.116 | ~0% | 34% | ~0% | Very peaceful |
| random | 2 | 0.335 | 47% | 7% | 27% | **CONTAMINATED** (5 agents, 3 rounds) |
| random | 3 | 0.660 | 46% | 40% | 4% | |

### Key Findings
- **Equal distribution is most consistently warlike** (Gini 0.64-0.74), with balanced attack/arm mix.
- **Unequal and random show high variance** — some reps peaceful (Gini ~0.1-0.2, all arm_self), others warlike (Gini ~0.7, 50% attack).
- **Initial conditions matter** — same game parameters produce wildly different outcomes depending on starting wealth distribution. Particularly unequal rep 3 and random rep 1 spontaneously equalized.
- **Random rep 2 contaminated** by spatial smoke test config change (5 agents, 3 rounds). Discarded.

---

## Runs 110-111: Spatial Field (Gemini Flash Lite, 7x7 grid, radius 2)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Test whether spatial constraints affect emergent behavior
- **Model**: google/gemini-2.5-flash-lite
- **Config**: 10 agents, 10 rounds, 7x7 toroidal grid, interaction radius 2, equal start (25.0), invest_self OFF, ALL COSTS = 0, T=40%, invest_other_return=5
- **Note**: Simplified spatial prompt (no coordinates, just neighbor list) after initial runs showed LLMs wasting tokens on distance math

### Iteration history
1. **First attempt (with coordinates)**: 35% invest_self was actually parsing fallbacks (LLM calculated Euclidean distances, ran out of tokens). Fallback gave free invest_self despite being disabled.
2. **Second attempt (do_nothing fallback)**: Fixed fallback but 66% do_nothing — game froze from parsing failures.
3. **Third attempt (simplified prompt)**: Removed coordinates, just listed neighbors. Parsing failures dropped to ~13%. Clean results below.

### Results (simplified prompt, n=2)

| Run | invest_other % | attack % | arm_self % | do_nothing % | Final Gini | Total resources |
|-----|---------------|----------|------------|-------------|-----------|-----------------|
| 110 | 67% | 12% | 8% | 13% | 0.39 | 585 |
| 111 | 77% | 4% | 6% | 13% | 0.46 | 635 |
| **Mean** | **72%** | **8%** | **7%** | **13%** | **0.43** | **610** |

### Comparison: Spatial vs Non-spatial (same model, same params)

| | Non-spatial (equal, mean) | Spatial (mean) |
|---|---|---|
| invest_other | ~17% | **72%** |
| attack | ~32% | **8%** |
| arm_self | ~36% | 7% |
| Final Gini | ~0.70 | **0.43** |
| Total resources | ~250 | **610** |

### Key Findings
- **Spatial constraints dramatically increase cooperation.** invest_other jumped from 17% to 72%, attack dropped from 32% to 8%.
- **Matthew Effect from cooperation.** In both runs, one agent became a "resource magnet" receiving investments from 4-5 agents per round, ending with 180-195 resources (30%+ of total). Emergent inequality from cooperation, not conflict.
- **Reciprocal investment pairs formed.** E.g., agent_1 ↔ agent_2 invested in each other across multiple rounds. Small neighborhoods with repeated interaction create iterated prisoner's dilemma dynamics.
- **Mechanisms**: (1) fewer targets → less attack opportunity, (2) repeated local interactions → reciprocity, (3) visible investment history → trust building, (4) isolation rounds → forced passivity.
- **"Invest in the richest" heuristic emerged.** Agents reasoned: "agent_10 has the most resources and has been a consistent recipient of investments" → positive feedback loop.
- **Prompt engineering matters.** Coordinates in prompt caused LLMs to waste tokens on distance calculations. Simplified neighbor list fixed parsing failures from 66% to 13%.

---

## Runs 112-119: Spatial Radius Sweep (Gemini Flash Lite)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Test how interaction radius affects cooperation/conflict gradient
- **Model**: google/gemini-2.5-flash-lite
- **Config**: 10 agents, 10 rounds, equal start, invest_self OFF, ALL COSTS = 0, T=40%, simplified spatial prompt (no coordinates)

### Results (n=2 per condition)

| Condition | Rep | invest_other % | attack % | do_nothing % | arm_self % | Final Gini |
|---|---|---|---|---|---|---|
| 7x7 r=1 | 1 | 49% | 4% | 38% | 9% | 0.285 |
| 7x7 r=1 | 2 | 54% | 7% | 30% | 9% | 0.205 |
| 7x7 r=2 | 1 | 59% | 10% | 23% | 8% | 0.389 |
| 7x7 r=2 | 2 | 60% | 15% | 16% | 9% | 0.579 |
| 7x7 r=3 | 1 | 14% | 58% | 22% | 6% | 0.772 |
| 7x7 r=3 | 2 | 26% | 51% | 13% | 10% | 0.654 |
| 10x10 r=2 | 1 | 41% | 6% | 45% | 8% | 0.384 |
| 10x10 r=2 | 2 | 51% | 10% | 30% | 9% | 0.372 |

### Aggregated means by radius (7x7 grid)

| Radius | Mean invest_other | Mean attack | Mean Gini |
|--------|------------------|-------------|-----------|
| r=1 | 52% | 6% | 0.25 |
| r=2 | 60% | 13% | 0.48 |
| r=3 | 20% | 55% | 0.71 |
| Non-spatial | ~17% | ~32% | ~0.70 |

### Key Findings
- **Clear cooperation→conflict gradient as radius increases.** r=1 is ultra-cooperative (52% invest, 6% attack), r=3 approaches non-spatial war (55% attack, Gini 0.71).
- **Phase transition between r=2 and r=3.** invest_other drops from 60% to 20%, attack jumps from 13% to 55%.
- **r=3 on 7x7 ≈ non-spatial.** Most agents are reachable (max Chebyshev distance on 7x7 torus is 3), so spatial constraints are effectively gone.
- **Sparser grid (10x10) = more isolation.** 10x10 r=2 shows higher do_nothing (38%) than 7x7 r=2 (20%) but similar cooperation levels.
- **do_nothing scales inversely with connectivity.** r=1: 34%, r=2: 20%, r=3: 18%. More isolation = more forced passivity.

---

## Runs 120-125: Action Order Sweep (Gemini Flash Lite, non-spatial)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Test simultaneous vs sequential action resolution
- **Model**: google/gemini-2.5-flash-lite
- **Config**: 10 agents, 10 rounds, equal start, invest_self OFF, ALL COSTS = 0, T=40%, non-spatial

### Results (n=3 per condition)

| Order | Rep | invest_other % | attack % | arm_self % | do_nothing % | Final Gini |
|---|---|---|---|---|---|---|
| Simultaneous | 1 | 8% | 14% | 71% | 7% | 0.397 |
| Simultaneous | 2 | 20% | 18% | 48% | 14% | 0.348 |
| Simultaneous | 3 | 34% | 6% | 48% | 12% | 0.490 |
| Sequential | 1 | 22% | 37% | 27% | 14% | 0.479 |
| Sequential | 2 | 36% | 18% | 27% | 19% | 0.623 |
| Sequential | 3 | 24% | 34% | 13% | 29% | 0.648 |

### Aggregated means

| Order | invest_other | attack | arm_self | do_nothing | Mean Gini |
|---|---|---|---|---|---|
| Simultaneous | 21% | 13% | 56% | 11% | 0.41 |
| Sequential | 27% | 30% | 22% | 21% | 0.58 |

### Key Findings
- **Simultaneous produces arms races.** 56% arm_self — when everyone decides at once, arming is the safe hedge against unseen attacks.
- **Sequential produces more aggression.** 30% attack (vs 13% simultaneous). Information advantage: seeing others' actions before deciding lets agents exploit vulnerabilities (e.g., attack agents who just spent or didn't arm).
- **Sequential is more unequal.** Gini 0.58 vs 0.41. Information asymmetry compounds — early movers who attack successfully snowball.
- **Sequential also has more cooperation AND more passivity.** 27% invest_other and 21% do_nothing (vs 21% and 11%). Seeing cooperation encourages reciprocity; seeing attacks encourages caution.
- **Simultaneous ≈ "everyone arms, nobody fights."** Sequential ≈ "some fight, some cooperate, some hide."

---

## Run 126: 30-agent Spatial (Gemini Flash Lite, 11x11, r=2)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Test if spatial cooperation scales to 30 agents (Debraj: "distribution changes at 30")
- **Model**: google/gemini-2.5-flash-lite
- **Config**: 30 agents, 10 rounds, 11x11 toroidal grid, r=2, equal start (25.0), invest_self OFF, ALL COSTS = 0, T=40%

### Results

| Metric | 10 agents (mean) | 30 agents |
|---|---|---|
| invest_other | 72% | 63% |
| attack | 8% | 12% |
| arm_self | 7% | 13% |
| do_nothing | 13% | 12% |
| Final Gini | 0.43 | 0.54 |
| Total resources | 610 | 1695 |

Top 3 agents held 39% of resources. Agent_12 ended with 285 (16.8% of total). 6 agents stuck at exactly 25.0 (never meaningfully interacted). Bottom agent at 2.5.

### Key Findings
- **Cooperation holds at 30 agents but drops slightly.** 63% invest_other (vs 72% at 10 agents). More agents = more competition within neighborhoods.
- **Hierarchy is steeper.** Gini 0.54 (vs 0.43). The Matthew Effect scales — "invest in the richest" concentrates wealth faster with more agents competing for investment.
- **Debraj was right.** Distribution changes at scale. The rich-get-richer dynamic is amplified.

---

## Runs 127-134: Information 2x2 Factorial (30 agents, spatial, Gemini Flash Lite)
- **Date**: 2026-02-13
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Disentangle effect of resource visibility vs history on cooperation
- **Model**: google/gemini-2.5-flash-lite
- **Config**: 30 agents, 10 rounds, 11x11 grid, r=2, equal start, invest_self OFF, ALL COSTS = 0, T=40%
- **Design**: 2x2 factorial — history (0 vs 10 rounds) x resources (visible vs hidden)

### Results (n=2 per condition)

| Condition | invest_other | attack | arm_self | do_nothing | Mean Gini |
|---|---|---|---|---|---|
| History + Resources visible | 64% | 12% | 12% | 13% | 0.49 |
| History + Resources hidden | 14% | 2.5% | 56% | 27% | 0.24 |
| No history + Resources visible | 67% | 14% | 8% | 11% | 0.55 |
| No history + Resources hidden | 16% | 3.7% | 52% | 29% | 0.24 |

### Key Findings
- **Resource visibility is the dominant factor, not history.** Removing history barely changes behavior (64→67% cooperation). Hiding resources transforms the game entirely (64→14% cooperation).
- **Cooperation is resource-based, not reputation-based.** Agents invest in whoever is richest ("agent_10 has the most resources"), not whoever was nicest. History is parsed but not used for reputation tracking.
- **Hidden resources → paranoid stalemate.** 52-56% arm_self, 2-4% attack, Gini ~0.24. Agents can't identify targets so they default to arming. Resources barely move.
- **The Matthew Effect requires resource visibility.** Without seeing who's richest, the "invest in the richest" positive feedback loop can't form. Result: low inequality but low dynamism.
- **History is redundant for this model.** Gemini Flash Lite doesn't extract reputation signals from raw action logs. It may need reputation to be pre-computed and explicitly shown.

---

## Runs 135-142: Reputation 2x2 Factorial (30 agents, spatial, Gemini Flash Lite)
- **Date**: 2026-02-09
- **Phase**: System Characterization (Sprint 2)
- **Purpose**: Test if pre-computed reputation summary rescues cooperation when resources are hidden
- **Model**: google/gemini-2.5-flash-lite
- **Config**: 30 agents, 10 rounds, 11x11 grid, r=2, equal start, invest_self OFF, ALL COSTS = 0, T=40%, history=10
- **Design**: 2x2 factorial — resource visibility (visible/hidden) x reputation summary (on/off)
- **Code change**: Added `_format_reputation()` method to `prompts.py` — pre-computes per-agent interaction counts from history (e.g., "agent_3: invested in you 2x, attacked you 0x"). Toggled via `show_reputation` in prompt_config.

### Results (n=2 per condition)

| Condition | invest_other | attack | arm_self | do_nothing | Mean Gini |
|---|---|---|---|---|---|
| Visible + No reputation | 70.7% | 11.9% | 10.2% | 7.4% | 0.526 |
| Visible + Reputation | 54.5% | 14.0% | 12.4% | 19.2% | 0.522 |
| Hidden + No reputation | 22.3% | 2.5% | 45.7% | 29.5% | 0.262 |
| Hidden + Reputation | 19.5% | 2.4% | 40.0% | 38.2% | 0.258 |

### Key Findings
- **Reputation does NOT rescue cooperation when resources are hidden.** Hidden+reputation (~19.5% invest) is nearly identical to hidden+no reputation (~22%). The paranoid stalemate persists — agents arm and wait regardless of reputation info.
- **Visible resources remain the dominant cooperation driver.** vis_norep averages ~71% cooperation vs ~22% for hidden conditions, confirming the information sweep finding.
- **Reputation may slightly reduce cooperation when resources are visible.** vis_rep (54.5%) vs vis_norep (70.7%), but high variance between reps (rep1: 44.7%, rep2: 64.3%) makes this uncertain.
- **Reputation increases do_nothing across the board.** Visible: 7.4% → 19.2%. Hidden: 29.5% → 38.2%. Pre-computed reputation info may overwhelm or distract the LLM, causing more parsing failures or indecision.
- **Bottom line: cooperation in this system is resource-signal-based, not reputation-based.** Agents cooperate when they can see who is rich (worth investing in), not based on who has been nice. Pre-computing reputation doesn't change this — the mechanism is "invest in the richest" not "invest in the nicest."

### Files
- `data/runs/rep_vis_norep_rep{1,2}_*.json`
- `data/runs/rep_vis_rep_rep{1,2}_*.json`
- `data/runs/rep_hid_norep_rep{1,2}_*.json`
- `data/runs/rep_hid_rep_rep{1,2}_*.json`

---

<!-- Template for new runs:

## Runs 143-242: Gemma 2 27B — Arch 1+2 Combined (Snellius)
- **Run IDs**: `model_gemma-2-27b-it_framing_{framing}_rep{1-20}`
- **Date**: 2026-02-17 (ran overnight), analyzed 2026-02-18
- **Phase**: Architecture Experiments (Phase 2a, Exp 1+2 combined)
- **Purpose**: Fingerprint (20 neutral reps) + framing factorial (5 framings × 20 reps) for Gemma 2 27B

### Config
| Parameter | Value |
|-----------|-------|
| num_agents | 30 |
| max_rounds | 50 |
| model | gemma-2-27b-it (Snellius vLLM, 1× H100) |
| framings | neutral, cooperative, competitive, strategic, cautious |
| reps per framing | 20 |
| spatial_enabled | true |
| interaction_radius | 2 |
| zero-cost regime | yes |
| invest_self | false |

### Results — Summary per framing

| Framing | Final Gini (mean±sd) | Coop ratio | First attack (mean round) | Dominant action |
|---------|---------------------|------------|--------------------------|-----------------|
| neutral | 0.778 ± 0.034 | 68.1% | 2.9 | invest_other (57%) |
| cooperative | 0.581 ± 0.036 | 88.7% | 18.8 | invest_other (59%) |
| competitive | 0.858 ± 0.035 | 37.2% | 1.1 | invest_other (31%) + attack (30%) |
| strategic | 0.725 ± 0.039 | 49.5% | 2.5 | invest_other (39%) + arm_self (16%) |
| cautious | 0.549 ± 0.057 | 78.5% | 9.1 | invest_other (55%) + do_nothing (9%) |

### Statistical Results
- **ANOVA (framing → Gini)**: F=217.04, p<0.0001, **η²=0.901** — framing explains 90% of Gini variance
- **ANOVA (framing → coop_ratio)**: significant, large effect
- **Pairwise**: 9/10 pairs significant after Bonferroni. Only cautious vs cooperative non-significant (d=0.69, p=0.36)
- **Largest effect**: competitive vs cautious, Cohen's d = 6.60
- **ICC (neutral Gini)**: 0.016 — almost all variance is within-run, runs are very consistent

### Observations
- **Counterintuitive finding**: cautious framing (Gini 0.549) produces MORE equality than cooperative (0.581). Cautious agents avoid conflict (1.2% attack, 9.4% do_nothing) more effectively than cooperative agents who occasionally create in-group/out-group dynamics.
- **η²=0.90 is massive**: prompt framing is the dominant determinant of emergent social structure for this model. Raises question: how much room is there for architecture effects in Arch 3?
- **Temporal dynamics**: all framings start at Gini ~0.1 and diverge around round 5-10. Competitive saturates early (~0.85 by round 20), cooperative/cautious plateau around 0.55-0.58.
- **Reasoning trace analysis**: within each framing, high vs low Gini runs have near-identical action distributions but systematically different reasoning vocabulary. Low-Gini runs: "investing", "return", "maximize". High-Gini runs: "threat", "survival", "chance". Reasoning is not purely epiphenomenal.
- **Comparison to Phase 1**: confirms cooperative bias of Gemma 2 (74% invest_other in earlier 10-agent neutral runs). At 30 agents the cooperation rate drops slightly (68%) but inequality increases.

### Files
- `data/runs/arch_combined_gemma2_27b/` (400 files: 100 runs × 4 types)
- `data/results/arch_gemma2/summary_df.csv`
- `data/results/arch_gemma2/analysis_results.json`
- `data/results/arch_gemma2/trace_analysis.json`
- `data/results/arch_gemma2/plots/` (6 meeting plots)
- `notebooks/arch_exp_gemma2.ipynb`

### Analysis scripts created
- `src/analysis/arch_analysis.py` — data loading, validation, Arch 1+2 statistics
- `src/analysis/trace_analysis.py` — reasoning trace keyword analysis, outcome-split comparison

---

## Runs 243+: Qwen3-32B — Arch 1+2 Combined (Snellius, IN PROGRESS)
- **Run IDs**: `model_Qwen3-32B_framing_{framing}_rep{N}`
- **Date**: Started 2026-02-18
- **Phase**: Architecture Experiments (Phase 2a, Exp 1+2 combined)
- **Purpose**: Same factorial as Gemma 2 (5 framings × 20 reps) for Qwen3-32B
- **Status**: RUNNING — 2 of 5 array tasks active, each on rep 1 of 10 after ~4 hours

### Performance Issue
- **~4 hours per run** (vs ~34 min for Gemma 2 = ~8× slower)
- GPU KV cache at 96-99% — model too large for 1 H100 with 30 agents
- Generation throughput: ~350 tokens/s (vs Gemma 2 which fit comfortably)
- **Walltime problem**: 24h limit, 10 reps per task = ~40h needed. Jobs will crash.
- **Options considered**: 2-GPU tensor parallel, fewer agents, more array tasks with fewer reps, or pivot to reasoning-as-architecture approach on Gemma 2

### Decision: TBD
Discuss with Debraj on Feb 27. Key question: is comparing Gemma vs Qwen (100 confounds) more valuable than systematically varying reasoning structure on one model?

---

## Run NNN: [description]
- **Run ID**: `YYYYMMDD_HHMMSS`
- **Date**: YYYY-MM-DD
- **Phase**:
- **Purpose**:

### Config
| Parameter | Value |
|-----------|-------|
| ... | ... |

### Results
| Metric | Value |
|--------|-------|
| Final Gini | |
| Final Palma | |
| Action stability | |
| Runtime | |

### Action Distribution
| Action | Count | % |
|--------|-------|---|

### Observations
-

### Files
- `data/runs/RUNID_history.json`
- `data/runs/RUNID_traces.json`
- `data/runs/RUNID_metrics.json`

-->
