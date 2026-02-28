# Arch Exp 1: Architectural Fingerprinting — Report
**Generated**: 2026-02-16
**Status**: IN PROGRESS (Gemini FL complete, DeepSeek + Llama 70B running)
**Config**: `experiments/architectural_fingerprint.yaml`
**Total runs**: 60 (3 models × 20 reps), 50 rounds, 10 agents, spatial ON (r=2)

---

## Experiment Design

**Question**: Do different LLM architectures produce distinct behavioral signatures under identical game conditions?

**Setup**: All game parameters held constant. Only the LLM model varies:
1. Google Gemini 2.5 Flash Lite (closed, Google)
2. DeepSeek V3.2 (open-weight, MoE architecture)
3. Meta Llama 3.3 70B Instruct (open-weight, dense)

20 replications per model. 50 rounds, 10 agents, zero-cost regime, spatial field (r=2).

---

## Results: Gemini 2.5 Flash Lite (20/20 runs complete)

### Summary Statistics

| Metric | Mean | Std | Min | Max |
|--------|------|-----|-----|-----|
| Final Gini | 0.838 | 0.048 | 0.694 | 0.892 |
| Cooperation ratio | 0.468 | 0.079 | 0.22 | 0.56 |
| First attack round | 1.9 | 0.4 | 1 | 3 |
| Top agent resource share | 79.0% | — | 39.5% | 97.3% |
| Hegemon emergence (>50%) | 19/20 runs (95%) | | | |
| Top 3 share | 97.4% | 2.4% | 89.5% | 100% |
| Fallbacks (do_nothing) | 3 total | | | |

### Gini Trajectory (mean across 20 runs)

| Phase | Rounds | Mean Gini | Interpretation |
|-------|--------|-----------|----------------|
| Start | 1 | 0.062 | Near-perfect equality |
| Early | 1-10 | 0.06→0.60 | Rapid inequality emergence |
| Mid | 11-30 | 0.60→0.81 | Continued growth, decelerating |
| Late | 31-50 | 0.81→0.84 | Plateau — hegemon established |

Steep monotonic increase, plateauing around round 30. Consistent across runs (low std).

### Action Distribution by Phase

| Phase | attack | invest_other | arm_self | do_nothing |
|-------|--------|-------------|----------|-----------|
| Early (1-10) | 38.6% | 44.7% | 11.9% | 4.9% |
| Mid (11-30) | 45.9% | 45.9% | 4.3% | 3.9% |
| Late (31-50) | 47.6% | 42.9% | 3.5% | 6.0% |

Cooperation starts dominant, attacks increase over time. By late game, attacks exceed cooperation. Arming drops after early rounds.

### Cooperation Rate Dynamics

- Initial spike (round 1-2): ~0.69 — agents start cooperative
- Sharp drop (round 3-4): ~0.33 — first attacks trigger retaliation
- Stabilization (round 5-45): ~0.45-0.50 — persistent mixed strategy
- Late decline (round 46-50): ~0.35 — end-game aggression

### Hegemon Pattern

- 95% of runs develop a single dominant agent controlling >50% of total resources
- Top 3 agents capture 97.4% of resources on average
- Bottom 7 agents left with 2.6%
- Matthew Effect: rich agents receive more invest_other actions, amplifying inequality

### Key Observations (Gemini FL)

1. **Rapid militarization**: Attacks begin round 1-2, never stop
2. **Cooperation persists alongside conflict**: ~45% cooperation ratio even at high inequality
3. **Hegemon inevitability**: Nearly all runs converge to single-agent dominance
4. **Invest-in-the-strongest**: Poor agents invest in rich agents (rational but inequality-amplifying)
5. **Phase structure**: equality → rapid stratification → oligarchic plateau

---

## Results: DeepSeek V3.2 (1/20 runs complete — PRELIMINARY)

*Running. ~50 min/run. Estimated completion: ~17 hrs from start.*

