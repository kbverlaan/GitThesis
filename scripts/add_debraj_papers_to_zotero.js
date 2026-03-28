// Run in Zotero > Tools > Developer > Run JavaScript
// Adds papers from Debraj's Mar 11 feedback that are missing from library
// Assigns each to the correct Thesis collection

async function addPapers() {
    // Collection keys
    const NETWORK_REWIRING = "UTLJR6UB";   // 14. Network Rewiring & Co-evolutionary GT
    const LLM_AGENTS       = "Y6E43H5F";   // 3. Emergent Structures — LLM Agents

    const papers = [
        {
            itemType: "journalArticle",
            title: "Scale-Free Networks Provide a Unifying Framework for the Emergence of Cooperation",
            creators: [
                { firstName: "Francisco C.", lastName: "Santos", creatorType: "author" },
                { firstName: "Jorge M.", lastName: "Pacheco", creatorType: "author" }
            ],
            publicationTitle: "Physical Review Letters",
            volume: "95",
            issue: "9",
            pages: "098104",
            date: "2005-08-26",
            DOI: "10.1103/PhysRevLett.95.098104",
            tags: [{ tag: "IV2-network" }, { tag: "debraj-recommended" }],
            collection: NETWORK_REWIRING
        },
        {
            itemType: "journalArticle",
            title: "Static network structure can stabilize human cooperation",
            creators: [
                { firstName: "David G.", lastName: "Rand", creatorType: "author" },
                { firstName: "Martin A.", lastName: "Nowak", creatorType: "author" },
                { firstName: "James H.", lastName: "Fowler", creatorType: "author" },
                { firstName: "Nicholas A.", lastName: "Christakis", creatorType: "author" }
            ],
            publicationTitle: "Proceedings of the National Academy of Sciences",
            volume: "111",
            issue: "48",
            pages: "17093-17098",
            date: "2014-12-02",
            DOI: "10.1073/pnas.1400406111",
            tags: [{ tag: "IV2-network" }, { tag: "debraj-recommended" }],
            collection: NETWORK_REWIRING
        },
        {
            itemType: "journalArticle",
            title: "Selection pressure transforms the nature of social dilemmas in adaptive networks",
            creators: [
                { firstName: "Sven", lastName: "Van Segbroeck", creatorType: "author" },
                { firstName: "Francisco C.", lastName: "Santos", creatorType: "author" },
                { firstName: "Tom", lastName: "Lenaerts", creatorType: "author" },
                { firstName: "Jorge M.", lastName: "Pacheco", creatorType: "author" }
            ],
            publicationTitle: "New Journal of Physics",
            volume: "13",
            issue: "1",
            pages: "013007",
            date: "2011-01",
            DOI: "10.1088/1367-2630/13/1/013007",
            tags: [{ tag: "IV2-network" }, { tag: "debraj-recommended" }],
            collection: NETWORK_REWIRING
        },
        {
            itemType: "preprint",
            title: "The Traitors: Deception and Trust in Multi-Agent Language Model Simulations",
            creators: [
                { firstName: "Pedro M.P.", lastName: "Curvo", creatorType: "author" }
            ],
            repository: "arXiv",
            archiveID: "2505.12923",
            date: "2025-05",
            DOI: "10.48550/arXiv.2505.12923",
            url: "https://arxiv.org/abs/2505.12923",
            tags: [{ tag: "LLM-agents" }, { tag: "deception" }, { tag: "debraj-recommended" }],
            collection: LLM_AGENTS
        }
    ];

    let added = [];
    for (const paper of papers) {
        const item = new Zotero.Item(paper.itemType);
        item.setField("title", paper.title);
        if (paper.publicationTitle) item.setField("publicationTitle", paper.publicationTitle);
        if (paper.repository) item.setField("repository", paper.repository);
        if (paper.archiveID) item.setField("archiveID", paper.archiveID);
        if (paper.volume) item.setField("volume", paper.volume);
        if (paper.issue) item.setField("issue", paper.issue);
        if (paper.pages) item.setField("pages", paper.pages);
        if (paper.url) item.setField("url", paper.url);
        item.setField("date", paper.date);
        item.setField("DOI", paper.DOI);
        item.setCreators(paper.creators);
        for (const tag of paper.tags) {
            item.addTag(tag.tag);
        }
        item.addToCollection(paper.collection);
        await item.saveTx();
        added.push(paper.title.substring(0, 50));
    }

    return `Done! Added ${added.length} papers:\n${added.map(t => `  - ${t}...`).join('\n')}`;
}

await addPapers();
