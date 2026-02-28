# Thesis Quality Checklist: Publishable Standard

## Context
MSc Computational Science thesis on reasoning depth × game structure → emergent social structure in LLM multi-agent systems. This checklist ensures every experiment, analysis, and writing decision meets publishable quality standards.

---

## 1. Experimental Design

### Reproducibility (non-negotiable)
- [ ] Every run has a unique, logged random seed
- [ ] Model version, API endpoint, and exact date logged per run
- [ ] Temperature fixed and documented (justify choice)
- [ ] Full prompt text versioned in repo — any change = new version number
- [ ] Hardware specs logged (GPU type, vLLM version, batch size)
- [ ] Complete config file saved per run (all parameters, not just swept ones)
- [ ] Code committed to git before each batch of runs — tag with experiment ID

### Statistical Power
- [ ] Minimum 20 runs per condition (more for noisy conditions)
- [ ] Power analysis conducted: pilot 5-10 runs → estimate ICC and effect sizes → simulate power (simr in R) targeting 80% power at d ≥ 0.5
- [ ] If underpowered, acknowledge explicitly and report effect sizes + confidence intervals anyway
- [ ] Document finite-size effects: at N=30, fluctuations scale as O(1/√30) ≈ 18%

### Controls
- [ ] Every manipulation has a well-defined control condition
- [ ] Reasoning levels (L0-L3) operationalized with exact prompt text, not just descriptions
- [ ] Order effects controlled: randomize option presentation in prompts
- [ ] No authority cues or sycophancy-inducing language in prompts (Sharma et al., 2023)
- [ ] Base parameters create genuine dilemmas (arm_cost > 0, verified via sweep)

---

## 2. Statistical Analysis

### Model Specification
- [ ] Mixed-effects models with proper nesting: `Outcome ~ Condition * GameParam + Round + Round² + (1|RunID)`
- [ ] Justify random effects structure (RunID as clustering variable — the simulation run is the unit of analysis, not the individual agent decision)
- [ ] Report ICC to quantify within-run clustering
- [ ] Use Satterthwaite approximation for degrees of freedom (lmerTest)
- [ ] Check and report model assumptions: residual normality, homoscedasticity, random effects distribution

### Effect Sizes and Uncertainty (non-negotiable)
- [ ] Report Cohen's d for all pairwise comparisons
- [ ] Report partial η² for omnibus tests
- [ ] Report 95% confidence intervals for all key estimates
- [ ] Report Bayes factors (Jeffreys-Zellner-Siow prior) for key comparisons — following Akata et al. (2025, Nature Human Behaviour)
- [ ] Never report only p-values. Effect size + CI is the minimum

### Multiple Comparisons
- [ ] Correct for multiple comparisons (Bonferroni or FDR as appropriate)
- [ ] Pre-register primary outcome variable (cooperation rate f_C) to distinguish confirmatory from exploratory
- [ ] Clearly label exploratory analyses as such

### Robustness
- [ ] Sensitivity analysis: do conclusions change with different model specifications?
- [ ] Report results with and without outlier runs (define outlier criterion a priori)
- [ ] If using prompt variants: report FormatSpread (Sclar et al., 2024) or PromptSensiScore (Zhuo et al., 2024)

---

## 3. Reasoning Trace Analysis

### Faithfulness (non-negotiable caveat)
- [ ] State explicitly in methods: "Reasoning traces are treated as behavioral data, not as mechanistic explanations of model computation"
- [ ] Cite the faithfulness literature: Turpin et al. (2023), Lanham et al. (2023), Chen et al. (2025)
- [ ] Cite the counter-evidence: Baker et al./METR (2025) — CoT-as-computation in tasks requiring step-by-step reasoning shows higher faithfulness
- [ ] Implement at least one faithfulness validation on a subset:
  - Option A (lightweight): Lanham et al.'s early-answering test — truncate CoT, check if decisions change
  - Option B (stronger): Thought Anchors resampling (Bogdan et al., 2025) — resample CoT 10-20× from opponent-modeling sentence onward, measure action distribution shift
- [ ] Frame the prompt as manipulating computational depth, not just semantic content (supported by Pfau et al., 2024 — filler tokens improve performance through additional forward passes)

