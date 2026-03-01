# Sprint 3: Feb 27 - Mar 14
**Phase**: Model Transition + Qwen Characterisation
**Meeting**: Mar 14 at 14:00 with Debraj

---

## Sprint Goals

### Phase 1: Baselines op Qwen (dit weekend + week 1)
- [ ] Deploy Qwen 3.5-27B (dense) op Snellius — validatie test
- [ ] Fingerprint: 20 neutral runs → baseline gedrag
- [ ] K-level reasoning sweep: L0/L1/L2/L3 × 5 reps = 20 runs
- [ ] Radius sweep: 4-6 radii × 3 reps × L0 = 12-18 runs
- [ ] Invest_self ON baseline: vergelijking ON vs OFF (2×5 reps)
- [ ] Analyseer stabilisatie (nieuw!) + vergelijk met Gemma 2 resultaten

### Phase 2: Nieuwe mechaniek (week 2-3)
- [ ] Utility-based movement implementeren (Schelling-type)
- [ ] K-level × radius factorial op beste params uit Phase 1

### Analysis: Embedding Time Series (Debraj suggestie, week 2)
- [ ] Script: lees _traces.json → concateneer prompt+response per agent-round → embed met text-embedding-3-small → T×D matrix
- [ ] Rolling statistics: mean embedding (semantic center of mass), covariance (diversity)
- [ ] UMAP/PCA plot van embedding trajectories, gekleurd per reasoning level
- [ ] Doel: visueel + statistisch bewijs dat L0/L1/L2/L3 distinct reasoning regimes zijn
- Data: al beschikbaar in _traces.json (geen logging changes nodig)

### Infrastructure (doorlopend)
- [x] TextGrad prompt optimization → RUNNING (job 20151816, instruction clarity focus)
  - Evaluator: Opus 4.6 via OpenRouter, focus op instruction clarity (niet reasoning depth)
  - Resultaat is diagnostic — prompts worden handmatig herzien, niet automatisch toegepast
- [x] Reasoning model traces: Qwen's native <think> CoT wordt gelogd in _traces.json
- [x] Ingroup/outgroup metrics geïntegreerd (network.py)
- [x] Stabilisatiemetrics geïntegreerd (metrics.py)

---

## Deliverables voor Debraj (Mar 14)
- Qwen 3.5 baseline: Gini, coop%, action dist, stabilisatie
- K-level vergelijking: Qwen vs Gemma 2 behavioral fingerprints
- Phase transition plot (Gini vs radius) op Qwen
- **Embedding time series**: UMAP/PCA plot van reasoning trajectories per level
- Plan voor utility-based movement
- TextGrad diagnostic assessment

---

## Daily Log

### Thu Feb 27 — Meeting + Infrastructure
- Meeting met Debraj: "very publishable" feedback
- Beide richtingen goedgekeurd: reasoning depth (ch) + credible commitment (ch)
- Beslissingen: Qwen 3.5 only, reasoning traces, utility movement, invest_self ON, TextGrad
- Qwen 3.5-27B (dense) download gestart op Snellius
- Test script gemaakt (test_qwen35.py) — 10 diverse scenario prompts
- vLLM compatibiliteit issue: 0.10.1 kent Qwen3.5 niet → proberen met 0.13.0
- Container build job submitted als fallback
- Switch van MoE (35B-A3B) naar dense (27B) — alle 27B params actief
- Network analysis + Leiden + ingroup/outgroup metrics geïntegreerd in pipeline
- Stabilisatiemetrics geïmplementeerd en geïntegreerd in sweep manifest
- production_design.md gearchiveerd (verouderd door Qwen switch)
- Roadmap + sprint 3 aangemaakt

### Fri Feb 28 (continued) + Sat Mar 1
- Qwen 3.5-27B test job succesvol: 8/10 scenarios pass, 2 fixed (max_tokens 8000→16000)
- Throughput benchmark: sequential 1417s vs concurrent 244s = **5.8x speedup** (234 tok/s)
- L3 prompt herschreven — nu echte recursieve reasoning ("they think I think")
- TextGrad pipeline gebouwd en gesubmit:
  - Refocus: instruction clarity only (geen reasoning depth scoring → geen confound)
  - Eval model: Opus 4.6 via OpenRouter
  - Job 20151816 draait — Stage 1 gradients tonen concrete clarity issues