### Summary Statistics (20/20 runs complete)

| Metric | DeepSeek V3.2 | Gemini FL | Difference |
|--------|--------------|-----------|------------|
| Final Gini | 0.090 ± 0.270 | 0.838 ± 0.048 | **Opposite extremes** |
| Cooperation ratio | 0.01% | 46.8% ± 7.9% | **Zero cooperation** |
| First attack round | 46.1 ± 14.7 | 1.9 ± 0.4 | **44 rounds later** |
| Dominant action | do_nothing (93%) | attack (45%) | **Passive vs aggressive** |
| Hegemon rate (>50%) | 10% (2/20) | 95% (19/20) | **Opposite** |

### Bimodal Distribution

**Critical finding**: DeepSeek produces a bimodal outcome:
- **18/20 runs (90%)**: Gini = 0.000 — perfect equality. All agents do nothing for 50 rounds.
- **2/20 runs (10%)**: Gini ≈ 0.900 — extreme inequality. Rare late-game attacks create hegemon.

Run 1 (the first completed) was one of the 2 outlier runs, initially suggesting DeepSeek was a "war machine". The full 20-run dataset reveals the opposite: DeepSeek defaults to **passive stalemate**.

### Action Distribution by Phase

| Phase | do_nothing | attack | arm_self | invest_other |
|-------|-----------|--------|----------|-------------|
| Early (1-10) | 92.2% | 6.3% | 1.6% | 0.0% |
| Mid (11-30) | 92.4% | 6.9% | 0.7% | 0.0% |
| Late (31-50) | 93.4% | 6.6% | 0.0% | 0.0% |

do_nothing dominates throughout. No learning, no adaptation, no cooperation. Arming decreases over time.

### Key Observations (DeepSeek V3.2)

1. **Passive equilibrium**: Agents default to inaction — qualitatively different from Gemini's active engagement
2. **No cooperation AND no conflict**: Neither invest_other nor attack actions are common
3. **Stereotyped behavior**: 90% of runs produce identical outcomes (Gini=0)
4. **Bimodal outliers**: 10% of runs show extreme inequality, suggesting rare stochastic breakouts from the passive equilibrium
5. **Interpretation**: DeepSeek may lack the strategic reasoning to evaluate game mechanics, defaulting to the safest action (do_nothing)

---

## Results: Llama 3.3 70B Instruct (20/20 runs complete)

### Summary Statistics

| Metric | Llama 70B | Gemini FL | DeepSeek |
|--------|----------|-----------|----------|
| Final Gini | **0.000 ± 0.000** | 0.838 ± 0.048 | 0.090 ± 0.270 |
| Cooperation ratio | 0.000 | 0.468 ± 0.079 | 0.0001 |
| First attack round | None (never) | 1.9 ± 0.4 | 46.1 ± 14.7 |
| Dominant action | do_nothing (100%) | attack (45%) | do_nothing (93%) |
| Hegemon rate | 0% | 95% | 10% |

### Key Observations (Llama 3.3 70B)

1. **Complete inertia**: 100% do_nothing across ALL 20 runs, ALL 50 rounds, ALL agents
2. **Zero variance**: Every run is identical — Gini = 0.000, no attacks, no cooperation
3. **Not even stochastic outliers**: Unlike DeepSeek (which has 2/20 outlier runs), Llama never deviates
4. **Implications for Origins**: This model produces no dynamics. If used on Snellius for Origins experiments, we would need a different model or prompt intervention.

**Critical concern**: Llama 70B was planned as the primary model for Origins experiments on Snellius. With 100% do_nothing behavior, it cannot produce the phase transitions we need to study. This needs to be addressed before committing to Llama for Origins.

---

## Cross-Model Comparison (ALL 60 RUNS COMPLETE)

### Summary Table

