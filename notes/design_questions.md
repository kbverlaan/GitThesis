# Open Game Design Questions

Collected during development. Decisions to make before production runs.
Decided items moved to sprint decision log.

---

## OPEN: Baseline Information Level (Mar 2)

**Question**: Should agents see each other's resources by default?

Current: full info — agents see all neighbours' resources + action history.
Proposed: **hidden resources as baseline**. Agents only learn about others through interaction and memory.

| Level | What you see | Implication |
|-------|-------------|-------------|
| Full info (current) | Neighbours' resources + actions | Can calculate attack EV precisely |
| Hidden resources (proposed baseline) | Only actions of neighbours | Must *learn* who is strong/weak through experience |
| Discovery only | Nothing until interaction | Most realistic, biggest change |

**Arguments for hidden resources as baseline:**
- More dynamic: agents must explore, can't just target the weakest
- More realistic: you don't know your neighbour's bank account
- Creates genuine uncertainty → connects cleanly to Harsanyi's type space
- Makes memory much more important (you learn through observation over time)
- Makes the information IV more meaningful: going from hidden→visible is a real manipulation

**Arguments against:**
- All current pilot data (L1/L3 sweeps) uses full info → not directly comparable
- Harder to validate agent reasoning (we can't check if they "correctly" estimated strength)
- May make L0/L1 agents essentially random (can't calculate EV without resource info)

**Implementation impact:** Medium. Prompt builder change (filter out resource values from neighbour descriptions). Engine unchanged. Memory system already tracks local observations.

**Decision needed before:** Production sweeps. Discuss with Debraj Mar 14.

---

## OPEN: Network Rewiring vs Fixed Grid (Mar 2)

**Question**: Should agents interact on a fixed spatial grid, or on a dynamic social network that rewires over time?

Current: fixed toroidal grid with `interaction_radius`. Agents don't move.
Proposed: **dynamic social network with periodic rewiring**.

| Approach | Mechanism | Pros | Cons |
|----------|-----------|------|------|
| Fixed grid | Static neighbours based on position | Simple, classic (Schelling, Epstein) | "Random movement not representable" (Debraj, Jan 30) |
| Rule-based movement | Agents move on grid per engine rule (e.g., flee hostiles, seek resources) | Keeps grid, adds dynamics | Arbitrary rule choice, grid geometry still constrains |
| **Network rewiring** | Drop low-utility neighbour, add new one every N rounds | No grid needed, pure social structure, richer network metrics | Biggest refactor, different architecture |

**Rewiring rule options:**
- Utility-based: drop neighbour with lowest cumulative return (investment - damage received)
- Threat-based: drop most-armed neighbour
- Schelling threshold: rewire if >k% of neighbours are hostile
- Random with preferential attachment: drop random, add with probability proportional to degree/resources

**Arguments for rewiring:**
- Dynamic network → network metrics (clustering, community evolution) become meaningful
- Already have network analysis code in metrics.py
- Solves Debraj's "random movement" objection
- No arbitrary grid geometry (toroidal, square, hex — all gone)
- Literature: Santos et al. (2006) "Cooperation prevails when individuals adjust their social ties"

**Arguments against:**
- Biggest refactor: replaces grid in engine.py, main.py, prompts, metrics
- All current data uses grid — not comparable
- Rewiring rule itself is a design choice that needs justification
- 1723 SBU remaining — risk of spending compute on debugging

**Implementation impact:** High. Replaces spatial system entirely. Touches engine, prompts, metrics, visualization.

**Decision needed before:** Production sweeps. Discuss with Debraj Mar 14.

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

---

*Last updated: 2026-03-02*
