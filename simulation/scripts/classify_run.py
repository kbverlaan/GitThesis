#!/usr/bin/env python3
"""
Pilot 5 regime classifier (v0 — WORKING DRAFT).

Reference: Obsidian Projecten/Thesis/Plannen/Coding Scheme - Pilot 5 Regimes.md

Usage:
  python classify_run.py <run_log.jsonl>
  python classify_run.py --batch <dir>
  python classify_run.py <run_log.jsonl> --strike-threshold 1 --paralysis-stdev 5.0
"""

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from collections import Counter


# ─── v0 default thresholds (tuneable; calibrate during coding pass) ─────────

DEFAULTS = {
    "attempt_threshold": 1,       # PREDATION iff n_coalition_attempts > k (behavioral)
                                  # default 1: ≥2 coalition attempts in event_window=3 rounds
                                  # = sustained coordination, not a single isolated event
    "strike_threshold": 0,        # used inside predation subs (success vs failed)
    "paralysis_stdev": 5.0,       # 1b iff stdev(final_wealth) < this
    "paralysis_do_nothing": 0.6,  # 1b iff do_nothing_fraction > this
    "top_n_others": 3,            # math-protected: top vs sum(top-N others)
    "hegemony_top_ratio": 2.0,    # 1c iff top_wealth ≥ this × mean(all others)
    "hegemony_runnerup_ratio": 1.5,  # 1c also requires top ≥ this × second_highest
    "bankruptcy_window": 5,       # last-K rounds for bankruptcy framing
    "solo_predator_min_strikes": 2,  # persistent solo predator threshold (per window)
    "partial_outcome_ratio": 0.5,  # outcome=partial iff 0 < success_ratio < this
    "window_size": 10,            # rolling window size in rounds (0 = whole run)
    "window_step": 1,             # step between consecutive windows
    "event_window": 3,            # last-K rounds of window used for predation/violence
                                  # detection only (wealth/struct features use full window)
    "smoothing": True,            # 3-window majority filter for sub-flip denoising
}

LABEL_NAMES = {
    "1a": "Active reciprocation (peace)",
    "1b": "Paralysis",
    "1c": "Peaceful hegemony",
    "2a": "Leader-organized predation",
    "2b": "Leaderless cyclical predation",
    "2c": "Math-protected accumulator",
}

NAMED_STRUCTURE_RE = re.compile(
    r"\b(?:the\s+)?"
    r"((?:[A-Z][a-z]+(?:[\-\s][A-Z][a-z]+){0,3})\s+"
    r"(?:Coalition|Pact|Bloc|Council|Loop|Queue|Engine|Sanctuary|Trap|"
    r"Alliance|Faction|Triangle|Team|Cycle|Rotation|Ring|Order|League|"
    r"Circle|Chain|Cartel|Syndicate))\b"
)

NAMED_STRUCTURE_STOP = {
    "but", "current", "maintain", "total", "potential", "combined", "strong",
    "weak", "any", "all", "no", "some", "this", "that", "these", "those",
    "another", "the", "an", "a", "my", "our", "your", "their", "his", "her",
    "new", "old", "first", "second", "third", "last", "next", "previous",
    "main", "secondary", "primary", "general", "specific", "common",
    "early", "late", "now", "soon", "later", "future", "past", "present",
    "good", "bad", "best", "worst", "better", "worse",
    "active", "passive", "open", "closed", "full", "empty",
    "predatory", "predator", "predator's",
    # verb-form first-tokens (caught by regex due to sentence-start capitalization)
    "proposes", "proposed", "proposing", "propose",
    "creates", "created", "creating", "create",
    "forms", "formed", "forming", "form",
    "joins", "joined", "joining", "join",
    "leaves", "left", "leaving", "leave",
    "supports", "supported", "support",
    "maintain", "maintains", "maintained", "maintaining",
    "if", "when", "while", "after", "before", "because",
}

NAMED_STRUCTURE_MIN_AGENTS = 2
NAMED_STRUCTURE_MIN_OCCURRENCES = 3

ROLE_CLAIM_RE = re.compile(
    r"\bI\s+(?:am|will\s+be|will\s+act\s+as|serve\s+as|have\s+become)\s+"
    r"(?:the\s+)?"
    r"(coordinator|leader|sovereign|predator|architect|organizer|hub|"
    r"queen|king|alpha|whale|protector|guardian|enforcer|patron|broker|"
    r"benevolent\s+leader|strongest|core|anchor|pillar)\b",
    re.IGNORECASE,
)

