# Thesis Proposal Development Log

**Project**: Master Thesis in Computational Science
**Author**: Koen Verlaan
**Started**: January 2026

---

## 2026-01-28: Major Framing Evolution

### Session Overview
Extended working session refining the research question through three major iterations. Started with IR theory framing, ended with emergent social structures framing.

---

### Version 1: Neorealism vs Constructivism

**Initial Framing:**
- "30 years since Wendt challenged Waltz..."
- RL agents = Neorealist actors (optimize relative gains)
- LLM agents = Constructivist actors (identity/norms)
- RQ: "Do neorealist and constructivist agents produce different outcomes?"

**Problem Identified (via external chatbot critique):**
This framing is **circular**. We define RL agents to optimize relative gains and LLM agents to reason about identity/norms. Of course they'll diverge - we built divergence into the design.

**The Confounding Problem:**
Two variables changing simultaneously:
1. Decision-making architecture (optimization vs semantic reasoning)
2. Goal structure (relative gains vs identity/norms)

If divergence occurs, which variable caused it?

---

### Version 2: Security Dilemma Escape

**Revised Framing:**
- Focus on ONE theoretical problem: the security dilemma
- RQ: "Can semantic reasoning escape security dilemmas that trap optimization?"
- Two-comparison design introduced:
  - Comparison 1: RL vs LLM-Control (architecture effect)
  - Comparison 2: LLM-Control vs LLM-Constructivist (framing effect)

**Key Insight:**
The LLM-Control condition (which I already had!) solves the confounding problem. It uses LLM architecture but with materialist goal framing - same goal as RL, different reasoning process.

**Problem Identified:**
Security dilemma framing is **too narrow**. My game can produce much richer emergent structures:
- Bilateral cooperation
- Multilateral coalitions
- Coalition wars
- Free-riding
- Hierarchy emergence
- Norm formation
- Polarization

The security dilemma lens (dyadic trust breakdown) only captures a fraction of this.

---

### Version 3: Emergent Social Structures (Final)

**Final Framing:**
- Position as extending Axelrod's cooperation work into semantic reasoning era
- RQ: "Do semantic priors enable qualitatively different emergent social structures than pure optimization?"
- All agents optimize **absolute resources** (not relative position)
- Measure: coalitions, cooperation, hierarchy, conflict, norms, network structure

**Why This Is Stronger:**

1. **Builds on established literature**: Axelrod showed optimizers CAN cooperate. I extend: do semantic reasoners cooperate DIFFERENTLY?

2. **Captures full game richness**: My game enables coalitions, hierarchy, norms - not just "escaping arms races"

3. **Results interesting either way**:
   - LLMs cooperate more → semantic priors matter
   - LLMs cooperate similarly → optimization dominates
   - LLMs cooperate less → semantic priors introduce biases

4. **Multiple audiences**: AI/ML, computational social science, game theory, complexity science

5. **Not circular**: Same goal, different reasoning - divergence is about architecture, not baked-in differences

---

### Key Design Decisions

**Reward Function Change:**
- OLD: Optimize relative position (my resources vs others)
- NEW: Optimize absolute resources (my resources)

Why? Absolute resources makes cooperation naturally attractive (positive-sum possible). Tests whether agents DISCOVER cooperation rather than being forced away from it. Divergence becomes more meaningful.

**Two-Comparison Design (preserved from v2):**

| Comparison | Agents | Same | Different | Tests |
|------------|--------|------|-----------|-------|
| 1 | RL vs LLM-Control | Goal (resources) | Architecture | Does semantic reasoning itself matter? |
| 2 | LLM-Control vs LLM-Constructivist | Architecture | Framing | Do identity/norm priors add something? |

**Interpretation Matrix:**

| RL vs LLM-Control | Control vs Constructivist | Interpretation |
|-------------------|---------------------------|----------------|
| Converge | Converge | Material incentives dominate all |
| Converge | Diverge | Framing matters, not architecture |
| Diverge | Converge | Architecture matters, not framing |
| Diverge | Diverge | Both architecture AND framing matter |

---

### Theoretical Grounding (Compressed)

**Don't need full IR theory review.** Frame around cooperation literature:

