---
name: search-paper
description: Search within a Zotero paper efficiently. Use when the user asks about a paper's content, wants to find a specific passage, or asks you to explain a section. Avoids reading entire papers into context.
allowed-tools: Bash, Read, Grep, mcp__zotero__zotero_search_items, mcp__zotero__zotero_get_item_fulltext, mcp__zotero__zotero_get_item_metadata
---

# Search Paper

Search within Zotero papers efficiently WITHOUT reading entire fulltexts into context.

## Arguments

$ARGUMENTS — either an item key + search term, or author/title + search term.

Examples:
- `/search-paper Camerer Poisson`
- `/search-paper Y9DILWJ6 cognitive hierarchy`
- `/search-paper Kuusela homogeneous level`

## Why this skill exists

Zotero fulltext is 15-30K tokens per paper. Reading it all wastes context. Instead:
- Cache the fulltext once to disk
- Use targeted searches (50-500 tokens per query)
- Explain mushed-together text in plain language when needed

## Cache location

`~/.claude/projects/-Users-kbverlaan/paper_cache/<ITEM_KEY>.txt`

## Helper script

`/Users/kbverlaan/GitThesis/scripts/search_paper.py`

## Workflow

### Step 1: Identify the paper

Parse the user's query:
- If there's a Zotero item key (uppercase alphanumeric, 8 chars like Y9DILWJ6): use directly
- If there's an author/title: search Zotero with `mcp__zotero__zotero_search_items`, get the item key

### Step 2: Check cache

```bash
ls ~/.claude/projects/-Users-kbverlaan/paper_cache/<ITEM_KEY>.txt 2>/dev/null
```

If cached, skip to Step 4.

### Step 3: Fetch and cache (only if not cached)

1. Fetch: `mcp__zotero__zotero_get_item_fulltext` with item key
2. The output gets saved to a tool-results file (shown in the response). Cache it:
```bash
python3 /Users/kbverlaan/GitThesis/scripts/search_paper.py <ITEM_KEY> --cache-from "<tool-results-file-path>"
```

### Step 4: Search

```bash
# Search for a term (shows 5 matches with 300 chars context)
python3 /Users/kbverlaan/GitThesis/scripts/search_paper.py <ITEM_KEY> "search term" --context 400

# Fewer/more hits
python3 /Users/kbverlaan/GitThesis/scripts/search_paper.py <ITEM_KEY> "term" --max-hits 3

# Show approximate table of contents
python3 /Users/kbverlaan/GitThesis/scripts/search_paper.py <ITEM_KEY> --toc

# Extract a longer section
python3 /Users/kbverlaan/GitThesis/scripts/search_paper.py <ITEM_KEY> --section "Methods"
```

### Step 5: Respond

- Show relevant passages
- If text is mushed together (no spaces — common with older PDFs), **explain in plain language**
- Answer the specific question, don't summarize the whole paper
- If no matches: try alternative terms, synonyms, or the concept in different words

## Known cached papers

| Key | Paper |
|-----|-------|
| Y9DILWJ6 | Camerer, Ho & Chong (2004) — Cognitive Hierarchy (QJE) |
| MAK7JGZQ | Kuusela & Roy (2024) — Hobbesian Trap (AAMAS) |
| 365LNMSS | Camerer et al. (2005) — Cognitive Hierarchy (conference version) |

Update this table as more papers get cached.

## Important

- NEVER read entire fulltext into context. Always use targeted searches.
- The script handles no-space PDF artifacts (searches both "Poisson distribution" and "Poissondistribution").
- Some older PDFs (QJE, AER) have terrible text extraction. Explain passages in plain language.
- Cache persists across sessions.