| Metric | Gemini FL | DeepSeek V3.2 | Llama 3.3 70B |
|--------|----------|--------------|---------------|
| Final Gini | **0.838 ± 0.048** | 0.090 ± 0.270 | 0.000 ± 0.000 |
| Cooperation ratio | **0.468 ± 0.079** | 0.0001 | 0.000 |
| First attack round | **1.9 ± 0.4** | 46.1 ± 14.7 | Never |
| % attack | **45.1%** | 6.6% | 0% |
| % invest_other | **44.4%** | 0.01% | 0% |
| % arm_self | 5.5% | 0.6% | 0% |
| % do_nothing | 4.9% | **92.8%** | **100%** |
| Hegemon rate | **95%** | 10% | 0% |
| Behavioral type | **Active war + cooperation** | Passive + rare outbreak | **Total inertia** |

### Statistical Tests

| Test | F / U | p-value | Interpretation |
|------|-------|---------|---------------|
| ANOVA (Gini) | F = 160.19 | **p < 0.000001** | Highly significant |
| ANOVA (Cooperation) | F = 659.33 | **p < 0.000001** | Highly significant |

### Pairwise Comparisons (Cohen's d)

| Pair | Gini d | Coop d | Significant? |
|------|--------|--------|-------------|
| Gemini vs DeepSeek | **3.76** | **8.12** | Yes (massive) |
| Gemini vs Llama | **23.94** | **8.12** | Yes (extreme) |
| DeepSeek vs Llama | 0.46 | 0.32 | No (both passive) |

Effect sizes of d > 3 are extraordinary. The model choice is the dominant factor in determining emergent behavior.

### Three Distinct Behavioral Regimes

1. **Gemini FL — "Hobbesian War with Matthew Effect"**
   - Active engagement from round 1
   - ~45% attack, ~45% invest_other
   - Cooperation creates inequality (invest in the strongest)
   - 95% of runs produce a single hegemon
   - Rich emergent dynamics

2. **DeepSeek V3.2 — "Passive Stalemate with Rare Breakouts"**
   - 93% do_nothing
   - 90% of runs: perfect equality (no one does anything)
   - 10% of runs: rare attack cascade creates extreme inequality
   - Bimodal outcome distribution

3. **Llama 3.3 70B — "Total Paralysis"**
   - 100% do_nothing, 100% of runs
   - Zero variance, zero dynamics
   - Model fails to engage with the game mechanics at all

---

## Technical Notes

- **JSON retry fix**: Gemini FL sometimes outputs reasoning text without JSON. Added retry mechanism. Reduced fallback rate from ~30% to <1%.
- **Total fallbacks**: Minimal across all 60 runs.
- **Runtime**: Gemini ~3 min/run, DeepSeek ~4 min/run (after warmup), Llama ~3 min/run. Total: ~4.5 hours.
- **Cost**: ~$6-8 estimated for all 60 runs.
- **DeepSeek run 1 anomaly**: First DeepSeek run took ~50 min (API cold start), subsequent runs ~4 min each.

---

## Decision Implications

### Strong result for Architectures thesis
The architectural fingerprint is unmistakable. Cohen's d > 3 for Gemini vs others is an extraordinarily large effect. Same game, same prompt, completely different emergent structures.

### Problem for Origins thesis
**Llama 3.3 70B produces zero dynamics.** This is the model planned for Origins experiments on Snellius. Options:
1. **Use Gemini FL for Origins** (via OpenRouter, costs ~$93)
2. **Use a different open-weight model on Snellius** (e.g., Mistral 7B, Qwen 7B — need to test)
3. **Modify the prompt** to be more directive (e.g., "You MUST choose an action other than do_nothing")
4. **Run Arch Exp 2** first — framing might unlock Llama's behavior (cooperative/competitive framings)

### Recommendation
Run Arch Exp 2 (model × framing factorial) before deciding. If a "competitive" or "strategic" framing activates Llama 70B, we can use that framing for Origins. If not, fall back to Gemini FL or test other open-weight models.