BANKRUPTCY_FRAMING_RE = re.compile(
    r"\b(bankruptcy\s+(?:trap|risk|threshold)|"
    r"too\s+(?:big|large|costly)\s+to\s+attack|"
    r"mathematically\s+(?:protected|safe|unattackable)|"
    r"net\s+loss\s+(?:to|for)\s+attack(?:ers?|ing))\b",
    re.IGNORECASE,
)


# ─── extractors ──────────────────────────────────────────────────────────────

def load_log(path):
    rounds = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rounds.append(json.loads(line))
    return rounds


def window_slice(rounds, start_round, end_round):
    return [r for r in rounds if start_round <= r.get("round", -1) <= end_round]


def round_range(rounds):
    rs = [r.get("round") for r in rounds if r.get("round") is not None and "agents" in r]
    return (min(rs), max(rs)) if rs else (None, None)


def agent_rounds(rounds):
    return [r for r in rounds if "agents" in r]


def final_wealth(rounds):
    last = agent_rounds(rounds)[-1]
    return {aid: a["resources"] for aid, a in last["agents"].items()}


def action_counts(rounds):
    c = Counter()
    total = 0
    for r in agent_rounds(rounds):
        for a in r["agents"].values():
            c[a.get("action", "")] += 1
            total += 1
    return c, total


ATTACKER_WIN = {"attackers", "coalition"}  # schema variants across log versions


def successful_coalition_strikes(rounds):
    events = []
    for r in rounds:
        for combat in r.get("combat", []) or []:
            attackers = combat.get("attackers", [])
            if len(attackers) >= 2 and combat.get("winner") in ATTACKER_WIN:
                events.append({
                    "round": r.get("round"),
                    "attackers": attackers,
                    "defender": combat.get("defender"),
                    "transfer": combat.get("total_transfer", 0.0),
                })
    return events


def successful_solo_strikes(rounds):
    events = []
    for r in rounds:
        for combat in r.get("combat", []) or []:
            attackers = combat.get("attackers", [])
            if len(attackers) == 1 and combat.get("winner") in ATTACKER_WIN:
                events.append({
                    "round": r.get("round"),
                    "attackers": attackers,
                    "defender": combat.get("defender"),
                    "transfer": combat.get("total_transfer", 0.0),
                })
    return events


def all_strike_events(rounds):
    events = []
    for r in rounds:
        for combat in r.get("combat", []) or []:
            events.append({
                "round": r.get("round"),
                "attackers": combat.get("attackers", []),
                "defender": combat.get("defender"),
                "winner": combat.get("winner"),
                "coalition": len(combat.get("attackers", [])) >= 2,
            })
    return events


def _normalize_structure_name(raw):
    s = raw.strip()
    s = re.sub(r"^(?:the|The|THE)\s+", "", s)
    return s


def _structure_is_blacklisted(name):
    first = name.split()[0].lower() if name else ""
    return first in NAMED_STRUCTURE_STOP


def detect_named_structures(rounds):
    """Return (filtered_counts, raw_counts).

    filtered_counts: institutions passing min-distinct-agents AND min-occurrences
                     filters and not in stopword blacklist.
    raw_counts: every regex match (for debugging / refinement).
    """
    raw_total = Counter()
    by_agent = {}  # name -> set of distinct agent ids mentioning it

    for r in agent_rounds(rounds):
        for msg in r.get("messages", []) or []:
            text = msg.get("text", "") or ""
            sender = msg.get("from")
            for m in NAMED_STRUCTURE_RE.finditer(text):
                name = _normalize_structure_name(m.group(1))
                raw_total[name] += 1
                if sender:
                    by_agent.setdefault(name, set()).add(sender)
        for aid, a in r["agents"].items():
            for field in ("memory", "thinking"):
                text = a.get(field) or ""
                for m in NAMED_STRUCTURE_RE.finditer(text):
                    name = _normalize_structure_name(m.group(1))
                    raw_total[name] += 1
                    by_agent.setdefault(name, set()).add(aid)

    filtered = Counter()
    for name, count in raw_total.items():
        if len(name.split()) < 2:
            continue
        if _structure_is_blacklisted(name):
            continue
        if count < NAMED_STRUCTURE_MIN_OCCURRENCES:
            continue
        if len(by_agent.get(name, ())) < NAMED_STRUCTURE_MIN_AGENTS:
            continue
        filtered[name] = count
    return filtered, raw_total


def detect_role_claims(rounds, top_agents=None):
    by_agent = {}
    for r in agent_rounds(rounds):
        for aid, a in r["agents"].items():
            if top_agents is not None and aid not in top_agents:
                continue
            for field in ("memory", "thinking"):
                text = a.get(field) or ""
                for m in ROLE_CLAIM_RE.finditer(text):
                    by_agent.setdefault(aid, Counter())[m.group(1).lower()] += 1
    return by_agent


