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

### Fri Feb 28
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

---

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

---

## Notes
- 75K extra SBU goedgekeurd — compute geen bottleneck meer
- Alle Gemma 2 resultaten zijn exploratory — moeten gevalideerd worden op Qwen
- Random walk nog actief — utility movement komt in Phase 2
