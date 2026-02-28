# Vragen na Arch 1+2 — Input voor Arch 3

**Datum**: 2026-02-18
**Context**: Gemma 2 27B resultaten (5 framings × 20 reps, 30 agents, 50 rounds)
**Status**: Te bespreken met Debraj (27 feb) en later te beantwoorden

---

## A. Framing-effect: Wat betekent η²=0.90?

- Framing verklaart 90% van Gini-variantie. Hoeveel ruimte is er nog voor een architectuur-effect in Arch 3?
- Is dit een plafond-probleem? Of kan architectuur-variatie orthogonaal werken op framing?
- Moeten we in Arch 3 framing constant houden (bijv. alleen neutral) om architectuur-effect te isoleren? Of juist framing × architectuur kruisen?

## B. Cautious < cooperative: Het counterintuïtieve finding

- Cautious framing produceert de laagste Gini (0.549), lager dan cooperative (0.581). Waarom?
- Hypothese 1: Cautious agents vermijden conflict → minder resource-vernietiging → gelijkere uitkomsten
- Hypothese 2: Cautious agents investeren conservatiever maar consistenter
- Hypothese 3: Cooperative agents creëren in-group/out-group dynamiek die ongelijkheid vergroot
- **TODO**: Kijk naar de action distributions — cautious heeft meer do_nothing (9.4%) en minder attack (1.2%). Is vermijding effectiever dan samenwerking?
- **Parallel met Debraj**: "More reasoning → more conflict". Hier: "more cooperation intent → more inequality". Zelfde mechanisme?

## C. Reasoning: Epiphenomenaal of causaal?

- Binnen dezelfde framing zijn action distributions bijna identiek voor high vs low Gini runs (bijv. cooperative: 95.1% vs 94.6% invest_other)
- Maar reasoning vocabulaire verschilt systematisch: low-Gini → "investing", "return", "maximize"; high-Gini → "threat", "survival", "chance"
- **Kernvraag**: Produceert de reasoning de uitkomst, of rationaliseert het model post-hoc?
- Als reasoning causaal is: dan is Arch 3 (architectuur-variatie van reasoning) zinvol
- Als reasoning epiphenomenaal is: dan moet Arch 3 iets anders variëren (bijv. observatie, geheugen)
- **TODO**: Kun je runs vinden waar reasoning halverwege *verandert* maar acties niet? Of omgekeerd?

## D. Temporele dynamiek: Wanneer divergeren framings?

- Alle framings beginnen bij Gini ~0.1 en divergeren rond ronde 5-10
- Competitive first attack: ronde 1.1; cooperative: ronde 18.8
- **Vraag**: Is er een kritisch punt (phase transition) waar het systeem "lockt" in een pad?
- **TODO**: Gebruik EWS-module (`ews.py`) om te checken: rolling variance, autocorrelatie, Binder cumulant
- Is de divergentie abrupt of geleidelijk? (Relevant voor of het een bifurcatie is)

## E. Implicaties voor Arch 3 design

- Welke architectuur-dimensies zijn het meest interessant om te variëren?
  - Reasoning depth (geen CoT vs CoT vs explicit ToM)?
  - Observation window (alleen huidige ronde vs N rondes geschiedenis)?
  - Memory structure (geen geheugen vs sliding window vs samenvatting)?
  - Social information (alleen eigen state vs groepsgemiddelde vs volledige observatie)?
- Moet Arch 3 dezelfde 5 framings gebruiken, of is 1 framing (neutral) genoeg?
- Hoeveel reps zijn nodig? Power analysis hint: 20 reps was overpowered voor framing-effect (η²=0.90). Voor kleinere architectuur-effecten wellicht meer nodig.

## F. Methodologische vragen

- ICC Gini = 0.016 — bijna alle variantie zit within-run. Betekent dit dat individuele agent-trajecten belangrijker zijn dan run-level aggregaten?
- De action distribution bars (plot 3) tellen niet op tot 100% — er mist ~15-30%. Welke actie is dat? (waarschijnlijk invest_self of do_nothing mapping issue)
- Moeten we mixed-effects modellen gebruiken voor Arch 3 in plaats van ANOVA? (agents genest in runs, runs genest in condities)

## G. Voor het Origins-verhaal

- De scatter (plot 6) toont framing-clusters die niet overlappen. Is framing een mediator of moderator van de coop→Gini relatie?
- Alle framings produceren ongelijkheid (Gini > 0.45). Zelfs cooperative framing met 88.7% invest_other produceert Gini 0.58. Waarom? Is ongelijkheid een emergent attractor van het systeem?
- Wat zegt dit over de "origins of order" vraag? Ontstaat structuur onafhankelijk van intentie?

## H. Alignment vs reasoning depth confound

- Bij Gemma 2 (minimaal aligned, heuristisch dense model) verwachten we: diepere reasoning → meer conflict, minder coöperatie
- Maar bij SOTA modellen (Opus 4.6, GPT-4) is dit niet per se zo — RLHF en Constitutional AI compenseren waarschijnlijk de "rationele agressie"
- Dit is een **fundamentele limitatie**: reasoning depth en alignment zijn confounded in cross-model vergelijkingen
- Binnen ons design (1 model, prompt-gevarieerde reasoning) isoleren we reasoning depth wél — maar alleen voor dit specifieke alignment-niveau
- **Claim moet zijn**: "bij een heuristisch dense model leidt diepere reasoning tot meer conflict" — niet universeel
- **Niet testbaar**: of alignment het conflict-effect van reasoning opheft (te veel confounds in cross-model vergelijking)
- **Discussiepunt voor paper**: dit is een eerlijke limitatie die de resultaten contextueel maakt, niet een zwakte

**Vragen voor Debraj**:
- Hoe framen we dit? Als limitatie in de discussion, of als expliciet onderdeel van de contributions?
- Is het nuttig om dit kort te testen met 1-2 runs op een sterk aligned model (bijv. via API), puur kwalitatief?

---

## Prioriteiten voor meeting 27 feb

1. [ ] Presenteer de 6 plots
2. [ ] Bespreek η²=0.90 en implicaties voor Arch 3 scope
3. [ ] Bespreek cautious < cooperative finding
4. [ ] Vraag Debraj: framing constant houden in Arch 3, of kruisen?
5. [ ] Vraag Debraj: welke architectuur-dimensies het meest informatief?
