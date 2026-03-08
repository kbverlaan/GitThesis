# Assumptions & Scope Boundaries

Working document. Every assumption here must be explicitly acknowledged in the
Methods chapter (§3) or Discussion (§6). If you can't defend it, cut the claim.

---

## A. Agent Architecture

1. **LLM-as-agent validity**: Prompted LLMs produce behavior sufficiently
   analogous to bounded-rational agents to study emergent social structure.
   - Limitation: LLMs are not humans. Results describe LLM populations, not
     human populations. Generalization requires explicit argument.
   - Cite: Akata et al. (2025), Park et al. (2023), Horton (2023 "homo silicus")

2. **Prompt = cognition manipulation**: Changing the prompt changes the
   agent's computational process in a way analogous to manipulating reasoning
   depth in cognitive hierarchy theory.
   - Strong assumption. Prompts manipulate output distribution, not necessarily
     internal computation. The faithfulness problem.
   - Cite: Turpin et al. (2024), Lanham et al. (2023)
   - Mitigation: treat reasoning traces as behavioral data, not mechanistic
     explanation. Validate with at least one faithfulness check.

3. **Single model, single temperature**: All agents use the same model
   (Qwen 3.5-27B) and temperature. Heterogeneity comes only from IVs.
   - Why: isolates IV effects. Mixed models confound architecture with reasoning.
   - Limitation: real populations have heterogeneous "cognitive architectures."
     Mixed-model runs are future work (see ideas.txt).

4. **Stateless agents (within-round)**: Agents receive a fresh prompt each
   round. No persistent internal state beyond what the prompt provides.
   - Memory is externalized: the prompt includes history/neighbor profiles.
   - This is a feature, not a bug: it means memory structure is a controlled IV,
     not a hidden variable.

## B. Game Design

5. **Percentage-based payoffs**: All costs and returns are percentages of
   current resources, not absolute values.
   - Why: scale-invariant, prevents trivial equilibria at extreme resource levels.
   - Assumption: agents can reason about percentages. Validated in Phase 1
     (L1+ agents compute EVs correctly in traces).

6. **Simultaneous moves**: All agents choose simultaneously each round.
   - Assumption: no first-mover advantage within a round.
   - Limitation: in reality, some actors move before others (Camerer's
     pseudo-sequential insight). Our design choice simplifies but may miss
     timing effects.

7. **Complete information (baseline)**: All agents see all resources by default.
   - This is the STRONGEST assumption. Real-world conflict involves deep
     uncertainty about opponent capabilities (Hobbes's "diffidence").
   - Explicitly acknowledged as baseline. Hidden-resources variant is Phase 3.
   - Cite: Kuusela & Roy (2024) also assume complete info as baseline.

8. **Fixed game rules**: The rules (payoff structure, available actions) are
   exogenous and constant throughout a run.
   - Agents cannot change the rules, form binding agreements (baseline), or
     create institutions.
   - Why: enables causal identification. Endogenous rules → no controlled IVs.
   - Limitation: real social order emerges partly FROM rule creation (Ostrom 1990).
     See ideas.txt "Endogenous Mechanism Design."

9. **No outside option**: Agents cannot leave the game or refuse to interact.
   - In spatial mode: agents can only interact with neighbors, but cannot
     choose to have zero neighbors.
   - Limitation: exit is a powerful mechanism in real social systems.

## C. Cognitive Hierarchy Mapping

10. **K-level via prompting**: L0-L3 map to Camerer's level-0 through level-3
    by prompting different reasoning depths.
    - L0 = fixed/random (no deliberation)
    - L1 = best response to uniform (EV calculation, no opponent modeling)
    - L2 = best response to predicted L1 behavior (opponent modeling)
    - L3 = recursive (model opponent's model of you)
    - This is inspired by, not identical to, Camerer (2004). Key differences:
      a. Camerer's agents compute analytically; ours reason in natural language
      b. Camerer's CH is a one-shot equilibrium concept; our game is repeated
      c. Camerer's distribution is Poisson(τ); we use fixed homogeneous levels
    - Cite: Zhang et al. (NAACL 2025) for LLM K-level prompting approach.

11. **Temporal reasoning is orthogonal to K-level**: All agents receive the
    same temporal instruction ("this is a repeated game..."). K-level prompts
    manipulate ONLY social modeling depth, not time horizon awareness.
    - This is a design choice, not a theoretical necessity. Camerer's CH is
      inherently static (one-shot). Our extension to repeated games requires
      this separation.

12. **Homogeneous reasoning levels per run**: All 30 agents in a run share
    the same K-level. No mixed populations.
    - Why: clean IV manipulation. Mixed populations confound level effects
      with ecological dynamics.
    - Limitation: unrealistic. In reality, not everyone reasons at the same
      depth. Mixed runs are future work.

## D. Measurement

13. **Gini coefficient as inequality proxy**: Gini measures resource
    inequality, our primary DV for "social order."
    - Assumption: inequality captures meaningful aspects of emergent structure.
    - Limitation: Gini is scale-free and misses qualitative structure (who is
      rich, why, coalition membership). Supplement with network metrics.

14. **Action entropy as behavioral diversity**: Shannon entropy over action
    distribution measures how diverse agent behavior is.
    - Low entropy = homogeneous behavior (all cooperate, or all attack).
    - High entropy = diverse strategies coexist.
    - Limitation: ignores temporal patterns (entropy is per-round, not sequential).

15. **Reasoning traces as data**: We analyze LLM thinking traces as behavioral
    data (what the model "says it considers"), NOT as faithful reports of
    internal computation.
    - Critical framing. Without this caveat, all trace-based analysis is
      epistemologically suspect.
    - Cite: Turpin et al. (2024), Lanham et al. (2023), Chen et al.

## E. Infrastructure

16. **Model equivalence across precision**: FP8 inference produces
    substantively identical behavior to FP16/BF16 for our task.
    - Validated: FP8 benchmark (planned Phase 2c). If distributions diverge
      significantly, fall back to BF16.

17. **vLLM serving is deterministic at temperature=0**: Given the same prompt,
    the same model produces the same output.
    - Approximately true. Small numerical differences possible across batches.
    - Mitigation: we run 20+ replicates per condition.

---

## How to use this document

1. **Before writing Methods**: check each assumption is acknowledged
2. **Before writing Discussion**: check each limitation is discussed
3. **Before defence**: be able to defend every line here
4. **When in doubt**: if you can't defend an assumption, weaken the claim

*Last updated: 2026-03-02*
