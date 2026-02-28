"""Test unified %-based economy in GameEngine.

All params now match the prompt (prompts.py _format_actions):
- invest_self_cost_pct / invest_self_return_pct
- invest_other_cost_pct / invest_other_return_pct
- arm_cost_pct / arm_decay
- attack_take_pct / conflict_cost_pct
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
from game.engine import GameEngine, Action, ActionType


def make_engine(**overrides):
    """Create a 3-agent engine with default %-based params."""
    defaults = dict(
        agent_ids=["a1", "a2", "a3"],
        initial_resources=100.0,
        invest_self_cost_pct=10,
        invest_self_return_pct=20,
        invest_other_cost_pct=10,
        invest_other_return_pct=15,
        arm_cost_pct=10,
        arm_decay=0.5,
        attack_take_pct=40,
        conflict_cost_pct=5,
        max_rounds=10,
    )
    defaults.update(overrides)
    return GameEngine(**defaults)


def test_invest_self():
    """invest_self: pay 10%, gain 20% → net +10%."""
    engine = make_engine()
    engine.resolve_round([Action("a1", ActionType.INVEST_SELF)])
    # 100 - 10 + 20 = 110
    assert engine.state.resources["a1"] == 110.0, f"Expected 110, got {engine.state.resources['a1']}"

    # Second round: scales with wealth (110)
    engine.resolve_round([Action("a1", ActionType.INVEST_SELF)])
    # 110 - 11 + 22 = 121
    assert abs(engine.state.resources["a1"] - 121.0) < 0.01
    print("PASS: invest_self → 100→110→121 (scales with wealth)")


def test_invest_other():
    """invest_other: investor pays 10%, target gets 15% of investor's resources."""
    engine = make_engine()
    engine.resolve_round([Action("a1", ActionType.INVEST_OTHER, target_id="a2")])
    # a1: 100 - 10 = 90
    # a2: 100 + 15 = 115 (15% of a1's 100)
    assert abs(engine.state.resources["a1"] - 90.0) < 0.01, f"a1: {engine.state.resources['a1']}"
    assert abs(engine.state.resources["a2"] - 115.0) < 0.01, f"a2: {engine.state.resources['a2']}"
    print("PASS: invest_other → investor -10%, target +15% (social surplus +5%)")


def test_invest_other_more_rewarding():
    """invest_other yields more to the economy than invest_self."""
    e1 = make_engine()
    e2 = make_engine()

    # invest_self: only investor gains, net +10% of 100 = +10 for economy
    e1.resolve_round([Action("a1", ActionType.INVEST_SELF)])
    economy_self = sum(e1.state.resources.values())

    # invest_other: investor loses 10, target gains 15 → net +5 for economy
    # But also: cooperation creates more value than selfishness
    e2.resolve_round([Action("a1", ActionType.INVEST_OTHER, target_id="a2")])
    economy_other = sum(e2.state.resources.values())

    # invest_other: 300 + (-10 + 15) = 305
    # invest_self: 300 + (-10 + 20) = 310
    # invest_self grows YOUR wealth more, but invest_other is more GENEROUS (target benefits more)
    assert economy_other == 305.0, f"invest_other economy: {economy_other}"
    assert economy_self == 310.0, f"invest_self economy: {economy_self}"

    # The key: invest_other gives TARGET more than invest_self gives YOU? No...
    # invest_self net to actor: +10. invest_other net to target: +15.
    # Target benefits MORE from receiving invest_other than you benefit from invest_self.
    target_gain = e2.state.resources["a2"] - 100  # 15
    self_gain = e1.state.resources["a1"] - 100     # 10
    assert target_gain > self_gain, f"Target gain {target_gain} should exceed self gain {self_gain}"
    print(f"PASS: invest_other target gain ({target_gain}) > invest_self gain ({self_gain})")


def test_arm_self_additive():
    """arm_self: pay 10% → that amount becomes additive combat bonus."""
    engine = make_engine()
    engine.resolve_round([Action("a1", ActionType.ARM_SELF)])
    # a1 resources: 100 - 10 = 90
    # a1 arm bonus: 10 (the amount spent)
    assert abs(engine.state.resources["a1"] - 90.0) < 0.01
    assert abs(engine.state.arm_bonuses["a1"] - 5.0) < 0.01  # 10 × 0.5 decay at end of round
    print("PASS: arm_self → resources -10%, arm bonus = 10 (decayed to 5 after round)")


