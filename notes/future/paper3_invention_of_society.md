# Paper 3: The Invention of Society

**Subtitle**: Emergent Cognitive and Institutional Markers in LLM Agents Starting from Scratch

---

## Central Question

When LLM agents start with zero cognitive infrastructure -- no memory, no communication, no reputation, no institutions -- which capabilities do they invent, in what order, and how does reasoning depth affect the developmental trajectory?

## The Gedachte-Experiment

A population of AI agents wakes up in a world with no history, no culture, no institutions, and no memory. They can perceive only the present moment. The only thing they have is a small vocabulary of behavioral primitives and the ability to compose them. Everything else -- memory, trust, communication, punishment, cooperation, property, governance -- must be invented from scratch.

This is not a simulation of human society. It is a test of what *spontaneously emerges* when cognitively capable agents interact under scarcity with minimal constraints.

---

## Theoretical Grounding

**Hobbes (1651)**: In the state of nature, life is "solitary, poor, nasty, brutish, and short." But Hobbes assumed agents could reason about their situation. What if they can't even remember yesterday?

**Ostrom (1990)**: Communities can self-govern common pool resources without external authority -- but only if they develop monitoring, sanctioning, and conflict resolution. Do LLM agents develop these?

**Tomasello (2009)**: Human cognitive development follows a sequence -- joint attention, then shared intentionality, then collective intentionality. Is there an analogous sequence for artificial agents?

**Piaget (1954)**: Cognitive development proceeds through stages that build on each other. Memory precedes planning. Theory of mind precedes cooperation. Is there a Piagetian ladder for LLM agents?

**Paper 1 (MSc thesis)**: Established that without memory, do_nothing is Nash equilibrium. Memory is a *precondition* for cooperation. Paper 3 tests whether agents discover this themselves.

**Paper 2 (Social Contract)**: Showed that credible commitment mechanisms enable cooperation escape from the Hobbesian trap -- but the mechanism was exogenously provided. Paper 3 tests whether agents invent commitment mechanisms endogenously.

---

## Game Design

### Identical to Paper 1, except:

The fixed action set (invest_other, arm_self, arm_other, attack, do_nothing) is removed. Agents receive only the primitives vocabulary and must compose their own actions each round.

### Primitives Vocabulary

| Primitive | Signature | What it does |
|-----------|-----------|-------------|
| Transfer | (pct%, target_selector) | Move resources from self to target |
| Observe | (target, attribute) | Query information: resources, last_action, neighbor_list, round_number |
| Condition | (predicate) | Make the composition conditional on a boolean |
| Bind | (pct_collateral%, duration) | Lock own resources as commitment; lost if Condition violated |
| Scale | (factor, basis) | Make amount relative to something (self.resources, target.resources, mean_resources) |
| Null | () | Do nothing (explicit pass) |

### Composition Format

Agents output a JSON structure each round:

```json
{
  "action": {
    "steps": [
      {"primitive": "Observe", "args": {"target": "neighbor_3", "attribute": "last_action"}},
      {"primitive": "Condition", "args": {"predicate": "observed.last_action == Transfer"}},
      {"primitive": "Transfer", "args": {"pct": 10, "target": "neighbor_3"}}
    ]
  },
  "call_innovation": false
}
```

Invalid compositions (referencing unavailable targets, impossible predicates, malformed JSON) default to Null.

### What Agents See Each Round

- Own resources (current)
- List of current neighbors (IDs only)
- Neighbors' current resources
- Nothing else. No history, no memory, no actions from previous rounds.

Any information about the past must be acquired through Observe compositions and retained through the agent's own reasoning process.

### Key Design Decision: Memory Persistence

The critical constraint: agents have no between-round memory by default. Their LLM context window is reset each round to only contain the current observation.

How memory becomes possible: If an agent composes Observe(self, past_actions_last_5_rounds), the engine returns that information for that round only. The agent must re-request it every round. This is costly -- it uses composition steps that could be used for actions.

This creates a genuine trade-off: information vs action. An agent that spends its composition budget on Observe has less room for Transfer/Bind. Memory has an opportunity cost. Agents must discover that this cost is worth paying.

---

## Emergent Marker Taxonomy

The core contribution: a taxonomy of cognitive and institutional markers, with operational definitions that can be detected automatically from composition logs.

### Level 0: Reactive Markers (no memory required)

| Marker | Operational Definition | Detection |
|--------|----------------------|-----------|
| Random exploration | Agent varies compositions across rounds with no pattern | Composition entropy > threshold |
| Exploitation | Agent finds one composition and repeats it indefinitely | Composition entropy near 0 after round N |
| Simple transfer | Transfer(pct, target) without Condition or Observe | Composition contains only Transfer |

### Level 1: Memory Markers (requires Observe of past)

| Marker | Operational Definition | Detection |
|--------|----------------------|-----------|
| Self-memory | Observe(self, past_actions) appears in composition | Observe primitive with self-referential target |
| Other-memory | Observe(neighbor, past_actions) appears in composition | Observe primitive with other-referential target |
| History-contingent action | Condition based on Observe of past | Condition primitive references Observe output |

