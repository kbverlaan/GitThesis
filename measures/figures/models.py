"""Section 4.4, Swap the model --- Gemma against Qwen, and a one-run probe.

Five runs per level, one payoff cell, one second model. That is an existence
proof that a finding can depend on the player and carries no estimate of how far
the dependence goes, which the chapter states and these figures do not try to
improve on.

The arms share their seeds, so a difference is not a difference in starting
position. `seed_overlap()` checks that rather than assuming it.
"""
from __future__ import annotations

import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
for _m in ("core", "_shared"):
    sys.path.insert(0, str(HIER.parent / _m))

from collections import Counter                                          # noqa: E402
import combat, graph, logs, model, runstat, text, turns                  # noqa: E402
from result import Result                                                # noqa: E402
import runstat  # noqa: E402
import runset                                                            # noqa: E402

LEVELS = ("L2", "L3", "L4")
ARMS = {"gemma": "prod_{}_knife",
        "qwen": "robust_qwen_{}_knife",
        "deepseek": "robust_deepseek_{}_knife"}


def _cells(arm: str):
    return {lvl: runset.cel(ARMS[arm].format(lvl)) for lvl in LEVELS}


# --- m:model-swap-arm ------------------------------------------------------

def seed_overlap() -> dict:
    """Which seeds the arms actually share, per level.

    The claim that the swap holds the starting position fixed rests on this, so
    it is computed rather than asserted. A seed present in one arm and not the
    other means the comparison at that level is between different draws.
    """
    uit = {}
    for lvl in LEVELS:
        per = {}
        for arm, patroon in ARMS.items():
            cel = patroon.format(lvl)
            per[arm] = {r["seed"] for r in runset.rijen() if r["cel"] == cel}
        gedeeld = per["gemma"] & per["qwen"]
        uit[lvl] = {"gemma": len(per["gemma"]), "qwen": len(per["qwen"]),
                    "shared": len(gedeeld),
                    "qwen_seeds_not_in_gemma": sorted(per["qwen"] - per["gemma"])}
    return uit


def inequality_by_arm() -> dict:
    """Final Gini per arm and level, with the two run-level ranges.

    The chapter claims the L2 cells do not overlap, which is a statement about
    ranges and not about means, so both are reported.
    """
    def samenvat(xs):
        return {"mean": round(sum(xs) / len(xs), 3), "n": len(xs),
                "min": round(min(xs), 3), "max": round(max(xs), 3)}

    uit = {}
    for lvl in LEVELS:
        per = {}
        for arm in ARMS:
            paths = runset.cel(ARMS[arm].format(lvl))
            per[arm] = samenvat(runstat.per_run(paths, runstat.final_gini))

        # The chapter compares the arms "on the same five seeds", and the whole
        # Gemma cell is fifteen or ten runs. Reporting only the full cell left
        # the sentence's own numbers unreproducible from this figure --- they
        # are the seed-matched ones, and they differ by up to six points.
        gedeeld = {r["seed"] for r in runset.rijen()
                   if r["cel"] == ARMS["gemma"].format(lvl)} & \
                  {r["seed"] for r in runset.rijen()
                   if r["cel"] == ARMS["qwen"].format(lvl)}
        op_seed = {r["bestand"]: r["seed"] for r in runset.rijen()
                   if r["cel"] == ARMS["gemma"].format(lvl)}
        paden = [p for p in runset.cel(ARMS["gemma"].format(lvl))
                 if op_seed.get(p.name) in gedeeld]
        if paden:
            per["gemma_on_shared_seeds"] = samenvat(
                runstat.per_run(paden, runstat.final_gini))

        per["overlap"] = not (per["gemma"]["max"] < per["qwen"]["min"]
                              or per["qwen"]["max"] < per["gemma"]["min"])
        g = per.get("gemma_on_shared_seeds")
        if g:
            per["overlap_on_shared_seeds"] = not (
                g["max"] < per["qwen"]["min"] or per["qwen"]["max"] < g["min"])
        uit[lvl] = per
    return uit


# --- m:address-each-other --------------------------------------------------

def _recipients_per_message(p) -> float | None:
    n = tot = 0
    for e in logs.rounds(p):
        for m in (e.get("messages") or []):
            n += 1
            tot += len(m.get("to") or [])
    return tot / n if n else None


