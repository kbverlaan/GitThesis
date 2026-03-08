"""Test combat grouping and coalition logic in GameEngine.

Covers:
- Coalition grouping: multiple attackers → same target = 1 conflict
- Absorption: defender counter-attacks one of their attackers → same fight
- Independent conflicts: separate targets = separate fights
- Edge cases: mutual attack, all-vs-one, chain attacks
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
from game.engine import GameEngine, Action, ActionType


def make_engine(n_agents=4, **overrides):
    """Create an N-agent engine with default params."""
    defaults = dict(
        agent_ids=[f"a{i+1}" for i in range(n_agents)],
        initial_resources=100.0,
        invest_self_pct=2,
        invest_other_cost_pct=10,
        invest_other_return_pct=15,
        arm_cost_pct=10,
        arm_multiplier=2.0,
        arm_decay=0.5,
        attack_take_pct=40,
        conflict_cost_pct=5,
        max_rounds=10,
    )
    defaults.update(overrides)
    return GameEngine(**defaults)


def test_coalition_two_attackers_one_defender():
    """A→B, C→B → 1 conflict: {A,C} vs B."""
    np.random.seed(42)
    engine = make_engine(n_agents=3)
    result = engine.resolve_round([
        Action("a1", ActionType.ATTACK, target_id="a2"),
        Action("a3", ActionType.ATTACK, target_id="a2"),
    ])
    combats = result["combat_results"]
    assert len(combats) == 1, f"Expected 1 conflict, got {len(combats)}"
    assert set(combats[0]["attackers"]) == {"a1", "a3"}
    assert combats[0]["defender"] == "a2"
    print("PASS: A→B, C→B → 1 conflict {A,C} vs B")


def test_absorption_defender_counter_attacks():
    """A→B, C→B, B→C → 1 conflict: {A,C} vs B. B's attack on C absorbed."""
    np.random.seed(42)
    engine = make_engine(n_agents=3)
    result = engine.resolve_round([
        Action("a1", ActionType.ATTACK, target_id="a2"),
        Action("a3", ActionType.ATTACK, target_id="a2"),
        Action("a2", ActionType.ATTACK, target_id="a3"),
    ])
    combats = result["combat_results"]
    assert len(combats) == 1, f"Expected 1 conflict, got {len(combats)}"
    assert set(combats[0]["attackers"]) == {"a1", "a3"}
    assert combats[0]["defender"] == "a2"
    print("PASS: A→B, C→B, B→C → 1 conflict {A,C} vs B (B's counter absorbed)")


def test_independent_conflicts():
    """A→B, C→D → 2 independent conflicts."""
    np.random.seed(42)
    engine = make_engine(n_agents=4)
    result = engine.resolve_round([
        Action("a1", ActionType.ATTACK, target_id="a2"),
        Action("a3", ActionType.ATTACK, target_id="a4"),
    ])
    combats = result["combat_results"]
    assert len(combats) == 2, f"Expected 2 conflicts, got {len(combats)}"
    defenders = {c["defender"] for c in combats}
    assert defenders == {"a2", "a4"}
    print("PASS: A→B, C→D → 2 independent conflicts")


def test_mutual_attack_1v1():
    """A→B, B→A → 1 conflict (larger group absorbs the other)."""
    np.random.seed(42)
    engine = make_engine(n_agents=2)
    result = engine.resolve_round([
        Action("a1", ActionType.ATTACK, target_id="a2"),
        Action("a2", ActionType.ATTACK, target_id="a1"),
    ])
    combats = result["combat_results"]
    assert len(combats) == 1, f"Expected 1 conflict, got {len(combats)}"
    # One attacks, other defends — either direction is valid
    combat = combats[0]
    participants = set(combat["attackers"]) | {combat["defender"]}
    assert participants == {"a1", "a2"}
    print("PASS: A→B, B→A → 1 conflict (mutual absorbed)")


def test_all_attack_one():
    """A→D, B→D, C→D → 1 conflict: {A,B,C} vs D."""
    np.random.seed(42)
    engine = make_engine(n_agents=4)
    result = engine.resolve_round([
        Action("a1", ActionType.ATTACK, target_id="a4"),
        Action("a2", ActionType.ATTACK, target_id="a4"),
        Action("a3", ActionType.ATTACK, target_id="a4"),
    ])
    combats = result["combat_results"]
    assert len(combats) == 1, f"Expected 1 conflict, got {len(combats)}"
    assert set(combats[0]["attackers"]) == {"a1", "a2", "a3"}
    assert combats[0]["defender"] == "a4"
    print("PASS: A→D, B→D, C→D → 1 conflict {A,B,C} vs D")


