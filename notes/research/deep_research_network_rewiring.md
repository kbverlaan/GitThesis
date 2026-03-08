# Dynamic network rewiring in agent-based game-theoretic simulations

**No existing work combines LLM agents, K-level reasoning, and co-evolutionary network dynamics — placing this thesis at a genuinely novel intersection of three active research frontiers.** The literature on strategy–network coevolution is mature (100+ papers since 2002), converging on a robust finding: dynamic topology promotes cooperation when rewiring is sufficiently fast, strategy-dependent, and allows positive assortment. However, all models assume simple strategies (cooperate/defect), never cognitive hierarchy. Meanwhile, the LLM multi-agent game theory literature (2023–2025) universally uses fixed pairings or well-mixed populations. The proposed thesis design — varying reasoning depth, enforcement mechanisms, and network structure simultaneously — fills three distinct gaps at once.

---

## 1. The ten papers that define this field

The co-evolutionary game theory literature begins with **Zimmermann, Eguíluz & San Miguel (2004, *Phys. Rev. E* 69:065102)**, who first modeled agents playing Prisoner's Dilemma on an adaptive network where dissatisfied players sever links and rewire randomly. This produced the foundational finding that cooperators self-organize into hubs while defectors become peripheral — **the first demonstration that hierarchy emerges endogenously from strategy–topology coevolution**.

**Santos, Pacheco & Lenaerts (2006, *PLoS Comput. Biol.* 2:e140)** formalized the key mechanism: cooperators facing defectors can sever the link with probability *w* and reconnect randomly. They demonstrated that cooperation prevails across all three social dilemmas (PD, Snowdrift, Stag Hunt) when the **timescale ratio** between strategy updating and link rewiring exceeds a critical threshold. This paper established the framework that most subsequent work builds upon.

**Pacheco, Traulsen & Nowak (2006, *Phys. Rev. Lett.* 97:258103)** introduced "Active Linking," where link formation and dissolution rates depend on strategy pairs (CC, CD, DD links). In the fast-linking limit, the effective payoff matrix transforms — a PD can become a coordination game. This provided the first **analytical solution** to why dynamic topology promotes cooperation and formalized the timescale separation approach to the simultaneity problem.

**Gross & Blasius (2008, *J. R. Soc. Interface* 5:259–271)** reviewed adaptive networks across disciplines, identifying four universal hallmarks: complex dynamics, robust topological self-organization, formation of distinct topological classes, and sensitivity near phase transitions. This cross-disciplinary review anchored co-evolutionary game theory within the broader adaptive networks framework.

**Ohtsuki, Hauert, Lieberman & Nowak (2006, *Nature* 441:502–505)** derived the elegantly simple rule **b/c > k**: cooperation is favored when benefit-to-cost ratio exceeds average degree. Allen, Lippner, Chen et al. (2017, *Nature* 544:227–230) generalized this to arbitrary weighted graphs using coalescent theory, computing critical b/c thresholds for any population structure.

**Rand, Arbesman & Christakis (2011, *PNAS* 108:19193–19198)** provided the crucial experimental validation with human subjects: cooperation was sustained at high levels **only** in "fluid" dynamic networks with frequent rewiring. Static, random, and "viscous" (slowly updating) networks all saw cooperation decay. This established that mere dynamism is insufficient — **rewiring frequency must cross a threshold**.

Three additional papers complete the essential landscape. **Van Segbroeck, Santos, Lenaerts & Pacheco (2009, *Phys. Rev. Lett.* 102:058105)** showed that **behavioral diversity in rewiring responses** — agents differing in how quickly they sever adverse ties — always promotes cooperation, a finding directly relevant to LLM agents with heterogeneous reasoning. **Akçay (2018, *Nature Comms* 9:2692)** provided the critical cautionary result: cooperation can select for network behaviors that *destroy* cooperative clusters, creating negative feedback loops that collapse cooperation. And **Su, McAvoy & Plotkin (2023, *Nature Comput. Sci.* 3:763–776)** proved analytically that transitions among network structures can favor cooperation **even when each individual static configuration would inhibit it** — temporal variation itself is a cooperation mechanism.

