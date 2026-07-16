#!/usr/bin/env python3
"""Strip een run tot een NEUTRALE samenvatting voor onafhankelijk labelen.

Doel: een blinde labelaar (mens of subagent) moet de CO-orde-type-definities
kunnen toepassen ZONDER de gate-output, DV-waarden, of enige conditie-hint
(comms-off/knife/forced) te zien. Bevat alleen ruwe gedrags-observaties:
actie-mix over de tijd, wie-doet-wat-naar-wie (geaggregeerd), representatieve
berichten met normatieve/sanctie/institutie-taal (verbatim), resource-verloop,
en commons-toestand. Runs worden geanonimiseerd tot 'Run NN'.

Gebruik: python3 strip_for_labeling.py run1.jsonl run2.jsonl ... > stripped.md
"""
import argparse, json, sys
from collections import Counter, defaultdict

ACT = {"transfer": "give", "take": "attack", "strengthen": "arm",
       "harvest": "harvest", "drop": "drop-tie", "invite": "invite-tie", "hold": "hold"}


def canon(info):
    a = str(info.get("action") or "hold").lower()
    ri = info.get("rewire_intent") or {}
    if a in ("hold", "do_nothing") and ri.get("drop"): return "drop"
    if a in ("hold", "do_nothing") and ri.get("invite"): return "invite"
    if a.startswith("invest") or a == "transfer": return "transfer"
    if a.startswith("take") or a == "attack": return "take"
    if "arm" in a or a == "strengthen": return "strengthen"
    if a.startswith("harvest"): return "harvest"
    if a in ("drop", "invite"): return a
    return "hold"


def summarize(path, run_id):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    nr = len(rows)
    out = [f"## Run {run_id}", f"Rounds: {nr}"]

    # actie-mix per kwart
    def block(rs):
        c = Counter()
        for d in rs:
            for info in (d.get("agents") or {}).values():
                c[canon(info)] += 1
        tot = sum(c.values()) or 1
        return " ".join(f"{ACT.get(k,k)}:{100*v//tot}%" for k, v in c.most_common())
    q = max(1, nr // 4)
    out.append("\nAction mix over time (quarters):")
    for i in range(0, nr, q):
        out.append(f"  R{i+1:>2}-{min(i+q,nr):>2}: {block(rows[i:i+q])}")

    # gerichte flows (geaggregeerd): geven, aanvallen, berichten
    give = Counter(); atk = Counter(); msg = Counter()
    mob_rounds = 0
    for d in rows:
        ag = d.get("agents") or {}
        by_t = defaultdict(int)
        for aid, info in ag.items():
            a = canon(info); t = info.get("target")
            if a == "transfer" and t: give[t] += 1
            if a == "take" and t: atk[t] += 1; by_t[t] += 1
        if by_t and max(by_t.values()) >= 3: mob_rounds += 1
        for m in (d.get("messages") or []):
            to = m.get("to"); tos = to if isinstance(to, list) else ([] if to in (None, "all") else [to])
            for t in tos: msg[t] += 1
    out.append(f"\nTargeting (whole run): {atk and sum(atk.values()) or 0} attacks over "
               f"{len(atk)} distinct targets; rounds where >=3 agents attacked one target: {mob_rounds}.")
    out.append(f"Transfers: {sum(give.values())} over {len(give)} distinct recipients.")

    # resource-verloop + overlevenden
    def totR(d): return sum(i.get("resources", 0) for i in (d.get("agents") or {}).values())
    res = [totR(d) for d in rows]
    finals = sorted((i.get("resources", 0) for i in rows[-1].get("agents", {}).values()), reverse=True)
    alive = sum(1 for x in finals if x > 0.5)
    out.append(f"\nTotal resources R1 -> R{nr}: {res[0]:.0f} -> {res[-1]:.0f}. "
               f"Final richest {finals[0]:.0f}, poorest {finals[-1]:.0f}, alive {alive}/{len(finals)}.")

    # commons (indien aanwezig)
    cb = [d.get("commons") for d in rows if isinstance(d.get("commons"), dict)]
    if cb:
        K = next((c.get("K") for c in cb if c.get("K")), 120)
        stocks = [c.get("stock_after_regen", c.get("stock_before")) for c in cb]
        stocks = [s for s in stocks if s is not None]
        collapsed = any(c.get("collapsed") for c in cb)
        out.append(f"\nShared resource pool (capacity {K:.0f}): start {stocks[0]:.0f}, "
                   f"low {min(stocks):.0f}, end {stocks[-1]:.0f}, collapsed: {collapsed}.")

    # representatieve berichten: normatief / sanctie / institutie-taal
    kws = ["must", "should", "shall", "forbidden", "may not", "violat", "betray",
           "traitor", "punish", "exile", "pact", "rule", "agree", "propose",
           "circle", "council", "coalition", "sanction", "enforce", "defect"]
    enf_kw = ["violat", "betray", "traitor", "punish", "exile", "defect", "sanction", "enforce"]
    cand = []                                   # (round, is_enforcement, text)
    seen = set()
    for d in rows:
        r = d.get("round")
        for m in (d.get("messages") or []):
            t = (m.get("text") or "").strip()
            low = t.lower()
            if any(k in low for k in kws) and t not in seen and len(t) > 15:
                seen.add(t)
                cand.append((r, any(k in low for k in enf_kw), t))
    # spreid over de run + prioriteer handhavings-taal (violation/enforcement)
    enf = [c for c in cand if c[1]]
    rest = [c for c in cand if not c[1]]
    def spread(lst, k):
        if len(lst) <= k: return lst
        step = len(lst) / k
        return [lst[int(i * step)] for i in range(k)]
    picked = sorted(spread(enf, 8) + spread(rest, 6), key=lambda c: c[0])
    quotes = [f"  R{r}: \"{t[:160]}\"" for (r, _, t) in picked]
    if quotes:
        out.append("\nSample messages (containing rule/norm/coordination language):")
        out += quotes[:14]
    else:
        out.append("\nNo messages in this run (agents could not communicate).")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    args = ap.parse_args()
    print("# Runs to label (each independent; no ordering meaning)\n")
    for i, p in enumerate(args.paths, start=1):
        print(summarize(p, f"{i:02d}"))
        print("\n---\n")


if __name__ == "__main__":
    main()
