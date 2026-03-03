# Open Game Design Questions

Collected during development. Decisions to make before production runs.
Decided items moved to sprint decision log.

---

## DECIDED: Hidden Resources as Base Default (Mar 2)

**Decision**: Hidden resources is the BASE DEFAULT for all conditions. Not an IV.

Agents see only their own resources; neighbours show as `???`. Memory accumulates local observations but resource values remain hidden (`?` in memory).

**Implementation**: Done (Mar 2). `prompts.py` hides neighbour resources + arm bonuses. `memory.py` respects `hide_resources` flag.

**Hobbes connection**: Hidden resources directly operationalizes Hobbes's "diffidence" — agents face genuine type uncertainty about neighbour strength, creating the conditions for preemptive arming. This is ALWAYS present as the base condition, providing the permanent backdrop of uncertainty.

**Testing**: May verify impact in OAT pilots (hidden vs visible as sensitivity check), but not a primary IV.

---

## DECIDED: Dynamic Network with Payoff-Based Rewiring (Mar 2)

**Decision**: Replace fixed spatial grid with dynamic social network. Rewiring probability **w** is the information IV.

**Design:**
- Initial network: Erdős-Rényi G(n,p) with expected degree ⟨k⟩ ≈ 4-6
- Rewiring mechanism: payoff-based. Each round, with probability w, agent drops lowest-payoff neighbour and reconnects to random non-neighbour
- Break-one-make-one: edge count conserved. Min degree ≥ 1 (no isolates)
- IV levels: w ∈ {0, 0.05, 0.3, 1.0} (static → viscous → fluid → fully dynamic)

**Mechanism Design mapping (strong):**
Network topology = TYPE SPACE. Who you can observe and interact with determines your information about others' types. w manipulates how much agents can restructure their information channels. At w=0, type space is frozen. At w=1, agents actively reshape it.

**Hobbes mapping (moderate, nuanced):**
Two layers of "diffidence" operate simultaneously:
1. **Hidden resources** (base default, always present): direct Hobbes — you don't know neighbour strength → genuine type uncertainty → preemptive arming. This is the PERMANENT backdrop of diffidence.
2. **Network rewiring w** (the IV): structural RESPONSE to diffidence. At w=0, agents are trapped with their neighbours — can't escape threats, diffidence is maximally constraining. At w=1, agents can flee dangerous neighbours and seek better partners — diffidence is still present (resources hidden) but agents have an EXIT OPTION.

So the mapping is: hidden resources creates Hobbes's diffidence. Network rewiring determines whether agents can structurally respond to it. Higher w doesn't remove uncertainty — it gives agents agency over their social environment.

This is actually a richer story than the original "visibility radius = diffidence" because it separates the source of uncertainty (hidden resources) from the structural conditions under which uncertainty operates (network fluidity).

**Key literature:**
- Zimmermann & Eguíluz (PRE 2004): foundational payoff-based rewiring
- Pacheco et al. (PRL 2006): phase transition at critical w*
- Rand et al. (PNAS 2011): human experiments confirm dynamic networks boost cooperation
- Ohtsuki et al. (Nature 2006): b/c > k rule for cooperation on graphs

**Risk:** LLM agents may not rewire "rationally" compared to evolutionary GT baselines. See risk register in roadmap.md.

**Implementation impact:** High. Replaces spatial system. Touches engine, prompts, metrics.

---

## OPEN: Unequal Starting Resources (Mar 2)

**Question**: Should agents start with equal resources (current) or heterogeneous endowments?

Current: all agents start with `initial_resources=25.0`.
Options:
- Equal (current): clean baseline, any inequality is emergent
- Uniform random (e.g., U[5, 50]): introduces initial heterogeneity
- Structured (e.g., 1 rich + 9 poor): tests specific scenarios (surpass, hegemon)

**Not an IV** — this is a base game parameter. Equal start is the clean baseline because any observed Gini > 0 is purely emergent. Unequal starts are interesting but should come after baseline results.

**Decision:** Keep equal for now. Revisit after production sweeps.

---

## OPEN: invest_other Return Multiplier Tuning

Current: `invest_other_return_pct=25` (target gets 25% of your resources when you pay 10%).
Social surplus: you lose 10, target gains 25 → system grows by 15. Cooperation is clearly socially optimal.

Is 25% too generous? If cooperation is always dominant, L1 agents should always cooperate → no dilemma.
But: invest_other benefits the TARGET, not you. Without reciprocity (memory), it's pure altruism.
With memory ON (default), repeated interaction makes reciprocity possible → dilemma exists.

OAT sweep includes invest_other_return_pct at [10, 15, 25] — this will answer the question empirically.

**Decision:** Let the sweep decide. Default 25% for now.

---

## DECIDED (moved to sprint log)

The following have been decided and logged in `sprint_3_feb27-mar14.md`:

- %-based economy (Feb 28)
- Additive arm bonus + ×0.5 decay (Feb 28)
- invest_self OFF by default (Feb 28)
- Memory default ON, local observations only (Mar 1)
- God-view neighbour profiles removed (Mar 1)
- Two-phase adaptive early stopping (Mar 1)
- bf16 over FP8 for Qwen 3.5-27B (Mar 2)
- Reasoning levels L0-L3 via prompt manipulation (Feb 27)
- Qwen 3.5-27B dense as single model (Feb 27)
- Hidden resources as base default (Mar 2)
- Dynamic network with payoff-based rewiring, w as IV (Mar 2)
- Communication scope: no-comm / DM / broadcast as IV3 (Mar 2)

---

*Last updated: 2026-03-02*
