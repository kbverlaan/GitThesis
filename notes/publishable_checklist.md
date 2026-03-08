# Publication Checklist: AAMAS-Targeted

## Target Venue
**AAMAS 2027** (Main Track). 8 pages + unlimited references. Double-blind.
Submission ~Oct 2026, notification ~Dec 2026, conference May 2027.
Thesis deadline July 15, 2026 — thesis is primary, paper is extracted from it.

## Template: Kuusela & Roy (AAMAS 2024)
Debraj's paper structure: ~0.75p intro, ~1p background, ~2.5p methods, ~3.5p results, ~0.75p discussion.
**Results dominate** (39%). Methods are formal but readable. Discussion is tight — under one page.
Declarative result section titles ("Cost Uncertainty Promotes Pre-Emptive Attacks").
Heavy appendix usage: sensitivity, algorithm details, proofs all deferred.

---

## 1. The Story (Writing Science — OCAR)

A paper is an argument, not a data dump. Every section serves the narrative arc.

### Opening: Why should the reader care?
- [ ] Open with Hobbes's question: how does order emerge from anarchy?
  - Kuusela & Roy: "There is at least one civilisation in the universe. What if there are more?"
  - Ours: "Hobbes identified three conditions that prevent social order: rational self-interest, uncertainty, and the absence of enforcement. We test all three — independently — in a society of LLM agents."
- [ ] Frame connects to real-world stakes: AI agent deployment, multi-agent coordination, institutional design for AI systems
- [ ] First paragraph is readable by any CS researcher, not just MAS specialists

### Challenge: What's hard / unknown / counterintuitive?
- [ ] State the naive expectation explicitly so you can break it
  - "One might expect that smarter agents cooperate more, that more information reduces conflict, and that communication enables peace..."
  - "Kuusela & Roy showed higher reasoning reinforces conflict in 2-agent RL. Does this hold across all three Hobbesian conditions in N-agent LLM systems?"
- [ ] Identify the gap precisely: mechanism design has three inputs (solution concept, type space, message space) — nobody has varied all three in multi-agent LLMs
- [ ] The gap is between existing work, not just "nobody did X"
- [ ] Note: Hobbes mapping is narrative (with caveats on info→diffidence); mechanism design mapping is the formal backbone

### Action: What did we do? (Methods + Experiments)
- [ ] Game formally specified (states, actions, transitions, rewards) — AAMAS expects this
- [ ] Three IVs operationalized as mechanism design inputs (solution concept, type space, message space)
- [ ] Experiments build logically: each IV gets its own experiment block
  - Exp 1: System characterisation (parameter screening)
  - Exp 2: Reasoning depth (solution concept) — L0-L3 × game structure
  - Exp 3: Information (type space) — visibility/memory manipulation
  - Exp 4: Communication & enforcement (message space) — no-comm → cheap talk → contracts
- [ ] Number and enumerate experiments at the start of Results section (Kuusela does this)

### Resolution: What did we find? So what?
- [ ] The counterintuitive finding IS the resolution — state it cleanly
- [ ] Connect back to the opening stakes
- [ ] Limitations are honest, not defensive (Kuusela lists 3 key assumptions and calls one "clearly not valid")
- [ ] Future work is concrete and brief (2-3 sentences max)

---

## 2. The Counterintuitive Finding

**This is what makes the paper publishable.** Debraj's pattern: set up an expectation, then break it with data.

### Candidates from our work (must validate on Qwen 3.5)
- [ ] "More reasoning → more conflict" (Kuusela replication in LLM domain) — but is it that simple?
- [ ] Non-monotonic pattern: L0 cooperative, L1 strategic, L2 defensive, L3 exploitative — reasoning doesn't monotonically help OR hurt
- [ ] "Deeper reasoning amplifies structural incentives" — L0 is blind to game params, L2/L3 respond explosively
- [ ] The cooperate-then-strike strategy: L3 cooperates MORE than L2 (47% vs 34%) but attacks 4× more (8% vs 2%)
- [ ] "No reasoning level escapes the Hobbesian trap" — but credible commitment does?

