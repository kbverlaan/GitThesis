#!/usr/bin/env python3
"""Search within a Zotero paper's fulltext.

Usage:
    python3 scripts/search_paper.py <item_key> <search_term> [--context 300]
    python3 scripts/search_paper.py <item_key> --section "Methods"
    python3 scripts/search_paper.py <item_key> --toc

Reads fulltext from Zotero tool-results cache or stdin.
Splits the blob into paragraphs and searches efficiently.
"""
import argparse
import json
import re
import sys
from pathlib import Path

CACHE_DIR = Path.home() / ".claude/projects/-Users-kbverlaan" / "paper_cache"


def load_fulltext(item_key: str) -> str:
    """Load fulltext from cache or tool-results."""
    cache_file = CACHE_DIR / f"{item_key}.txt"
    if cache_file.exists():
        return cache_file.read_text()

    # Search tool-results for this item
    tool_results = Path.home() / ".claude/projects/-Users-kbverlaan"
    for d in tool_results.iterdir():
        if not d.is_dir():
            continue
        for f in d.glob("*.txt"):
            try:
                data = json.loads(f.read_text())
                text = data.get("result", "")
                if item_key in text[:500]:
                    # Found it — cache and return
                    paragraphs = split_paragraphs(text)
                    clean = "\n\n".join(paragraphs)
                    CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(clean)
                    return clean
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

    print(f"ERROR: No fulltext found for {item_key}. Fetch it first via Zotero MCP.", file=sys.stderr)
    sys.exit(1)


def split_paragraphs(text: str) -> list[str]:
    """Split a single-line blob into readable paragraphs."""
    # Strip the JSON metadata prefix if present (everything before "Full Text" or "## Full Text")
    ft_match = re.search(r'(?:## Full Text|Full Text)\s*', text)
    if ft_match:
        text = text[ft_match.end():]

    # Many Zotero PDF extractions lose all whitespace. Try to recover.
    # Insert spaces before capitals that follow lowercase (camelCase boundary)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    # Insert space before ( if preceded by letter
    text = re.sub(r'([a-zA-Z])\(', r'\1 (', text)

    # Replace common paragraph boundaries
    text = re.sub(r'(\.\s{2,})', r'.\n\n', text)
    # Section numbering patterns: "I. ", "II. ", "1. ", "3.1 ", "A. "
    text = re.sub(r'(?<=[.!?])\s*((?:I{1,3}V?|VI{0,3}|[A-Z]|[0-9]+)\.\s+[A-Z])', r'\n\n\1', text)

    # Split on actual newlines
    paragraphs = re.split(r'\n{2,}', text)
    # Clean up
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
    return paragraphs


def add_spaces(text: str) -> str:
    """Try to recover spaces from mushed-together PDF text."""
    # Insert spaces before capitals that follow lowercase
    result = re.sub(r'([a-z,;.!?])([A-Z])', r'\1 \2', text)
    # Insert space before ( if preceded by letter/digit
    result = re.sub(r'([a-zA-Z0-9])\(', r'\1 (', result)
    # Insert space after ) if followed by letter
    result = re.sub(r'\)([a-zA-Z])', r') \1', result)
    # Don't touch already-spaced text
    return result


def search(text: str, query: str, context: int = 300, max_hits: int = 5) -> None:
    """Search for query in text, show context around matches."""
    lower_text = text.lower()
    # Also search without spaces (PDF extraction artifact)
    query_lower = query.lower()
    query_nospace = query_lower.replace(" ", "")
    hits = []
    idx = 0
    while len(hits) < max_hits:
        # Try both with and without spaces
        idx1 = lower_text.find(query_lower, idx)
        idx2 = lower_text.find(query_nospace, idx) if query_nospace != query_lower else -1
        if idx1 < 0 and idx2 < 0:
            break
        # Take the earliest match
        if idx1 < 0:
            idx = idx2
        elif idx2 < 0:
            idx = idx1
        else:
            idx = min(idx1, idx2)

        start = max(0, idx - context)
        end = min(len(text), idx + len(query) + context)
        snippet = add_spaces(text[start:end].strip())
        hits.append((idx, snippet))
        idx += len(query) + 100  # skip ahead

    if not hits:
        print(f"No matches for '{query}'")
        return

    print(f"Found {len(hits)} match(es) for '{query}':\n")
    for i, (pos, snippet) in enumerate(hits, 1):
        print(f"--- Match {i} (pos {pos}) ---")
        print(snippet)
        print()


def show_toc(text: str) -> None:
    """Extract likely section headers."""
    # Look for numbered sections and ALL CAPS headers
    patterns = [
        r'(?:^|\n)\s*(\d+\.?\d*\.?\d*\s+[A-Z][A-Za-z\s,&:]+)',  # "3.1 Methods"
        r'(?:^|\n)\s*([A-Z][A-Z\s]{5,})',  # "INTRODUCTION"
    ]
    headers = []
    for pat in patterns:
        for m in re.finditer(pat, text):
            h = m.group(1).strip()
            if len(h) > 3 and len(h) < 100:
                headers.append((m.start(), h))

    headers.sort()
    # Deduplicate nearby
    filtered = []
    for pos, h in headers:
        if not filtered or pos - filtered[-1][0] > 50:
            filtered.append((pos, h))

    print("Table of Contents (approximate):\n")
    for pos, h in filtered:
        print(f"  [{pos:>6}] {h}")


def show_section(text: str, section_name: str, max_chars: int = 2000) -> None:
    """Extract a section by name."""
    idx = text.lower().find(section_name.lower())
    if idx < 0:
        print(f"Section '{section_name}' not found")
        return
    # Go back to find section start
    start = max(0, idx - 50)
    end = min(len(text), idx + max_chars)
    print(f"--- Section near '{section_name}' (pos {idx}) ---\n")
    print(text[start:end])
    print("\n[... truncated ...]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search within Zotero papers")
    parser.add_argument("item_key", help="Zotero item key")
    parser.add_argument("query", nargs="?", help="Search term")
    parser.add_argument("--context", type=int, default=300, help="Characters of context around match")
    parser.add_argument("--max-hits", type=int, default=5, help="Max matches to show")
    parser.add_argument("--section", help="Extract a section by name")
    parser.add_argument("--toc", action="store_true", help="Show table of contents")
    parser.add_argument("--cache-from", help="Cache fulltext from this JSON file")
    args = parser.parse_args()

    # Allow caching from a specific file
    if args.cache_from:
        data = json.loads(Path(args.cache_from).read_text())
        text = data.get("result", "")
        paragraphs = split_paragraphs(text)
        clean = "\n\n".join(paragraphs)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{args.item_key}.txt"
        cache_file.write_text(clean)
        print(f"Cached {len(clean)} chars to {cache_file}")
        sys.exit(0)

    text = load_fulltext(args.item_key)

    if args.toc:
        show_toc(text)
    elif args.section:
        show_section(text, args.section)
    elif args.query:
        search(text, args.query, context=args.context, max_hits=args.max_hits)
    else:
        print(f"Paper loaded: {len(text)} chars. Use --toc, --section, or provide a search query.")