- Debraj Slack feedback (na meeting):
  1. **Embedding time series**: prompt+response → `text-embedding-3-small` → T×D matrix per run.
     Rolling stats, UMAP/PCA trajectories. Clustering = bewijs voor distinct reasoning regimes.
     **Logging check: alles al aanwezig in _traces.json (prompt + response per agent-round)**
  2. **TextGrad prompt uncertainty**: run meerdere keren → distributie van locally optimal prompts →
     evalueer of ze convergeren naar zelfde emergent outcomes. Validatie sprint.
- design_questions.md aangemaakt (% vs absolute invests, coalition visibility, cost structure)
- ideas.txt opgeschoond (121→50 regels)

---

### Fri Feb 28 (evening)
- **Persistent agent memory implemented** (`src/agents/memory.py`)
  - Sliding window own action history + per-neighbor observation summaries
  - Information is local: only see what's in your radius, incoming actions always known
  - Stale entries persist with "last seen round X" marker
  - Backwards compatible: `memory.enabled: false` → old god-view neighbor profiles
- Tested with scripted 5-round simulation (test_memory.py) — spatial isolation works correctly
- Tested with real LLM calls (test_memory_integration.py) — 3 agents, 3 rounds, gemini-flash-lite
- Fixed 3 bugs: off-by-one in seen count, combat outcomes leaking to defender's action log, resource "0" for never-seen agents
- Committed: `3f316f9`
- Memory comparison experiment created: `experiments/memory_comparison.yaml`
  - Qwen 3.5-27B, 10 agents, 20 rounds, L1 reasoning, memory on vs off, 3 reps
  - Submit script: `snellius/submit_memory_comparison.sh`