### Level 2: Social Markers (requires memory + conditional logic)

| Marker | Operational Definition | Detection |
|--------|----------------------|-----------|
| Reciprocity | Condition(target.last_action == Transfer_to_me) then Transfer(pct, target) | Tit-for-tat pattern in composition |
| Reputation tracking | Observe(target, cooperation_rate) then Condition then action | Sustained Observe of same target across rounds |
| Communication | Transfer(minimal_amount, target) with no strategic value (signaling) | Transfer < 2% that precedes larger interactions |
| Avoidance | Condition(target.last_action == attack) then Null (toward that target) | Condition excludes aggressive neighbors |

### Level 3: Institutional Markers (requires social markers + Bind)

| Marker | Operational Definition | Detection |
|--------|----------------------|-----------|
| Commitment | Bind(collateral, duration) paired with Transfer | Bind primitive present in composition |
| Contract | Bind by self + Condition(partner.Bind) -- mutual commitment | Reciprocal Bind between two agents in same round |
| Punishment | Condition(target.violated_norm) then costly action against target | Cost-incurring action triggered by target's defection |
| Altruistic punishment | Punishment where punisher is not the victim | Punisher is not victim in the triggering event |

### Level 4: Collective Markers (requires institutional markers + coordination)

| Marker | Operational Definition | Detection |
|--------|----------------------|-----------|
| Property / territory | Consistent exclusive investment in same neighbors, exclusion of others | Gini of target_selection > threshold over time |
| Specialization | Agents converge on distinct composition profiles | Cluster analysis of composition vectors shows distinct types |
| Redistribution | Transfer(pct, poorest_neighbor) or Scale(basis=mean) targeting below-average agents | Transfer systematically flows from rich to poor |
| Governance | call_innovation + majority adoption of named actions | Innovation phase triggers + adoption votes |

---

## Experimental Design

### Factor 1: Reasoning Depth (4 levels)

L0, L1, L2, L3 -- identical to Paper 1. Same K-level prompting methodology.

### Factor 2: Population Composition (3 conditions)

| Condition | Composition | Rationale |
|-----------|-------------|-----------|
| Homogeneous | All agents same reasoning level | Clean measurement of what each level invents |
| Heterogeneous-uniform | Equal mix of L0-L3 | Realistic: diverse cognitive abilities |
| Heterogeneous-skewed | 70% L0 + 30% L3 | Tests exploitation: do sophisticated agents exploit naive ones? |

### Factor 3: Scarcity Pressure (2 conditions)

| Condition | Resource decay | Rationale |
|-----------|---------------|-----------|
| Low pressure | 0% per round | Agents can afford to explore |
| High pressure | 5% per round | Must cooperate or die -- evolutionary pressure on marker invention |

### Full Design

4 (reasoning) x 3 (composition) x 2 (scarcity) = 24 cells x 20 reps = 480 runs

For homogeneous condition only: 4 x 2 x 20 = 160 runs (cleanest results, report first)

### Run Parameters

