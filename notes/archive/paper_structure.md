# Paper Structure: The Origins of Order

**Status**: Structuur-document, geen proza. Koen schrijft alle tekst.
**Laatste update**: 2026-02-18

---

## Title

TODO: Schrijf een titel. Richting:
- Iets met "reasoning depth", "emergent social structure", "LLM agents"
- Hou het kort en specifiek

---

## Abstract

TODO: Schrijf 150-250 woorden. Structuur:
1. Context (1-2 zinnen): multi-agent systemen, emergente structuur
2. Gap (1 zin): onduidelijk welke rol reasoning speelt
3. Methode (2-3 zinnen): resource allocation game, varieer reasoning depth, meet emergente structuur
4. Key results (2-3 zinnen): framing effect η²=0.90, reasoning depth → conflict, phase transition shifts
5. Implicatie (1 zin)

---

## 1. Introduction

### Claim: Sociale structuur ontstaat spontaan in multi-agent systemen, maar we begrijpen niet welke factoren dit sturen

TODO: Schrijf intro. Punten om te maken:

- Wanneer autonome agents interacteren met beperkte middelen, ontstaan hiërarchieën, ongelijkheid, coalities
- Klassiek bestudeerd in ABM (Axelrod 1984, Epstein & Axtell Sugarscape, Schelling 1971)
- LLM-agents brengen iets nieuws: ze *redeneren* over hun keuzes — in natuurlijke taal, zichtbaar
- Kernvraag: in hoeverre bepaalt de *diepte* van die reasoning de emergente structuur?
- Parallel met Kuusela & Roy (AAMAS 2024): meer reasoning → meer conflict in RL setting
- Dit paper: test dezelfde hypothese met prompt-gevarieerde reasoning op LLM agents

### Contributions (bullet points voor in de tekst)
- Laat zien dat prompt framing 90% van de variantie in ongelijkheid verklaart (η²=0.90)
- Test of reasoning depth hetzelfde mechanisme is (TODO: resultaten)
- Onderzoekt of reasoning depth phase transitions in spelstructuur verschuift (TODO: resultaten)
- Analyseert reasoning traces als correlaten van uitkomsten (niet als verklaringen — Turpin et al. 2023)

### Literatuur-connecties
- Kuusela & Roy (AAMAS 2024) — methodologische template
- Zhang et al. (NAACL 2025) — K-Level Reasoning
- Turpin et al. (NeurIPS 2023), Lanham et al. (2023) — faithfulness van CoT
- Park et al. (2023) — Generative Agents
- Ju et al. (2024) — Sense and Sensitivity (prompt sensitivity)

---

## 2. Related Work

TODO: Schrijf 3-4 subsecties. Hieronder de structuur en wat er in moet.

### 2.1 Emergent social structure in multi-agent systems
- Axelrod (1984): coöperatie uit herhaling
- Epstein & Axtell: Sugarscape — ongelijkheid uit simpele regels
- Schelling: micro-regels → macro-patronen
- Leibo et al. (2017): MARL in social dilemmas
- Baker et al. (2019): emergent tool use
- TODO: Jouw positie — wij gebruiken LLM agents i.p.v. RL agents

### 2.2 LLM agents in strategic settings
- Park et al. (2023): Generative Agents
- Abdelnabi et al. (2024): LLM negotiation met gestructureerde CoT
- arXiv:2502.20432: CoT niet universeel effectief in games
- arXiv:2601.15047: reasoning equilibria ≠ Nash equilibria
- TODO: Jouw positie — wij variëren reasoning *systematisch*, niet ad hoc

### 2.3 Reasoning depth and strategic behavior
- Kuusela & Roy (AAMAS 2024): Level-0 vs Level-2 in RL → meer reasoning = meer conflict
- Zhang et al. (NAACL 2025): K-Level Reasoning framework
- Cognitive hierarchy models (Camerer et al. 2004)
- TODO: Jouw positie — wij doen K-Level via prompt-instructie, niet via multi-call recursie

