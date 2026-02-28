# Practical Experiment Plan
**Created**: 2026-02-16
**Last updated**: 2026-02-16 (end of day)
**Strategy**: Hybrid — Architectures as safe base, Origins phase transition in parallel
**Remaining sprints**: 10 (Feb 27 → Jul 3), meeting every 2 weeks

---

## Build status

### Code — DONE

| Module | File | Status | What it does |
|--------|------|--------|-------------|
| Game engine | `game/engine.py`, `game/spatial.py` | DONE (pre-existing) | Invest/arm/attack game, toroidal spatial field |
| LLM agent | `agents/llm_agent.py`, `agents/prompts.py` | DONE | OpenRouter API, 5 prompt framings |
| Sweep runner | `sweep.py` | DONE | Factorial/grid designs, target routing, auto-logging |
| Basic metrics | `analysis/metrics.py` | DONE | Gini, Palma, action stability, action distribution |
| Run-level metrics | `analysis/metrics.py` | DONE | cooperation_ratio, first_attack_round, retaliation_probability, coalition_stability |
| Extended metrics | `analysis/metrics.py` | DONE | Theil T, Atkinson index, per-round f_C timeseries, cross-run f_C variance |
| EWS | `analysis/ews.py` | DONE | Rolling variance/AC-1/skewness, Kendall τ, Binder cumulant, transition detection |
| Network analysis | `analysis/network.py` | DONE | Leiden communities, NMI, Elo ratings, steepness, Landau h', centrality, sliding windows |
| Statistical tests | `analysis/stats.py` | DONE | Two-way ANOVA, partial η², Bayes factors, ICC, dominance analysis, mixed-effects, power analysis |
| Run logger | `run_logger.py` | DONE | Auto-logs git hash, configs, results, decisions. Searchable master log. |
| Validation | `validate_sweep.py` | DONE | Convergence, consistency, effect sizes, Mann-Whitney U, plots |

### Code — NOT YET BUILT (lower priority)

| Module | Priority | When needed | Effort |
|--------|----------|-------------|--------|
| Trace analysis pipeline (`analysis/traces.py`) | MEDIUM | Sprint 6 (if Origins path) | 4-5 days |
| Prompt sensitivity (FormatSpread, PSS) | LOW | Sprint 6 (if Architectures path) | 1-2 days |
| RL baseline agent | LOW | Decision at Sprint 5 | 3-5 days |
| TIPMOC power-law fit | LOW | Only if EWS inconclusive | 3 hrs |

### Packages installed
numpy, scipy, pandas, matplotlib, seaborn, networkx, leidenalg, igraph, statsmodels

### Experiment configs — DONE

| YAML file | Experiment | Design | Conditions | Runs |
|-----------|-----------|--------|------------|------|
| `phase_transition_radius.yaml` | Origins 1a | 1D sweep | radius: 1→10 | 10 × 20 = 200 |
| `phase_transition_agents.yaml` | Origins 1b | 1D sweep | agents: 5→60 | 7 × 20 = 140 |
| `information_visibility_sweep.yaml` | Origins 1c | 2×2×2 factorial | hide_resources × reputation × history | 8 × 20 = 160 |
| `necessary_sufficient.yaml` | Origins 3 | 2×3 factorial | spatial × framing | 6 × 20 = 120 |
| `architectural_fingerprint.yaml` | Arch 1 | 1D sweep | 3 models | 3 × 20 = 60 |
| `prompt_framing_factorial.yaml` | Arch 2 | 3×5 factorial | model × framing | 15 × 20 = 300 |

All configs: 50 rounds, 20 reps per condition, 10 agents, zero-cost regime, spatial ON (r=2), invest_self OFF.

**Missing config**: Arch Exp 3 robustness (needs design after Exp 1+2 results).

---

## Exploratory runs completed (Sprint 2, 142 runs)

