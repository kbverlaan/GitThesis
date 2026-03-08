# Reading List — Origins of Order

**Status**: Started 2026-03-02
**Honest baseline**: Kuusela & Roy (read), Larooij & Törnberg (half), rest unread.

Legend: [ ] unread, [~] started/skimmed, [x] read

---

## Tier 1 — Core (before Mar 14 meeting)

These papers directly define your experimental design and framing. You cannot write your methods section without them.

### Your direct comparison papers
- [x] Kuusela & Roy (2024) — "Higher Order Reasoning under Intent Uncertainty Reinforces the Hobbesian Trap" (AAMAS). Debraj's paper. Your methodological template. K-level reasoning in 2-agent RL → Hobbesian Trap.
- [ ] Akata et al. (2025) — "Playing repeated games with LLMs" (Nature HB). Bayesian analysis, multiple games, LLM cooperation patterns. Closest LLM comparison to your work. Memory: full history in prompt. **In Zotero.**
- [ ] Dai et al. (2024) — "Artificial Leviathan: Exploring Social Evolution of LLM Agents Through the Lens of Hobbesian Social Contract Theory". Hobbes + LLM agents + social contract emergence. Memory: sliding window (30 actions), varies depth as IV. Validates your memory approach. **NOT in Zotero — add!**
- [ ] Camerer, Ho & Chong (2004) — "A Cognitive Hierarchy Model of Games" (QJE). K-level reasoning theory. Foundation for your L0-L3 manipulation. **NOT in Zotero — add!**

### CoT faithfulness (you MUST know these for your traces-as-data argument)
- [ ] Lanham et al. (2023) — "Measuring Faithfulness in Chain-of-Thought Reasoning". Early answering + paraphrase tests. Defines the faithfulness baseline. **In Zotero.**
- [ ] Chen et al. (2025) — "Reasoning Models Don't Always Say What They Think" (Anthropic). Reasoning models specifically. Shows unfaithfulness persists in o1/R1-style models. Directly relevant to your Qwen 3.5 traces. **In Zotero.**

### Hobbes formalized
- [ ] Baliga & Sjöström (2004) — "Arms Races and Negotiations" (ReStud). Hobbes → formal game theory. Security dilemma, arming, preventive war. Maps directly to your arming mechanic. **NOT in Zotero — add!**

### Spatial ABM foundations (needed for movement design decision)
- [ ] Epstein & Axtell (1996) — *Growing Artificial Societies*, Ch. 2-4. Sugarscape movement rules, vision, resource gradients. The canonical spatial ABM. **In Zotero — move from Tier 4!**
- [ ] Schelling (1971) — "Dynamic Models of Segregation". Threshold-based movement creates macro patterns from micro rules. **In Zotero — move from Tier 4!**

**Total: 8 papers. Aim: 1 per day this week + weekend.**

---

## Tier 2 — Theoretical Foundations (before Apr 1)

These give depth to your three IVs. You need them for your introduction and related work.

