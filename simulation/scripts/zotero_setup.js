// Zotero JS Console script — Tools → Developer → Run JavaScript
// Adds missing papers by DOI, creates new collections, cleans old tiers

(async function() {
    const libraryID = Zotero.Libraries.userLibraryID;
    const parentKey = "8IHZK6TT"; // "Thesis — Origins of Order"

    // ── 1. Create new sub-collections ──────────────────────────
    const newCollections = {
        "12. Mechanism Design & Game Theory": null,
        "13. Theory of Mind": null,
        "14. Network Rewiring & Co-evolutionary GT": null,
    };

    for (const name of Object.keys(newCollections)) {
        // Check if already exists
        const existing = Zotero.Collections.getByLibrary(libraryID)
            .find(c => c.name === name);
        if (existing) {
            newCollections[name] = existing.key;
            Zotero.debug(`Collection "${name}" already exists: ${existing.key}`);
        } else {
            const col = new Zotero.Collection();
            col.libraryID = libraryID;
            col.name = name;
            col.parentKey = parentKey;
            await col.saveTx();
            newCollections[name] = col.key;
            Zotero.debug(`Created collection "${name}": ${col.key}`);
        }
    }

    // ── 2. Papers to add ───────────────────────────────────────
    const papers = [
        // Mechanism Design & Game Theory
        { doi: "10.1287/mnsc.14.3.159", collection: "12. Mechanism Design & Game Theory", note: "Harsanyi 1967 - Incomplete Information" },
        { doi: "10.1111/0034-6527.00287", collection: "12. Mechanism Design & Game Theory", note: "Baliga & Sjöström 2004 - Arms Races" },
        { doi: "10.1287/moor.6.1.58", collection: "12. Mechanism Design & Game Theory", note: "Myerson 1981 - Optimal Auction Design" },
        { doi: "10.1177/1043463195007001004", collection: "12. Mechanism Design & Game Theory", note: "Sally 1995 - Cheap Talk Meta-Analysis" },
        // Crawford & Sobel has no DOI — added manually below
        // Hurwicz 1960 — book chapter, added manually below

        // Theory of Mind
        { doi: "10.1016/j.artint.2013.05.004", collection: "13. Theory of Mind", note: "De Weerd 2013 - ToM levels in agents" },
        { doi: "10.1007/s10458-015-9317-1", collection: "13. Theory of Mind", note: "De Weerd 2017 - Negotiating with other minds" },
        { doi: "10.1007/s10992-009-9115-9", collection: "13. Theory of Mind", note: "Verbrugge 2009 - Logic and Social Cognition" },

        // Network Rewiring & Co-evolutionary GT
        { doi: "10.1371/journal.pcbi.0020140", collection: "14. Network Rewiring & Co-evolutionary GT", note: "Santos, Pacheco & Lenaerts 2006 - Cooperation Prevails" },
        { doi: "10.1111/j.1420-9101.2005.01063.x", collection: "14. Network Rewiring & Co-evolutionary GT", note: "Santos & Pacheco 2006 - New Route to Cooperation" },
        { doi: "10.1103/PhysRevE.69.065102", collection: "14. Network Rewiring & Co-evolutionary GT", note: "Zimmermann et al 2004 - Coevolution" },
        { doi: "10.1073/pnas.1108243108", collection: "14. Network Rewiring & Co-evolutionary GT", note: "Rand et al 2011 PNAS - Dynamic Social Networks" },
        { doi: "10.1103/PhysRevLett.102.058105", collection: "14. Network Rewiring & Co-evolutionary GT", note: "Van Segbroeck et al 2009 - Reacting to Adverse Ties" },

        // Political Philosophy / Foundational
        { doi: "10.1017/CBO9780511807763", collection: "1. Foundational ABM & Cooperation", note: "Ostrom 1990 - Governing the Commons" },
        { doi: "10.1093/acprof:oso/9780195178111.001.0001", collection: "1. Foundational ABM & Cooperation", note: "Binmore 2005 - Natural Justice" },
    ];

    // ── 3. Add papers by DOI ───────────────────────────────────
    let added = 0;
    let failed = [];

    for (const paper of papers) {
        try {
            const translate = new Zotero.Translate.Search();
            translate.setIdentifier({ DOI: paper.doi });
            translate.setHandler("translators", function(_, translators) {
                translate.setTranslator(translators);
            });

            const translators = await translate.getTranslators();
            translate.setTranslator(translators);

            const items = await translate.translate({
                libraryID: libraryID,
                collections: [newCollections[paper.collection] || ""],
                saveAttachments: false
            });

            if (items && items.length > 0) {
                // Add to correct collection if not auto-assigned
                const collKey = newCollections[paper.collection];
                if (collKey) {
                    const col = Zotero.Collections.getByLibrary(libraryID)
                        .find(c => c.key === collKey);
                    if (col && !col.hasItem(items[0].id)) {
                        await col.addItem(items[0].id);
                    }
                }
                added++;
                Zotero.debug(`✓ Added: ${paper.note} (${paper.doi})`);
            }
        } catch (e) {
            failed.push(paper.note + " — " + e.message);
            Zotero.debug(`✗ Failed: ${paper.note} — ${e.message}`);
        }

        // Small delay to avoid rate limiting
        await Zotero.Promise.delay(1000);
    }

    // ── 4. Clean up old tier collections ───────────────────────
    // Remove the outdated To Read tier sub-collections
    const oldTierKeys = [
        "38L3BBP4", // Tier 1 — Before Feb 27
        "ZNJHWBY5", // Tier 2 — Sprint 3 (before Mar 14)
        "E3776XPN", // Tier 3 — Phase 2c/2d (before Apr 15)
        "J4W456BA", // Tier 4 — Writing phase
        "RL7ELU47", // 📚 To Read (parent)
    ];

    // NOTE: Items in these collections are NOT deleted — only the collections.
    // Items remain in the library and in any other collections they belong to.
    for (const key of oldTierKeys) {
        try {
            const col = Zotero.Collections.getByLibrary(libraryID)
                .find(c => c.key === key);
            if (col) {
                // Remove sub-collections first (children before parent)
                await col.eraseTx();
                Zotero.debug(`Removed collection: ${col.name}`);
            }
        } catch (e) {
            Zotero.debug(`Could not remove ${key}: ${e.message}`);
        }
    }

    // ── 5. Summary ─────────────────────────────────────────────
    const summary = `
=== ZOTERO SETUP COMPLETE ===
Papers added by DOI: ${added}/${papers.length}
${failed.length > 0 ? "Failed:\n  " + failed.join("\n  ") : "No failures!"}

MANUAL ADDS NEEDED:
1. Crawford & Sobel (1982) — no DOI, add via JSTOR:
   https://www.jstor.org/stable/1913390
   → Collection: 12. Mechanism Design & Game Theory

2. Hurwicz (1960) — book chapter, add via Cambridge:
   https://doi.org/10.1017/cbo9780511752940.014
   → Collection: 12. Mechanism Design & Game Theory

3. Hobbes (1651) Leviathan — add manually as book:
   https://www.gutenberg.org/ebooks/3207
   → Collection: 1. Foundational ABM & Cooperation

Old tier collections removed (items preserved in library).
    `;

    Zotero.debug(summary);
    return summary;
})();
