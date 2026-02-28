#!/usr/bin/env python3
"""
Set up Zotero reading list and clean duplicates via local API.
Requires Zotero to be running.
"""
import json
import urllib.request
import urllib.error
import random
import string

BASE = "http://localhost:23119/api/users/0"

def api_get(path):
    url = f"{BASE}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def api_post(path, data):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def api_delete(path, version=0):
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, method="DELETE")
    req.add_header("If-Unmodified-Since-Version", str(version))
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code

def api_patch(path, data, version=0):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="PATCH")
    req.add_header("Content-Type", "application/json")
    req.add_header("If-Unmodified-Since-Version", str(version))
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def random_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def create_collection(name, parent_key=None):
    data = [{"name": name}]
    if parent_key:
        data[0]["parentCollection"] = parent_key
    result = api_post("/collections", data)
    if isinstance(result, dict) and "successful" in result:
        successful = result["successful"]
        if successful:
            first = list(successful.values())[0]
            key = first.get("key") or first.get("data", {}).get("key")
            print(f"  Created collection: {name} ({key})")
            return key
    elif isinstance(result, dict) and "success" in result:
        return result["success"].get("0")
    print(f"  Failed to create: {name} — {result}")
    return None

def add_item_to_collection(item_key, collection_key):
    """Add item to collection by updating the item's collections list."""
    try:
        item = api_get(f"/items/{item_key}")
        version = item.get("version", 0)
        collections = item.get("data", {}).get("collections", [])
        if collection_key not in collections:
            collections.append(collection_key)
            api_patch(f"/items/{item_key}", {"collections": collections}, version)
            return True
        return True  # already in collection
    except Exception as e:
        print(f"  Failed to add {item_key}: {e}")
        return False

def delete_item(item_key):
    try:
        item = api_get(f"/items/{item_key}")
        version = item.get("version", 0)
        status = api_delete(f"/items/{item_key}", version)
        return status in (200, 204)
    except Exception as e:
        return False

def main():
    print("=" * 60)
    print("  Zotero Cleanup & Reading List Setup")
    print("=" * 60)

    # ========== PART 1: DELETE DUPLICATES ==========
    print("\n--- Part 1: Deleting duplicates ---")

    orphan_dupes = [
        # CoEngineer orphan duplicates (122 items)
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
        # Thesis duplicates
        "SBRXPHN2",  # Akata dupe (keeper: PFHEXKMA)
        "4ZPVPKCP",  # Barez dupe (keeper: EMJ8ES9G)
    ]

    deleted = 0
    for key in orphan_dupes:
        if delete_item(key):
            deleted += 1
    print(f"  Deleted {deleted}/{len(orphan_dupes)} duplicates")

    # ========== PART 2: CREATE READING LIST ==========
    print("\n--- Part 2: Creating reading list ---")

    parent_key = create_collection("To Read")
    if not parent_key:
        print("ERROR: Could not create parent collection")
        return

    tiers = [
        {
            "name": "Tier 1 — Before Feb 27 (urgent)",
            "papers": [
                "MAK7JGZQ",  # Kuusela & Roy — finish results section
                "FWKEC6IS",  # Turpin et al. — Unfaithful CoT
            ]
        },
        {
            "name": "Tier 2 — Sprint 3 (before Mar 14)",
            "papers": [
                "VWSFDYJY",  # Lanham et al. — Measuring Faithfulness
                "FYPM6N4Q",  # Chen et al. — Reasoning Models Don't Say What They Think
                "3PV7NVDG",  # Leibo et al. — MARL Social Dilemmas
                "PFHEXKMA",  # Akata et al. — Playing repeated games with LLMs
                "EWWEJ7KA",  # Chua & Evans — Are Reasoning Models More Faithful?
            ]
        },
        {
            "name": "Tier 3 — Phase 2c/2d (before Apr 15)",
            "papers": [
                "IHP5KR5A",  # Park et al. — Generative Agents
                "96EI7Y86",  # Larooij & Törnberg — Validation challenge
                "EMJ8ES9G",  # Barez et al. — CoT Is Not Explainability
                "8CPP2XXJ",  # Baker — CoT-as-computation vs rationalization
                "MRA9K5DT",  # Perc et al. — Statistical physics of cooperation
                "UGLDB735",  # Rachum et al. — Emergent Dominance Hierarchies
                "6AFVGHQE",  # Lorè & Heydari — Strategic behavior + game structure
            ]
        },
        {
            "name": "Tier 4 — Writing phase (background)",
            "papers": [
                "87STH5SJ",  # Epstein & Axtell — Sugarscape
                "QFLJEAVH",  # Axelrod & Hamilton — Evolution of Cooperation
                "5V88R5N6",  # Schelling — Segregation
                "2JNYITMZ",  # Sclar et al. — FormatSpread
                "FC6AVF4V",  # Zhuo — PromptSensiScore
                "TWGAJYB5",  # Scheffer et al. — Early-warning signals
                "S9JC4J9Y",  # Vezhnevets et al. — Concordia
                "9F7WA9TU",  # Pellert et al. — LLMs replicate cooperation
            ]
        },
    ]

    for tier in tiers:
        tier_key = create_collection(tier["name"], parent_key)
        if not tier_key:
            continue

        added = 0
        for paper_key in tier["papers"]:
            if add_item_to_collection(paper_key, tier_key):
                added += 1
        print(f"  Added {added}/{len(tier['papers'])} papers to {tier['name']}")

    # ========== SUMMARY ==========
    print("\n" + "=" * 60)
    print(f"  Done!")
    print(f"  Deleted: {deleted} duplicates")
    print(f"  Created: 5 collections (1 parent + 4 tiers)")
    print(f"  Papers sorted into reading list tiers")
    print()
    print("  Still missing from Zotero (add manually):")
    print("  - Zhang et al. K-Level Reasoning: arxiv.org/abs/2402.01521 → Tier 1")
    print("  - Pfau et al. Dot by Dot: arxiv.org/abs/2404.15758 → Tier 1")
    print()
    print("  After reading: right-click paper → Add Tag → 'read'")
    print("=" * 60)


if __name__ == "__main__":
    main()