### 2.4 Faithfulness of reasoning traces
- Turpin et al. (NeurIPS 2023): CoT systematisch biased door oppervlakkige features
- Lanham et al. (2023): faithfulness varieert per taak, grotere modellen minder faithful
- Chen et al. (2025): reasoning models geven <2% toe aan hint-gebruik
- METR (2025): CoT is toch informatief ondanks imperfecte faithfulness
- TODO: Jouw positie — wij analyseren traces als correlaten, niet als causale verklaringen

---

## 3. Methods

### 3.1 Game environment
- Resource allocation game met N agents (typisch 30)
- Acties: invest_other, arm_self, arm_other, attack, do_nothing
- Spatial constraints: interaction radius beperkt zichtbaarheid en interactie
- Zero-cost regime: arm en conflict kosten niets
- 50 rondes per simulatie
- TODO: Beschrijf de game mechanics in detail — jij kent dit het beste

### Data
| Parameter | Waarde |
|-----------|--------|
| Agents | 30 |
| Rondes | 50 |
| Spatial | ja, r=2 (tenzij gevarieerd) |
| invest_self | uit |
| invest_other return | 5 |
| attack_take_percent | 40% |
| arm_multiplier | 2× voor 3 rondes |
| Zero-cost | ja (arm_cost=0, conflict_cost=0) |

### 3.2 Agent architecture
- Gemma 2 27B-IT als base model (via vLLM op Snellius H100)
- Elke agent krijgt observatie → prompt → JSON response (action + reasoning)
- TODO: Beschrijf de prompt structuur (verwijs naar prompts.py)

### 3.3 Experimental conditions

**Experiment 1: Framing effect (completed)**
- 5 framings × 20 reps = 100 runs
- Framings: neutral, cooperative, competitive, strategic, cautious
- Doel: hoeveel van de emergente structuur wordt bepaald door instructie?

**Experiment 2: Reasoning depth (TODO)**
- 3-4 reasoning levels × 20 reps = 60-80 runs op Gemma 2 27B
- Levels:

| Level | Instructie |
|-------|-----------|
| 0 (heuristisch) | TODO: exacte prompt — richting "state your choice briefly" |
| 1 (strategisch) | TODO: exacte prompt — richting "calculate expected value of each action" |
| 2 (theory of mind) | TODO: exacte prompt — richting "predict what each nearby agent will do, then choose" |

- Doel: repliceert "meer reasoning → meer conflict" (Kuusela & Roy) met prompt-variatie

**Experiment 3: Origins — phase transitions × reasoning depth (TODO)**
- Spatial radius (r=1,2,3,4,global) × reasoning level (0,1,2) × 20 reps = 300 runs
- Doel: verschuift de phase transition als agents dieper redeneren?

**Experiment 4: Robustness (TODO)**
- Key conditions op tweede model (Qwen3-32B), 10-20 reps
- Doel: generaliseerbaarheid checken

### 3.4 Metrics
- **Gini coefficient**: ongelijkheid in resource-verdeling [0,1]
- **Palma ratio**: top 10% / bottom 40%
- **Cooperation ratio**: invest_other / alle meaningful actions
- **First attack round**: wanneer begint conflict
- **Action distribution**: % per actie type
- **Gini trajectory**: Gini per ronde over 50 rondes

### 3.5 Statistical analysis
- One-way ANOVA met eta-squared per experiment
- Pairwise comparisons: Bonferroni-corrected t-tests + Cohen's d + Bayes Factor
- ICC: intraclass correlatie voor between-run vs within-run variantie
- Two-way ANOVA voor interactie-effecten (reasoning × structure)
- Reasoning traces: frequentie-analyse, differentiële woorden per uitkomst

---

## 4. Results

### 4.1 System characterization (Phase 1 — kort samenvatten)

TODO: Schrijf 1 alinea. Kernpunten:
- 142 parameter sweep runs
- Spatial constraints sterkste coöperatie-driver (17% → 72%)
- War equilibrium robuust tegen payoff-veranderingen
- Matthew Effect: coöperatie creëert ongelijkheid
- Verwijzing: details in supplementary / appendix