### Coding
- [ ] Use LACA framework (Chew et al., 2023): codebook → prompt calibration → LLM coding with justifications → reliability
- [ ] Report inter-rater reliability with Gwet's AC1 (not just Cohen's kappa — AC1 is more robust to prevalence effects)
- [ ] Human-verify 10-20% of coded traces
- [ ] Triangulate: cross-reference stated reasoning with actual choices. Report concordance rate

### Trace Metrics
- [ ] Theory-of-mind depth coded per trace (L0-L3 following Jia et al., 2025)
- [ ] Track whether prompted reasoning level matches observed reasoning level (they may diverge)
- [ ] Quantify: % agents mentioning future payoffs, opponent intentions, coalition dynamics pre- vs. post-transition
- [ ] Use BERTopic or embedding similarity for emergent themes (not just predefined codes)

---

## 4. Phase Transition Detection (if pursuing Origins angle)

### Primary Detection
- [ ] Rolling-window EWS: variance, lag-1 autocorrelation, skewness over ~10-round windows
- [ ] Trend significance: Kendall's τ > 0.4, p < 0.05
- [ ] Gaussian kernel smoothing for detrending
- [ ] Report EWS for each individual run, not just aggregated

### Validation
- [ ] Variance peak across parameter sweep (susceptibility analogue)
- [ ] If multiple agent counts: Binder cumulant crossing
- [ ] TIPMOC for parametric detection of power-law divergence (arXiv:2602.10817)

### What Counts as Evidence
- [ ] Sharp transition = strong claim. Define threshold: coefficient of variation of critical point < X across replications
- [ ] Smooth crossover = weaker but valid claim. Report crossover region width
- [ ] No transition = also a finding. Report it honestly

---

## 5. Metrics (computed consistently across all experiments)

### Per-run, per-round
- [ ] Cooperation rate f_C(t) — primary outcome
- [ ] Gini coefficient — resource inequality
- [ ] Pre-emptive attack frequency — Hobbesian metric (attacks not preceded by attack from target)
- [ ] First-attack timing

### Per-run, per-window (5-round sliding windows)
- [ ] Coalition structure via Leiden algorithm (sweep γ ∈ {0.5, 0.8, 1.0, 1.5, 2.0})
- [ ] Coalition stability: NMI between consecutive partitions
- [ ] Network reciprocity, density, clustering coefficient

### Per-run, aggregate
- [ ] Elo steepness (hierarchy metric)
- [ ] Theil T index (decomposable inequality)
- [ ] Final cooperation rate (last 10 rounds, to capture equilibrium)

### Reporting
- [ ] All metrics defined precisely in methods section with formulas
- [ ] Each metric justified with citation
- [ ] Report distributions, not just means — boxplots or violin plots per condition

---

## 6. Figures and Visualizations

### Standards
- [ ] Every figure interpretable without reading the caption in detail
- [ ] Colorblind-safe palette (viridis or similar)
- [ ] Error bars or shaded confidence bands on all time series
- [ ] Individual run trajectories visible (transparent lines) behind condition means
- [ ] Font size ≥ 8pt in all figures (including axis labels)
- [ ] Vector format (PDF/SVG) for all plots, not rasterized

### Key Figures to Include
- [ ] Cooperation rate over rounds, per condition (the "hero figure")
- [ ] Parameter sweep with variance peak (if doing phase transition)
- [ ] Radar chart or heatmap: metric profiles per reasoning level
- [ ] Interaction plot: reasoning level × game parameter (showing the non-monotonic pattern)
- [ ] Example reasoning traces (one per level) — anonymized/shortened
- [ ] Network snapshots at key timepoints showing coalition structure

---

## 7. Writing

### Structure
- [ ] Introduction: Hobbesian Trap framing → gap (nobody studies reasoning depth × emergent structure) → contribution
- [ ] Related work: Position clearly against K-Level Reasoning (Zhang et al., 2024), GTBench (Duan et al., 2024), Lorè & Heydari (2024), and Kuusela & Roy (2024)
- [ ] Methods: Sufficient detail for replication. Include full prompt texts in appendix
- [ ] Results: Separate confirmatory (pre-registered) from exploratory findings
- [ ] Discussion: Explicitly state limitations. Don't oversell