def detect_bankruptcy_framing(rounds, window):
    arounds = agent_rounds(rounds)
    tail = arounds[-window:] if window > 0 else arounds
    count = 0
    for r in tail:
        for msg in r.get("messages", []) or []:
            if BANKRUPTCY_FRAMING_RE.search(msg.get("text", "") or ""):
                count += 1
        for a in r["agents"].values():
            for field in ("memory", "thinking"):
                text = a.get(field) or ""
                if BANKRUPTCY_FRAMING_RE.search(text):
                    count += 1
                    break  # don't double-count within same agent-round
    return count


BROADCAST_TARGETS = {"all", "broadcast", "everyone", "ALL", None, ""}


def extract_network_features(rounds):
    arounds = agent_rounds(rounds)
    if not arounds:
        return {}
    edge_counts = []
    densities = []
    rewires_added_total = 0
    rewires_dropped_total = 0
    rewires_eligible_total = 0
    rewires_actual_total = 0
    n_agents_last = len(arounds[-1]["agents"])
    max_edges = n_agents_last * (n_agents_last - 1) / 2 if n_agents_last > 1 else 1

    for r in arounds:
        net = r.get("network", {}) or {}
        edges = net.get("edges", []) or []
        edge_counts.append(len(edges))
        n_ag = len(r.get("agents", {}))
        max_e = n_ag * (n_ag - 1) / 2 if n_ag > 1 else 1
        densities.append(len(edges) / max_e if max_e > 0 else 0.0)
        stats = net.get("rewire_stats", {}) or {}
        rewires_added_total += stats.get("edges_added", 0) or 0
        rewires_dropped_total += stats.get("edges_dropped", 0) or 0
        rewires_eligible_total += stats.get("agents_eligible", 0) or 0
        rewires_actual_total += stats.get("agents_rewired", 0) or 0

    return {
        "mean_edges": round(sum(edge_counts) / len(edge_counts), 2) if edge_counts else 0.0,
        "mean_network_density": round(sum(densities) / len(densities), 3) if densities else 0.0,
        "total_rewires_added": rewires_added_total,
        "total_rewires_dropped": rewires_dropped_total,
        "total_rewires_eligible": rewires_eligible_total,
        "total_rewires_actual": rewires_actual_total,
        "rewire_actual_rate": round(
            rewires_actual_total / rewires_eligible_total, 3
        ) if rewires_eligible_total > 0 else 0.0,
    }


def extract_communication_features(rounds):
    arounds = agent_rounds(rounds)
    total_msgs = 0
    broadcasts = 0
    senders = Counter()
    receivers = Counter()
    pairs = set()
    for r in arounds:
        for msg in r.get("messages", []) or []:
            total_msgs += 1
            sender = msg.get("from")
            recipient = msg.get("to")
            if sender:
                senders[sender] += 1
            if recipient in BROADCAST_TARGETS:
                broadcasts += 1
            elif recipient:
                receivers[recipient] += 1
                if sender:
                    pairs.add((sender, recipient))
    n_rounds = len(arounds)
    return {
        "total_messages": total_msgs,
        "messages_per_round": round(total_msgs / n_rounds, 2) if n_rounds else 0.0,
        "broadcast_count": broadcasts,
        "broadcast_fraction": round(broadcasts / total_msgs, 3) if total_msgs else 0.0,
        "top_senders": dict(senders.most_common(5)),
        "top_receivers": dict(receivers.most_common(5)),
        "n_unique_sender_receiver_pairs": len(pairs),
    }


# ─── feature extraction ─────────────────────────────────────────────────────