| Runs | Sweep | Key finding |
|------|-------|-------------|
| 001-002 | invest_self on/off (30 agents) | invest_self OFF necessary for dynamics |
| 003-022 | invest_other_cost (5 values × 3 reps) | High variance, no clean monotonic effect |
| 023 | Zero-cost baseline | Eliminates bankruptcy stalemate, pure war game |
| 024-038 | invest_other_return (5 values × 3 reps) | Cooperation flat at 2-4% regardless of return (Nova Micro) |
| 039-053 | attack_take_percent T (5 values × 3 reps) | **Phase transition T=20→T=10** (Gini 0.46→0.20), but behavior unchanged |
| 054-055 | Gemini Flash vs Nova Micro | Architecture + objective independently determine structure |
| 056-070 | arm_multiplier (5 values × 3 reps) | No effect — agents don't reason about multiplier |
| 071-085 | arm_duration (5 values × 3 reps) | Mild effect — short duration = "action tax" |
| 086-100 | Gemini Flash Lite T sweep (5 values × 3 reps) | **Architecture determines parameter sensitivity** |
| 101-109 | Initial distribution (3 types × 3 reps) | Equal most warlike, unequal/random high variance |
| 110-119 | Spatial radius sweep (4 conditions × 2 reps) | **invest_other 17%→72% with spatial. Phase transition r=2→r=3** |
| 120-125 | Action order (2 types × 3 reps) | Simultaneous = arms races, sequential = aggression |
| 126 | 30-agent spatial | Cooperation holds but Matthew Effect amplified |
| 127-134 | Information 2×2 factorial (30 agents) | **Resource visibility > history as cooperation driver** |
| 135-142 | Reputation 2×2 factorial (30 agents) | Reputation does NOT rescue cooperation when resources hidden |

### Key decisions from exploratory phase
1. **Zero-cost regime** as default — eliminates bankruptcy stalemate
2. **invest_self OFF** — forces social interaction
3. **Nova Micro** for bulk sweeps ($0.06/$0.25 per M tokens, 1.8s/round)
4. **Gemini Flash Lite** for targeted experiments (parameter-sensitive, cooperates more)
5. **Dropped theta (c/b) framing** — doesn't work for military actions
6. **Spatial ON by default** — creates richer dynamics

---

## Sprint plan (updated)

### Sprint 3: Feb 16 - Feb 27 ← CURRENT
**Theme**: Architectures experiments (OpenRouter) + Snellius setup
**Meeting deliverable (Feb 27)**: Arch Exp 1 results, Snellius access confirmed