def _mean_degree(p, laatste: bool = True) -> float | None:
    rs = logs.rounds(p)
    e = rs[-1] if laatste else rs[0]
    net = e.get("network") or {}
    edges = net.get("edges") or []
    leden = {x for a, b in edges for x in (a, b)} | set(e.get("agents") or {})
    return 2 * len(edges) / len(leden) if leden else None


def _invites(p) -> int:
    return sum(1 for e in logs.rounds(p)
               for a in (e.get("agents") or {}).values()
               if (a.get("rewire_intent") or {}).get("invite"))


def _severings(p) -> int:
    return sum(1 for e in logs.rounds(p)
               for a in (e.get("agents") or {}).values()
               if (a.get("rewire_intent") or {}).get("drop"))


def _largest_coalition(p) -> int | None:
    v = [len(c.get("attackers") or []) for _, c in combat.fights(p)]
    return max(v) if v else None


REACH = {
    "recipients_per_message": _recipients_per_message,
    "mean_degree_first_round": lambda p: _mean_degree(p, laatste=False),
    "mean_degree_last_round": _mean_degree,
    "invitations": _invites,
    "severings": _severings,
    "solo_share_of_attacks": combat.solo_share,
    "largest_coalition": _largest_coalition,
}


def how_broadly_they_coordinate() -> dict:
    """The reach axis: how many agents a model addresses, links to and attacks with.

    Every quantity is a per-run value summarised over five to ten runs, and the
    totals the chapter quotes for severings and invitations are sums rather than
    means, so both are given.
    """
    uit = {}
    for arm in ARMS:
        per_level = {}
        for lvl in LEVELS:
            paths = runset.cel(ARMS[arm].format(lvl))
            rij = {}
            for naam, scalar in REACH.items():
                xs = [scalar(p) for p in paths]
                geldig = [x for x in xs if x is not None]
                rij[naam] = {"mean": round(sum(geldig) / len(geldig), 2) if geldig else None,
                             "total": round(sum(geldig), 1) if geldig else None,
                             "max": round(max(geldig), 2) if geldig else None,
                             "defined_in": len(geldig), "runs": len(xs)}
            per_level[lvl] = rij
        uit[arm] = per_level
    return uit


# --- m:pact-institution-language -------------------------------------------

def coined_terms_by_arm() -> dict:
    """Shared names per arm and level, on the same three-adopter threshold.

    The threshold is what makes the comparison interesting and also what makes
    it partly circular: a name needs three adopters, and a model that addresses
    2.5 agents per message rarely reaches three. Both the count and the reach
    are reported so a reader can see the two together.

    Wordings of one arrangement are folded together before counting, which
    matters more for a comparison between arms than within one: a model that
    repeats a phrase verbatim and a model that rephrases it each time would
    otherwise differ in coined names without differing in what they coined.
    """
    uit = {}
    for arm in ARMS:
        per_level = {}
        for lvl in LEVELS:
            paths = runset.cel(ARMS[arm].format(lvl))
            per = {}
            for drempel in (2, 3, 4):
                aantal = [len(text.named_agreements(p, drempel)) for p in paths]
                per[f"min_users={drempel}"] = {"total": sum(aantal),
                                               "mean": round(sum(aantal) / len(aantal), 2),
                                               "per_run": sorted(aantal)}
            per_level[lvl] = per
        uit[arm] = per_level
    return uit


# --- m:welfare-arrangements-redistribute -----------------------------------

def nobody_rescues_the_dying() -> dict:
    """Transfers reaching an agent already below one resource.

    A structural count with no detector in it: an agent's holdings and the
    target of every transfer are both in the action log. The denominator is
    every agent-round spent below the threshold, so the figure answers "of all
    the chances there were to rescue someone, how many were taken".
    """
    uit = {}
    for arm in ARMS:
        onder = gered = 0
        for lvl in LEVELS:
            for p in runset.cel(ARMS[arm].format(lvl)):
                k, g = runstat.destitute_and_rescues(p)
                onder += k
                gered += g
        uit[arm] = Result(value=gered, n=len(LEVELS) * 5, denominator=onder,
                          unit="agent-rounds below one resource",
                          note=f"{gered} transfers reached an agent below 1.0 "
                               f"resource, out of {onder} agent-rounds spent there").as_dict()
    return uit