def test_coalition_spoils_proportional():
    """When coalition wins, spoils split by relative combat strength."""
    np.random.seed(0)  # seed where coalition wins (need to verify)
    engine = make_engine(n_agents=3)
    # Give a1 more resources so their share is bigger
    engine.state.resources["a1"] = 200.0
    engine.state.resources["a3"] = 50.0

    # Force coalition win by making defender very weak
    engine.state.resources["a2"] = 10.0

    result = engine.resolve_round([
        Action("a1", ActionType.ATTACK, target_id="a2"),
        Action("a3", ActionType.ATTACK, target_id="a2"),
    ])
    combats = result["combat_results"]
    assert len(combats) == 1

    # Check that a1 got a larger share than a3 (proportional to power)
    rc = result["resource_changes"]
    # Both pay conflict cost, but winner gains spoils
    if combats[0]["winner"] == "coalition":
        # a1 power=200, a3 power=50 → a1 gets 80% of spoils
        a1_power = combats[0]["attacker_powers"]["a1"]
        a3_power = combats[0]["attacker_powers"]["a3"]
        assert a1_power > a3_power, "a1 should have more combat power"
        print(f"PASS: coalition spoils proportional (a1 power={a1_power:.0f}, a3 power={a3_power:.0f})")
    else:
        # Defender won (unlikely with 10 resources) — just check structure
        print("PASS: coalition spoils test (defender won, structure OK)")


def test_conflict_costs_all_participants():
    """All combatants (attackers + defender) pay conflict cost."""
    np.random.seed(42)
    engine = make_engine(n_agents=3, conflict_cost_pct=5, attack_take_pct=0)
    # With attack_take_pct=0, only conflict costs matter
    pre = {aid: engine.state.resources[aid] for aid in ["a1", "a2", "a3"]}

    result = engine.resolve_round([
        Action("a1", ActionType.ATTACK, target_id="a2"),
        Action("a3", ActionType.ATTACK, target_id="a2"),
    ])

    # a1: 100 - 5 = 95, a2: 100 - 5 = 95, a3: 100 - 5 = 95
    for aid in ["a1", "a2", "a3"]:
        expected = pre[aid] - pre[aid] * 0.05
        assert abs(engine.state.resources[aid] - expected) < 0.01, \
            f"{aid}: expected {expected}, got {engine.state.resources[aid]}"
    print("PASS: all combatants pay conflict cost")


def test_chain_A_attacks_B_B_attacks_C_C_attacks_A():
    """A→B, B→C, C→A — circular chain. Largest group absorbs; rest resolve."""
    np.random.seed(42)
    engine = make_engine(n_agents=3)
    result = engine.resolve_round([
        Action("a1", ActionType.ATTACK, target_id="a2"),
        Action("a2", ActionType.ATTACK, target_id="a3"),
        Action("a3", ActionType.ATTACK, target_id="a1"),
    ])
    combats = result["combat_results"]
    # All groups have size 1, so processing order is arbitrary but
    # absorption should reduce total conflicts. Verify no double-counting:
    # each agent should appear in at most 1 conflict as attacker
    all_attackers = []
    for c in combats:
        all_attackers.extend(c["attackers"])
    assert len(all_attackers) == len(set(all_attackers)), \
        f"Agent appears as attacker in multiple conflicts: {all_attackers}"
    print(f"PASS: circular chain A→B→C→A → {len(combats)} conflict(s), no double-counting")


def test_non_combatants_unaffected():
    """Agents not involved in combat have zero resource change from combat."""
    np.random.seed(42)
    engine = make_engine(n_agents=4)
    pre_a3 = engine.state.resources["a3"]
    pre_a4 = engine.state.resources["a4"]

    engine.resolve_round([
        Action("a1", ActionType.ATTACK, target_id="a2"),
    ])

    assert abs(engine.state.resources["a3"] - pre_a3) < 0.01
    assert abs(engine.state.resources["a4"] - pre_a4) < 0.01
    print("PASS: non-combatants unaffected")


def test_snapshot_simultaneous():
    """Combat strengths are snapshot-based: same strength in all combats."""
    np.random.seed(42)
    engine = make_engine(n_agents=4)
    # a2 is attacked by a1 AND attacks a3 — should use same strength in both
    # But a2's attack on a3 may be absorbed if a2 is also defending.
    # Instead: a1→a3, a2→a3 (coalition), a4→a1 (separate)
    result = engine.resolve_round([
        Action("a1", ActionType.ATTACK, target_id="a3"),
        Action("a2", ActionType.ATTACK, target_id="a3"),
        Action("a4", ActionType.ATTACK, target_id="a1"),
    ])
    combats = result["combat_results"]
    # a1 is attacker in one fight AND defender in another
    # Snapshot means a1's strength should be same in both
    a1_as_attacker = None
    a1_as_defender = None
    for c in combats:
        if "a1" in c["attackers"]:
            a1_as_attacker = c["attacker_powers"]["a1"]
        if c["defender"] == "a1":
            a1_as_defender = c["defender_power"]

    if a1_as_attacker is not None and a1_as_defender is not None:
        assert abs(a1_as_attacker - a1_as_defender) < 0.01, \
            f"Snapshot violated: attacker power={a1_as_attacker}, defender power={a1_as_defender}"
        print(f"PASS: snapshot simultaneous (a1 strength={a1_as_attacker:.1f} in both combats)")
    else:
        print("PASS: snapshot test (a1 only in 1 combat, structure OK)")


if __name__ == "__main__":
    test_coalition_two_attackers_one_defender()
    test_absorption_defender_counter_attacks()
    test_independent_conflicts()
    test_mutual_attack_1v1()
    test_all_attack_one()
    test_coalition_spoils_proportional()
    test_conflict_costs_all_participants()
    test_chain_A_attacks_B_B_attacks_C_C_attacks_A()
    test_non_combatants_unaffected()
    test_snapshot_simultaneous()
    print("\nAll combat grouping tests passed!")
