# Production Runs Design Document

**Status**: ITERATIEF — wordt bijgewerkt naarmate sweeps, literatuur, en Debraj-feedback binnenkomen.
**Doel**: Wanneer dit document "final" is, kunnen we de productieruns direct submitten.
**Laatste update**: 2026-02-19

---

## 1. Kernexperimenten

### Experiment A: Reasoning Depth Production
**Vraag**: Produceert dieper redeneren systematisch andere emergente structuren?
**Design**: 4 reasoning levels × 20 reps = 80 runs

| Factor | Waarden |
|--------|---------|
| Model | Gemma 2 27B |
| Reasoning levels | L0, L1, L2, L3 |
| Reps | 20 |
| Agents | 30 |
| Rounds | 50 |
| Spatial radius | 2 |
| Base params | TODO — selecteer na sweep-analyse (zie §3) |

**Analyse**: One-way ANOVA + pairwise (Tukey HSD), effect sizes (Cohen's d, η²), Bayes factors, mixed-effects met RunID als random effect.

### Experiment B: Origins Factorial (reasoning × radius)
**Vraag**: Verschuift de phase transition als agents dieper redeneren?
**Design**: 4 levels × 6 radii × 20 reps = 480 runs

| Factor | Waarden |
|--------|---------|
| Reasoning levels | L0, L1, L2, L3 |
| Spatial radius | 1, 2, 3, 4, 6, 10 |
| Reps | 20 |
| Overige params | Zelfde als Experiment A |

**Analyse**: Two-way ANOVA (reasoning × radius), interactie-effect (partial η²), phase transition curves per level, mixed-effects model.

**Hero figure**: 4 Gini-vs-radius curves in één plot. Verschuiving = kernresultaat.

---

## 2. Uitbreidingsexperimenten (kandidaten)

Uit Kuusela & Roy vergelijking + ideas.txt. Niet per se allemaal runnen — prioriteer op basis van compute budget en Debraj's feedback.

### Experiment C: Mixed Reasoning Levels
**Vraag**: Domineren diep-redenerende agents naïeve agents, of worden ze uitgebuit?
**Design opties**:
- C1: 15 L0 + 15 L2, 20 reps = 20 runs
- C2: 10 L0 + 10 L1 + 10 L2, 20 reps = 20 runs
- C3: Full mix matrix (diverse ratios), 5 reps = ~40 runs

**Motivatie**: Ecologische validiteit — in de echte wereld redeneren niet alle agents even diep. Kuusela & Roy hadden altijd homogene levels.
**Implementatie**: Nieuw sweep parameter `mixed_reasoning` → per-agent reasoning level toewijzing.
**Open vraag**: Hoe assignen we levels aan agents? Random? Spatiaal geclustered?

### Experiment D: Surpass Scenario
**Vraag**: Triggert een resource-voorsprong agressie, en verlaagt reasoning depth de drempel?
**Design**: 4 levels × {control, surpass} × 10 reps = 80 runs

**Implementatie**: Start 1 agent met 2× resources (initial_resources=50 voor agent 0, 25 voor rest). Meet first_attack_round en wie aanvalt.
**Open vraag**: Is dit een nieuw experiment of een variant van Experiment A?

### Experiment E: Streak Analysis
**Vraag**: Hoe lang zijn peace/attack streaks per reasoning level?
**Design**: Geen extra runs nodig — analyse op data uit Experiment A en B.

**Implementatie**: Tel consecutive rounds zonder aanval per agent. Fit geometrische/exponentiële distributie. Vergelijk parameters per level.
**Kuusela & Roy**: Vonden power-law-achtige patronen. Koen's verwachting: peace streaks zijn niet zeldzaam, maar aanvallen herverdelen snel.

---

## 3. Open Ontwerpbeslissingen

### 3a. Base Parameters — KRITIEK
**Status**: WACHT OP invest_return sweep + analyse

Huidige configs gebruiken **zero costs** (arm_cost=0, conflict_cost=0). Sweeps laten zien:
- arm_cost=0 maakt arm_self trivially dominant (geen kosten, alleen voordelen)
- conflict_cost=0 maakt aanvallen te goedkoop

**Kandidaat base params** (na analyse van 96 sweep runs):

| Parameter | Huidig | Kandidaat | Rationale |
|-----------|--------|-----------|-----------|
| arm_cost | 0 | 2 | Maakt bewapening een echte trade-off. L0-L2 interactie sterkst bij arm_cost=2 |
| conflict_cost | 0 | 3? | Maakt aanvallen kostbaar, maar niet prohibitief |
| invest_return | 5 | TODO | Wacht op sweep resultaten |
| invest_self | false | false | Bevestigd: invest_self ON = stalemate |

**Beslisregel**: Parameters moeten een **genuïne strategische dilemma** creëren — geen trivially dominant strategies. Toets met pilot (3 reps) na parameterkeuze.

### 3b. Reasoning Levels: 3 of 4?
**Status**: BESLOTEN — 4 levels (L0-L3)

Pilot + sweeps bevestigen dat L3 kwalitatief anders is dan L2:
- L2 = defensieve hoarder (arm_self 37%, attack 2%)
- L3 = selectieve predator (arm_self 16%, attack 8%, cooperatie 47%)

L3 toevoegen aan productie is essentieel voor het non-monotonische verhaal.
**NB**: Huidige production.yaml en origins.yaml hebben nog maar 3 levels — updaten!

### 3f. Prompt Wijzigingen (Feb 19)
**Status**: DOORGEVOERD — Snellius pilot data is niet meer vergelijkbaar met productieruns

Twee wijzigingen in `src/agents/prompts.py` die de prompt significant veranderen:

**A. Personalized neighbor profiles** (vervangt flat history dump):
- Oud: alle 300 acties (30 agents × 10 rounds) als flat dump, ~86% van prompt tokens
- Nieuw: per-neighbor één regel met resources, dominant gedrag, directe interacties
- Voorbeeld: `agent_3 [19]: invest other | invest other you 2x | you invest other them 2x`
- Alleen visible neighbors in spatial mode, broke agents gemarkeerd

**B. K-level reasoning block** (vervangt placeholder in JSON template):
- Oud: reasoning instructie verstopt als placeholder `"reasoning": "<Consider that...>"`
- Nieuw: prominente `THINK BEFORE CHOOSING:` sectie vóór JSON template
- Elke level stelt expliciet wat het aanneemt over anderen (K-level recursie):
  - L0: geen reasoning block
  - L1: "Other agents choose without strategic reasoning" (= zij zijn L0)
  - L2: "Other agents calculate their best action (Level-1 reasoning)" (= zij zijn L1)
  - L3: "Other agents predict your behavior and respond to it (Level-2 reasoning)" (= zij zijn L2)
- Genummerde stappen geven structuur (scaffolding), maar vullen de inhoud niet in

**Ontwerpkeuze reasoning blocks**: We manipuleren de *aanname over anderen*, niet de exacte denkstappen. Meer forceren → meet prompt-compliance i.p.v. reasoning depth. Variatie in reasoning output is informatief als data.

**Validatie (OpenRouter quick test)**: 10 agents, 20 rounds, Gemma 2 27B, L3:
- Oud prompt: Gini=0.89, cooperation=13%, attack dominant, shallow reasoning
- Nieuw prompt: Gini=0.44, cooperation=39%, arm_self=44%, invest=37%, attack=10%
- Reasoning toont expliciet opponent modeling en referenties naar neighbor profiles

**Impact**: Alle productieruns moeten met de nieuwe prompts. Snellius pilot (9 runs) dient als referentie voor de oude prompt-structuur, niet als baseline voor productie.

### 3c. Aantal Reps
**Status**: 20 reps per conditie (standaard)

- Pilot (3 reps): voldoende voor richting, niet voor statistiek
- Productie (20 reps): voldoende voor ANOVA + pairwise comparisons
- Power analyse TODO: bereken benodigd n uit pilot ICC + effect sizes

### 3d. Radii Selectie
**Status**: 6 waarden: 1, 2, 3, 4, 6, 10

- 1-4: hoge resolutie rond de verwachte transitie (r=2→3 is de bekende grens)
- 6: ruim boven transitie
- 10: ≈ globaal voor 30 agents op ~11×11 grid

### 3e. Framing
**Status**: BESLOTEN — alleen neutral framing

Arch 1+2 liet zien dat framing η²=0.901 van Gini-variantie verklaart. We willen reasoning depth isoleren, niet vermengen met framing. Neutral only.

---

## 4. Compute Budget

| Experiment | Runs | GPU-uren (est) | SBU (est) |
|-----------|------|----------------|-----------|
| A: Reasoning depth production | 80 | ~45h × 1 GPU | ~225 |
| B: Origins factorial | 480 | ~55h × 4 GPUs | ~1100 |
| C: Mixed levels (C1+C2) | 40 | ~23h × 1 GPU | ~115 |
| D: Surpass scenario | 80 | ~45h × 1 GPU | ~225 |
| **Totaal (kern A+B)** | **560** | | **~1325 SBU** |
| **Totaal (alles)** | **680** | | **~1665 SBU** |

(Gebaseerd op Gemma 2: ~34 min/run op 1 H100)

---

## 5. Volgorde & Afhankelijkheden

```
invest_return sweep compleet
        ↓
Base parameters selectie (§3a)
        ↓
Update YAML configs (L3 toevoegen, base params)
        ↓
Validatiepilot (3 reps op nieuwe base params)
        ↓
GO/NO-GO → Debraj feedback (Feb 27)
        ↓
    ┌───────────────┐
    │  Experiment A  │ (80 runs, ~2 dagen)
    │  reasoning     │
    │  depth prod    │
    └───────┬───────┘
            ↓ (resultaten informeren B)
    ┌───────────────┐
    │  Experiment B  │ (480 runs, ~7-8 dagen)
    │  origins       │
    │  factorial     │
    └───────┬───────┘
            ↓ (als resultaten interessant)
    ┌───────────────┐
    │  Experiment C  │ (mixed levels, 40 runs)
    │  Experiment D  │ (surpass, 80 runs)
    └───────────────┘
```

---

## 6. Checklist voor Finalisatie

- [ ] invest_return sweep resultaten geanalyseerd
- [ ] Base parameters gekozen (geen trivially dominant strategies)
- [ ] Validatiepilot gedraaid (3 reps, visuele check)
- [ ] L3 toegevoegd aan production.yaml en origins.yaml
- [ ] Power analyse gedaan (pilot ICC → benodigd n)
- [ ] Debraj akkoord op design (Feb 27 meeting)
- [ ] Mixed reasoning implementatie ontworpen (als we Exp C doen)
- [ ] Surpass implementatie ontworpen (als we Exp D doen)
- [ ] Alle YAMLs up-to-date en getest

---

## 7. Versiegeschiedenis

| Datum | Wijziging |
|-------|-----------|
| 2026-02-19 | Initieel document. Kernexperimenten A+B, uitbreidingen C/D/E uit Kuusela & Roy vergelijking. Open beslissingen gemarkeerd. |
| 2026-02-19 | §3f: Promptwijzigingen gedocumenteerd (personalized profiles + K-level reasoning blocks). Snellius pilot niet meer vergelijkbaar. |