**Background:**
Axelrod (1984) showed optimizers can achieve cooperation through repeated interaction. But this cooperation is mechanistic - agents stumble into equilibria without "understanding" cooperation.

**Question:**
LLMs bring semantic priors: norm recognition, identity formation, narrative interpretation. Do these enable qualitatively different social structures?

**Two Hypotheses:**
1. **Optimization Dominance**: Material incentives determine outcomes regardless of reasoning. RL and LLM converge.
2. **Semantic Enhancement**: Semantic priors enable richer cooperation that pure optimization cannot achieve.

---

### Game Design Rationale

The game naturally enables emergent structures without forcing them:

| Action | Effect | Enables |
|--------|--------|---------|
| Invest-Self | Resource growth | Accumulation |
| Invest-Other | Transfer resources | Trust signaling, cooperation |
| Arm-Self | Military capability | Threat, defense, ambiguity |
| Arm-Other | Alliance formation | Coalitions, commitment |
| Attack | Resource appropriation | Conflict, hierarchy |

**General Sufficiency Principle**: Minimal elements, maximal emergence potential. The AGENTS determine what structures emerge, not the game mechanics.

---

### Metrics (Expanded for v3)

**Coalition Dynamics:**
- Number of distinct coalitions
- Coalition stability (duration)
- Coalition formation speed
- Inter vs intra-coalition conflict

**Cooperation Patterns:**
- Investment frequency (self vs other)
- Reciprocity rate
- Trust persistence
- Network density

**Hierarchy/Dominance:**
- Gini coefficient over time
- Hub emergence (centrality)
- Tributary relationships

**Conflict Dynamics:**
- Attack frequency
- Betrayal rate
- Arms race indicators

**Norm Emergence:**
- Implicit rule development
- In-group/out-group treatment
- LLM reasoning trace analysis

**Network Structure:**
- Modularity
- Clustering
- Evolution over time

---

### Publication Positioning

**Stronger with v3 framing because:**

1. **Novel contribution is clear**: Not just "comparing RL vs LLM" but asking what semantic priors ADD to cooperation dynamics

2. **Builds on established work**: Axelrod is foundational - you're extending it, not starting from scratch

3. **Multiple audiences**:
   - AI/ML: "How do LLM agents differ from RL in multi-agent coordination?"
   - Computational Social Science: "Do semantic priors enable institutional emergence?"
   - Complexity/ABM: "Emergent structures from different agent architectures"
   - Game Theory: "Beyond Axelrod - semantic reasoning in repeated games"

4. **Results robust**: Any outcome is publishable (convergence, divergence in either direction)

---

### Potential Reviewer Concerns + Responses

**"Why these specific LLM prompts?"**
→ Clear prompt design rationale. LLM-Control = minimal framing. LLM-Constructivist = identity/norms.

**"Is this just prompt engineering?"**
→ LLM-Control isolates architecture from framing. If RL ≠ LLM-Control, it's architecture, not prompts.

**"How do you know it's semantic priors vs different exploration?"**
→ Analyze LLM reasoning traces. What ARE they reasoning about when they cooperate?

**"Why not existing cooperation benchmarks?"**
→ Existing benchmarks test OUTCOME. We test MECHANISM and STRUCTURE.

---

### Next Steps

1. Rewrite abstract around "semantic priors + emergent structures"
2. Rewrite context around cooperation literature (Axelrod), not IR theory
3. Update methods with absolute resource optimization and expanded metrics
4. Position significance as extending Axelrod into semantic reasoning era
5. Keep two-comparison design throughout

---

### Lessons Learned

1. **Start with the mechanism, not the theory**: The game mechanics create interesting dynamics. The theory explains why they matter.

2. **Control conditions matter**: LLM-Control was already in my design but I buried it. It's actually the key to scientific rigor.

3. **Broader is often better**: "Emergent social structures" > "security dilemma escape" > "neorealism vs constructivism"

4. **Same goal, different reasoning**: This is the clean comparison. Different goals confounds the experiment.

5. **External critique is valuable**: The chatbot critique about confounding variables fundamentally improved the design.

---

## Future Log Entries

(Add entries as the thesis progresses)

---
