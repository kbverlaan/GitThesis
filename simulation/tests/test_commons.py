"""Commons stock dynamics: GovSim-style doubling, % -of-K harvest, random
rationing on over-claim, absorbing collapse. Deterministic (no LLM)."""
import numpy as np
import pytest

from game.engine import GameEngine, Action, ActionType


def _engine(agents, K=100.0, init=None, collapse_frac=0.05, R0=100.0):
    return GameEngine(agent_ids=agents, initial_resources=R0,
                      delta_R=1.0, mu_arm=0.0,
                      commons_enabled=True, commons_K=K, commons_init=init,
                      commons_collapse_frac=collapse_frac)


def _harvest_round(eng, harvests):
    """harvests: {aid: pct}. Everyone holds; given agents also harvest."""
    acts = [Action(a, ActionType.DO_NOTHING, None, harvest=harvests.get(a, 0.0))
            for a in eng.state.agents]
    return eng.resolve_round(acts)


def test_sustainable_harvest_holds_stock():
    # GovSim slice: K=100, 5 agents each take 10% (=10 units) → 50 left → doubles to 100.
    a = [f"A{i}" for i in range(5)]
    eng = _engine(a, K=100.0)
    log = _harvest_round(eng, {x: 10.0 for x in a})
    assert eng.state.commons_stock == pytest.approx(100.0)          # held at K
    assert log["commons"]["harvested"] == pytest.approx(50.0)
    for x in a:
        assert eng.state.resources[x] == pytest.approx(110.0)        # +10 units each


def test_doubling_from_half():
    a = ["A", "B"]
    eng = _engine(a, K=100.0, init=50.0)
    _harvest_round(eng, {})                                          # nobody harvests
    assert eng.state.commons_stock == pytest.approx(100.0)          # 50 -> doubles -> capped K


def test_overclaim_rationed_to_stock():
    # init 30, 5 agents each claim 10% (10) = 50 claimed > 30 → grants sum to 30 exactly.
    np.random.seed(0)
    a = [f"A{i}" for i in range(5)]
    eng = _engine(a, K=100.0, init=30.0)
    log = _harvest_round(eng, {x: 10.0 for x in a})
    assert log["commons"]["harvested"] == pytest.approx(30.0)        # never more than stock
    total_gain = sum(eng.state.resources[x] - 100.0 for x in a)
    assert total_gain == pytest.approx(30.0)


def test_overharvest_collapses_and_is_absorbing():
    # init 50, 5 agents each 10% (10) = 50 == stock → 0 left < C(5) → collapse.
    np.random.seed(0)
    a = [f"A{i}" for i in range(5)]
    eng = _engine(a, K=100.0, init=50.0)
    _harvest_round(eng, {x: 10.0 for x in a})
    assert eng.state.commons_collapsed is True
    assert eng.state.commons_stock == pytest.approx(0.0)
    # absorbing: a later round grants nothing, stays collapsed
    r_before = dict(eng.state.resources)
    log2 = _harvest_round(eng, {x: 8.0 for x in a})
    assert log2["commons"]["harvested"] == pytest.approx(0.0)
    assert eng.state.commons_stock == pytest.approx(0.0)
    assert eng.state.resources == r_before


def test_stock_shown_as_percent_in_observation():
    a = ["A", "B"]
    eng = _engine(a, K=100.0, init=73.0)
    obs = eng.state.get_observation("A")
    assert obs["commons"]["stock_pct"] == pytest.approx(73.0)
    assert obs["commons"]["collapsed"] is False


def test_commons_off_by_default_no_state():
    eng = GameEngine(agent_ids=["A", "B"], initial_resources=100.0, delta_R=1.0)
    assert eng.state.commons_K == 0.0
    obs = eng.state.get_observation("A")
    assert "commons" not in obs                                      # gated off
