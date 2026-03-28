// Run in Zotero > Tools > Developer > Run JavaScript
// Creates updated reading plan as standalone note in "Thesis — Origins of Order"

async function createReadingPlan() {
    const THESIS_COLLECTION = "8IHZK6TT"; // Thesis — Origins of Order

    const note = new Zotero.Item("note");
    note.setNote(`
<h1>📖 Reading Plan — March 8-21, 2026 (v2)</h1>

<h2>Weekend 8-9 maart — Theoretisch fundament</h2>
<p>Doel: de drie theoretische pijlers onder je IVs snappen.</p>
<ol>
<li><b>Kuusela &amp; Roy (2024)</b> — HERLEZEN. Focus: hoe mapt zijn L0-L2 op jouw L0-L3? Waar wijkt ToM af van CH? Noteer wat je anders doet en waarom. <i>[~30 min]</i></li>
<li><b>De Weerd et al. (2013)</b> "How much does it help to know what she knows you know?" — ToM niveaus, non-lineaire effecten. <i>[~1.5 uur]</i></li>
<li><b>Crawford &amp; Sobel (1982)</b> "Strategic Information Transmission" — Cheap talk, babbling equilibrium. <i>[~1 uur]</i></li>
<li><b>Hobbes, Leviathan Ch.13</b> — Drie oorzaken van conflict. <i>[~30 min]</i></li>
</ol>

<h2>Week 9-13 maart — Methodologisch + netwerk</h2>
<ol start="5">
<li><b>Akata et al. (2025)</b> "Playing repeated games with LLMs" — Methodologisch voorbeeld. Bayes factors, effect sizes. <i>[~1 uur]</i></li>
<li><b>Santos &amp; Pacheco (2005)</b> PRL — Scale-free networks provide unifying framework for cooperation. Heterogene netwerken → coöperatie over hele parameterruimte PD + snowdrift. <i>[~45 min]</i> 🆕 <i>Debraj aanbeveling</i></li>
<li><b>Santos, Pacheco &amp; Lenaerts (2006)</b> PLoS CompBio — Payoff-based rewiring. <i>[~45 min]</i></li>
<li><b>Rand et al. (2011)</b> PNAS — Dynamic networks promote cooperation bij mensen. <i>[~45 min]</i></li>
<li><b>Rand et al. (2014)</b> PNAS — Static network structure stabilizes cooperation when b/c &gt; k. Experimenteel bewijs. <i>[~45 min]</i> 🆕 <i>Debraj aanbeveling</i></li>
<li><b>De Weerd et al. (2017)</b> "Negotiating with other minds" — ToM + communicatie interactie. KEY paper. <i>[~1.5 uur]</i></li>
<li><b>Turpin (2023)</b> — CoT faithfulness. Citeren voor reasoning traces als data. <i>[~45 min]</i></li>
</ol>

<h2>Week 14-21 maart — Verdieping</h2>
<ol start="12">
<li><b>Harsanyi (1967)</b> Part I — Type uncertainty formalisatie. <i>[~1 uur]</i></li>
<li><b>Hurwicz (1960)</b> — MD framework: solution concept, type space, message space. <i>[~1 uur]</i></li>
<li><b>Ostrom (1990)</b> Ch.1-3 — Counterpoint Hobbes: wanneer werkt zelfbestuur? <i>[~2 uur]</i></li>
<li><b>Sally (1995)</b> — Cheap talk boost ~40% coöperatie. Basis IV3. <i>[~30 min]</i></li>
<li><b>Chen (2025)</b> — Faithfulness update reasoning models. <i>[~45 min]</i></li>
<li><b>Van Segbroeck et al. (2011)</b> New J. Phys. — Selection pressure transforms social dilemmas in adaptive networks. Active linking: strategie-evolutie + netwerk-evolutie versterkt coöperatie. <i>[~1 uur]</i> 🆕 <i>Debraj aanbeveling, was parking lot</i></li>
<li><b>Curvo (2025)</b> "The Traitors" — LLM agents met persistent memory in social deduction game. Deception &gt; detection bij sterkere modellen. Vergelijk hun memory-architectuur met jouw note-to-self. <i>[~1.5 uur]</i> 🆕 <i>Debraj aanbeveling</i></li>
</ol>

<h2>Parking lot</h2>
<ul>
<li>Baliga &amp; Sjöström (2004) — arms races formalisatie</li>
<li>Zimmermann et al. (2004) — eerste co-evolutionary rewiring</li>
<li>Binmore (2005) — brug evolutionaire GT en social contract</li>
</ul>

<h2>Leesprotocol</h2>
<p>Per paper: (1) abstract + conclusie eerst, (2) noteer in 3 zinnen de claim, (3) lees volledig, (4) schrijf 1 alinea mapping naar thesis. Sla op als Zotero child note bij het item.</p>
`);
    note.addTag("march-2026");
    note.addTag("reading-plan");
    note.addToCollection(THESIS_COLLECTION);
    await note.saveTx();

    return "Done! Created updated reading plan (v2) in Thesis — Origins of Order collection.";
}

await createReadingPlan();
