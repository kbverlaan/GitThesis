# Thesis Narrative: The Origins of Order

**Laatste update**: 2026-02-18
**Doel van dit document**: Eén plek waar het verhaal van de thesis altijd duidelijk is. Als je verdwaalt, lees dit.

---

## De vraag

Wanneer je autonome agents in een gedeelde omgeving plaatst met beperkte middelen, ontstaan er spontaan sociale structuren — hiërarchieën, coalities, ongelijkheid. **Waar komt die orde vandaan?**

Specifiek: in hoeverre wordt de emergente sociale structuur bepaald door (a) de structuur van de omgeving, en (b) hoe de agents *redeneren* over hun situatie?

---

## Het verhaal in vijf stappen

### Stap 1: Het systeem begrijpen (Phase 1 — KLAAR)

Voordat je iets kunt variëren, moet je het systeem begrijpen.

**Wat we vonden** (142 runs, parameter sweeps):
- Ruimtelijke beperkingen zijn de sterkste driver van coöperatie (17% → 72%)
- Resource zichtbaarheid drijft coöperatie, niet reputatie
- War equilibrium is robuust tegen payoff-veranderingen
- Matthew Effect: coöperatie zelf creëert ongelijkheid ("invest in de rijkste")
- Objective framing flipt equilibria: "maximize" → oorlog, "avoid last" → 83% coöperatie

**Conclusie**: de structuur van het spel bepaalt de uitkomst meer dan de parameters.

### Stap 2: Modellen en framing hebben enorme effecten (Phase 2a — KLAAR)

Verschillende LLM-architecturen produceren kwalitatief verschillende werelden:
- Gemini Flash Lite: actieve oorlog + coöperatie (Gini 0.84)
- DeepSeek V3.2: passieve stalemate (93% do_nothing)
- Gemma 2 27B: coöperatief met conflict (68% invest_other, Gini 0.78)

En prompt framing op één model (Gemma 2) verklaart **90% van de variantie** in ongelijkheid (η²=0.90). Cautious framing produceert méér gelijkheid dan cooperative framing — counterintuïtief.

**Conclusie**: zowel het model (wie) als de instructie (hoe) bepalen de emergente structuur. Maar dit zijn confounded vergelijkingen — modellen verschillen op 100 dimensies tegelijk.

### Stap 3: Isoleer reasoning depth als variabele (Phase 2b — TODO)

**De pivot**: in plaats van modellen vergelijken (confounded), variëren we *reasoning depth* op één model (Gemma 2 27B).

Geïnspireerd door:
- **Debraj's Level-0/1/2 framework** (Kuusela & Roy, AAMAS 2024): meer reasoning → meer conflict
- **K-Level Reasoning** (Zhang et al., NAACL 2025): recursieve belief-modellering op LLMs
- Onze eigen observatie: QwQ-32B (diep reasoning model) valt 51% aan, Gemma 2 (heuristisch) coöpereert 74%

**Experiment design**:
- Level-0: minimale reasoning instructie ("kies een actie")
- Level-1: strategische CoT ("bereken de verwachte waarde van elke actie")
- Level-2: theory of mind ("voorspel wat andere agents gaan doen, kies dan")
- Eventueel Level-3: recursief ("wat denken zij dat jij gaat doen?")

**Verwachte finding**: meer reasoning → meer conflict → hogere Gini. Dit repliceert Debraj's finding met een ander mechanisme (prompt-gestuurd i.p.v. RL-gestuurd).

**Literatuur over faithfulness**: reasoning traces zijn niet 100% faithful (Turpin et al., 2023; Lanham et al., 2023; Chen et al., 2025). Analyseer traces als correlaten, niet als verklaringen. Maar ze dragen wél informatie (METR, 2025).

### Stap 4: Origins — Phase transitions × reasoning depth (Phase 2c — TODO)

Dit is waar het wetenschappelijk interessant wordt.

**Vraag**: Verschuiven de phase transitions van het systeem als agents dieper redeneren?

**Experiment design**: Reasoning depth × game structuur factorial
- Spatial radius sweep (r=1,2,3,4,global) × reasoning level (0,1,2)
- Information architecture (visibility × history) × reasoning level
- Eventueel: scale (10,20,30 agents) × reasoning level

**Verwachte finding**: Level-2 agents zijn gevoeliger voor structuurveranderingen dan Level-0. De phase transition verschuift — dieper reasoning vereist sterkere structurele constraints om coöperatie af te dwingen.

**Waarom dit sterk is**:
- Het verbindt Debraj's reasoning-levels met spelstructuur in één experiment
- Het is een interactie-effect — publiceerbaar en theoretisch interessant
- Het beantwoordt de Origins-vraag: orde ontstaat uit de *interactie* tussen reasoning en structuur, niet uit één van beide alleen

### Stap 5: Robustness check (Phase 2d — TODO)

**Vraag**: Zijn de gevonden patronen model-specifiek of generaliseerbaar?

- Herhaal de key experiments op een tweede model (Qwen3-32B of een ander beschikbaar model)
- Niet 100 runs nodig — 10-20 per conditie is genoeg voor kwalitatieve vergelijking
- Verwachting: zelfde richting, mogelijk ander magnitude

De Qwen3 runs die nu al draaien (zelfs als ze maar deels klaar komen) leveren data voor deze robustness check.

---

## Het argument

```
Model-architectuur bepaalt gedrag                    (Stap 2, established)
         ↓ maar confounded
Prompt framing bepaalt gedrag                        (Stap 2, η²=0.90)
         ↓ maar welke dimensie?
Reasoning depth is de sleutel-dimensie               (Stap 3, te testen)
         ↓
Reasoning depth × spelstructuur → emergente orde     (Stap 4, de kern)
         ↓
Robuust over modellen heen?                          (Stap 5, validatie)
```

**De one-liner**: De sociale structuur die ontstaat in een multi-agent systeem wordt bepaald door de interactie tussen hoe diep agents redeneren en hoe het spel gestructureerd is.

---

## Connectie met bestaand werk

| Referentie | Connectie |
|-----------|-----------|
| Kuusela & Roy (AAMAS 2024) | Meer reasoning → meer conflict. Wij repliceren met prompt-variatie i.p.v. RL |
| Zhang et al. (NAACL 2025) | K-Level Reasoning framework. Wij passen dit toe op dynamisch multi-agent systeem |
| Turpin et al. (NeurIPS 2023) | CoT is niet altijd faithful. Wij analyseren traces als correlaten |
| Mengesha & Roy (ICCS 2025) | Game selection → inequality. Wij: reasoning selection → inequality |
| Axelrod (1984) | Coöperatie uit herhaling. Wij: coöperatie uit structuur × reasoning |
| Schelling (1971) | Micro-regels → macro-patronen. Ons hele framework |

---

## Praktisch: wat is waar?

| Wat | Waar |
|-----|------|
| Dit narratief | `notes/thesis_narrative.md` (dit document) |
| Roadmap + sprints | `notes/roadmap.md` |
| Experiment log | `notes/experiment_log.md` |
| Vragen voor Debraj | `notes/questions_post_arch12.md` |
| Meeting prep | `notes/meeting_prep_27_feb.md` |
| Gemma 2 resultaten | `data/results/arch_gemma2/` |
| Analyse code | `src/analysis/arch_analysis.py`, `trace_analysis.py` |
| Plots | `data/results/arch_gemma2/plots/` |
| Notebook | `notebooks/arch_exp_gemma2.ipynb` |
