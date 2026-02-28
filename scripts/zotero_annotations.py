#!/usr/bin/env python3
"""Read Zotero 7 annotations directly from SQLite database.

Usage:
    python zotero_annotations.py                    # all annotations
    python zotero_annotations.py --item MAK7JGZQ    # by parent item key
    python zotero_annotations.py --search "fear"     # search in highlights/comments
    python zotero_annotations.py --stats             # annotation stats per paper
"""
import sqlite3
import argparse
import json
import os
from pathlib import Path

ZOTERO_DB = Path(os.environ.get("ZOTERO_DB", "~/Zotero/zotero.sqlite")).expanduser()


def get_connection():
    if not ZOTERO_DB.exists():
        raise FileNotFoundError(f"Zotero database not found at {ZOTERO_DB}")
    return sqlite3.connect(f"file:{ZOTERO_DB}?mode=ro", uri=True)


def get_annotations(item_key=None, search=None):
    conn = get_connection()
    query = """
        SELECT
            ia.type,
            ia.text,
            ia.comment,
            ia.pageLabel,
            ia.color,
            ia.sortIndex,
            i.key AS annotation_key,
            pi.key AS attachment_key,
            COALESCE(pi2.key, pi.key) AS parent_key,
            COALESCE(
                (SELECT GROUP_CONCAT(v.value, ' — ')
                 FROM itemData id2
                 JOIN itemDataValues v ON id2.valueID = v.valueID
                 JOIN fields f ON id2.fieldID = f.fieldID
                 WHERE id2.itemID = COALESCE(att.parentItemID, pi.itemID)
                 AND f.fieldName = 'title'),
                'Unknown'
            ) AS paper_title,
            COALESCE(
                (SELECT GROUP_CONCAT(cd.lastName || ', ' || cd.firstName, '; ')
                 FROM itemCreators ic
                 JOIN creators cd ON ic.creatorID = cd.creatorID
                 WHERE ic.itemID = COALESCE(att.parentItemID, pi.itemID)
                 AND ic.orderIndex < 2),
                'Unknown'
            ) AS authors
        FROM itemAnnotations ia
        JOIN items i ON ia.itemID = i.itemID
        JOIN items pi ON ia.parentItemID = pi.itemID
        LEFT JOIN itemAttachments att ON pi.itemID = att.itemID
        LEFT JOIN items pi2 ON att.parentItemID = pi2.itemID
        WHERE 1=1
    """
    params = []

    if item_key:
        query += " AND (pi2.key = ? OR pi.key = ?)"
        params.extend([item_key, item_key])

    if search:
        query += " AND (ia.text LIKE ? OR ia.comment LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY parent_key, CAST(ia.pageLabel AS INTEGER), ia.sortIndex"

    cursor = conn.execute(query, params)
    columns = [d[0] for d in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return results


def get_stats():
    conn = get_connection()
    query = """
        SELECT
            COALESCE(pi2.key, pi.key) AS parent_key,
            COALESCE(
                (SELECT v.value
                 FROM itemData id2
                 JOIN itemDataValues v ON id2.valueID = v.valueID
                 JOIN fields f ON id2.fieldID = f.fieldID
                 WHERE id2.itemID = COALESCE(att.parentItemID, pi.itemID)
                 AND f.fieldName = 'title'),
                'Unknown'
            ) AS paper_title,
            COUNT(*) AS annotation_count,
            SUM(CASE WHEN ia.comment != '' AND ia.comment IS NOT NULL THEN 1 ELSE 0 END) AS with_comments
        FROM itemAnnotations ia
        JOIN items i ON ia.itemID = i.itemID
        JOIN items pi ON ia.parentItemID = pi.itemID
        LEFT JOIN itemAttachments att ON pi.itemID = att.itemID
        LEFT JOIN items pi2 ON att.parentItemID = pi2.itemID
        GROUP BY parent_key
        ORDER BY annotation_count DESC
    """
    cursor = conn.execute(query)
    columns = [d[0] for d in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return results


def main():
    parser = argparse.ArgumentParser(description="Read Zotero 7 annotations from SQLite")
    parser.add_argument("--item", help="Parent item key (e.g., MAK7JGZQ)")
    parser.add_argument("--search", help="Search in highlight text or comments")
    parser.add_argument("--stats", action="store_true", help="Show annotation stats per paper")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.stats:
        results = get_stats()
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(f"\n{'Paper':<70} {'Annot':>5} {'Notes':>5}")
            print("-" * 85)
            for r in results:
                title = r["paper_title"][:67] + "..." if len(r["paper_title"]) > 70 else r["paper_title"]
                print(f"{title:<70} {r['annotation_count']:>5} {r['with_comments']:>5}")
            print(f"\nTotal: {sum(r['annotation_count'] for r in results)} annotations across {len(results)} papers")
        return

    results = get_annotations(item_key=args.item, search=args.search)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    if not results:
        print("No annotations found.")
        return

    current_paper = None
    for r in results:
        if r["paper_title"] != current_paper:
            current_paper = r["paper_title"]
            print(f"\n{'='*80}")
            print(f"  {r['authors']} — {current_paper}")
            print(f"  Zotero key: {r['parent_key']}")
            print(f"{'='*80}")

        ann_type = {1: "highlight", 2: "note", 3: "image", 4: "ink", 5: "underline"}.get(r["type"], "?")
        page = r["pageLabel"] or "?"
        print(f"\n  [{ann_type}] p.{page}")
        if r["text"]:
            print(f"  > {r['text']}")
        if r["comment"]:
            print(f"  💬 {r['comment']}")


if __name__ == "__main__":
    main()
