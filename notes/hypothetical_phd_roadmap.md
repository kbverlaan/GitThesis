# Hypothetical PhD Roadmap: The Origins of Order

**Central question**: Given no external authority, what social order emerges spontaneously from AI-AI interaction, and what determines its form?

**Gedachte-experiment**: Autonomous AI agents, no human intervention — how do they shape the world?

**Theoretical spine**: Hobbes' Leviathan as roadmap — state of nature → social contract → constitutional governance. But bottom-up, without a Leviathan.

*Status: speculative roadmap, not a commitment. Everything beyond Paper 1 depends on results, funding, and whether Koen decides to pursue a PhD.*

*Last updated: March 3, 2026*

---

## Paper 1 — State of Nature (MSc thesis, 2026)

**Question**: How does reasoning depth interact with game structure to shape emergent social order?

**Setup**: 30 LLM agents, fixed coordination game (invest/arm/attack), Qwen 3.5-27B, L0-L3 reasoning depth × structural parameters.

**Expected key finding**: Non-monotonic pattern. L0 = naive cooperator, L1 = strategic calculator, L2 = defensive hoarder, L3 = selective predator. Deeper reasoning amplifies structural incentives rather than transcending them.

**What stays for future papers**: The coordination game framework, %-based economy, co-evolutionary network, local observation memory, coalition attacks, Gini/cooperation/modularity metrics pipeline.

**What this establishes**: Baseline understanding of what LLM agents do under fixed rules. The reference point for everything that follows.

**Target venue**: AAMAS 2027

---

## Paper 2 — Social Contract (~Year 1)

**Question**: Can agents escape the Hobbesian trap through self-initiated binding commitments, and does the mechanism survive strategic exploitation?

**What's new (one thing)**: Credible commitment mechanism — collateral-based contracts between agents. Everything else identical to Paper 1.

**Design**: Collateral sweep (0%, 10%, 25%, 50%, 100%) × reasoning depth (L0-L3). Paper 1 results serve as the no-contract baseline.