def extract_features(rounds, params, window=None):
    """Extract features. If window=(start_round, end_round), only count events / read
    wealth from that round-range slice. 'Snapshot' features (wealth) use the last round
    in window; 'count' features (strikes, attempts, named structures, role-claims,
    bankruptcy framing) only count events whose round is in window."""
    if window is not None:
        start, end = window
        rounds = window_slice(rounds, start, end)

    arounds = agent_rounds(rounds)
    n_agents = len(arounds[-1]["agents"]) if arounds else 0
    n_rounds = len(arounds)
    w_start, w_end = round_range(rounds)

    wealth = final_wealth(rounds)
    sorted_wealth = sorted(wealth.values(), reverse=True)
    sorted_agents = sorted(wealth.items(), key=lambda kv: kv[1], reverse=True)
    top_agent = sorted_agents[0][0] if sorted_agents else None
    top_w = sorted_wealth[0] if sorted_wealth else 0.0
    second_w = sorted_wealth[1] if len(sorted_wealth) > 1 else 0.0
    top_n_others = sorted_wealth[1:1 + params["top_n_others"]]
    top_n_others_sum = sum(top_n_others)
    others_all = sorted_wealth[1:]
    mean_others_all = (sum(others_all) / len(others_all)) if others_all else 0.0

    actions, total_actions = action_counts(rounds)
    do_nothing_n = actions.get("no_action", 0) + actions.get("do_nothing", 0)
    do_nothing_frac = do_nothing_n / total_actions if total_actions else 0.0

    # Violence/predation features: count only over the last `event_window` rounds of
    # the feature window. This avoids "window echo" where a single strike round labels
    # ~window_size consecutive windows as predation.
    event_window = params.get("event_window", 0)
    if event_window and w_end is not None:
        event_cutoff = w_end - event_window + 1
        event_rounds = [r for r in rounds if r.get("round", -1) >= event_cutoff]
    else:
        event_rounds = rounds

    successful_strikes = successful_coalition_strikes(event_rounds)
    solo_strikes = successful_solo_strikes(event_rounds)
    all_strikes = all_strike_events(event_rounds)
    coalition_attempts = [s for s in all_strikes if s["coalition"]]
    solo_attacker_counts = Counter()
    for s in solo_strikes:
        for a in s["attackers"]:
            solo_attacker_counts[a] += 1
    persistent_solo_predators = {a for a, n in solo_attacker_counts.items() if n >= params["solo_predator_min_strikes"]}

    named, named_raw = detect_named_structures(rounds)
    role_claims = detect_role_claims(rounds, top_agents={top_agent} if top_agent else None)
    role_claims_top1 = role_claims.get(top_agent, Counter())

    bankruptcy_hits = detect_bankruptcy_framing(rounds, params["bankruptcy_window"])

    stdev_wealth = statistics.pstdev(sorted_wealth) if len(sorted_wealth) > 1 else 0.0

    network = extract_network_features(rounds)
    comms = extract_communication_features(rounds)
    attack_actions = actions.get("attack", 0)
    arm_actions = actions.get("arm_self", 0) + actions.get("arm_other", 0)
    invest_actions = actions.get("invest_other", 0) + actions.get("invest_self", 0)

    return {
        "n_agents": n_agents,
        "n_rounds": n_rounds,
        "window_start": w_start,
        "window_end": w_end,
        "top_agent": top_agent,
        "top_wealth": round(top_w, 2),
        "second_wealth": round(second_w, 2),
        "top_n_others_wealth": [round(x, 2) for x in top_n_others],
        "top_n_others_sum": round(top_n_others_sum, 2),
        "mean_others_all": round(mean_others_all, 2),
        "stdev_final_wealth": round(stdev_wealth, 2),
        "action_counts": dict(actions),
        "do_nothing_fraction": round(do_nothing_frac, 3),
        "n_successful_coalition_strikes": len(successful_strikes),
        "n_successful_solo_strikes": len(solo_strikes),
        "solo_attacker_counts": dict(solo_attacker_counts),
        "persistent_solo_predators": sorted(persistent_solo_predators),
        "n_coalition_attempts": len(coalition_attempts),
        "n_all_strike_events": len(all_strikes),
        "n_unique_coalition_attackers": _unique_attacker_count(coalition_attempts),
        "named_structures": dict(named),
        "named_structures_raw_top": dict(named_raw.most_common(15)),
        "role_claims_top1": dict(role_claims_top1),
        "bankruptcy_framing_hits_last_window": bankruptcy_hits,
        "n_attack_actions": attack_actions,
        "n_arm_actions": arm_actions,
        "n_invest_actions": invest_actions,
        "network": network,
        "communication": comms,
        "_successful_strikes_detail": successful_strikes,
    }


def _unique_attacker_count(strike_events):
    s = set()
    for e in strike_events:
        for a in e.get("attackers", []):
            s.add(a)
    return len(s)


# ─── classifier ─────────────────────────────────────────────────────────────