## Decisions This Sprint
| Date | Decision | Reasoning |
|------|----------|-----------|
| Feb 27 | Qwen 3.5-27B (dense) over 35B-A3B (MoE) | Dense = alle 27B params actief, betere vLLM compat, geen MoE routing issues |
| Feb 27 | Lazy imports voor leidenalg | Voorkomt crash op machines zonder leidenalg (lokaal dev) |
| Feb 27 | Stabilisatie via rolling std | Eenvoudig, interpreteerbaar. window=10, threshold=0.02 voor Gini |
| Feb 27 | TextGrad: Claude evalueert Qwen's `<think>` blocks | Qwen mag niet zijn eigen output evalueren. OpenRouter Claude Sonnet als evaluator. Beoordeelt interne CoT, niet JSON reasoning field. |
| Feb 27 | TextGrad twee stages: base prompt + per-level reasoning | Stage 1: shared instructional text (objective, actions, constraints). Stage 2: L0-L3 reasoning blocks apart. L0 start als empty string. |
| Feb 27 | TextGrad Option B (orig vs optimized vergelijking) → robustness sprint | Niet nu, maar als robustness check in validatie sprint |
| Feb 28 | TextGrad evalueert instruction clarity, NIET reasoning depth | Scoring van "juiste" reasoning output = confound. Evaluator checkt alleen of prompt helder is. |
| Feb 28 | Opus 4.6 als TextGrad evaluator (niet Sonnet) | Beter in beoordelen subtiele instructie-onduidelijkheden. Meerkosten ~$1. |
| Feb 28 | Embedding time series analyse (Debraj suggestie) | prompt+response → text-embedding-3-small → UMAP/PCA. Geen extra logging nodig — _traces.json bevat alles. |
| Feb 28 | Persistent agent memory (local observations) | Replace god-view neighbor profiles with accumulated local observations. Agents only know what they see/experience. Potential methodological contribution (no game-theory LLM paper has systematic memory architecture). |
| Feb 28 | Unified engine+prompt params (%-based) | Engine rewritten to match prompt exactly. Same param names: `invest_self_cost_pct`, `invest_other_return_pct`, `arm_cost_pct`, `arm_decay`, etc. No more dual param sets. All costs/returns are % of actor's resources. |
| Feb 28 | Additive arm bonus + ×0.5 decay | Engine now matches prompt: arm_self spends 10% → that amount becomes additive combat bonus. strength = resources + arm_bonus. Bonus halves each round. Old: multiplicative (resources × multiplier) with fixed duration. |
| Feb 28 | invest_other_return_pct (not mult) | Changed from multiplier to direct %: target gets invest_other_return_pct% of your resources. Cleaner, sweepable. Default 15%. |
| Feb 28 | arm_other_cost_pct separate from arm_cost_pct | Split arming cost for self vs other — can now sweep independently. Default both 10%. |
| Feb 28 | Two-stage screening sweeps (final) | Stage 1: 9 OAT sweeps × L1+L3 × 2 reps = 116 runs. invest_self OFF default. 3 focus metrics: cooperation ratio, Gini, E-I index. Stage 2: factorial on top 2-3 params at production scale. |
| Feb 28 | invest_self OFF default in param sweeps | Even +2% net gain causes 100% invest_self in L1 runs. Must be OFF. Tested separately in invest_self toggle sweep. |
| Feb 28 | Removed 0-cost sweep values | 0-cost arming/conflict = no dilemma. arm [0,5,10,20]→[5,10,20], conflict [0,5,10,20]→[2,5,10,20]. |
| Feb 28 | Memory comparison runs cancelled | Old engine params (absolute, not %), agents did 99% do_nothing. Wasted SBU. Memory sweep included in nightrun with correct params. |
| Mar 1 | Memory default ON (was OFF) | Without memory, do_nothing is Nash equilibrium — no reciprocity possible. invest_other costs 10%, returns nothing to investor. Memory enables learned reciprocity. |
| Mar 1 | God-view neighbor profiles removed | Memory OFF now means NO history (only current state). Old system leaked omniscient info: engine told agents what every neighbor did. Inconsistent with local observation design. |
| Mar 1 | vLLM reasoning field fix | vLLM --reasoning-parser puts thinking in `msg.reasoning`, not `msg.reasoning_content`. Old code checked wrong attr → thinking traces lost (4000+ tokens generated but not saved). |
| Mar 1 | Wall time 4h→8h | L1 ~37min/run + L3 ~67min/run. 8 runs/task = ~7h worst case. 4h was too short. |
| Mar 1 | Early stopping: Two-Phase Adaptive (D+C) | Lee et al. (2015) rolling-window + patience-based. Gini+entropy must both stabilise for 5 rounds after min_rounds=15. No LLM paper uses convergence detection → methodological contribution. |
| Mar 1 | L3 rerun with 20 rounds | 10 rounds te kort voor L3 dynamica. 20 rondes met 5h wall time. Early stopping nog niet actief (eerst valideren). |
| Mar 1 | RQ updated: three Hobbesian conditions | Three IVs = mechanism design's three formal inputs (exact). Hobbes's three causes of conflict as narrative frame (with caveats on info→diffidence). See roadmap. |
| Mar 1 | Publishable checklist rewritten for AAMAS | OCAR story structure, Kuusela's patterns, 8-page budget, declarative section titles, 3 focus metrics, dual theoretical framework (MD + Hobbes). |

---

### Sat Mar 1 — Nightrun Debugging + Theoretical Grounding

**Nightrun v2 analysis** (memory OFF, 13/116 L1 runs complete):
- ALL L1 runs: 99-100% `do_nothing`, Gini=0.000
- Not a fallback/parse error — model genuinely chooses do_nothing
- Thinking traces confirm: model calculates EV correctly, do_nothing dominates
  - invest_other: -2.5 (costs 10%, returns nothing to investor)
  - attack: -2.5 expected (50/50 coinflip at equal resources minus conflict cost)
  - do_nothing: 0.0 → rational choice
- Root cause: without memory, no reciprocity possible → cooperation is irrational
- `reasoning_content` attr was None because vLLM uses `reasoning` (not `reasoning_content`)
  - Model generates 4000+ thinking tokens but they weren't saved
  - 48-char response, 4262 completion tokens, 127s latency

**Three fixes applied** (synced to Snellius):
1. `src/agents/llm_agent.py`: memory default `True` (was `False`)
2. `src/agents/prompts.py`: removed god-view fallback (memory OFF = no history, not omniscient profiles)
3. `src/agents/llm_agent.py`: `getattr(msg, 'reasoning_content', None) or getattr(msg, 'reasoning', None)`