**Code — DONE today:**
- [x] Build EWS module (rolling variance, AC-1, skewness, Kendall's τ, Binder cumulant)
- [x] Build network analysis module (Leiden, NMI, Elo, steepness, centrality)
- [x] Build statistical analysis module (ANOVA, η², Bayes factors, ICC, mixed-effects)
- [x] Add Theil T, Atkinson index, per-round f_C, cross-run f_C variance to metrics
- [x] Build run logger (traceability: git hash, config, results, decisions)
- [x] Integrate run logger + extended metrics into sweep.py
- [x] Update all experiment YAMLs to production settings (20 reps, 50 rounds)
- [x] Create information_visibility_sweep.yaml
- [x] Dual-backend support (OpenRouter + vLLM)
- [x] **DECIDED**: 3 models — Gemini FL, DeepSeek V3.2, Llama 3.3 70B (dropped Nova Micro)

**Experiments — this week:**
- [x] Run Arch Exp 1: architectural fingerprinting (60 runs) ← RUNNING NOW
- [ ] Run validate_sweep.py on Arch Exp 1 results
- [ ] Quick analysis: do the 3 models produce distinct signatures?

**Snellius:**
- [x] Snellius budget reactivation requested
- [ ] Confirm access, test vLLM with Llama 70B
- [ ] Create SLURM job script for sweep.py

**Literature — TODO:**
- [ ] Read Perc et al. (2017) — phase transition framing
- [ ] Read Akata et al. (2025) — factorial LLM experiment methodology

### Sprint 4: Mar 13 - Mar 27
**Theme**: Arch Exp 2 (OpenRouter) + Origins on Snellius

- [ ] Run Arch Exp 2: model × framing factorial (300 runs, ~$65, OpenRouter)
- [ ] Apply network analysis to Arch Exp 1 data
- [ ] Statistical analysis: ANOVA, η², dominance analysis on factorial data
- [ ] Run Origins Exp 1a: radius sweep (200 runs, Llama 70B on Snellius — free)
- [ ] Quick EWS analysis on radius sweep — is there a transition signal?
- [ ] Literature: Lorè & Heydari (2024), Traag et al. (2019)

### Sprint 5: Mar 27 - Apr 10
**Theme**: Remaining Origins experiments on Snellius

- [ ] Run Origins Exp 1b: agent count sweep (140 runs, Snellius)
- [ ] Run Origins Exp 1c: info visibility (160 runs, Snellius)
- [ ] Run Origins Exp 3: necessary/sufficient (120 runs, Snellius)
- [ ] EWS + Binder cumulant analysis — is the phase transition real?
- [ ] Run Arch Exp 3: robustness (design based on Exp 1+2 results)

### Sprint 6: Apr 10 - Apr 24
**Theme**: Deep analysis

- [ ] Full statistical analysis across all experiments
- [ ] Network evolution analysis
- [ ] Trace analysis if needed
- [ ] **DECISION POINT**: Origins or Architectures framing for thesis?

### Sprint 7: Apr 24 - May 8
**Theme**: All experiments complete, start writing

### Sprints 8-10: May 8 - Jul 3
**Theme**: Writing

**Cost strategy**: Arch experiments on OpenRouter (~$80 total). All Origins experiments on Snellius with Llama 3.3 70B (free). Limitation acknowledged: Origins results may be model-dependent; Arch Exp 1 demonstrates this.

---

## Model decision (UPDATED — dual-backend strategy)

### API models (OpenRouter — for Sprint 3 quick iteration)

| Model | Cost (in/out $/M) | Speed | Cooperation | Parameter sensitivity | JSON reliability |
|-------|-------------------|-------|-------------|----------------------|-----------------|
| Nova Micro (nitro) | $0.06/$0.25 | 1.8s/round | Very low (3%) | Flat — ignores params | Good |
| Gemini 2.5 Flash Lite | ~$0.15/$0.60 | 3-4s/round | Moderate (14-37%) | Responsive | Good |
| DeepSeek V3.2 | ~$0.14/$0.28 | 4-5s/round | Unknown at scale | Unknown | Unknown |

### Local models (Snellius vLLM — for Sprint 4+ bulk production)

| Model | Parameters | VRAM (FP16) | Fits 1× A100? | Notes |
|-------|-----------|-------------|---------------|-------|
| Llama 3.1 8B Instruct | 8B | ~16 GB | Yes | Good baseline, fast |
| Mistral 7B Instruct v0.3 | 7B | ~14 GB | Yes | Good JSON, fast |
| Qwen 2.5 7B Instruct | 7B | ~14 GB | Yes | Strong reasoning |
| Llama 3.1 70B Instruct | 70B | ~140 GB | No (2× A100) | Comparable to API models |
| Mixtral 8x7B Instruct | 47B | ~90 GB | No (2× A100) | MoE, good throughput |

### Strategy
- **Sprint 3 (now)**: Use OpenRouter API models for quick iteration
  - Gemini Flash Lite as primary for Origins (parameter-sensitive, shows transitions)
  - All 3 API models for Architectures experiments
- **Sprint 4+**: Switch to Snellius for production bulk runs
  - Open-weight models via vLLM — practically unlimited compute
  - Can run larger models (70B) as additional architecture comparison
  - ~640 SBU for all 1100 runs with 7B model (from 50k-100k allocation)

### Snellius access
- UvA can request 50k-100k SBU via "Direct institute contract" through supervisor
- SURF provides vLLM container: `/projects/2/managed_datasets/containers/vllm/vllm.sif`
- SLURM scripts: `github.com/SURF-ML/vllm-inference-slurm`
- A100 = 128 SBU/hr, H100 = 192 SBU/hr

### Codebase support
- `config/openrouter_config.yaml` — OpenRouter backend (default)
- `config/vllm_config.yaml` — vLLM backend (Snellius/local)
- Experiment YAMLs can override via `api_config: vllm_config.yaml` or `base_openrouter.base_url`
- Zero code changes needed to switch between backends

---

## Run budget (updated)

| Experiment | Model(s) | Backend | Runs | Est. cost | Est. wall time |
|------------|----------|---------|------|-----------|----------------|
| Arch Exp 1: fingerprinting | 3 models | OpenRouter | 60 | ~$15 | ~3hrs |
| Arch Exp 2: factorial | 3 models × 5 framings | OpenRouter | 300 | ~$65 | ~15hrs |
| Arch Exp 3: robustness | TBD | OpenRouter | ~120 | ~$18 | ~6hrs |
| Origins Exp 1a: radius | Llama 3.3 70B | Snellius | 200 | free | ~2hrs |
| Origins Exp 1b: agents | Llama 3.3 70B | Snellius | 140 | free | ~1.5hrs |
| Origins Exp 1c: info | Llama 3.3 70B | Snellius | 160 | free | ~1.5hrs |
| Origins Exp 3: nec/suf | Llama 3.3 70B | Snellius | 120 | free | ~1hr |
| **Total** | | | **~1100** | **~$98** | **~30hrs** |

Snellius runs zijn veel sneller (vLLM batching op A100, geen API latency).

Runs are unattended — wall time ≠ work time. Can run overnight/parallel.

---

## What to drop if time is short

**Cut first (nice-to-have):**
- RL baseline agent (3-5 days saved)
- TIPMOC parametric detection
- FormatSpread / PromptSensiScore
- BERTopic on traces

**Cut second (weakens but doesn't kill):**
- Binder cumulant (keep EWS as primary)
- Faithfulness validation (acknowledge limitation)
- Information visibility sweep (have exploratory data)
- Elo steepness + Landau's h'

**Never cut:**
- Theil T, Atkinson — trivial to compute, high value
- EWS on radius sweep — core of Origins
- Model × framing factorial — core of Architectures
- Network analysis basics (Leiden, NMI)
- Mixed-effects statistical model

---

## Decision log

| Date | Decision | Reasoning |
|------|----------|-----------|
| Feb 13 | Zero-cost regime as default | Eliminates bankruptcy stalemate (runs 023+) |
| Feb 13 | invest_self OFF | Forces social interaction, confirmed by run 001 stalemate |
| Feb 13 | Nova Micro for bulk sweeps | $0.06/$0.25, 1.8s/round, valid JSON |
| Feb 13 | Dropped theta framing | Doesn't work for military actions, switched to param sensitivity |
| Feb 16 | Hybrid strategy | Architectures as safe base, Origins in parallel |
| Feb 16 | 50 rounds, 20 reps per condition | 50 rounds for convergence, 20 reps for statistical power |
| Feb 16 | Model choice pending | Need to decide: Gemini FL as primary for Origins? |
| Feb 16 | Dual-backend support | Codebase now supports OpenRouter API + local vLLM (Snellius). base_url configurable per experiment. |
| Feb 16 | Snellius as bulk compute | Plan: OpenRouter for quick iteration (Sprint 3), Snellius for production bulk (Sprint 4+). UvA can get 50k-100k SBU. |
| Feb 16 | Llama 3.3 70B replaces Nova Micro | Nova Micro too rigid (3% coop, ignores params). Replaced with Llama 70B: open-weight, same model on Snellius later. 3 models: Gemini FL, DeepSeek V3.2, Llama 3.3 70B. |
| Feb 16 | Snellius accounts expired | All 3 accounts have expired CBA budgets. Reactivation requested. |
| Feb 16 | Origins on Snellius, Arch on OpenRouter | Origins experiments use Llama 70B on Snellius (free). Arch experiments use 3 models on OpenRouter (~$98). Acknowledge model-dependency as limitation. |
| Feb 16 | Arch Exp 2 reduced to 10 reps | Arch is overview/baseline for Origins. 10 reps sufficient for effect detection. Saves ~$29. |
| Feb 16 | Snellius SBUs approved | Budget reactivated. Waiting on Meta model approval for Llama 3.3 70B access. |
| Feb 16 | DeepSeek ~50 min/run (cold start) | First run slow, subsequent ~4 min. Arch Exp 1 completed in 4.5 hours total. |
| Feb 16 | **Arch Exp 1 COMPLETE** | 60/60 runs. Gemini=war+cooperation, DeepSeek=passive stalemate, Llama=total inertia. ANOVA p<0.000001, Cohen's d>3. |
| Feb 16 | **Llama 70B problem for Origins** | 100% do_nothing in all 20 runs. Cannot be used for Origins without prompt intervention. Arch Exp 2 will test if framing unlocks behavior. |
| Feb 16 | Arch Exp 2 started | 150 runs (3 models × 5 framings × 10 reps). Critical: does framing activate Llama/DeepSeek? |
| Feb 17 | **Arch Exp 1 data INVALID** | API key hit spending limit during DeepSeek rep2. DeepSeek had only 2 real runs (rest fallback). Llama had 0 real runs (all fallback). "Three behavioral regimes" finding was artifact of API failures. |
| Feb 17 | Arch Exp 2 failed to start | OpenRouter key limit exceeded. 0/150 runs completed. |
| Feb 17 | **Arch Exp 1 rerun (partial)** | Reran DeepSeek + Llama. DeepSeek: 9/20 real runs obtained. Llama: 4/20 real runs (connection errors). |
| Feb 17 | **CORRECTED: All 3 models produce war** | DeepSeek real data: Gini ~0.83, attack-dominant, aggressive. Llama real data: Gini ~0.76, war + cooperation, hegemons. NOT passive/inert — that was fallback artifacts. |
| Feb 17 | OpenRouter too unstable for Llama 70B | 4883 connection errors during Llama run. Stopped experiment. |
| Feb 17 | **Reconsidering model choice for Snellius** | Llama 3.3 70B ranked ~150 on LM Arena. Qwen3-30B-A3B (MoE, 1× A100, Apache 2.0) or Qwen3-32B (dense, 1× A100) are stronger and cheaper alternatives. No Meta approval needed. |
| Feb 17 | **Runs stopped, new plan needed** | Have: 20 Gemini + 9 DeepSeek + 4 Llama valid runs. OpenRouter unreliable. Pivot to Snellius with open-weight models. |
| Feb 17 | **CoT-before-action JSON format** | Changed JSON output from {action, target, reasoning} to {reasoning, action, target}. Reasoning field now comes first so the model thinks step-by-step before committing to an action (Wei et al. 2022, Kojima et al. 2022). Autoregressive generation means field order matters — previous format made reasoning a post-hoc rationalization. |
| Feb 17 | **4 new models for Snellius** | Chosen for high Elo + architectural diversity. (1) Qwen3-235B-A22B — large MoE, 2-4×A100. (2) MiMo-V2-Flash — large MoE (Xiaomi), 4×A100. (3) Qwen3-30B-A3B — small MoE, 1×A100. (4) QwQ-32B — dense reasoning model, 1×A100. All Apache 2.0/MIT, no HF approval needed. |
