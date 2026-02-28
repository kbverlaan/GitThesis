// ============================================================
// Zotero Cleanup & Reading List Script
// Run in: Zotero > Tools > Developer > Run JavaScript
// ============================================================
// 1. Deletes 124 orphan duplicates (122 CoEngineer + 2 thesis)
// 2. Creates "To Read" collection with Tier 1-4 subcollections
// 3. Adds thesis reading list papers to correct tiers
// ============================================================

async function main() {
    let results = { deleted: 0, skipped: 0, collections_created: 0, papers_added: 0 };

    // ========== PART 1: DELETE DUPLICATES ==========
    const orphanDuplicateKeys = [
        // CoEngineer orphan duplicates (122 items, each paper has 2 extra copies)
        "RWUT4PXY","2HRRLI5Y","MJHJIJXU","7H9UQ3K5","QITMWM2F","ISV9QDIU",
        "7XE9FZ7U","BK7KB2DF","M3WGN3U2","XQAU53CA","6T29R3TR","37CDWJY7",
        "KZEW27QP","R5YSGU2I","RUVD6IDL","KILB6JUX","LHCEPQFN","LY47JK49",
        "I72K8ZM9","C6NA8WAI","6GBTPEWN","FMFUWT9Z","WCLI255Z","P52Z77UB",
        "8PA3KRHU","MLJJV662","GN4NHTB4","VVTR6B5H","Z3HQTVYU","RML97KLB",
        "UE7SEDEG","YZAXLUAN","JCP6KCLE","D8NLU4D9","ZLQW4G5S","B2R3T7YZ",
        "FLL3DBSG","68T42FWV","WR2IRCSD","IAJZ8CJC","ANH68H3L","CRLZTC63",
        "DXZMK9TZ","8XTRNQJX","YLNY9MDR","8BD6NKK2","XDETKNWI","TXFT964G",
        "LK9UUG4S","N2F5SPA5","N9DBBY9X","ZSF9QEBI","7HNUFQY4","49MHCEYX",
        "L73GGM64","NUX4PLDQ","66EH2MKL","DMT4KZ2E","6AM2Z4K3","DSWL5W88",
        "R5ZSDFMK","JP2UNGTL","F8VEK7B5","MWYSI5GJ","B349UBIN","BXTMAWHG",
        "HX466F9D","9ZI2TDTQ","P84TJZ5N","AZSQLT7N","3N75R2XT","F9CDI7PQ",
        "JJXIVR2S","VBFPBHE6","FZTWFZIW","6YRBWNWS","W4Z7QKKQ","9BG3QAVW",
        "9QWFUQZP","GTDGH6F9","DYDEHR37","2WKTUUS9","FCVGMQ3B","T8JNFAGE",
        "Y9XGNUEV","CDXJJY4R","HVUAQVFL","BNZDUISC","VSPFQB7P","ULA43ATJ",
        "DY8M946P","ZZ6ZZ4I6","8ZX8A3A6","MMJSYJ2C","4MITPN4G","TS7HDQQA",
        "GLCFMVKN","Q7NNFWUG","RVRWMQ5B","Z5RJFYI2","VA7XWX34","4V683DGA",
        "VWS2VM26","SSATLU6V","EHQ8NUV4","ZHGF25CB","9D3T4UIS","E95CIBLN",
        "B8S6UUQA","47TC2B8G","Y6VGNVJ5","ERYBAP63","ZCABP2VH","848I42XR",
        "EWEKQ44Y","PTUKXC7K","RKQGCZZ7","D7JY47Z5","TETXB8YU","QI9QNUGW",
        "VCGLVVA6","4IIN4L4Z",
        // Thesis duplicates
        "SBRXPHN2",  // Akata et al. dupe (keeper: PFHEXKMA)
        "4ZPVPKCP",  // Barez et al. dupe (keeper: EMJ8ES9G)
    ];

    for (const key of orphanDuplicateKeys) {
        try {
            const item = await Zotero.Items.getByLibraryAndKeyAsync(
                Zotero.Libraries.userLibraryID, key
            );
            if (item) {
                await item.eraseTx();
                results.deleted++;
            } else {
                results.skipped++;
            }
        } catch (e) {
            results.skipped++;
        }
    }

    // ========== PART 2: CREATE "To Read" COLLECTIONS ==========
    const libraryID = Zotero.Libraries.userLibraryID;

    // Create parent "To Read" collection
    let toRead = new Zotero.Collection();
    toRead.libraryID = libraryID;
    toRead.name = "📚 To Read";
    await toRead.saveTx();
    results.collections_created++;

    // Create tier subcollections
    const tiers = [
        { name: "Tier 1 — Before Feb 27 (urgent)", papers: [
            "MAK7JGZQ",  // Kuusela & Roy (AAMAS 2024) — finish reading results section
            "FWKEC6IS",  // Turpin et al. — Unfaithful CoT (NeurIPS 2023)
        ]},
        { name: "Tier 2 — Sprint 3 (before Mar 14)", papers: [
            "VWSFDYJY",  // Lanham et al. — Measuring Faithfulness (Anthropic 2023)
            "FYPM6N4Q",  // Chen et al. — Reasoning Models Don't Say What They Think (Anthropic 2025)
            "3PV7NVDG",  // Leibo et al. — MARL Sequential Social Dilemmas (2017)
            "PFHEXKMA",  // Akata et al. — Playing repeated games with LLMs (2025)
            "EWWEJ7KA",  // Chua & Evans — Are Reasoning Models More Faithful? (2025)
        ]},
        { name: "Tier 3 — Phase 2c/2d (before Apr 15)", papers: [
            "IHP5KR5A",  // Park et al. — Generative Agents (2023)
            "96EI7Y86",  // Larooij & Törnberg — Validation challenge (2025)
            "EMJ8ES9G",  // Barez et al. — CoT Is Not Explainability
            "8CPP2XXJ",  // Baker — CoT-as-computation vs rationalization
            "MRA9K5DT",  // Perc et al. — Statistical physics of cooperation (2017)
            "UGLDB735",  // Rachum et al. — Emergent Dominance Hierarchies in RL (2024)
            "6AFVGHQE",  // Lorè & Heydari — Strategic behavior and game structure (2024)
        ]},
        { name: "Tier 4 — Writing phase (background)", papers: [
            "87STH5SJ",  // Epstein & Axtell — Sugarscape (1996)
            "QFLJEAVH",  // Axelrod & Hamilton — Evolution of Cooperation (1981)
            "5V88R5N6",  // Schelling — Dynamic models of segregation (1971)
            "2JNYITMZ",  // Sclar et al. — FormatSpread (2024)
            "FC6AVF4V",  // Zhuo — PromptSensiScore (2024)
            "TWGAJYB5",  // Scheffer et al. — Early-warning signals (2009)
            "S9JC4J9Y",  // Vezhnevets et al. — Concordia (2023)
            "9F7WA9TU",  // Pellert et al. — LLMs replicate human cooperation (2025)
        ]},
    ];

    for (const tier of tiers) {
        let coll = new Zotero.Collection();
        coll.libraryID = libraryID;
        coll.name = tier.name;
        coll.parentID = toRead.id;
        await coll.saveTx();
        results.collections_created++;

        // Add papers to this tier
        for (const key of tier.papers) {
            try {
                const item = await Zotero.Items.getByLibraryAndKeyAsync(libraryID, key);
                if (item) {
                    await coll.addItem(item.id);
                    results.papers_added++;
                }
            } catch (e) {
                // Paper might not exist in library yet
            }
        }
    }

    // ========== SUMMARY ==========
    return `Done!
- Deleted: ${results.deleted} duplicate items
- Skipped: ${results.skipped} (not found or already deleted)
- Collections created: ${results.collections_created}
- Papers added to reading list: ${results.papers_added}

NOTE: Zhang et al. (K-Level Reasoning) and Pfau et al. (Dot by Dot) are not yet
in your Zotero library. Add them manually:
- Zhang: https://arxiv.org/abs/2402.01521
- Pfau: https://arxiv.org/abs/2404.15758

After reading a paper, tag it with "read" in Zotero to track progress.`;
}

main();
