// Run in Zotero > Tools > Developer > Run JavaScript
// Adds 3 missing IV grounding papers to your library

async function addPapers() {
    const papers = [
        {
            itemType: "journalArticle",
            title: "Cooperation, social networks, and the emergence of leadership in a prisoner's dilemma with adaptive local interactions",
            creators: [
                { firstName: "Martin G.", lastName: "Zimmermann", creatorType: "author" },
                { firstName: "Victor M.", lastName: "Eguíluz", creatorType: "author" }
            ],
            publicationTitle: "Physical Review E",
            volume: "72",
            issue: "5",
            pages: "056118",
            date: "2005-11-16",
            DOI: "10.1103/PhysRevE.72.056118",
            tags: [{ tag: "IV2-network" }, { tag: "thesis-core" }]
        },
        {
            itemType: "journalArticle",
            title: "Cooperation Prevails When Individuals Adjust Their Social Ties",
            creators: [
                { firstName: "Francisco C.", lastName: "Santos", creatorType: "author" },
                { firstName: "Jorge M.", lastName: "Pacheco", creatorType: "author" },
                { firstName: "Tom", lastName: "Lenaerts", creatorType: "author" }
            ],
            publicationTitle: "PLoS Computational Biology",
            volume: "2",
            issue: "10",
            pages: "e140",
            date: "2006-10-27",
            DOI: "10.1371/journal.pcbi.0020140",
            tags: [{ tag: "IV2-network" }, { tag: "thesis-core" }]
        },
        {
            itemType: "journalArticle",
            title: "Strategic Information Transmission",
            creators: [
                { firstName: "Vincent P.", lastName: "Crawford", creatorType: "author" },
                { firstName: "Joel", lastName: "Sobel", creatorType: "author" }
            ],
            publicationTitle: "Econometrica",
            volume: "50",
            issue: "6",
            pages: "1431-1451",
            date: "1982-11",
            DOI: "10.2307/1913390",
            tags: [{ tag: "IV3-communication" }, { tag: "thesis-core" }]
        }
    ];

    for (const paper of papers) {
        const item = new Zotero.Item(paper.itemType);
        item.setField("title", paper.title);
        item.setField("publicationTitle", paper.publicationTitle);
        item.setField("volume", paper.volume);
        item.setField("issue", paper.issue);
        item.setField("pages", paper.pages);
        item.setField("date", paper.date);
        item.setField("DOI", paper.DOI);
        item.setCreators(paper.creators);
        for (const tag of paper.tags) {
            item.addTag(tag.tag);
        }
        await item.saveTx();
        return_value = `Added: ${paper.title.substring(0, 60)}...`;
    }

    return `Done! Added ${papers.length} papers.`;
}

await addPapers();