def _compute_layer2_flags(features, params):
    """Orthogonal feature flags: coordination + outcome. Computed regardless of modal label."""
    n_coal_att = features["n_coalition_attempts"]
    n_coal_wins = features["n_successful_coalition_strikes"]
    persistent_solo = features["persistent_solo_predators"]
    n_solo_wins = features["n_successful_solo_strikes"]
    has_top_role = bool(features["role_claims_top1"])

    # coordination
    if not n_coal_att and not persistent_solo:
        coord = "none"
    elif persistent_solo and not n_coal_att:
        coord = "solo"
    elif n_coal_att and not persistent_solo:
        if has_top_role:
            coord = "coalition-led"
        else:
            coord = "coalition-leaderless"
    else:
        coord = "mixed"

    # outcome: only meaningful if regime-defining violence (coordination != none).
    # Otherwise outcome=none (isolated 1-off attacks don't define an outcome).
    if coord == "none":
        outcome = "none"
    else:
        total_strike_events = features["n_all_strike_events"]
        total_wins = n_coal_wins + n_solo_wins
        if total_strike_events == 0:
            outcome = "none"
        else:
            win_ratio = total_wins / total_strike_events
            if win_ratio == 0:
                outcome = "failed"
            elif win_ratio < params["partial_outcome_ratio"]:
                outcome = "partial"
            else:
                outcome = "successful"

    return {"coordination": coord, "outcome": outcome}


def classify(features, params):
    trace = []
    flags = []

    n_attempts = features["n_coalition_attempts"]
    n_strikes = features["n_successful_coalition_strikes"]
    persistent_solo = features["persistent_solo_predators"]
    is_predation = (n_attempts > params["attempt_threshold"]) or bool(persistent_solo)

    if not is_predation:
        trace.append(
            f"n_coalition_attempts={n_attempts} ≤ {params['attempt_threshold']} AND "
            f"no persistent_solo_predator → PEACE branch"
        )

        is_paralysis = (
            features["stdev_final_wealth"] < params["paralysis_stdev"]
            and features["do_nothing_fraction"] > params["paralysis_do_nothing"]
        )
        if is_paralysis:
            trace.append(
                f"stdev_wealth={features['stdev_final_wealth']} < {params['paralysis_stdev']} "
                f"AND do_nothing_frac={features['do_nothing_fraction']} > {params['paralysis_do_nothing']} → 1b"
            )
            return "1b", trace, flags

        top_w = features["top_wealth"]
        mean_others_all = features["mean_others_all"]
        second_w = features["second_wealth"]
        runnerup_ratio = (top_w / second_w) if second_w > 0 else 0.0
        meanothers_ratio = (top_w / mean_others_all) if mean_others_all > 0 else 0.0
        is_hegemon = (
            runnerup_ratio >= params["hegemony_runnerup_ratio"]
            and meanothers_ratio >= params["hegemony_top_ratio"]
        )
        if is_hegemon:
            trace.append(
                f"hegemon: top/second={runnerup_ratio:.2f} ≥ {params['hegemony_runnerup_ratio']} "
                f"AND top/mean_others={meanothers_ratio:.2f} ≥ {params['hegemony_top_ratio']} → 1c"
            )
            return "1c", trace, flags

        trace.append(
            f"not paralysis, not hegemony (top={top_w}, second={second_w}, "
            f"top/second={runnerup_ratio:.2f}, top/mean_others={meanothers_ratio:.2f}) → 1a"
        )
        return "1a", trace, flags

    trace.append(
        f"PREDATION: n_coalition_attempts={n_attempts} (>{params['attempt_threshold']}?), "
        f"persistent_solo_predators={persistent_solo}, coalition_wins={n_strikes}"
    )
    if n_strikes == 0 and n_attempts > params["attempt_threshold"]:
        flags.append("failed_coalition_predation — attempts present but no successful coalition strikes")
    if persistent_solo:
        flags.append(f"solo_predator_present — {','.join(persistent_solo)} with ≥{params['solo_predator_min_strikes']} successful solo strikes")

    top_w = features["top_wealth"]
    sum_others = features["top_n_others_sum"]
    has_top_role_claim = bool(features["role_claims_top1"])
    bankruptcy_hits = features["bankruptcy_framing_hits_last_window"]

    # 2c: math-protected accumulator (no role-claim, top uncatchable, bankruptcy framing)
    if top_w >= sum_others and not has_top_role_claim and bankruptcy_hits >= 1:
        trace.append(
            f"math-protected: top={top_w} ≥ sum(top-{params['top_n_others']} others)={sum_others}; "
            f"top role-claims=0; bankruptcy-framing={bankruptcy_hits} → 2c"
        )
        return "2c", trace, flags

    # 2a: leader-organized (named + role-claim + (coalition≥3 OR persistent solo predator))
    named = features["named_structures"]
    n_unique_attackers = features["n_unique_coalition_attackers"]
    leader_via_coalition = n_unique_attackers >= 3
    leader_via_solo = bool(persistent_solo)
    if named and has_top_role_claim and (leader_via_coalition or leader_via_solo):
        trace.append(
            f"2a: named={list(named.keys())[:3]}; top role-claims={list(features['role_claims_top1'].keys())}; "
            f"leader_via_coalition={leader_via_coalition} (unique_attackers={n_unique_attackers}); "
            f"leader_via_solo={leader_via_solo}"
        )
        return "2a", trace, flags

    if named and not has_top_role_claim:
        flags.append("named_structure_present_but_no_top1_role_claim — review 2a/2b boundary")
    if has_top_role_claim and not named:
        flags.append("top1_role_claim_without_named_structure — review")
    if n_unique_attackers < 3 and n_strikes > 0:
        flags.append(f"coalition_dyad — unique_attackers={n_unique_attackers} < 3 (2a/2b edge case)")

    trace.append(
        f"no 2a/2c match: named={bool(named)}, top_role_claim={has_top_role_claim}, "
        f"unique_coal_attackers={n_unique_attackers}, persistent_solo={bool(persistent_solo)} → 2b"
    )
    return "2b", trace, flags