### 4.2 Framing effect (Experiment 1 — data compleet)

TODO: Schrijf resultaten. Kernpunten:

**Hoofdresultaat**: Framing verklaart 90% van Gini-variantie
- ANOVA: F=217.04, p<0.0001, η²=0.901
- → Figuur: plot1_boxplot_gini.png

**Per framing**:

| Framing | Gini (mean±sd) | Coop ratio | First attack |
|---------|---------------|------------|-------------|
| cautious | 0.549 ± 0.057 | 78.5% | ronde 9.1 |
| cooperative | 0.581 ± 0.036 | 88.7% | ronde 18.8 |
| strategic | 0.725 ± 0.039 | 49.5% | ronde 2.5 |
| neutral | 0.778 ± 0.034 | 68.1% | ronde 2.9 |
| competitive | 0.858 ± 0.035 | 37.2% | ronde 1.1 |

**Counterintuïtief finding**: cautious < cooperative op Gini
- Cautious agents vermijden conflict (1.2% attack) effectiever dan cooperative agents
- → Figuur: plot2_gini_trajectory.png (temporele divergentie)
- → Figuur: plot3_action_distribution.png

**Pairwise vergelijkingen**: 9/10 paren significant na Bonferroni
- Enige uitzondering: cautious vs cooperative (d=0.69, p=0.36)
- Largest effect: competitive vs cautious, d=6.60
- → Figuur: plot4_cohens_d_heatmap.png

**Temporal dynamics**:
- Alle framings beginnen bij Gini ~0.1, divergeren rond ronde 5-10
- Competitive saturates bij ~0.85 rond ronde 20
- Cooperative/cautious plateauen rond 0.55-0.58

### 4.3 Reasoning trace analysis (data compleet)

TODO: Schrijf resultaten. Kernpunten:

**Action distributions bijna identiek in high vs low Gini runs**:
- Bv. cooperative: 95.1% vs 94.6% invest_other — verschil <1%
- Maar Gini range: 0.535-0.670

**Reasoning vocabulaire verschilt systematisch**:
- Low-Gini runs: "investing", "return", "maximize", "current"
- High-Gini runs: "threat", "survival", "chance", "armed"
- → Figuur: plot5_differential_keywords.png

**Interpretatie** (TODO: jouw analyse):
- Traces zijn niet puur epiphenomenaal — ze dragen informatie over uitkomsten
- Maar: faithfulness-literatuur waarschuwt voor overclaiming (Turpin et al., Lanham et al.)
- Veilige claim: reasoning vocabulaire is een *correlaat*, geen bewezen *oorzaak*

**Scatter: Gini vs coöperatie**:
- Duidelijke negatieve relatie
- Framing-clusters overlappen niet
- → Figuur: plot6_gini_vs_coop.png

### 4.4 Reasoning depth effect (Experiment 2 — TODO)

TODO: Resultaten invullen na experimenten

Verwachte structuur:
- ANOVA op reasoning level → Gini (+ cooperation, first attack)
- Per level: gemiddelde metrics
- Vergelijking met Kuusela & Roy's Level-0/Level-2 finding
- Trace analyse: verandert de reasoning vocabulaire met de instructie?

### 4.5 Phase transitions × reasoning depth (Experiment 3 — TODO)

TODO: Resultaten invullen na experimenten

Verwachte structuur:
- Phase transition curves per reasoning level
- Interactie-effect: reasoning × spatial radius
- Verschuift de transitie bij r=2→r=3 met reasoning depth?

### 4.6 Robustness (Experiment 4 — TODO)

TODO: Kwalitatieve vergelijking met tweede model

---

## 5. Discussion

TODO: Schrijf discussie. Structuur en punten:

### 5.1 Framing als dominante factor
- η²=0.90 is enorm — prompt-instructie bepaalt de wereld die ontstaat
- Cautious < cooperative: vermijding effectiever dan coöperatie-intentie
- Connectie met Debraj: objective framing flipt equilibria (Phase 1 finding bevestigd)
- TODO: Wat betekent dit? Jouw interpretatie.