### Claims Calibration
- [ ] Match claim strength to evidence strength:
  - Strong evidence (effect size + statistical significance + robustness) → "We find that..."
  - Moderate evidence (significant but not robust, or robust but small effect) → "Our results suggest..."
  - Weak evidence (trends, exploratory) → "We observe preliminary evidence that..."
- [ ] Never claim causality from prompt → behavior without the faithfulness caveat
- [ ] Frame reasoning depth manipulation as: "prompts that elicit different levels of deliberation" not "we made agents think deeper"

### Novelty Claims (be precise)
- [ ] Existing: CoT/K-level reasoning affects individual game performance (GTBench, K-R, TMGBench, Jia et al.)
- [ ] Existing: LLMs show different strategic behavior under different framings (Lorè & Heydari, 2024)
- [ ] Existing: Higher-order reasoning reinforces Hobbesian Trap in 2-agent RL (Kuusela & Roy, 2024)
- [ ] **Novel: Reasoning depth produces qualitatively different emergent social structures (not just performance differences) in multi-agent systems**
- [ ] **Novel: The effect is non-monotonic and conditional on game structure (interaction effect)**
- [ ] **Novel: Extension of Hobbesian Trap framework from 2-agent RL to 30-agent LLM systems**

### Limitations Section (include all of these)
- [ ] CoT faithfulness — traces are behavioral data, not ground truth on model cognition
- [ ] Single model (Gemma 2 27B) — generalization to other architectures is future work
- [ ] Finite-size effects at N=30
- [ ] Prompt sensitivity — results may vary with semantically equivalent reformulations
- [ ] LLM stochasticity from hardware (up to 9%, arXiv:2506.09501)
- [ ] Complete information assumption — real social systems have partial observability

---

## 8. Code and Data Management

### Repository
- [ ] Clean, documented codebase with README
- [ ] Requirements file with pinned versions
- [ ] Scripts to reproduce every figure from raw data
- [ ] Raw data preserved (all run logs, traces, configs)

### Logging (per run)
- [ ] Full action history (agent × round matrix)
- [ ] Resource trajectories (agent × round)
- [ ] Reasoning traces (JSON: reasoning, beliefs, strategy, cooperation_intention, action)
- [ ] Run metadata (seed, config, model version, timestamp, duration)
- [ ] Any errors or API failures

---

## 9. Key Literature to Cite

### Reasoning Depth in Strategic Settings
- Zhang et al. (2024/2025), K-Level Reasoning — NAACL 2025
- Jia et al. (2025), arXiv:2502.20432 — CoT not universally effective for strategic reasoning
- Duan et al. (2024), GTBench — NeurIPS 2024
- Pfau et al. (2024), "Let's Think Dot by Dot" — computational depth matters independent of content

### CoT Faithfulness & Interpretation
- Turpin et al. (2023), NeurIPS — unfaithful explanations
- Lanham et al. (2023), Anthropic — measuring faithfulness
- Chen et al. (2025), Anthropic — reasoning models unfaithfulness
- Baker et al./METR (2025) — CoT-as-computation vs rationalization
- Bogdan et al. (2025), "Thought Anchors", arXiv:2506.19143 — sentence-level causal analysis
- Bogdan et al. (2025), "Thought Branches", arXiv:2510.27484 — resampling for causal claims

### LLM Game Theory
- Akata et al. (2025), Nature Human Behaviour — LLMs in repeated games, SCoT
- Lorè & Heydari (2024), Scientific Reports — framing > game structure
- TMGBench (2025), Neurocomputing — 2nd-order ToM minimal gain

### Hobbesian Trap
- Kuusela & Roy (2024), AAMAS — higher-order reasoning reinforces trap
- Mengesha & Roy (2025), Nature Comms — phase transitions in ABMs

### Methods
- Perc et al. (2017), Physics Reports — cooperation phase transitions
- Scheffer et al. (2009), Nature — early warning signals
- Traag et al. (2019) — Leiden algorithm
- Sclar et al. (2024), ICLR — FormatSpread
- Chew et al. (2023) — LACA framework for trace coding