### IV1: Reasoning depth / Theory of Mind
- [ ] Zhang et al. (2024) — "K-Level Reasoning: Establishing Higher Order Beliefs in LLMs". LLM-specific K-level reasoning. Prompt-based manipulation. **In Zotero.**
- [ ] Pfau et al. (2024) — "Let's Think Dot by Dot: Hidden Computation in Transformer Language Models". What CoT actually does computationally. **In Zotero.**
- [ ] Mazeika et al. (2025) — "Utility Engineering: Analyzing and Controlling Emergent Value Systems in AIs". LLM preferences satisfy rational choice axioms (transitivity, completeness) and coherence emerges with scale. Thurstonian utility model. Supports your assumption that LLM agents can exhibit rational preferences. Cite in Methods (reasoning depth justification) and Related Work (LLMs as rational actors). **NOT in Zotero — add!**
- [ ] de Weerd, Verbrugge & Verheij (2013) — "How much does it help to know what she knows you know?" (Artificial Intelligence). Agent-based ToM-0/1/2/3 in competitive games. ToM-1>>ToM-0, diminishing returns at ToM-3. Justifies L0-L3 range. **NOT in Zotero — add!**
- [ ] de Weerd, Verbrugge & Verheij (2017) — "Negotiating with other minds" (JAAMAS). ToM in Colored Trails negotiation. KEY: higher ToM advantage amplified when communication is available. Predicts reasoning×communication interaction effect. **NOT in Zotero — add!**
- [ ] Kosinski (2024) — "Evaluating large language models in theory of mind tasks" (PNAS). LLMs have emergent ToM; GPT-4 ≈ 6-y/o. Motivates prompt-based ToM manipulation on real capability. **NOT in Zotero — add!**
- [ ] Li et al. (2023/24) — "Theory of Mind for Multi-Agent Collaboration via LLMs" (arXiv:2310.10701). Explicit belief tracking (≈note-to-self) improves ToM expression. **NOT in Zotero — add!**

### IV2: Information structure
- [ ] Crawford & Sobel (1982) — "Strategic Information Transmission" (Econometrica). Cheap talk theory. Foundation for why information structure matters in strategic interaction. **NOT in Zotero — add!**

### IV3: Communication & enforcement (mechanism design)
- [ ] Hurwicz (1960) — "Optimality and Informational Efficiency in Resource Allocation Processes". Origin of mechanism design. You cite him — read him. **NOT in Zotero — add!**
- [ ] Myerson (1979) — "Incentive Compatibility and the Bargaining Problem". Revelation principle. Why enforcement changes equilibria. **NOT in Zotero — add!**

### Hobbes & social contract
- [ ] Hobbes (1651) — *Leviathan*, Chapter 13. The three causes of conflict: competition, diffidence, glory. Read the original — it's 10 pages. **NOT in Zotero — add!**
- [ ] Ostrom (1990) — *Governing the Commons*, Ch. 1-3. Counterpoint to Hobbes: groups CAN self-govern without Leviathan. Relevant for your enforcement IV. **NOT in Zotero — add!**

**Total: 7 papers/chapters.**

---

## Tier 3 — State of the Art & Comparison (before May 1)

These position your work in the LLM-agents landscape.

### LLM agents in games
- [ ] Pellert et al. (2025) — "LLMs replicate and predict human cooperation across experiments". LLM vs human comparison. **In Zotero.**
- [ ] Horton (2023) — "Homo Silicus". LLMs as simulated economic agents. **In Zotero.**
- [ ] Lorè & Heydari (2024) — "Strategic behavior of LLMs: game structure vs contextual framing". Framing effects in LLM game play. **In Zotero.**
- [ ] Ashery et al. (2025) — "Emergent social conventions and collective bias in LLM populations". Emergent norms without explicit rules. **In Zotero.**
- [ ] Piatti et al. (2024) — "Cooperate or Collapse" (NeurIPS). GovSim: N LLM agents in commons dilemma. Communication is critical for cooperation. Closest structural analogue to your design. **NOT in Zotero — add!**
- [ ] Wilf et al. (2025) — "Will Systems of LLM Agents Cooperate?" (arXiv:2501.16173). LLM strategic biases vary by model identity. Justifies single-model design choice. **NOT in Zotero — add!**

### Emergent structure
- [ ] Park et al. (2023) — "Generative Agents: Interactive Simulacra of Human Behavior". Defines the field. 25-agent LLM society. **In Zotero.**
- [ ] Rachum et al. (2024) — "Emergent Dominance Hierarchies in RL Agents". Gini, hierarchy emergence in RL. Direct metric comparison to your work. **In Zotero.**

### Phase transitions & ABM methodology
- [ ] Scheffer et al. (2009) — "Early-warning signals for critical transitions" (Nature). Your EWS metrics foundation. **In Zotero.**
- [ ] Leibo et al. (2017) — "Multi-agent RL in Sequential Social Dilemmas". Defines the sequential social dilemma framework. **In Zotero.**

