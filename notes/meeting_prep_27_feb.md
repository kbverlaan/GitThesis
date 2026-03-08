# Meeting Notes - Debraj - 27 Feb 2026

**Sprint 2**: Feb 13 - Feb 27 | **Duur**: ~40 min

---

## Presentatie

Slide deck: `meeting27slidedeck.key` (archived in GitThesis root)

12 slides gepresenteerd:
1. Title slide
2. The Game — action table, base params, invest_self OFF rationale
3. Phase 1: Characterisation — 142 OpenRouter runs, parameter sweeps, spatial radius phase transition (7×7 grid, R=1/2/3)
4. Phase 2: Framing — 100 Gemma 2 27B runs, η²=0.901, framing verklaart 90% Gini-variantie
5. Phase 3a: Reasoning Depth Pilot (old prompts) — L0-L3 met arm_cost=0, L2 hoarder, fear spiral quotes
6. Phase 3b: Reasoning × Game Structure — 132 runs, arm_cost sweep, invest_self sweep, "deeper reasoning amplifies structure"
7. Old vs. New Prompts — confound (arm_cost + prompt change), 60% context reductie
8. Pre-emptive attacks & Action stability — base rate caveat, agents convergeren niet
9. Where we stand — done/behind/uncertain
10. Two directions — Reasoning Depth × Structure vs Credible Commitment
11. Credible Commitment detail — contract mechanics, collateral sweep, WHY (Hobbesian trap geen enkel level ontsnapt)
12. Questions for Debraj

---

## Debraj's Reactie

**Algemeen**: Zichtbaar enthousiast. Zei dat de preliminaire resultaten "very publishable" zijn. Wil dat ik **beide richtingen** doe — reasoning depth als één chapter, credible commitment als apart chapter.

---

## Feedback per Onderwerp

### Metrics & Stabilisatie
- Huidige metrics (Gini, coop%, etc.) zijn niet slecht, maar er is **geen rationale om ze aan het einde te meten als ze niet gestabiliseerd zijn**
- Oplossingen: (1) laat time plots zien, of (2) laat het spel draaien tot stabilisatie met een max wall time
- Interessant experiment: **dynamische game length** — spel stopt pas als een stabiliteitscriterium bereikt is

### Invest Self als Baseline
- Invest_self ON moet als **baseline** getoond worden, niet als weggelaten conditie
- Het stalemate (Gini 0.000) is op zichzelf een interessant resultaat en geeft context aan de andere condities

### Phase Transitions in Reasoning (L2)
- Debraj wil **phase transitions zien in de reasoning zelf** voor L2
- Niet helemaal duidelijk wat hij bedoelt — mogelijk: plot reasoning traces over tijd en kijk of er een kwalitatieve verschuiving is op een bepaald punt
- **TODO**: verduidelijken bij volgende meeting

### Ingroup/Outgroup Dynamiek
- Specifiek geïnteresseerd of L3 **ingroup/outgroup** vormt waar L2 dat niet doet
- Mijn antwoord: waarschijnlijk niet, omdat agents random bewegen en steeds nieuwe buren zien — ze bouwen geen relaties op
- **Debraj's oplossing**: Schelling-type movement — agents bewegen op basis van **utiliteit**, niet random. In het echt bewegen mensen ook niet random maar naar plekken die hen iets opleveren
- **TODO**: nieuw movement scheme implementeren (utility-based)

### Prompting & Reasoning Models
- **Gebruik alleen reasoning models** (niet instructed K-level op een non-reasoning model)
- Gebruik **hun eigen** reasoning traces als observatie-object, niet het "reasoning" veld dat ik ze laat invullen — dat is niet hetzelfde!
- K-instructed prompting is **verdedigbaar** als methode
- **TextGrad** gebruiken voor prompt engineering — ook voor het kwantificeren van uncertainty
- **TODO**: uitzoeken wat TextGrad precies inhoudt en hoe het toe te passen

### Parameter Presentatie
- Bij het variëren van theta (cost/benefit): toon de **percentage** (cost-to-benefit ratio), niet absolute waarden
- Was verrast dat hogere kosten geen effect hadden — ik zei dat Nova Micro waarschijnlijk te dom was om structuur te begrijpen