---

## 2. A taxonomy of rewiring rules reveals two dominant approaches

The literature contains at least eleven distinct rewiring mechanisms, but two dominate overwhelmingly. These can be organized by what information triggers rewiring and what determines the new connection target.

**Strategy-dependent rewiring** (the most studied mechanism) severs links based on a neighbor's observed strategy. In the canonical Santos et al. (2006) formulation, a cooperator linked to a defector breaks the connection with probability *w* per round. This requires only strategy observability — not payoff information — and has direct experimental support from Rand et al. (2011) and Fehl, van der Post & Semmann (2011, *Ecology Letters* 14:546–551). Its simplicity, robustness, and experimental validation make it the default choice in the literature.

**Payoff/utility-based rewiring** drops the neighbor yielding the lowest cumulative payoff, following Zimmermann et al. (2004) and Eguíluz, Zimmermann, Cela-Conde & San Miguel (2005, *Am. J. Sociology* 110:977–1008). This is more information-intensive (requiring payoff observation) but naturally handles continuous-payoff games where binary cooperate/defect labels don't apply — **directly relevant to the thesis's six-action resource game with percentage-based economy**.

Beyond these two, the literature documents several alternatives. **Reputation-based rewiring** (Fu, Hauert, Nowak & Wang, 2008, *Phys. Rev. E* 78:026117) severs links with lowest-reputation neighbors and reconnects via triadic closure to the highest-reputation agent's partners. This outperforms random reconnection and combines indirect reciprocity with network dynamics. **Active linking** (Pacheco et al., 2006) assigns strategy-pair-dependent birth/death rates to links — CC links are long-lived, CD links are fragile — producing analytically tractable dynamics. **Aspiration-based rewiring** (building on Posch, Pichler & Sigmund, 1999, *Proc. R. Soc. B* 266:1427; and Zhou et al., 2021, *Nature Comms* 12:3548) triggers rewiring when an agent's own payoff falls below an aspiration threshold, requiring only self-evaluation without neighbor comparison. **Behavioral diversity models** (Van Segbroeck et al., 2009) assign heterogeneous rewiring propensities — some agents break bad ties quickly, others tolerate them — and show diversity itself promotes cooperation. **Strategy-independent rewiring** (Szolnoki & Perc, 2009, *EPL* 86:30007) deletes edges when players change strategy and adds random edges at fixed intervals, demonstrating that even neutral rewiring can induce multilevel selection and promote cooperation.

Less common mechanisms include **reinforcement-learning-based link weighting** (Skyrms & Pemantle, 2000), where interaction probabilities evolve via Pólya-urn dynamics; **link weight coevolution** (Huang et al., 2015, *Sci. Rep.* 5:14783), where edge weights rather than topology change; **preferential attachment rewiring** (Poncela et al., 2008, *PLoS ONE* 3:e2449), reconnecting proportional to target degree; and **mutual consent** models requiring both parties to agree on link formation.

For the thesis's six-action game, **payoff-based rewiring is most appropriate** because actions cannot be cleanly classified as "cooperate" or "defect" — the six actions (invest self, invest other, arm self, arm other, attack, do nothing) create a continuous hostility spectrum that payoff evaluation naturally captures. A Schelling-type threshold variant — rewire if >k% of neighbors performed hostile actions (arm other, attack) in the last *n* rounds — offers a clean hybrid that leverages the action semantics without requiring full payoff observability.

---

## 3. What dynamic topology does to cooperation, conflict, and hierarchy

The literature converges on three robust findings, one critical caveat, and one understudied phenomenon.