**Total: 8 papers.**

---

## Tier 4 — Writing Phase Background (May-June)

Read as needed during writing. Lower urgency but adds depth.

- [ ] Binmore (2005) — *Natural Justice*. Evolutionary game theory + social contract bridge. **NOT in Zotero.**
- [ ] Maskin (1999) — "Nash Equilibrium and Welfare Optimality" (ReStud). Implementation theory. **NOT in Zotero.**
- [ ] Axelrod & Hamilton (1981) — "The Evolution of Cooperation". Classic. **In Zotero.**
- [ ] Perc et al. (2017) — "Statistical physics of human cooperation". Spatial cooperation dynamics. **In Zotero.**
- [~] Larooij & Törnberg (2025) — "Validation is the central challenge for generative social simulation". Finish reading! **In Zotero.**
- [ ] Lee et al. (2015) — "Complexities of ABM Output Analysis" (JASSS). Your early stopping citation. **NOT in Zotero — add!**
- [ ] Gelman & Rubin (1992) — R-hat convergence. Your post-hoc validation. **NOT in Zotero — add!**
- [ ] Turpin et al. (2023) — "Language Models Don't Always Say What They Think". OG unfaithfulness paper. **In Zotero.**
- [ ] Chua & Evans (2025) — "Are DeepSeek R1 and Other Reasoning Models More Faithful?" **In Zotero.**
- [ ] Dubey et al. (2018) — "Investigating Human Priors for Playing Video Games". Semantic ablation inspiration. **In Zotero.**
- [ ] Binmore (2005) — *Natural Justice*. Evolutionary game theory + social contract bridge. **NOT in Zotero.**

---

## Papers to add to Zotero

Priority additions (not currently in library):

| Paper | Collection |
|-------|-----------|
| Dai et al. (2024) — Artificial Leviathan | 3. Emergent Structures — LLM Agents |
| Camerer, Ho & Chong (2004) — Cognitive Hierarchy | 3. Emergent Structures — LLM Agents |
| Baliga & Sjöström (2004) — Arms Races | 1. Foundational ABM & Cooperation |
| Crawford & Sobel (1982) — Strategic Info Transmission | 1. Foundational ABM & Cooperation |
| Hurwicz (1960) — Mechanism Design | 1. Foundational ABM & Cooperation |
| Myerson (1979) — Incentive Compatibility | 1. Foundational ABM & Cooperation |
| Hobbes (1651) — Leviathan Ch.13 | 1. Foundational ABM & Cooperation |
| Ostrom (1990) — Governing the Commons | 1. Foundational ABM & Cooperation |
| Binmore (2005) — Natural Justice | 1. Foundational ABM & Cooperation |
| Lee et al. (2015) — ABM Output Analysis | 11. Methodology & Validation |
| Gelman & Rubin (1992) — R-hat | 11. Methodology & Validation |
| Maskin (1999) — Implementation Theory | 1. Foundational ABM & Cooperation |
| Mazeika et al. (2025) — Utility Engineering | 3. Emergent Structures — LLM Agents |
| de Weerd et al. (2013) — ToM agent-based | 1. Foundational ABM & Cooperation |
| de Weerd et al. (2017) — Negotiating with other minds | 1. Foundational ABM & Cooperation |
| Kosinski (2024) — LLM ToM evaluation | 3. Emergent Structures — LLM Agents |
| Li et al. (2023/24) — ToM for Multi-Agent Collaboration | 3. Emergent Structures — LLM Agents |
| Piatti et al. (2024) — Cooperate or Collapse | 3. Emergent Structures — LLM Agents |
| Wilf et al. (2025) — Will LLM Agents Cooperate | 3. Emergent Structures — LLM Agents |

---

*Last updated: 2026-03-07*
