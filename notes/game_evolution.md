# Game Design Evolution

## Zomer 2025: TNO Proposal (totaal ander project)
- "A Generative Intel Agent in a Digital Twin for Simulated Crisis Information Analysis"
- Digital Twin + RAG + CoT + sitreps voor crisis management
- 9 maanden plan, Gantt charts, TNO Defence Safety & Security
- Verworpen: te prestige-gedreven, paste niet bij Koen

## 11 december 2025: 3-actie payoff matrix
- Acties: Threat, Cooperate, Accept
- Payoff matrix (threat/threat = -/-, cooperate/cooperate = ++/++)
- Reputatie via observatie van interacties
- "Je kan je reputatie ontvluchten en naar een nieuw cluster agents gaan"
- Experiment: Baseline vs Generative Agents
- Kernvragen al aanwezig: "Wat is macht?", "In hoeverre is informatie belangrijk?"

## December 2025: Mail aan Debraj
- "cooperate or threaten", pairwise interactions
- "no notion of power, rank, or leadership is hard-coded"
- RL vs LLM vergelijking als kern-RQ
- Debraj's critiques: (1) power must emerge, (2) role of LLM agents must be conceptually clear

## 5 januari 2026: Bond-based threat game
- Acties: Invest, Threat
- Utility = som van je bonds (symmetrisch, max 5)
- Threat → ontvanger kiest: buigen (betaal T=3) of vechten
- Vechten: kost C=5, bond kapot, alle bonds -1, winnaar obv utility+bonds
- Twee-staps interactie (threat → response)
- Verworpen: te complex voor simultaan LLM prompting

## 28 januari 2026: RQ pivots (3 versies in 1 dag)
- V1: Neorealism vs Constructivism → verworpen (circulair)
- V2: Security Dilemma escape → verworpen (te smal)
- V3: Emergent Social Structures (RL vs LLM) → werd de proposal

## 30 januari 2026: Proposal af, thesis is GO
- Supervisor: Debraj Roy
- RQ: "Do semantic priors enable qualitatively different emergent social structures?"

## 13 februari 2026: V1 — Eerste code
- 6 agenten, 25 resources
- 5 acties (invest_self, invest_other, arm_self, arm_other, attack)
- Absolute kosten (invest cost=0 return=2, arm_cost=5, conflict_cost=3)
- Arming met duration timer (3 rondes)
- 10 rondes, via OpenRouter API
- Geen spatial grid

## 16 februari 2026: V2 — Spatial grid + framing
- Spatial grid (interaction_radius=2)
- 10 agenten in experiments
- Gemma 2 27B, 5 prompt framings × 20 reps
- Resultaat: framing η²=0.901 (90% Gini variance)

## 18 februari 2026: Pivot — Architecture → Reasoning Depth
- Weg van RL vs LLM vergelijking
- "Comparing different models is confounded — they differ on 100 dims"
- Naar K-level reasoning op één model (Debraj's template)

## 28 februari 2026: V3 — %-based redesign
- 30 agenten (Debraj's suggestie)
- Percentage-based economy (invest 10%/15%, arm 10%, conflict 5%)
- arm_duration → arm_decay 0.5 (exponentieel)
- do_nothing als 6e actie
- invest_self OFF (trivially dominant bij L1)
- Agent memory (sliding window, 10 rondes)
- Gemma 2 → Qwen 3.5-27B (dense)
- OpenRouter → lokale vLLM op Snellius H100
- 50 rondes (was 10)

## 1-2 maart 2026: V4 — Huidige versie
- invest_self vereenvoudigd: flat +2% (was cost 10% / return 20%)
- arm_multiplier: 2.0 expliciet (bonus = cost × multiplier)
- Early stopping (two-phase adaptive, patience=5)
- Temporal reasoning in base prompt (los van K-level)

## Rode draad
De kern is sinds december 2025 hetzelfde: agents, conflict, cooperatie, emergentie.
Elke pivot was een reactie op een reëel probleem. De implementatie werd scherper,
het fundament bleef.

## Wat verdween
- TNO/crisis intel (zomer 2025)
- RL vs LLM vergelijking (feb 18)
- Gemma 2 27B (feb 28)
- OpenRouter API (feb 28)
- Absolute economy (feb 28)
- Arm duration timer (feb 28)
- Prompt framing (5 types) (feb 18)

## Wat erbij kwam
- Spatial grid (feb 16) → straks adaptive network topology
- K-level reasoning L0-L3 (feb 18)
- %-based economy (feb 28)
- Agent memory (feb 28)
- Early stopping (mar 1)
- arm_multiplier (mar 1)
- Hobbes + Mechanism Design framing (feb)