### 5.2 Reasoning depth en conflict (TODO — na experimenten)
- Repliceert of weerlegt Kuusela & Roy's "meer reasoning → meer conflict"?
- Mechanisme: EV-calculatie laat zien dat aanvallen rationeel is?
- Of juist: diepere reasoning → betere coöperatie door opponent modeling?

### 5.3 Reasoning en alignment
- Belangrijk punt: bij Gemma 2 (minder alignment) kan diepere reasoning tot conflict leiden
- Bij SOTA modellen (Opus, GPT-4) is dit waarschijnlijk niet zo — RLHF/Constitutional AI compenseert
- Dit is een **limitatie**: we testen reasoning depth op een specifiek model met specifiek alignment-niveau
- Claim is dus: "reasoning depth → conflict *bij dit type model*", niet universeel
- Vervolgonderzoek: systematisch alignment-niveau variëren (maar dat kan niet via prompting)

### 5.4 Phase transitions verschuiven (TODO — na experimenten)
- Als Level-2 agents sterkere structurele constraints nodig hebben voor coöperatie → dat is het kernresultaat
- Connectie: Mengesha & Roy (ICCS 2025) — game selection → inequality. Hier: reasoning selection → inequality

### 5.5 Faithfulness van traces
- Traces zijn informatief maar niet per se faithful (Turpin et al., Lanham et al., Chen et al.)
- Wij vinden: zelfde acties, andere vocabulaire, andere uitkomsten
- Voorzichtige claim: traces correleren met uitkomsten, causaliteit niet bewezen
- Suggestie voor vervolgonderzoek: interventie-experimenten (perturbeer traces, meet gedragsverandering)

### 5.6 Limitations
- Één base model (Gemma 2 27B) — generaliseerbaarheid onbekend
- Single-call reasoning instructie is zwakkere manipulatie dan multi-call K-Level
- 30 agents, 50 rondes — schaaleffecten niet volledig onderzocht
- Zero-cost regime is specifieke game-variant
- Reasoning depth via prompt ≠ reasoning depth via architectuur
- Alignment confound: niet te scheiden van reasoning depth in dit design

---

## 6. Conclusion

TODO: Schrijf conclusie. Punten:
- Beantwoord de onderzoeksvraag: emergente structuur wordt bepaald door interactie reasoning × structuur
- Kernresultaten samenvatten (η²=0.90, reasoning depth effect, phase transition shift)
- Bijdrage: eerste systematische test van reasoning depth in dynamisch multi-agent systeem
- Toekomstig werk: alignment × reasoning interactie, multi-call K-Level, grotere modellen

---

## Figures overzicht

| # | Beschrijving | File | Status |
|---|-------------|------|--------|
| 1 | Boxplot: final Gini per framing | `plot1_boxplot_gini.png` | KLAAR |
| 2 | Gini trajectory per framing (mean + 95% CI) | `plot2_gini_trajectory.png` | KLAAR |
| 3 | Stacked bar: action distribution per framing | `plot3_action_distribution.png` | KLAAR |
| 4 | Heatmap: pairwise Cohen's d | `plot4_cohens_d_heatmap.png` | KLAAR |
| 5 | Tabel: differentiële reasoning keywords | `plot5_differential_keywords.png` | KLAAR |
| 6 | Scatter: Gini vs cooperation ratio | `plot6_gini_vs_coop.png` | KLAAR |
| 7 | Boxplot/trajectory: Gini per reasoning level | TODO | Na Exp 2 |
| 8 | Phase transition curves per reasoning level | TODO | Na Exp 3 |
| 9 | Interactie-effect heatmap: reasoning × structure | TODO | Na Exp 3 |
| 10 | Cross-model robustness vergelijking | TODO | Na Exp 4 |

---

## Appendix ideeën

- A: Volledige prompt templates per conditie
- B: Alle pairwise comparison tabellen
- C: Per-framing reasoning trace voorbeelden (sample traces)
- D: Robustness: sensitivity analyse op reps (is 20 genoeg?)