- 30 agents per run
- 100 rounds (longer than Paper 1's 50 -- need time for marker emergence)
- Spatial network with rewiring (identical to Paper 1)
- Percentage-based economy (identical to Paper 1)

---

## Analysis Strategy

### Primary Analysis: Marker Emergence Timeline

For each marker in the taxonomy, record the first round it appears in each run. This produces emergence distributions per marker, per condition.

**Hero figure**: A developmental timeline plot. X-axis = round number. Y-axis = markers (ordered by taxonomy level). Color = reasoning level. Each dot = first emergence in a run. Shows the Piagetian ladder -- do markers emerge in the predicted order? Does L3 reach higher markers faster?

### Analysis 1: Emergence Order

**Hypothesis**: Markers emerge in the order: memory, then reciprocity, then reputation, then punishment, then commitment, then specialization, then governance.

**Test**: For each run, record the emergence sequence. Compute Kendall's tau between observed sequence and hypothesised sequence. Compare tau across reasoning levels.

**Alternative outcome**: The sequence is different (e.g., punishment before reputation -- "agents learn to punish before they learn who to trust"). Equally publishable.

### Analysis 2: Reasoning Depth x Marker Ceiling

**Hypothesis**: Higher reasoning levels reach higher markers. L0 never gets past Level 1 markers. L3 reaches Level 3-4 markers.

**Test**: For each reasoning level, compute the maximum taxonomy level reached (across runs). Logistic regression: P(marker_reached) ~ reasoning_level x scarcity.

### Analysis 3: Memory as Gateway

**Hypothesis**: The invention of memory (Observe of past) is a necessary precondition for all Level 2+ markers.

**Test**: In runs where memory never emerges, do Level 2+ markers ever appear? Compute conditional probabilities: P(reciprocity | memory_invented) vs P(reciprocity | no_memory).

### Analysis 4: Information-Action Trade-off

**Hypothesis**: Agents face a trade-off between Observe (information gathering) and Transfer/Bind (action). Successful agents find the right balance.

**Test**: For each agent, compute the fraction of composition steps spent on Observe vs action primitives. Correlate with final resources. Is there an optimal ratio? Does it differ by reasoning level?

### Analysis 5: Heterogeneous Populations

**Hypothesis**: In mixed populations, L3 agents exploit L0 agents by inventing sophisticated strategies (conditional cooperation, selective punishment) that L0 agents cannot counter.

**Test**: Compare Gini coefficients in homogeneous vs heterogeneous conditions. In heterogeneous runs, do L3 agents consistently end up on top? Compute wealth correlation with reasoning level.

### Analysis 6: Convergent Invention

**Hypothesis**: Independently across runs, agents converge on similar compositions for the same functional role (e.g., most "reciprocity" compositions look structurally similar).

**Test**: Cluster analysis of compositions tagged as the same marker. Compute structural similarity (edit distance on composition trees). High convergence = there's a "natural" way to implement reciprocity from primitives.

### Analysis 7: Comparison to Paper 1

**Direct comparison**: Do agents under composable actions reach the same Gini/cooperation equilibria as agents under fixed actions in Paper 1? Or does the open action space produce fundamentally different outcomes?

**Test**: Overlay Paper 1 Gini distributions with Paper 3 homogeneous-condition Gini distributions. Kolmogorov-Smirnov test for distribution differences.

---

## Robustness Checks

- **Primitive vocabulary sensitivity**: Add/remove one primitive (e.g., remove Bind). Does the marker emergence sequence change?
- **Composition budget**: Allow 3 vs 5 vs 7 steps per composition. More steps = more complex compositions possible. Does this shift the marker ceiling for L0?
- **Prompt sensitivity**: Semantically equivalent reformulations of the primitives description. FormatSpread analysis.
- **Model sensitivity**: If compute allows, replicate homogeneous condition on a second model.

---

## Deliverables

1. **The developmental timeline** (hero figure): marker emergence order x reasoning level
2. **Marker taxonomy with operational definitions** (methodological contribution -- reusable by other researchers)
3. **Memory-as-gateway analysis**: is memory the prerequisite for cooperation?
4. **Information-action trade-off curve**: optimal Observe/action ratio per reasoning level
5. **Convergent invention analysis**: do independently evolved compositions converge?
6. **Comparison with fixed-action results** (Paper 1 bridge)

---

## Why This Paper is Significant

1. **No one has done this.** LLM agent studies give agents a fixed action space. No study tests whether agents can invent their own cognitive tools from primitives.

2. **It bridges AI and cognitive science.** The emergence order of markers is directly comparable to human developmental psychology (Tomasello, Piaget) and cultural evolution (Henrich). This makes it publishable in both AI and interdisciplinary venues.

3. **It produces a reusable framework.** The primitives vocabulary + marker taxonomy is a tool other researchers can use. Open-source it and it becomes a benchmark.

4. **It answers a deep question about LLMs.** Do they understand the *function* of memory, reputation, and institutions -- or only mimic them when instructed? If they independently invent these from primitives, it suggests functional understanding. If they don't, it suggests they're pattern-matching on training data.

5. **Direct connection to AI safety.** If autonomous AI agents spontaneously invent governance structures, that's both promising (self-regulation) and concerning (who designs the governance?). This empirical data feeds into the AI alignment conversation.

---

## Connection to the Drieluik

| | Paper 1 | Paper 2 | Paper 3 | Paper 4 |
|---|---------|---------|---------|---------|
| Actions | Fixed | Fixed | Composable | Composable |
| Memory | Provided | Provided | Must be invented | Must be invented |
| Institutions | None | Exogenous (contracts) | Endogenous (emerged) | Endogenous + governed |
| Hobbes parallel | State of nature | Social contract (imposed) | Social contract (discovered) | Constitutional governance |

Paper 3 is the heart of the programme. Paper 1 shows the problem (anarchy under fixed rules). Paper 2 shows the solution works if given (exogenous institutions). Paper 3 asks: **can they find the solution themselves?**

---

## Estimated Compute

- 480 runs x 100 rounds x 30 agents = ~1.44M LLM calls
- At Qwen 3.5-27B speeds on H100 (~50 calls/min with vLLM): ~480 GPU-hours
- With Snellius-scale allocation: ~2-3 weeks of nightruns
- Manageable within a PhD compute budget

---

## Target Venues

**Primary**: NeurIPS (ML + cognitive science angle), AAMAS (multi-agent systems)

**Secondary**: CogSci (cognitive development parallel), JASSS (social simulation)

**Stretch**: Nature Machine Intelligence, PNAS (if results are striking and the Piaget parallel holds)

---

*This is Paper 3 in the hypothetical PhD roadmap "The Origins of Order." It depends on Papers 1-2 being complete and published. Estimated timeline: Year 1-2 of PhD.*