def _coalition_size_unique(strike_events):
    s = set()
    for e in strike_events:
        for a in e["attackers"]:
            s.add(a)
    return len(s)


# ─── trajectory (rolling window) ────────────────────────────────────────────

def classify_window(rounds, params, start_round, end_round):
    features = extract_features(rounds, params, window=(start_round, end_round))
    if features["n_rounds"] == 0:
        return None
    label, trace, flags = classify(features, params)
    layer2 = _compute_layer2_flags(features, params)
    return {
        "window_start": start_round,
        "window_end": end_round,
        "label": label,
        "label_name": LABEL_NAMES[label],
        "layer2": layer2,
        "decision_trace": trace,
        "flags": flags,
        "features": {k: v for k, v in features.items() if not k.startswith("_")},
    }


def classify_trajectory(rounds, params, window_size, step):
    full_start, full_end = round_range(rounds)
    if full_start is None:
        return []
    windows = []
    end = full_start + window_size - 1
    while end <= full_end:
        start = end - window_size + 1
        w = classify_window(rounds, params, start, end)
        if w is not None:
            windows.append(w)
        end += step
    if params.get("smoothing"):
        windows = smooth_trajectory(windows)
    return windows


def smooth_trajectory(windows):
    """Majority filter over 3 windows: if w[i-1].label == w[i+1].label != w[i].label,
    treat w[i] as a transient noise spike and adopt the neighbors' label.
    The window's features stay unchanged; only the label and layer2 derived from
    the smoothed label are flagged. Adds 'smoothed_from' to layer2 for transparency.
    """
    if len(windows) < 3:
        return windows
    labels = [w["label"] for w in windows]
    smoothed = list(labels)
    for i in range(1, len(labels) - 1):
        if labels[i - 1] == labels[i + 1] and labels[i] != labels[i - 1]:
            smoothed[i] = labels[i - 1]
    out = []
    for w, new_label in zip(windows, smoothed):
        if new_label != w["label"]:
            w_copy = dict(w)
            w_copy["smoothed_from"] = w["label"]
            w_copy["label"] = new_label
            w_copy["label_name"] = LABEL_NAMES[new_label]
            out.append(w_copy)
        else:
            out.append(w)
    return out


PEACE_LABELS = {"1a", "1b", "1c"}
PREDATION_LABELS = {"2a", "2b", "2c"}


def trajectory_pattern(episodes):
    """High-level pattern summary from compressed episode sequence."""
    if not episodes:
        return "empty"
    labels = [e["label"] for e in episodes]
    had_predation = any(l in PREDATION_LABELS for l in labels)
    first_is_peace = labels[0] in PEACE_LABELS
    last_is_peace = labels[-1] in PEACE_LABELS
    last_is_hegemony = labels[-1] == "1c"
    last_is_paralysis = labels[-1] == "1b"

    if not had_predation:
        if last_is_hegemony:
            return "peaceful_to_hegemony" if labels[0] != "1c" else "hegemony_throughout"
        if last_is_paralysis:
            return "peaceful_to_paralysis" if labels[0] != "1b" else "paralysis_throughout"
        return "peaceful_throughout"

    if last_is_peace:
        if last_is_hegemony:
            return "predation_then_hegemony"
        if last_is_paralysis:
            return "predation_then_paralysis"
        return "predation_then_peace"

    if first_is_peace:
        return "peace_then_predation"
    return "predation_throughout"