**Key questions**:
- Is there a collateral threshold where cooperation stabilises?
- Does the threshold differ by reasoning level? (Do L3 agents need less commitment to cooperate because they understand the mechanism better, or more because they're better at exploiting it?)
- Do agents voluntarily propose contracts, or avoid them?
- **The interesting null result**: L3 agents exploit contracts (propose, collect collateral, defect optimally) → the Hobbesian trap is not solved by mechanism alone, it requires matching cognitive sophistication. This would be a finding, not a failure.

**What this adds to the programme**: Agents can escape anarchy *if* the right institutional mechanism is available. But the mechanism is exogenously provided — agents didn't invent it. The gap between "mechanism exists" and "mechanism works" depends on reasoning depth.

**Risk mitigation**: If collateral contracts are too thin as standalone paper, merge with Paper 3 — "from exogenous to endogenous institutions" as a single arc.

**Target venue**: AAMAS or ECAI

**Note**: This is the credible commitment chapter from the MSc thesis. If the thesis chapter is strong enough, it may already be publishable with minor extension (more reps, robustness checks, additional analysis).

---

## Paper 2b — Cross-Model Replication (~Year 1, parallel with Paper 2)

**Question**: Are the reasoning depth effects from Paper 1 a property of LLM agents in general, or Qwen 3.5 specifically?

**Why early**: This is the foundation risk. If Paper 1 results are model-specific, Papers 3-4 inherit that weakness. Running this early (before building the composable DSL) is cheap insurance.

**What's new (one thing)**: Same experimental design as Paper 1, run on 2-3 additional models (e.g., Llama 4, Gemma 3, Mistral Large — whatever fits on 1-2 H100s at the time).

**Design**: L0/L1/L3 × 2-3 models × key parameter conditions from Paper 1. Not the full factorial — just enough to test whether behavioral fingerprints replicate.

**Key questions**:
- Does the non-monotonic L0→L1→L2→L3 pattern replicate across architectures?
- Are the qualitative roles (calculator, hoarder, predator) conserved, or model-specific?
- Do effect sizes (η²) hold, or collapse?

**Possible outcomes**:
- Replicates → strong foundation, continue with confidence
- Partially replicates (pattern holds, effect sizes differ) → interesting in itself, publish as "reasoning depth effects are robust but magnitude is architecture-dependent"
- Doesn't replicate → pivot the programme. Still publishable as a negative result, but changes the framing from "general property" to "model-conditional"

**What this adds to the programme**: External validity. Without this, every subsequent paper carries the caveat "but only tested on one model."

**Target venue**: Workshop paper (AAMAS workshop, LLM Agents workshop) or short paper. Doesn't need to be a full publication — just needs to exist.

---

## Paper 3 — Institutional Innovation (~Year 1-2)

**Question**: What happens when agents can design their own actions?

**What's new (one thing)**: Composable action space from primitives. Fixed actions (invest/arm/attack) are removed. Agents compose actions from a small vocabulary:
- Transfer(pct, target_selector)
- Condition(predicate)
- Observe(target, attribute)
- Bind(pct_collateral, duration)
- Scale(factor, basis)

The game engine validates compositions; invalid ones become do_nothing.

**Design**: Three conditions compared directly:

| Condition | Actions | Rules |
|-----------|---------|-------|
| Fixed (Paper 1 replication) | Hardcoded | Fixed |
| Composable | Primitives | Fixed |
| Composable + Contracts (Paper 2 mechanism) | Primitives | Fixed |

Cross with reasoning depth (L0-L3) → 3 × 4 factorial.

**Key questions**:
- Do agents reinvent the hardcoded actions, or discover novel strategies?
- What categories of actions emerge? (cooperative, competitive, parasitic, institutional)
- Does the action lexicon converge or keep growing?
- Do L3 agents invent more complex compositions than L0?

**Engineering risk**: The primitives DSL is the hardest engineering challenge in the programme. The set needs to be expressive enough for interesting compositions but constrained enough for the engine to validate. Expect 2-3 iterations before the design stabilises. Budget a full quarter for DSL design + piloting before production runs.

**What this adds to the programme**: Agents have agency over *what they can do*, not just *what they choose to do*. Tests whether institutional innovation emerges from cognitive sophistication.

**Target venue**: AAMAS, NeurIPS (if framing leans ML), or JASSS (if framing leans social simulation)

---

## Paper 4 — Constitutional Governance (~Year 2-3)

**Question**: What happens when agents also control *when* and *how* rules change?

**What's new (one thing)**: Endogenous innovation phases with democratic governance. Agents vote on when to hold innovation rounds and which proposed actions to adopt into a shared action lexicon.

**Design**: Building on Paper 3's composable actions, add:
- `call_innovation` flag each round; >X% triggers innovation phase
- During innovation: propose new compositions, majority vote to adopt
- Adopted actions enter shared lexicon (reusable by all)
- The threshold X is itself voteable (constitutional amendment)

Compare: Composable-only (Paper 3) vs Composable + Governance (Paper 4).

**Key questions**:
- Who calls innovation phases — rich or poor agents?
- Do dominant agents block institutional change to protect status quo?
- Does the shared lexicon stabilise (lock-in) or keep changing (revolution)?
- Does democratic governance reduce or formalise inequality?

**The interesting null results** (plan for these in advance):
- Agents never call innovation → institutional inertia is the default, even with the capability. Finding: agency over rules ≠ exercise of that agency. Interesting parallel to voter apathy.
- Dominant agents block everything → institutions formalise power, don't redistribute it. Finding: Ostrom's self-governance requires something beyond cognitive capability — perhaps equality of power as a precondition.
- Lexicon explodes (no convergence) → composability without governance produces chaos, not order. Finding: constitutional structure (voting) is necessary for institutional stability.

**What this adds to the programme**: The full three-level system — playing within rules, changing rules, deciding when rules change. Ostrom territory: self-governance of common pool resources, but with AI agents.

**Connection to Mengesha & Roy (2025)**: They show game selection drives inequality via evolutionary drift. This paper asks: does *deliberate* game selection (voting, proposals) lead to more or less inequality than blind drift?

**Target venue**: AAMAS, ICCS, or interdisciplinary (PNAS if results are striking enough)

---

## Proefschrift Structure

| Chapter | Content | Based on |
|---------|---------|----------|
| 1. Introduction | The gedachte-experiment. Hobbes framing. Gap. Contributions. | — |
| 2. Background | ABM, MARL, LLM agents, game theory, institutional economics, Ostrom | — |
| 3. The Game | Shared framework: coordination game, primitives, metrics | Technical chapter |
| 4. State of Nature | Fixed rules, reasoning depth effects | Paper 1 |
| 5. Social Contract | Credible commitment mechanisms | Paper 2 |
| 6. Institutional Innovation | Composable actions from primitives | Paper 3 |
| 7. Constitutional Governance | Endogenous rule formation + voting | Paper 4 |
| 8. Robustness & Generalization | Cross-model, scale, robustness | Paper 2b + additional |
| 9. Discussion | Synthesis, limitations, implications for AI governance | — |
| 10. Conclusion | Answer to the central question | — |

---

## What This Means for the Current MSc Thesis

The MSc thesis is Paper 1 + the beginnings of Paper 2 (credible commitment chapter). Everything beyond that is **out of scope** for July 2026. Specifically:

**In scope (MSc thesis)**:
- Reasoning depth experiments on Qwen 3.5-27B (Paper 1 core)
- Origins factorial: reasoning × structure interactions (Paper 1 core)
- Credible commitment chapter (Paper 2 seed)
- Robustness: prompt sensitivity, faithfulness validation (Paper 1 quality)

**Explicitly out of scope (future work section)**:
- Composable actions / primitives DSL (Paper 3)
- Endogenous innovation phases / voting (Paper 4)
- Cross-model replication (Paper 2b — but flag it as immediate next step)
- Scale experiments beyond 30 agents

**The future work section of the thesis** should sketch the drieluik (Papers 1→2→3-4) as the natural research programme. This plants the flag for the PhD without overloading the MSc.

---

## Key References Connecting the Programme

- Kuusela & Roy (AAMAS 2024) — RL reasoning depth in Hobbesian trap (direct predecessor, Paper 1)
- Mengesha & Roy (ICCS 2025) — Evolutionary game selection → inequality (Paper 4 connection)
- Conitzer (2024) — Program equilibria (Paper 2 theoretical basis)
- Park et al. (UIST 2023) — Generative Agents architecture (methodological inspiration)
- Park et al. (2024) — 1,000 People (validation paradigm for Paper 2b)
- Larooij et al. (AI Review 2025) — Validation of generative social simulations (Paper 2b framing)
- Project Sid (Altera 2024) — Large-scale emergent AI civilizations (related but less controlled)
- Ostrom (1990) — Governing the Commons (theoretical foundation for Papers 3-4)
- Crawford & Sobel (1982) — Cheap talk (Paper 1 communication scope)
- Hobbes (1651) — Leviathan (the whole framing)

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Paper 1 results don't replicate on other models | **Critical** | Paper 2b early. If partial replication → reframe as model-conditional. |
| Paper 2 (contracts) too thin for standalone | Medium | Merge with Paper 3 into single "exogenous → endogenous institutions" paper. |
| Primitives DSL (Paper 3) too hard to design | High | Budget full quarter for iteration. Start with minimal set (Transfer + Condition only), expand if it works. |
| Paper 4 null results (agents don't govern) | Medium | Pre-register interesting null results (see above). Every outcome is publishable if framed correctly. |
| Compute scaling for 100+ agents (Paper 2b/proefschrift) | Medium | By year 2-3, inference costs will be lower. Also: multi-GPU serving, smaller models as proxies. |
| Field moves faster than the programme | High | The Hobbes framing + Ostrom connection is distinctive enough to stay relevant even if "LLM agents play games" becomes crowded. The institutional innovation angle (Papers 3-4) is the moat. |
| Funding | High | NWO (AI governance angle), ELLIS, or industry lab. Debraj's lab (Mengesha connection) is natural fit. Maik Larooij as co-supervisor strengthens LLM-ABM validation angle. |