FIGURES = {
    "m:model-swap-arm": lambda: {"seeds": seed_overlap(),
                                 "inequality": inequality_by_arm()},
    "m:address-each-other": how_broadly_they_coordinate,
    "m:pact-institution-language": coined_terms_by_arm,
    "m:rescues-the-dying": nobody_rescues_the_dying,
}


# --- m:second-order-reasoning ----------------------------------------------

def attribution_orders() -> dict:
    """How far the reasoning traces model other minds, per arm and level.

    The unit is the reasoning block, not the sentence. That departs from the
    rule the rest of the language family enforces, and it is the measure's own
    definition: an attribution can span two sentences and splitting would cut
    the nesting apart. These shares are therefore not comparable with any
    sentence-level figure elsewhere in the chapter.

    Two cell lists serve two purposes and they are not interchangeable. The
    between-arm comparison uses knife-edge only, because that is the sole cell
    the robustness arms ran and therefore the only matched column. The
    within-Gemma spread uses every production cell, because it is the noise
    floor: it says how large a difference has to be before it is worth reading,
    and a comparison narrower than that spread sits inside it.

    The probe is what the design is for. If the order of attribution tracked how
    broadly a model coordinates, the arm that writes to 1.4 to 2.4 recipients and
    coins no shared name should sit lowest. It is too small to confirm anything
    and exactly large enough to refute that.

    Three things are reported beside the rates because each answers an
    objection. The length control divides by block length, since a longer block
    has more chances to match. The plural-first-person share matters because one
    arm writes "we" where the others write "I", and counting that as another
    agent turns its own reasoning into an attribution. And the within-arm spread
    across capacity levels is given, because if it exceeds the difference
    between arms then the arm comparison sits inside its own noise.
    """
    uit = {}
    # Every production cell, not only knife-edge. The within-arm spread across
    # capacity levels and payoff cells is the figure that decides whether the
    # between-arm comparison means anything: if one model varies more against
    # itself than the two models differ from each other, the model difference
    # sits inside its own noise. That cannot be seen from the knife-edge column
    # alone, which is what an earlier version of this list measured.
    cellen = ([f"prod_{r}_{q}" for r in ("L1", "L2", "L3", "L4")
               for q in ("scar", "knife", "abund")]
              + [f"prod_{r}_knife_nocomm" for r in ("L1", "L2", "L3", "L4")]
              + [f"robust_{m}_{r}_knife" for m in ("qwen", "deepseek") for r in LEVELS])
    for c in cellen:
        try:
            paths = runset.cel(c)
        except runset.RunsetError:
            continue
        tel = Counter()
        lengtes = []
        for p in paths:
            namen = set()
            for e in logs.rounds(p):
                namen |= set((e.get("agents") or {}).keys())
            for e in logs.rounds(p):
                for a in (e.get("agents") or {}).values():
                    blok = str(a.get("thinking") or "")
                    if not blok.strip():
                        continue
                    tel["blocks"] += 1
                    tel[f"order{text.attribution_order(blok, namen)}"] += 1
                    tel["plural"] += text.plural_first_person(blok)
                    lengtes.append(len(blok.split()))
        n = tel["blocks"]
        if not n:
            continue
        mediaan_lengte = sorted(lengtes)[len(lengtes) // 2]
        kort = [l for l in lengtes if l <= mediaan_lengte]
        uit[c] = Result(
            value={"blocks": n,
                   "order_2_or_higher_pct": round(100 * (tel["order2"] + tel["order3"]) / n, 2),
                   "order_3_pct": round(100 * tel["order3"] / n, 3),
                   "order_3_count": tel["order3"]},
            n=len(paths), denominator=n, unit="reasoning blocks",
            sensitivity={"first_person_plural_pct": round(100 * tel["plural"] / n, 1),
                         "median_block_words": mediaan_lengte,
                         "blocks_at_or_below_median_length": len(kort)},
            note="unit is the reasoning block, not the sentence; not comparable "
                 "with sentence-level figures").as_dict()
    return uit


FIGURES["m:second-order-reasoning"] = attribution_orders