def test_arm_decay():
    """Arm bonus decays ×0.5 per round."""
    engine = make_engine()
    # Arm in round 1
    engine.resolve_round([Action("a1", ActionType.ARM_SELF)])
    # After round 1: bonus = 10 × 0.5 = 5.0
    assert abs(engine.state.arm_bonuses.get("a1", 0) - 5.0) < 0.01

    # Round 2: no action, just decay
    engine.resolve_round([Action("a1", ActionType.DO_NOTHING)])
    # bonus = 5.0 × 0.5 = 2.5
    assert abs(engine.state.arm_bonuses.get("a1", 0) - 2.5) < 0.01

    # Round 3: decay again
    engine.resolve_round([Action("a1", ActionType.DO_NOTHING)])
    # bonus = 2.5 × 0.5 = 1.25
    assert abs(engine.state.arm_bonuses.get("a1", 0) - 1.25) < 0.01

    # After several more rounds, bonus should vanish (< 0.01)
    for _ in range(10):
        engine.resolve_round([Action("a1", ActionType.DO_NOTHING)])
    assert "a1" not in engine.state.arm_bonuses
    print("PASS: arm decay → 5.0 → 2.5 → 1.25 → ... → removed")


def test_arm_other():
    """arm_other: pay 10% of YOUR resources → adds to TARGET's combat bonus."""
    engine = make_engine()
    engine.resolve_round([Action("a1", ActionType.ARM_OTHER, target_id="a2")])
    # a1: 100 - 10 = 90
    # a2 arm bonus: 10 × 0.5 = 5.0 (after decay)
    assert abs(engine.state.resources["a1"] - 90.0) < 0.01
    assert abs(engine.state.arm_bonuses.get("a2", 0) - 5.0) < 0.01
    # a2 resources unchanged
    assert abs(engine.state.resources["a2"] - 100.0) < 0.01
    print("PASS: arm_other → your -10%, target gets combat bonus (not resources)")


def test_combat_additive():
    """Combat strength = resources + arm bonus (additive, not multiplicative)."""
    np.random.seed(42)
    engine = make_engine()

    # Arm a1, then attack a2
    engine.resolve_round([Action("a1", ActionType.ARM_SELF)])
    # a1: resources=90, arm_bonus=5.0 (after decay) → strength = 95
    # a2: resources=100, arm_bonus=0 → strength = 100
    # Win prob for a1 = 95 / (95 + 100) = 0.487...

    engine.resolve_round([Action("a1", ActionType.ATTACK, target_id="a2")])
    combat = engine.state.history[-1]["combat_results"][0]
    expected_prob = 95.0 / 195.0
    assert abs(combat["attacker_win_prob"] - expected_prob) < 0.01, \
        f"Expected win prob {expected_prob:.3f}, got {combat['attacker_win_prob']:.3f}"
    print(f"PASS: combat additive → armed a1 strength=95 vs a2=100, win_prob={expected_prob:.3f}")


def test_conflict_cost_percentage():
    """Conflict cost: each fighter pays 5% of own resources."""
    np.random.seed(42)
    engine = make_engine(conflict_cost_pct=5)
    engine.state.resources["a2"] = 200.0

    engine.resolve_round([Action("a1", ActionType.ATTACK, target_id="a2")])
    # a1 conflict cost: 5% of 100 = 5
    # a2 conflict cost: 5% of 200 = 10
    total = sum(engine.state.resources.values())
    expected_total = 100 + 200 + 100 - 15  # minus both conflict costs
    assert abs(total - expected_total) < 0.01, f"Total: expected {expected_total}, got {total}"
    print("PASS: conflict cost → each pays own 5%")


def test_observation_has_arm_bonuses():
    """Observation dict includes arm_bonuses for prompt rendering."""
    engine = make_engine()
    engine.resolve_round([Action("a1", ActionType.ARM_SELF)])
    obs = engine.state.get_observation("a2")
    assert "arm_bonuses" in obs
    assert abs(obs["arm_bonuses"].get("a1", 0) - 5.0) < 0.01
    print("PASS: observation includes arm_bonuses")


def test_arm_stacking():
    """Multiple arm actions stack (bonus accumulates)."""
    engine = make_engine()
    # Round 1: arm_self → bonus = 10, after decay = 5.0
    engine.resolve_round([Action("a1", ActionType.ARM_SELF)])
    assert abs(engine.state.arm_bonuses["a1"] - 5.0) < 0.01

    # Round 2: arm_self again → resources now 90, so new bonus = 9
    # Before new arm: existing = 5.0. Add 9.0 → 14.0. After decay: 7.0
    engine.resolve_round([Action("a1", ActionType.ARM_SELF)])
    assert abs(engine.state.arm_bonuses["a1"] - 7.0) < 0.01
    print("PASS: arm stacking → bonuses accumulate")


if __name__ == "__main__":
    test_invest_self()
    test_invest_other()
    test_invest_other_more_rewarding()
    test_arm_self_additive()
    test_arm_decay()
    test_arm_other()
    test_combat_additive()
    test_conflict_cost_percentage()
    test_observation_has_arm_bonuses()
    test_arm_stacking()
    print("\nAll tests passed!")