def compress_trajectory(windows):
    """Collapse consecutive same-label windows into episodes.

    Each window has a single timestamp = window_end (the last round it covers).
    Episode {first_observed, last_observed, label, n_windows, duration} describes
    a contiguous span of windows with the same label.
    """
    if not windows:
        return []
    episodes = []
    cur = {
        "label": windows[0]["label"],
        "first_observed": windows[0]["window_end"],
        "last_observed": windows[0]["window_end"],
        "n_windows": 1,
    }
    for w in windows[1:]:
        if w["label"] == cur["label"]:
            cur["last_observed"] = w["window_end"]
            cur["n_windows"] += 1
        else:
            cur["duration"] = cur["last_observed"] - cur["first_observed"] + 1
            episodes.append(cur)
            cur = {
                "label": w["label"],
                "first_observed": w["window_end"],
                "last_observed": w["window_end"],
                "n_windows": 1,
            }
    cur["duration"] = cur["last_observed"] - cur["first_observed"] + 1
    episodes.append(cur)
    return episodes


# ─── runner ─────────────────────────────────────────────────────────────────

def classify_file(path, params):
    rounds = load_log(path)
    window_size = params.get("window_size", 0)

    if window_size <= 0:
        features = extract_features(rounds, params)
        label, trace, flags = classify(features, params)
        layer2 = _compute_layer2_flags(features, params)
        return {
            "run": Path(path).stem.replace("_log", "").replace("_reasoning_live", ""),
            "path": str(path),
            "mode": "whole_run",
            "label": label,
            "label_name": LABEL_NAMES[label],
            "layer2": layer2,
            "decision_trace": trace,
            "flags": flags,
            "features": {k: v for k, v in features.items() if not k.startswith("_")},
        }

    windows = classify_trajectory(rounds, params, window_size, params["window_step"])
    if not windows:
        return {"run": Path(path).stem, "path": str(path), "error": "no agent rounds"}
    end_state = windows[-1]
    episodes = compress_trajectory(windows)
    pattern = trajectory_pattern(episodes)
    return {
        "run": Path(path).stem.replace("_log", "").replace("_reasoning_live", ""),
        "path": str(path),
        "mode": "trajectory",
        "window_size": window_size,
        "window_step": params["window_step"],
        "n_windows": len(windows),
        "end_state_label": end_state["label"],
        "end_state_label_name": LABEL_NAMES[end_state["label"]],
        "end_state_layer2": end_state["layer2"],
        "trajectory_pattern": pattern,
        "trajectory_labels": [w["label"] for w in windows],
        "regime_episodes": episodes,
        "windows": windows,
    }