**Dynamic topology reliably promotes cooperation** when three conditions hold: rewiring is sufficiently fast relative to strategy dynamics (Santos et al., 2006; Pacheco et al., 2006; Rand et al., 2011), link-breaking is at least partially conditioned on partner behavior or outcomes (not purely random), and agents can form new connections with some positive probability. The mechanism is **positive assortment**: cooperators cluster together while defectors become isolated, amplifying the payoff advantage of mutual cooperation. Santos & Pacheco (2005, *Phys. Rev. Lett.* 95:098104) showed that even on static networks, degree heterogeneity (as in scale-free networks) promotes cooperation across the entire parameter range for both PD and Snowdrift games — hubs become cooperation nuclei that anchor cooperative clusters (Gómez-Gardeñes, Campillo, Floría & Moreno, 2007, *Phys. Rev. Lett.* 98:108103).

**The effect is game-dependent.** Hauert & Doebeli (2004, *Nature* 428:643–646) demonstrated that spatial structure *inhibits* cooperation in the Snowdrift game for a wide parameter range — overturning the assumption that structure universally helps. Roca, Cuesta & Sánchez (2009, *Phys. Life Rev.* 6:208–249) showed that **update rules matter as much as topology**: the same network yields opposite results under different strategy-update mechanisms (synchronous vs. asynchronous, death-birth vs. birth-death). This means the thesis must report its update protocol precisely.

**Hierarchy and social differentiation emerge endogenously.** Eguíluz et al. (2005) found that co-evolutionary dynamics on adaptive networks produce three emergent roles: leaders (high-connectivity cooperators), conformists, and exploiters. The network self-organizes into small-world topology with strong hierarchical structure. **Leaders are essential for sustaining cooperation; disrupting them triggers cascading social crises.** This finding maps directly onto the thesis's interest in emergent social order.

The critical caveat comes from **Akçay (2018)**: successful cooperation can evolve to select for increased random connectivity, which dissolves the cooperative clusters that enabled cooperation in the first place. This negative feedback loop can cause cooperation to **collapse cyclically** unless exogenous constraints (connection costs, social inheritance) stabilize the network. For a 50-round simulation, this suggests monitoring for late-round cooperation collapse as networks restructure.

Phase transitions are ubiquitous. The benefit-to-cost threshold **b/c > k** (Ohtsuki et al., 2006) provides a clean prediction for static networks. For dynamic networks, the **timescale ratio** W = T_strategy/T_rewiring is the critical parameter, with cooperation favored above a game-dependent threshold (Santos et al., 2006; Pacheco et al., 2006). Su et al. (2023) proved that temporal network variation is itself a cooperation mechanism — transitions among configurations can favor cooperation even when no single configuration would.

---

## 4. Implementation patterns from the computational literature

The practical design space for dynamic network simulations involves six decisions, each with a clear consensus in the literature.

**Update timing.** Asynchronous updating dominates: at each Monte Carlo step, one random agent is selected to potentially rewire and/or update strategy. The **timescale ratio** *w* controls the relative frequency of rewiring vs. strategy events. In the Santos et al. (2006) framework, each step involves either a strategy update (probability 1−*w*) or a rewiring event (probability *w*), with *w* as the key tunable parameter. For the thesis's round-based structure, implementing one rewiring opportunity per agent per round with probability *w* is the most natural adaptation.

**Edge operations.** The standard approach is **break-one-make-one**: an agent severs one existing edge and forms one new edge, conserving total edges. This prevents network dissolution or densification artifacts. With N=30 agents, degree can range 0–29; conserving edges keeps the network in a manageable regime.

**Initial network seeding.** The most common choices are **regular random graphs** (fixed degree *k*, used by Santos et al., 2006; Fu et al., 2008) and **Erdős–Rényi G(n,p)** random graphs (Pacheco et al., 2006). For N=30, a regular random graph with *k*=4–6 is standard and defensible. Starting from different topologies (lattice, Erdős–Rényi, scale-free) as an experimental condition tests initial topology sensitivity.

