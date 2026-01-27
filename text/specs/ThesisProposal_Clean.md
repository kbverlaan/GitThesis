# The Origins of Order

**Do stable power structures emerge from material constraints alone, or do they require semantic understanding?**

Koen Verlaan  
Master Computational Science Thesis Proposal  
January 2026

---

## The Question

Complex political orders—stable alliances, hierarchies, balance-of-power dynamics—are typically attributed to high-level human cognition: trust, loyalty, moral reasoning, or deliberate institutional design. This research asks whether such structures can emerge from pure optimization under material constraints, without any semantic understanding of social concepts.

**Central Hypothesis**: Stable social structures emerge from the physics of power (resource constraints and transaction costs), rendering semantic understanding of concepts like "loyalty" or "betrayal" unnecessary for their formation.

---

## The Experiment

We test this by comparing fundamentally different agent architectures in an identical environment:

### Agent Types
1. **RL Agents (PPO)**: Pure utility maximizers with no semantic knowledge
2. **RL Agents (PPO + LSTM)**: Memory-enabled optimizers  
3. **LLM Agents (Semantic)**: Prompted with social concepts ("You are a clan leader. Loyalty matters. Betrayal has consequences.")
4. **LLM Agents (Control)**: Semantically stripped ("You are Node 4. Maximize variable U.")

### The Environment: "The Lattice"

A minimal multi-agent game where agents choose between:
- **INVEST**: Pay 1 utility to strengthen a bond with another agent
- **THREATEN**: Demand tribute from another agent
- **YIELD or FIGHT**: When threatened, pay tribute or risk conflict

**Core Mechanisms**:

*Material constraints*:
- **Conflict cost (c)**: War is expensive—both parties pay a fixed cost
- **Probabilistic combat**: Power determines win probability via sigmoid function
- **Income**: Agents earn utility equal to the sum of their bond strengths each turn

*Implicit coalition power*:
- When conflict occurs, each side's power = their utility + sum of all their bond strengths
- Bonds represent *latent support*—not explicit coordination, but structural backing
- Strong bonds make you more powerful in conflict, even without active "help" from allies

**Key design insight**: There are no coalition action choices, no "call for help" buttons. Bonds affect combat outcomes automatically. This tests whether agents will *still* build stable relationships purely because doing so increases their structural power—whether they understand "alliance" as a concept or simply learn "high bonds = good for me."

---

## What Makes This Strong

**No explicit coordination required**: Unlike models with coalition formation mechanics, bonds here are pure investment decisions. There's no agreement phase, no explicit promise-keeping. This isolates the fundamental question: will agents build stable relationships purely from material incentives?

**The shadow of the future is minimal**: Bonds help you win fights, and winning fights is good. But building bonds costs resources. The only reason to maintain relationships is if you anticipate future conflicts where that support matters. This is the essence of political order—sacrificing immediate gains for structural position.

**The semantic test is clean**: 
- RL agents see: "I have bond values with others. Higher bonds increase my win probability."
- LLM agents might think: "These are alliances. I should be loyal to allies and wary of betrayers."

If both produce the same patterns—stable bond networks, balanced coalitions, hierarchy—then semantic concepts like "loyalty" are descriptive, not generative.

---

## What We Measure

**Structural outcomes**:
- **Gini coefficient**: Inequality in utility distribution
- **Bond network topology**: Clustering, centralization, balance
- **Stability**: How long do bond relationships persist?
- **Turnover**: How often does the power ranking change?

**Behavioral patterns**:
- **Investment frequency**: How much do agents invest vs threaten?
- **Conflict rates**: How often do threats escalate to war?
- **Bond concentration**: Do agents diversify bonds or concentrate them?

**Power metrics**:
- **Structural criticality**: Simulated removal—how much does the system change?
- **Leverage**: How much do an agent's bonds swing conflict outcomes?
- **Extraction efficiency**: Tribute gained vs costs paid

---

## Expected Outcomes

Three possible regimes:

| Pattern | Gini | Conflict Rate | Bond Stability | Interpretation |
|---------|------|---------------|----------------|----------------|
| **Hobbesian Anarchy** | Low | High | Low | No stable structure; constant war |
| **Balance of Power** | Medium | Low | High | Stable multipolar alliances |
| **Imperial Hegemony** | High | Low | High | One dominant agent; stable vassalage |

**Key Hypotheses**:

**H1 (Memory is external)**: No significant difference between Markovian RL and LSTM RL
- *Reasoning*: Bond matrix is observable—memory is externalized in the structure itself

**H2 (Semantic priors matter)**: LLM (Semantic) shows higher bond stability and lower conflict than RL agents
- *Reasoning*: Semantic priors ("loyalty is good") act as an equilibrium selection mechanism

**H3 (Physics dominates culture)**: At high conflict cost (c > 5), all agent types converge to similar structures
- *Reasoning*: When war is sufficiently expensive, material constraints force cooperation regardless of cognitive architecture

---

## Why This Matters

**For Political Science**: Provides computational validation of structural realism (Waltz, Mearsheimer). Can balance-of-power dynamics emerge without culture or institutions? Is anarchy really the fundamental driver?

**For AI Research**: Tests Silver et al.'s "Reward is Enough" hypothesis. Does social intelligence require semantic understanding, or does it emerge from scalar reward optimization in structured environments?

**For Philosophy of Social Science**: Addresses the structure-agency debate empirically. Do material conditions determine social order (Marx, Waltz), or do ideas and culture shape outcomes (constructivism)?

---

## Methodology

**Phase 1: Environment validation** (2 weeks)
- Confirm environment stability across parameter ranges
- Establish that multiple equilibria exist (not just one trivial outcome)

**Phase 2: RL training** (3-4 weeks)
- Train PPO agents (Markovian and LSTM) to convergence
- Sweep over conflict cost parameter c ∈ [2, 3, 5, 7, 10]
- Run 30+ episodes per condition

**Phase 3: LLM deployment** (2-3 weeks)
- Deploy Llama-3 agents (semantic and control prompts)
- Same parameter sweep
- 30+ episodes per condition

**Phase 4: Analysis** (2 weeks)
- Compare structural outcomes across agent types
- Statistical testing for significance
- Analyze whether convergence depends on friction parameter

---

## Core Contribution

This research isolates whether **semantic understanding is causally necessary** for emergent social order. By eliminating explicit coordination mechanics and using agents with fundamentally different cognitive architectures under identical material constraints, we can test:

1. **Generative sufficiency**: Are material incentives alone sufficient to produce stable hierarchies?
2. **Semantic superfluity**: Do concepts like "loyalty" and "betrayal" add functional value, or are they post-hoc narratives?
3. **Structural determinism**: Do high friction costs force cooperation regardless of agent cognition?

If mindless optimizers build the same alliance networks as semantically-aware agents, it suggests that political order emerges from the physics of power—not from culture, norms, or shared understanding. The narratives we tell about loyalty and betrayal would be epiphenomenal descriptions of structurally determined behavior.

If semantic agents reliably coordinate where optimization fails, it suggests that culture and shared concepts solve problems that material incentives alone cannot.

Either way, we learn something fundamental about the origins of order.