### Requirements for the finding
- [ ] Must survive replication on Qwen 3.5 (all Gemma 2 results are exploratory)
- [ ] Must be robust to base parameter choice (that's what the sweeps test)
- [ ] Must be statistically significant with proper CIs
- [ ] Must be explainable — WHY does this happen? (reasoning traces as evidence, not proof)

---

## 3. Experimental Design

### Formal Game Specification (AAMAS requirement)
- [ ] Full formal model: states, action space, observation function, transition dynamics, reward function
- [ ] %-based economy formally defined (not just described in code comments)
- [ ] Spatial structure formally defined (grid, radius, visibility)
- [ ] Reasoning levels operationalized with exact prompt text (appendix)

### Experiment Progression (Kuusela's pattern)
- [ ] **Exp 1: System characterisation** — baseline behaviour under parameter variation (the OAT sweeps)
- [ ] **Exp 2: Reasoning depth main effect** — L0/L1/L2/L3 at fixed game params
- [ ] **Exp 3: The interaction** — reasoning depth × game structure (the key finding)
- [ ] **Exp 4: Credible commitment** — can contracts break what no reasoning level escapes? (separate chapter/paper?)
- [ ] Each experiment has a declarative title that states its conclusion

### Statistical Power
- [ ] Minimum 20 runs per condition for production experiments
- [ ] Power analysis from pilot data (ICC, effect sizes → simr)
- [ ] If underpowered: acknowledge, report effect sizes + CIs anyway

### Controls & Reproducibility
- [ ] Every run: unique seed, full config, model version, hardware, vLLM version logged
- [ ] Temperature fixed and documented
- [ ] Code tagged in git per experiment batch
- [ ] Prompt text versioned — any change = new version number

---

## 4. Analysis

### Primary Metrics (pick 3, not 15)
- [ ] **Cooperation ratio** f_C(t) — primary outcome (maps to Kuusela's attack frequency)
- [ ] **Gini coefficient** — inequality / hierarchy emergence
- [ ] **E-I index** — coalition formation / ingroup-outgroup dynamics
- [ ] All three reported as time series, not just end-values (Debraj: "no rationale for end-values if not stabilised")

### Statistical Models
- [ ] Mixed-effects: `Outcome ~ ReasoningLevel * GameParam + Round + (1|RunID)`
- [ ] Effect sizes: Cohen's d (pairwise) + partial eta-squared (omnibus) + 95% CIs
- [ ] Bayes factors for key comparisons (Akata et al., 2025)
- [ ] Multiple comparison correction (FDR)
- [ ] Report ICC for within-run clustering

### Robustness
- [ ] Sensitivity to base parameters (that's what Stage 1 sweeps establish)
- [ ] Prompt sensitivity: FormatSpread (Sclar et al., 2024) on semantically equivalent reformulations
- [ ] Results with/without outlier runs

---

## 5. Reasoning Traces

### Framing (non-negotiable)
- [ ] "Reasoning traces are behavioral data, not mechanistic explanations"
- [ ] Cite faithfulness literature: Turpin (2023), Lanham (2023), Chen (2025)
- [ ] Frame prompts as "computational depth manipulation" (Pfau et al., 2024)

### Validation
- [ ] At least one faithfulness test: early-answering (Lanham) or Thought Anchors (Bogdan)
- [ ] Concordance rate: stated reasoning vs actual action choice

### As Evidence (not decoration)
- [ ] Traces explain the counterintuitive finding — WHY does L3 cooperate-then-strike?
- [ ] Embedding trajectories (Debraj suggestion): UMAP/PCA showing distinct reasoning regimes
- [ ] Example traces per level in paper (1-2 sentences each), full traces in appendix

---

## 6. Figures

AAMAS = 8 pages. Every figure must earn its space. Kuusela uses 5 figures (1 method, 4 results).

### Essential Figures (thesis + paper)
- [ ] **Hero figure**: Cooperation ratio over rounds, per reasoning level (mean + CI bands + individual trajectories)
- [ ] **Interaction plot**: Reasoning level × game parameter → Gini or cooperation (the non-monotonic pattern)
- [ ] **Parameter sweep**: Variance/sensitivity across theta values (susceptibility analogue)
- [ ] **Reasoning trace evidence**: Embedding UMAP or representative trace excerpts

### Figure Standards
- [ ] Colorblind-safe (viridis)
- [ ] Consistent axes across related figures (Kuusela reuses heatmap format across Exp 2-4)
- [ ] Error bars / CI bands on everything
- [ ] Font size >= 8pt, vector format (PDF)
- [ ] Each figure interpretable without reading full caption

### For Paper (not thesis): Choose 4-5 Max
- [ ] Method figure: game schematic or agent architecture (1 figure)
- [ ] Results figures: 3-4 max, each tied to one experiment/finding

---

## 7. Writing Discipline

### AAMAS 8-Page Constraint
- [ ] Introduction: 0.75 pages max — hook, gap, contribution, outline
- [ ] Background/Related Work: 1 page max — position against 4-6 key papers, not a literature survey
- [ ] Methods: 2-2.5 pages — formal game + reasoning levels + experimental design
- [ ] Results: 3-3.5 pages — THIS IS THE PAPER. Build from baseline → surprise.
- [ ] Discussion: 0.75 pages max — synthesis, limitations, future work
- [ ] Everything else → appendix (prompt texts, full param tables, sensitivity analysis, algorithm details)

### Declarative Section Titles (Kuusela's style)
- Bad: "4.1 Experiment 1: Parameter Sensitivity"
- Good: "4.1 Cheap Arming Creates Arms Races Only When Agents Reason Deeply"

### Claims Calibration
- [ ] Strong: "We find that..." — for statistically significant + robust + meaningful effect size
- [ ] Moderate: "Our results suggest..." — significant but not fully robust, or small effect
- [ ] Weak: "We observe preliminary evidence..." — trends, exploratory
- [ ] Honest uncertainty: "While the exact frequencies are uncertain, the result is qualitatively different" (Kuusela's exact phrasing for their noisiest result)
- [ ] Never: "We made agents think deeper" → Always: "Prompts that elicit different levels of deliberation"

### Novelty Claims (precise positioning)
- [ ] **Existing**: CoT affects individual strategic performance (GTBench, K-Level, TMGBench)
- [ ] **Existing**: LLM behavior varies with framing (Lore & Heydari, 2024)
- [ ] **Existing**: Higher reasoning reinforces Hobbesian Trap in 2-agent RL (Kuusela & Roy, 2024)
- [ ] **Existing**: Cheap talk theory (Crawford & Sobel, 1982), mechanism design (Hurwicz/Maskin/Myerson)
- [ ] **Novel**: First systematic manipulation of all three mechanism design inputs in multi-agent LLM systems
- [ ] **Novel**: Reasoning depth produces qualitatively different emergent social STRUCTURES (not just individual performance) in N-agent systems
- [ ] **Novel**: The effect is non-monotonic and conditional on game structure (interaction)
- [ ] **Novel**: Cheap talk effectiveness in LLMs (if confirmed) — behavioral commitment absent in rational agent models
- [ ] **Novel**: Extension from 2-agent RL to 30-agent LLM — same trap, different mechanism

### Theoretical Grounding (dual framework)
- [ ] **Mechanism design** (formal, exact): three IVs = solution concept, type space, message space (Hurwicz 1960)
- [ ] **Hobbes** (narrative, with caveats): three IVs ≈ competition, diffidence, lack of common power (*Leviathan* 1651)
- [ ] **Caveat on info→diffidence**: less information → more uncertainty → more defensive action is a causal chain, not a direct mapping. Harsanyi (1967) formalizes incomplete info; Hobbes's diffidence is broader (includes wantrouwen with full info)
- [ ] **Supporting**: Baliga & Sjöström (2004) formalize Hobbesian trap with cheap talk; Habermas on communicative action; Camerer et al. (2004) cognitive hierarchy

### Limitations (honest, not defensive)
- [ ] CoT faithfulness caveat
- [ ] Single model (Qwen 3.5-27B) — generalization is future work
- [ ] Finite-size effects at N=30
- [ ] Prompt sensitivity
- [ ] K-instructed vs natural reasoning depth — our prompts manipulate, nature selects
- [ ] Hobbes mapping is narrative, not formal — mechanism design is the exact framework

---

## 8. What Debraj Values (from his papers)

Patterns to follow:

1. **The question already matters.** Don't open with a technical gap. Open with a question that has real-world stakes.
2. **Counterintuitive result IS the paper.** The title, abstract, and structure all build toward breaking an expectation.
3. **Formal rigor serves the story.** Full game specification, but embedded in readable narrative.
4. **Experiments build logically.** Each answers a question the previous left open. Numbered and enumerated upfront.
5. **Dual contribution.** Method + finding. The paper is publishable on either alone. (Ours: local agent memory + reasoning depth findings?)
6. **Assumption honesty.** List the strongest assumptions and flag their fragility. "Clearly not a valid assumption" — this increases credibility.
7. **Real-world resonance in the conclusion.** Always connect back to something outside the model.
8. **Appendices carry heavy load.** Main paper is self-contained for reading; details are external.

---

## 9. Key Literature

### Must-Cite (positioning)
- Kuusela & Roy (AAMAS 2024) — direct predecessor, same supervisor
- Zhang et al. (NAACL 2025) — K-Level Reasoning framework
- Akata et al. (Nature Human Behaviour, 2025) — LLMs in repeated games
- Lore & Heydari (Scientific Reports, 2024) — framing effects
- Jia et al. (arXiv:2502.20432) — CoT not universally effective

### Must-Cite (faithfulness)
- Turpin et al. (NeurIPS 2023) — unfaithful CoT
- Lanham et al. (Anthropic, 2023) — measuring faithfulness
- Chen et al. (Anthropic, 2025) — reasoning models unfaithfulness
- Pfau et al. (2024) — computational depth independent of content

### Must-Cite (methods)
- Perc et al. (Physics Reports, 2017) — cooperation phase transitions
- Traag et al. (2019) — Leiden algorithm (if using coalitions)
- Sclar et al. (ICLR, 2024) — FormatSpread

### Should-Cite (Debraj's group)
- Mengesha & Roy (Nature Comms, 2025) — phase transitions in ABMs
- Mengesha & Roy (ICCS, 2025) — game selection → inequality
- Bazyleva, Garibay & Roy (Sci Rep, 2024) — GSA in multiscale models

---

## 10. Code & Data

- [ ] Clean repo with README and requirements (pinned versions)
- [ ] Scripts to reproduce every figure from raw data
- [ ] Per-run logging: actions, resources, traces, configs, metadata, errors
- [ ] Appendix materials on Zenodo (Kuusela's approach) — prompt texts, full param tables, raw data