**New connection targets.** Uniform random selection from non-neighbors is the default (Santos et al., 2006). Fu et al. (2008) showed that **triadic closure** (connecting to a friend-of-friend) outperforms random reconnection for promoting cooperation. Preferential attachment (connecting proportional to target degree) generates scale-free topology but creates extreme hubs. For an exogenous mechanism in the thesis, uniform random is simplest and most conservative; triadic closure is a strong alternative.

**Degree constraints and disconnection.** Most models allow variable degree but conserve total edges. For N=30, disconnected components are a real risk. Three solutions exist: enforce minimum degree ≥ 1, only allow rewiring when degree > 1, or treat isolated agents as "loners" who receive no game interactions. The first option is simplest and most common.

**Edge properties.** Unweighted, undirected edges dominate the evolutionary game theory literature (>90% of papers). Weighted edges appear primarily in the reinforcement-learning tradition (Skyrms & Pemantle, 2000) and link-weight coevolution models (Huang et al., 2015). For the thesis, **unweighted undirected edges** are standard and sufficient.

---

## 5. Three distinct gaps converge on this thesis

The literature reveals three significant gaps that the proposed thesis uniquely addresses.

**Gap 1: K-level reasoning has never been placed on structured populations.** Cognitive Hierarchy Theory (Camerer, Ho & Chong, 2004) has been studied in well-mixed evolutionary settings (Gracia-Lázaro, Floría & Moreno, 2017, *Games* 8:1) and Bayesian Theory of Mind has been evolved via replicator dynamics (Devaine, Hollard & Daunizeau, 2014, *PLoS ONE* 9:e87619; Kleiman-Weiner, Vientós, Rand & Tenenbaum, 2025, *PNAS* 122:e2400993122). Mosleh & Rand (2018, *Sci. Rep.* 8:6293) placed dual-process cognition on static networks. But **no paper combines K-level or cognitive hierarchy agents with any network structure**, let alone dynamic/co-evolutionary networks. The question "Does network stability depend on agent sophistication?" is completely unanswered.

**Gap 2: LLM multi-agent game theory uses no dynamic network topology.** A comprehensive search of the 2023–2025 literature reveals that every LLM game-theoretic simulation uses either fixed pairings (Akata et al., 2023), well-mixed populations (Willis et al., 2025, AAMAS; Piatti et al., 2024, NeurIPS), or spatial proximity without explicit rewiring (Park et al., 2023). The closest work is **Papachristou & Yuan (2025, *PNAS Nexus* 4:pgaf317)**, which shows LLM agents naturally reproduce preferential attachment and triadic closure in network formation tasks — but studies network formation, not strategy–topology coevolution in games. The Concordia framework (Vezhnevets et al., 2023, DeepMind) architecturally supports dynamic networks but no published experiment implements game-outcome-dependent rewiring.

**Gap 3: The intersection of all three — LLM agents + cognitive hierarchy + co-evolutionary networks — is entirely unexplored.** The co-evolutionary literature (Santos, Pacheco, Perc, Szolnoki) always uses simple C/D strategies. The cognitive hierarchy literature always uses well-mixed populations. The LLM literature always uses static interaction structures. No work bridges any two of these three frontiers simultaneously, let alone all three.

This gap structure means the thesis can make a **genuinely novel contribution** even with conservative design choices. Simply demonstrating how K-level reasoning depth interacts with dynamic network topology in an LLM multi-agent setting would be the first result of its kind.

---

## 6. Temporal network metrics for a 50-round, 30-agent simulation

Analyzing dynamic networks requires metrics beyond static snapshots. The temporal network analysis literature (anchored by Holme & Saramäki, 2012, *Physics Reports* 519:97–125; Nicosia et al., 2013, in *Temporal Networks*, Springer) provides a rich toolkit, of which five metrics are essential for this thesis.

**Edge persistence** measures how long partnerships endure — computed as the number of consecutive rounds an edge exists. Correlating persistence with agent strategy type directly tests whether cooperative partnerships are more durable than exploitative ones. **Jaccard similarity** between successive network snapshots J(G_t, G_{t+1}) = |E_t ∩ E_{t+1}| / |E_t ∪ E_{t+1}| provides a normalized [0,1] stability measure per round, and per-node neighborhood Jaccard captures individual agents' relationship volatility. Both are trivially computed from adjacency matrices.

