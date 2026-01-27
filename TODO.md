# Proposal Draft TODO - Due Friday

**Goal:** Complete draft for supervisor discussion

---

## ✅ MUST-HAVE (Priority 1)

### 1. Introduction Section - Clean Up
- [ ] Polish Realism vs Constructivism framing (use Wikipedia if needed)
- [ ] Add 1-2 sentences on why this matters (theoretical gap + practical relevance)
- [ ] **Fix LLM → Constructivism mapping** (resolve "Merk dat ik moeite heb...")
  - Write 2-3 sentences: LLMs interpret meaning from interactions, construct narratives about relationships, act based on semantic understanding of history
- [ ] Consider adding "Reward is Enough" reference for RL agents
- [ ] Remove all Dutch placeholder notes and brackets

### 2. Research Question - Define Hierarchy
- [ ] **Operationalize "hierarchy"** (your remark: "What is hierarchy? How do I measure that?")
  - Write 2-3 sentences: Hierarchy = persistent resource inequality + stable power relations
  - Measured by: Gini coefficient, network centrality, coalition stability
- [ ] Review and sharpen subquestions
- [ ] Verify H1-H3 are testable and aligned with main RQ

### 3. Literature Review Section - ADD NEW SECTION ⚠️
- [ ] **Theoretical Foundations** (2-3 paragraphs):
  - Waltz on structural realism (Wikipedia + your understanding)
  - Wendt on constructivism (your notes + Wikipedia)
  - The debate between them
- [ ] **Computational Approaches to Social Phenomena** (1-2 paragraphs):
  - Axelrod's Evolution of Cooperation
  - Epstein's Sugarscape
  - Agent-based modeling of social dynamics
- [ ] **LLMs as Social Agents** (1-2 paragraphs):
  - Generative Agents (Park et al.)
  - Recent work on LLM multi-agent systems
  - Why LLMs are suitable for modeling semantic reasoning

### 4. Methodology - Expand Three Condition Design
- [ ] Add 1 paragraph explaining simulation design choices:
  - Why Invest/Defend/Attack actions?
  - Why is this minimal setup sufficient?
- [ ] **Expand Three Condition Design** (currently just bullets):
  - [ ] Pure RL: 2-3 sentences (PPO? LSTM-PPO? Implementation details)
  - [ ] Semantic LLM: 2-3 sentences (constructivist prompting strategy)
  - [ ] Control LLM: 2-3 sentences (optimization/realist prompting strategy)

### 5. Metrics and Analysis Section - ADD NEW SECTION ⚠️
- [ ] **Structural Metrics:**
  - Resource inequality (Gini coefficient)
  - Network structure (centralization, clustering coefficient)
  - Coalition stability (duration of alliances)
- [ ] **Behavioral Metrics:**
  - Conflict frequency
  - Cooperation rate (investment in others)
  - Defense patterns
- [ ] **Identity/Role Metrics:**
  - Behavioral consistency over time
  - Role differentiation (classify agents: aggressive/cooperative/neutral)
- [ ] **Statistical Approach:**
  - Comparison method (ANOVA, effect sizes)
  - Number of runs per condition

---

## 📋 NICE-TO-HAVE (Priority 2)

### 6. Expected Outcomes/Implications
- [ ] Add 1 paragraph on what different results would mean:
  - If RL = LLM outcomes → supports Realism
  - If Semantic LLM ≠ RL → supports Constructivism
  - If Control LLM ≈ RL but Semantic LLM ≠ RL → semantic interpretation matters

### 7. Parameter Tuning - Resolve Uncertainty
- [ ] Either: Remove section for now (add during implementation)
- [ ] Or: Reframe as finding parameter ranges where multiple equilibria are possible (not "making RL interesting")

---

## 🔧 POLISH (Priority 3)

### 8. Timeline/Planning
- [ ] Copy relevant parts from `06_planning.md`
- [ ] Adjust based on three-condition design

### 9. References - Format Properly
- [ ] Wendt (1992) - full citation
- [ ] Waltz (1979) - full citation
- [ ] Axelrod (1984) - if mentioned
- [ ] Silver et al. (2021) - "Reward is Enough" if used
- [ ] Generative Agents paper - if mentioned
- [ ] Format all references consistently

### 10. Final Polish
- [ ] Remove all Dutch notes/placeholders
- [ ] Remove uncertainty markers "[Not sure about this one yet]"
- [ ] Read through for narrative coherence
- [ ] Spellcheck
- [ ] Ensure section titles are clear

---

## Time Estimates

- Priority 1 (Must-have): ~4 hours
- Priority 2 (Nice-to-have): ~1.5 hours
- Priority 3 (Polish): ~1 hour

**Total: ~6.5 hours focused work**

---

## Notes

- Focus on Priority 1 items first - these are critical for supervisor discussion
- Use Wikipedia for lit review background (don't dive into new primary sources today)
- Draft doesn't need to be perfect - just complete and coherent
- Can refine based on supervisor feedback Friday