**Nightrun v2 cancelled**, data archived to `data/runs/archive_v2_nomemory/`

**Nightrun v3 submitted** (jobs 20197381-20197397):
- Same 9 sweeps, 116 runs, 15 array tasks
- Memory ON by default, god-view removed, reasoning traces saved
- Wall time: 8h (was 4h)
- Expected completion: ~morning Mar 1

**Theoretical grounding research** (4 research agents):
- Hobbes's three causes of conflict map to our three IVs (competition→reasoning, diffidence→information, lack of common power→communication)
- Mechanism design's three inputs provide exact formal mapping (solution concept, type space, message space)
- Habermas, Turner, Simmel provide sociological grounding
- RQ updated to reflect three-IV Hobbesian framing
- Missing canonical refs identified for Zotero (Binmore, Ostrom, Crawford & Sobel, etc.)
- Publishable checklist completely rewritten for AAMAS with OCAR structure + Debraj's patterns

### Fri Feb 28 — Engine Rewrite + Nightrun Design
- **Engine rewrite: unified params + additive arms + decay**
  - Discovered prompt-engine mismatch: prompt described %-based additive arms with decay, engine used absolute multiplicative with fixed duration
  - Engine completely rewritten to match prompt. Single set of param names: `invest_self_cost_pct`, `invest_other_return_mult`, `arm_cost_pct`, `arm_decay`, etc.
  - `GameState.arm_bonuses: Dict[str, float]` replaces `active_arms: Dict[str, int]` + `arm_coalitions`
  - Combat: `strength = resources + arm_bonus` (additive). Arm bonus decays ×0.5/round.
  - invest_other: target gets cost × return_mult (1.5 default) → 15% of investor's resources. More rewarding to target than invest_self is to actor.
  - Test: `test_percentage_economy.py` — 10 tests pass (invest, arm, decay, stacking, combat, observation)
  - `game_params.yaml` + `main.py` updated to unified params
- **Memory clarity eval**: Fixed deployment issues (model name, Py3.9, API key, reasoning traces via model_extra). Job 20186098 shows 8-10/10 on memory parsing.
- **Night run Stage 1 v1** (9 OAT sweeps, 132 runs) — CANCELLED: invest_self ON caused 100% invest_self in L1, 0-cost values were nonsensical
- **Night run Stage 1 v2** (9 OAT sweeps, 116 runs, ~12K SBU):
  - Conflict theta: conflict_cost_pct [2,5,10,20] + attack_take_pct [20,40,60,80]
  - Arming theta: arm_cost_pct (self) [5,10,20] + arm_other_cost_pct [5,10,20]
  - Cooperation theta: invest_other_return_pct [10,15,25] + invest_other_cost_pct [5,10,20]
  - Spatial: interaction_radius [1,2,3]
  - Toggles: invest_self [on,off] + memory [on,off]
  - All × L1+L3 × 2 reps. invest_self OFF default. Focus metrics: cooperation ratio, Gini, E-I index.
  - Submit: `snellius/submit_qwen_nightrun.sh` (15 array tasks)
- **Memory comparison cancelled** — ran with old absolute params, 99% do_nothing. Memory now tested in nightrun with correct % params.
- **Old files archived** — 16 files (Gemma 2 configs, OpenRouter scripts, stale experiments) moved to `experiments/archive/` and `snellius/archive/`

