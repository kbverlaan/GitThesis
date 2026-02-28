# Open Game Design Questions

Collected during development. Decisions to make before/during production runs.

---

## DECIDED: %-Based Economy (2026-02-28)

All costs and returns scale with the actor's current resources. This ensures every action remains meaningful at any wealth level and creates richer dynamics where reasoning depth matters more.

### Parameter Proposal

| Parameter | Value | Mechanic |
|-----------|-------|----------|
| `invest_self_cost` | 10% of your resources | You pay 10% |
| `invest_self_return` | 20% of your resources | You gain 20% (net +10%) |
| `invest_other_cost` | 10% of your resources | You pay 10% |
| `invest_other_return` | 25% of invested amount | Target gains 25% of what you paid (= 2.5% of your resources) |
| `arm_self_cost` | 10% of your resources | Resources consumed (gone from economy) |
| `arm_self_boost` | ×2.0 initial combat multiplier | Decays ×0.5 per round |
| `arm_other_cost` | 10% of your resources | Resources consumed (gone from economy) |
| `arm_other_boost` | Cost amount becomes combat power for target | Decays ×0.5 per round |
| `attack_take_percent` | 40% of loser's resources | Winner takes from loser |
| `conflict_cost` | 5% of each fighter's resources | Both pay, regardless of outcome |

### Key Design Principles

**1. invest_other grows the pie (invest_self too, but less efficiently)**
- invest_self: you pay 10%, gain 20% → net +10% for you, +10% for economy
- invest_other: you pay 10%, target gains 25% of that → net -10% for you, +2.5% for target, net system growth +2.5% vs -10% = still net loss for system?

**→ OPEN: invest_other return multiplier needs tuning.** If target gains 25% of your 10% investment, that's only 2.5% of your resources going to them. That might be too low. Alternative: target gains 150% of what you paid (= 15% of your resources). Then:
- You lose 10%, target gains 15% → system grows by 5%. Social surplus exists.
- invest_self: +10% for you. invest_other: -10% for you, +15% for target. Classic social dilemma.

**2. arm_other ≠ invest_other (combat power only, not wealth)**
- arm_other costs you 10% of resources. Those resources are **consumed** (removed from economy).
- The consumed amount becomes **temporary combat power** for the target.
- Target's resource count does NOT increase — only their fighting strength.
- This is a pure military expenditure: the pie shrinks, but someone gets protection.

**3. Combat power decays (×0.5 per round)**
Instead of binary armed/unarmed with fixed duration, combat boosts decay exponentially:

| Round after arming | Remaining boost | Effective multiplier (arm_self) |
|--------------------|----------------|--------------------------------|
| 0 (just armed) | 100% | ×2.0 |
| 1 | 50% | ×1.5 |
| 2 | 25% | ×1.25 |
| 3 | 12.5% | ×1.125 |
| 4+ | <10% | removed (threshold) |

Decay rate: `boost_t = initial_boost × 0.5^t`
Removal threshold: when boost < 10% of initial → removed entirely.

This creates **timing pressure**: arm now → attack immediately for max effect, or wait and lose power. Makes arm_self a commitment device.

For arm_other: the combat power boost for the target decays the same way. Sustained protection requires repeated investment → ongoing alliance cost.

**4. conflict_cost scales with wealth**
Both attacker and defender pay 5% of their own resources. Rich agents risk more in absolute terms. Prevents "free attacks" at any wealth level.

### Strategic Implications

| Action | You | Target | Economy | Strategic role |
|--------|-----|--------|---------|---------------|
| invest_self | +10% | — | Grows | Safe growth, no interaction |
| invest_other | -10% | +15%* | Grows more | Social surplus, requires trust |
| arm_self | -10% | — | Shrinks | Commitment device, time pressure |
| arm_other | -10% | combat↑ | Shrinks | Military alliance, no wealth transfer |
| attack | -5% + maybe lose 40% | -5% + maybe lose 40% | Shrinks (conflict costs) | Redistribution, risky |
| do_nothing | 0 | — | Neutral | Default safe option |

*invest_other return multiplier TBD — see open question above.

### What This Enables for K-Level Reasoning

- **L0** (reactive): invest_self is obviously good → dominates. Boring but stable.
- **L1** (EV calculation): attack EV depends on relative resources and armed status. Now requires actual math because everything scales.
- **L2** (opponent modeling): predicting armed status matters more — decay means timing is critical. "Will they attack while still strong?"
- **L3** (recursive): commitment devices work — arm yourself to signal aggression, then don't attack (bluff). Opponents who model you at L2 will react to the signal.

---

## Still Open

### invest_other Return Multiplier
- Target gets X% of what you invested. X = 150% means social surplus exists (you lose 10, target gains 15).
- If X is too high → cooperation trivially dominant. If too low → nobody cooperates.
- Need to find the sweet spot where invest_self is individually rational but invest_other is socially optimal.
- **Suggestion**: start with 150% (target gains 15% of your resources when you pay 10%). Test and tune.

### Coalition Visibility
- Full info (current): agents see who supports whom → enables strategic targeting of supporters
- Partial: only see that an agent HAS coalition support, not from whom
- Hidden: coalition bonuses apply but aren't announced → agents must infer from combat outcomes

### Coalition as Protection Racket
- arm_other enables maffia-like structures (strong agent "protects" weaker ones). Is this emergent or should we design for it?
- With decay, protection requires ongoing investment → creates dependency relationships.

### Decay Removal Threshold
- Currently proposed: remove when boost < 10% of initial.
- Could also use absolute threshold or fixed number of rounds as hard cap.
- ×0.5 decay means effectively gone after 4 rounds regardless.

## Information & Observation

- **History window**: Currently `recent_history` shows last N rounds of neighbor actions. How much history is optimal? Too little → can't detect patterns. Too much → prompt token bloat, model confused.
- **Resource visibility**: `hide_resources` option exists but untested. Partial information could create very different dynamics (uncertainty → caution or uncertainty → aggression?).
- **Neighbor profile format**: Currently `agent_3 [25]: invest other | invest other you 1x`. Is this format clear enough? Does the model correctly parse dominant behavior vs interaction history?

## Spatial Structure

- **Spatial radius interaction with reasoning depth**: Does L3 recursive reasoning matter less when you only have 3 neighbors vs 6? Fewer neighbors = simpler prediction task.
- **Dynamic neighborhoods**: Currently fixed spatial structure. Should agents be able to "move" or should neighborhoods shift?

## Reasoning Depth Manipulation

- **L0 instruction**: Currently None (no reasoning block). L0 uses `enable_thinking=False` at model level. TextGrad confirmed: no prompt instruction needed.
- **Thinking budget as continuous variable**: Qwen3.5 supports `thinking_budget` parameter. Could replace discrete L0-L3 with continuous reasoning depth (0 / 512 / 2048 / 8192 tokens). Pro: finer-grained. Con: less interpretable, harder to connect to K-level theory.

---

*Last updated: 2026-02-28*