### Contracts / Credible Commitment
- **Doe het!** Als apart chapter naast reasoning depth
- "Je kunt eigenlijk doen wat je wilt, want niemand heeft dit eerder gedaan"
- Bijna geen multi-agent LLM onderzoek naar K-level reasoning of contracts
- Werd enthousiast over ingroup/outgroup formatie
- Extensies (asymmetrische contracten, contract duration, delegatie) zijn allemaal OK
- Ik zei dat ik het spel speciaal had ontworpen voor dit soort dynamieken, en dat de extensies maffia-achtige structuren mogelijk maken — hij glimlachte en knikte

### Model Keuze
- **Streng: één model!** Alles opnieuw draaien op één model
- Akkoord met de nieuwe Qwen (3.5-35B-A3B)
- Alles tot nu toe was exploratief — sweeps/characterisation moeten opnieuw met het gekozen model
- Maakt sommige eerdere resultaten onzeker ("ja maar dat was op Nova Micro...")

---

## Beslissingen

| Beslissing | Uitkomst |
|-----------|----------|
| Richting A of B? | **Beide!** Reasoning depth + credible commitment als aparte chapters |
| Is K-instructed verdedigbaar? | **Ja**, maar gebruik reasoning models met hun eigen traces |
| Base params? | Maakt niet uit — kies wat de interessantste resultaten oplevert |
| Één model? | **Ja, strikt.** Qwen 3.5-27B. Alles opnieuw draaien |
| Scope? | Breed — beide richtingen + extensies als tijd het toelaat |
| Collateral % als manipulatie? | Beslissing voor later, eerst experimenten draaien |

---

## Actiepunten

### Hoge prioriteit
- [ ] **Qwen 3.5-35B-A3B deployen op Snellius** en valideren dat het werkt
- [ ] **Volledige characterisation opnieuw draaien** op Qwen — parameter sweeps, spatial radius, framing
- [ ] **Utility-based movement** implementeren (Schelling-type, niet random walk)
- [ ] **TextGrad** onderzoeken — wat is het, hoe toepassen voor prompt engineering + uncertainty
- [ ] **Reasoning model traces** — gebruik het model's eigen CoT, niet het instructed reasoning veld

### Medium prioriteit
- [ ] **Stabilisatie-metrics** implementeren — dynamische game length of time plots
- [ ] **Invest_self ON** als baseline toevoegen aan alle vergelijkingen
- [ ] **Contract mechaniek** implementeren voor credible commitment chapter
- [ ] **Cost-to-benefit ratio** als presentatiemethode voor theta sweeps

### Lager prioriteit / later
- [ ] Verduidelijk "phase transitions in reasoning" bij volgende meeting
- [ ] Ingroup/outgroup analyse (na utility-based movement)
- [ ] Extensies: multi-party contracts, asymmetrische contracten, delegatie
- [ ] Literatuur: Turpin, Lanham, TextGrad paper

---

## Sprint 3 Doelen (Feb 27 - Mar 14)

- [ ] Qwen 3.5 op Snellius: deploy + validatie pilot (5 runs)
- [ ] Characterisation rerun op Qwen: parameter sweeps + spatial radius
- [ ] Utility-based movement scheme ontwerpen + implementeren
- [ ] TextGrad paper lezen + haalbaarheid beoordelen
- [ ] Contract mechaniek: ontwerp + eerste implementatie
- [ ] Stabilisatie-analyse: time plots voor bestaande data

---

## Reflectie

Beste meeting tot nu toe. Debraj zei expliciet "very publishable" — eerste keer dat hij dat zegt. Beide richtingen goedgekeurd geeft veel ruimte maar ook risico op scope creep. Kernrisico: alles opnieuw draaien op Qwen kost tijd en SBU's. Prioriteit moet zijn: model deployen en characterisation herhalen, pas daarna nieuwe features (contracts, movement).

Het punt over reasoning models vs instructed reasoning is fundamenteel — als we Qwen 3.5 gebruiken (een reasoning model), dan is het model's eigen chain-of-thought de data, niet mijn prompt-instructie. Dat verandert de methodologie significant en maakt de faithfulness-discussie relevanter.