## Snellius Jobs
| Job ID | Description | Status |
|--------|-------------|--------|
| 20136320 | Test Qwen3.5-27B + vllm-0.13.0 | ❌ FAILED (old model path) |
| 20136324 | Build latest vLLM container | ✅ DONE (vllm-0.16.0) |
| 20137660 | Test Qwen3.5-27B + vllm-latest | ❌ FAILED — vLLM 0.16.0 doesn't support Qwen3_5ForConditionalGeneration |
| 20139674 | Build vLLM nightly container | ✅ DONE (vllm-nightly.sif v0.16.1rc1) |
| 20149449 | Test Qwen 3.5-27B (10 scenarios) | ✅ DONE — 8/10 pass, 2 fixed |
| 20149957 | Throughput + L3 prompt test | ✅ DONE — 5.8x speedup, L3 recursive reasoning confirmed |
| 20151816 | TextGrad instruction clarity optimization | 🔄 RUNNING — Stage 1 Epoch 2/3 |
| 20179410 | Memory comparison: on vs off × 3 reps (Qwen 3.5-27B, L1) | ❌ CANCELLED — old engine params, 99% do_nothing |
| 20186098 | Memory clarity eval (with thinking traces) | 🔄 RUNNING |
| 20194059-88 | Nightrun v1 (9 sweeps, 132 runs) | ❌ CANCELLED — invest_self ON, 0-cost values |
| 20195643-667 | Nightrun v2 (memory OFF, no reasoning traces) | ❌ CANCELLED — do_nothing equilibrium, reasoning traces lost |
| 20197381 | Nightrun v3: conflict_cost_pct [2,5,10,20] | 🔄 RUNNING (8h, memory ON) |
| 20197382 | Nightrun v3: attack_take_pct [20,40,60,80] | 🔄 RUNNING |
| 20197387 | Nightrun v3: arm_cost_pct (self) [5,10,20] | 🔄 RUNNING |
| 20197388 | Nightrun v3: arm_other_cost_pct [5,10,20] | 🔄 RUNNING |
| 20197389 | Nightrun v3: invest_other_return_pct [10,15,25] | 🔄 RUNNING |
| 20197390 | Nightrun v3: invest_other_cost_pct [5,10,20] | 🔄 RUNNING |
| 20197395 | Nightrun v3: interaction_radius [1,2,3] | 🔄 RUNNING |
| 20197396 | Nightrun v3: invest_self [on,off] | 🔄 RUNNING |
| 20197397 | Nightrun v3: memory [on,off] | 🔄 RUNNING |
| 20201444 | invest_return sweep (L1+L3 × 2 reps) | ⚠️ PARTIAL — L1 saved, L3 time-limited |
| 20203534 | L3 rerun invest_return (20 rounds, 5h) | 🔄 RUNNING |

---

### Sat Mar 1 (continued) — invest_return analysis + Early Stopping

**invest_return sweep analysis** (job 20201444):
- L1 runs (both reps): 100% do_nothing, Gini=0.000. Confirmed: without invest_self, do_nothing is strictly dominant for L1.
- L3 run: attacks from round 1, arming from round 4, Gini rising to 0.108. **Hobbesian Trap confirmed**: L3 agents calculate same negative EV as L1 but attack preemptively, reasoning about others' potential aggression.
- L3 run crashed at 2h time limit (round 7/10). Traces lost (save_results not reached).
- Logging fix: vLLM `--reasoning-parser qwen3` puts thinking in `thinking` field, not JSON body. Fixed in main.py.

**L3 rerun submitted** (job 20203534):
- Config: `experiments/qwen_l3_rerun_invest_return.yaml` — 20 rounds, 2 reps, L3 only
- 5h time limit (was 2h). Includes logging fix so traces will show correctly.

**Early stopping implemented** (Two-Phase Adaptive, Option D + C):
- Literature review: Lee et al. (2015, JASSS) rolling-window ABM convergence, Gelman & Rubin (1992) R-hat. No LLM multi-agent paper uses formal convergence detection — methodological contribution.
- Design: Phase 1 (exploration, min_rounds=15), Phase 2 (convergence: Gini range + entropy range < threshold for patience=5 rounds)
- Files modified: `src/analysis/metrics.py` (new `check_early_stopping()`), `src/main.py` (loop integration), `src/sweep.py` (manifest fields)
- Backwards compatible: no config = disabled. Config via `base_params.early_stopping` in experiment YAML.
- Design doc: `notes/design_early_stopping.md`

---

## Notes
- 75K extra SBU goedgekeurd — compute geen bottleneck meer
- Alle Gemma 2 resultaten zijn exploratory — moeten gevalideerd worden op Qwen
- Random walk nog actief — utility movement komt in Phase 2
- Sequential action_order runs ~30x slower (no parallel LLM calls) — may need more time