**Multislice community detection** (Mucha, Richardson, Macon, Porter & Onnela, 2010, *Science* 328:876–878) generalizes modularity optimization to temporal networks by coupling snapshots via identity links across time slices. This enables tracking coalition formation, merging, splitting, and dissolution across all 50 rounds — directly operationalizing "emergent social order." The GenLouvain algorithm implements this efficiently.

**Temporal motifs** (Kovanen, Karsai, Kaski, Kertész & Saramäki, 2011, *J. Stat. Mech.* P11005) identify recurring temporally-ordered interaction patterns among small node groups. With 30 agents, 2–3 node motifs are computationally tractable and can reveal reciprocity patterns, exploitation chains, and information cascading structures. **Network entropy** of the degree distribution H(t) = −Σ p(k) log p(k) tracks structural complexity over time, with declining entropy indicating crystallization of coalitions and rising entropy signaling network disruption.

The Python packages **teneto** (temporal degree centrality, volatility, burstiness), **pathpy** (higher-order paths, causal structure), and **NetworkX** (per-snapshot static metrics) together cover the complete analysis pipeline. GenLouvain (via MATLAB or Python port) handles multislice community detection. All computations are trivially tractable at the 30-node, 50-round scale.

---

## Recommended design for the thesis

Based on the full literature review, the most defensible design combines established mechanisms with the thesis's unique features.

**Rewiring rule: Payoff-based with hostility threshold.** Given the six-action game where strategies cannot be classified as simple cooperate/defect, pure strategy-dependent rewiring (Santos et al., 2006) does not apply directly. Instead, implement a **hybrid payoff-hostility rule**: each round, with probability *w*, the simulation engine evaluates each agent's neighborhood and severs the edge to the neighbor who either (a) yielded the lowest cumulative payoff over the last *n* rounds (utility-based, following Zimmermann et al., 2004) or (b) performed the most hostile actions (arm other, attack) toward the focal agent over the last *n* rounds (threat-based). The new connection target should be selected **uniformly at random** from non-neighbors, as this is the most conservative and well-studied default. This hybrid is defensible because it directly adapts two established mechanisms — payoff-based (Zimmermann et al., 2004) and strategy-conditioned (Santos et al., 2006) — to the thesis's richer action space.

**Rewiring as independent variable.** Vary the rewiring probability *w* ∈ {0, 0.05, 0.3, 1.0} as one condition, mapping to the static → viscous → fluid → fully dynamic spectrum identified by Rand et al. (2011). This directly tests the timescale ratio's effect alongside reasoning depth (L0–L3) and enforcement mechanisms.

**Initial network: Erdős–Rényi G(30, p) with expected degree ⟨k⟩ ≈ 4–6.** This is standard, well-understood, and appropriate for N=30. Ensure the initial graph is connected. Consider also testing k-regular random graphs for comparison, as these are the most common baseline in the Santos/Pacheco tradition.

**Implementation protocol.** Use asynchronous updating with break-one-make-one edge conservation. Enforce minimum degree ≥ 1 to prevent disconnected agents. Apply rewiring **between** game rounds (not during), which naturally implements the alternating-update approach used by Santos et al. (2006) and Fu et al. (2008). This cleanly separates game dynamics from network dynamics while allowing feedback between them.

**Analysis pipeline.** Report per-round Jaccard similarity, edge persistence distributions, multislice community structure (Mucha et al., 2010), degree entropy time series, and network volatility. Correlate all network metrics with reasoning depth (L0–L3) to test the novel question: does network stability depend on agent sophistication?

This design is conservative in its individual components — every element has strong precedent — while being genuinely novel in its combination. The three-way factorial (reasoning depth × enforcement mechanism × network dynamics) with 20 replications per cell provides the statistical power to detect interaction effects that no prior study has been positioned to examine.