def format_per_window_dashboard(result):
    """One-glance human-readable summary per window."""
    lines = []
    run = result.get("run", "?")
    lines.append(f"=== {run}  ({result.get('n_windows', 0)} windows, "
                 f"window_size={result.get('window_size')}, step={result.get('window_step')})  ===")
    lines.append(f"END-STATE: {result['end_state_label']} ({LABEL_NAMES[result['end_state_label']]})  "
                 f"trajectory_pattern: {result['trajectory_pattern']}")
    lines.append("")
    prev_top = None
    for w in result["windows"]:
        f = w["features"]
        l2 = w["layer2"]
        top = f["top_agent"]
        top_changed = "*" if prev_top is not None and top != prev_top else " "
        prev_top = top
        smoothed = f" [smoothed from {w['smoothed_from']}]" if "smoothed_from" in w else ""
        head = (f"W:R{f['window_end']:>3d}  {w['label']} {top_changed}{top:>10s}={f['top_wealth']:>7.1f}  "
                f"2nd={f['second_wealth']:>6.1f}  rest_mean={f['mean_others_all']:>6.1f}  "
                f"[{l2['coordination']:>20s}/{l2['outcome']:>10s}]{smoothed}")
        lines.append(head)

        violence_parts = []
        if f["n_coalition_attempts"]:
            violence_parts.append(f"coal_att={f['n_coalition_attempts']}({f['n_successful_coalition_strikes']}w)")
        if f["n_successful_solo_strikes"]:
            solos = ",".join(f"{a}({n})" for a, n in f["solo_attacker_counts"].items())
            violence_parts.append(f"solo_w={f['n_successful_solo_strikes']}[{solos}]")
        if f.get("n_attack_actions", 0):
            violence_parts.append(f"atk_acts={f['n_attack_actions']}")
        if violence_parts:
            lines.append("           violence: " + "  ".join(violence_parts))

        net = f.get("network", {})
        if net:
            lines.append(f"           network:  density={net['mean_network_density']:.3f}  "
                         f"edges={net['mean_edges']:.1f}  rewires=+{net['total_rewires_added']}/-{net['total_rewires_dropped']}")
        comms = f.get("communication", {})
        if comms.get("total_messages"):
            top_s = ",".join(f"{a}({n})" for a, n in list(comms["top_senders"].items())[:3])
            lines.append(f"           comms:    msgs={comms['total_messages']}  "
                         f"bcasts={comms['broadcast_count']}({comms['broadcast_fraction']:.2f})  "
                         f"top_senders=[{top_s}]")

        named = f.get("named_structures", {})
        if named:
            top_n = ",".join(f"'{k}'({v})" for k, v in list(named.items())[:3])
            lines.append(f"           named:    {top_n}")
        rc = f.get("role_claims_top1", {})
        if rc:
            claims = ",".join(f"{k}({v})" for k, v in rc.items())
            lines.append(f"           claims:   {top}: {claims}")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?", help="Path to a *_log.jsonl file")
    p.add_argument("--batch", help="Classify all *_log.jsonl in a directory")
    p.add_argument("--attempt-threshold", type=int, default=DEFAULTS["attempt_threshold"])
    p.add_argument("--strike-threshold", type=int, default=DEFAULTS["strike_threshold"])
    p.add_argument("--paralysis-stdev", type=float, default=DEFAULTS["paralysis_stdev"])
    p.add_argument("--paralysis-do-nothing", type=float, default=DEFAULTS["paralysis_do_nothing"])
    p.add_argument("--top-n-others", type=int, default=DEFAULTS["top_n_others"])
    p.add_argument("--bankruptcy-window", type=int, default=DEFAULTS["bankruptcy_window"])
    p.add_argument("--window-size", type=int, default=DEFAULTS["window_size"],
                   help="Rolling window size in rounds (0 = whole-run mode)")
    p.add_argument("--window-step", type=int, default=DEFAULTS["window_step"])
    p.add_argument("--solo-predator-min-strikes", type=int, default=DEFAULTS["solo_predator_min_strikes"])
    p.add_argument("--no-smoothing", action="store_true", help="Disable 3-window majority-filter smoothing")
    p.add_argument("--per-window", action="store_true", help="Print one-glance dashboard per window")
    p.add_argument("--summary", action="store_true", help="Compact one-line summary per run (batch mode)")
    args = p.parse_args()

    params = dict(DEFAULTS)
    params.update({
        "attempt_threshold": args.attempt_threshold,
        "strike_threshold": args.strike_threshold,
        "paralysis_stdev": args.paralysis_stdev,
        "paralysis_do_nothing": args.paralysis_do_nothing,
        "top_n_others": args.top_n_others,
        "bankruptcy_window": args.bankruptcy_window,
        "window_size": args.window_size,
        "window_step": args.window_step,
        "solo_predator_min_strikes": args.solo_predator_min_strikes,
        "smoothing": not args.no_smoothing,
    })

    if args.batch:
        results = []
        seen = set()
        for fp in sorted(Path(args.batch).glob("*_log.jsonl")):
            stem = fp.name.replace("_log.jsonl", "")
            seen.add(stem)
            results.append(classify_file(fp, params))
        for fp in sorted(Path(args.batch).glob("*_reasoning_live.jsonl")):
            stem = fp.name.replace("_reasoning_live.jsonl", "")
            if stem in seen:
                continue
            results.append(classify_file(fp, params))
        if args.per_window:
            for r in results:
                if r.get("mode") == "trajectory":
                    print(format_per_window_dashboard(r))
                    print()
        elif args.summary:
            for r in results:
                if r.get("mode") == "trajectory":
                    eps = r["regime_episodes"]
                    ep_str = " → ".join(f"{e['label']}@R{e['first_observed']}-{e['last_observed']}" for e in eps)
                    print(f"{r['run']:42s}  end={r['end_state_label']}  "
                          f"pattern={r['trajectory_pattern']:28s}  "
                          f"{ep_str}")
                else:
                    print(f"{r['run']:42s}  {r['label']}  "
                          f"[{r['layer2']['coordination']:>20s}/{r['layer2']['outcome']:>10s}]  "
                          f"att={r['features']['n_coalition_attempts']:3d}  "
                          f"cwins={r['features']['n_successful_coalition_strikes']:3d}  "
                          f"sowins={r['features']['n_successful_solo_strikes']:3d}  "
                          f"top={r['features']['top_wealth']:7.1f}  "
                          f"named={len(r['features']['named_structures'])}  "
                          f"flags={len(r['flags'])}")
        else:
            json.dump(results, sys.stdout, indent=2, default=str)
            print()
        return

    if not args.path:
        p.error("provide a path or --batch <dir>")
    result = classify_file(args.path, params)
    if args.per_window and result.get("mode") == "trajectory":
        print(format_per_window_dashboard(result))
        return
    json.dump(result, sys.stdout, indent=2, default=str)
    print()


if __name__ == "__main__":
    main()
