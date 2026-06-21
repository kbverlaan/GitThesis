"""Commons fraction_own (B+C) harvest mode: harvest = f_i × R_i, continuous and
unbounded (can empty the pool). Rationing, collapse, and regeneration are shared
with category mode. Also checks category mode is unchanged (regression).
Deterministic (no LLM)."""
from types import SimpleNamespace

import numpy as np
import pytest

from game.engine import GameEngine, Action, ActionType
from agents.llm_agent import LLMAgent


def _snap(game_params, raw):
    dummy = SimpleNamespace(game_params=game_params)
    return LLMAgent._snap_harvest(dummy, raw)


def _engine(agents, K=100.0, init=None, collapse_frac=0.05, R0=100.0,
            mode="fraction_own"):
    return GameEngine(agent_ids=agents, initial_resources=R0,
                      delta_R=1.0, mu_arm=0.0,
                      commons_enabled=True, commons_K=K, commons_init=init,
                      commons_collapse_frac=collapse_frac,
                      commons_harvest_mode=mode)


def _harvest_round(eng, harvests):
    """harvests: {aid: raw harvest field}. Everyone holds; given agents harvest."""
    acts = [Action(a, ActionType.DO_NOTHING, None, harvest=harvests.get(a, 0.0))
            for a in eng.state.agents]
    return eng.resolve_round(acts)


# --- fraction_own math: harvest = f_i × R_i drawn from the stock ---------------

def test_fraction_harvest_math():
    # K=600 (big enough to cover claims), 2 agents R=100 each.
    # f=0.10 → each draws 0.10*100 = 10 units.
    a = ["A", "B"]
    eng = _engine(a, K=600.0, init=600.0)
    log = _harvest_round(eng, {"A": 0.10, "B": 0.10})
    assert log["commons"]["harvested"] == pytest.approx(20.0)
    assert eng.state.resources["A"] == pytest.approx(110.0)
    assert eng.state.resources["B"] == pytest.approx(110.0)
    # stock: 600 - 20 = 580, doubles capped at 600
    assert eng.state.commons_stock == pytest.approx(600.0)


def test_fraction_scales_with_own_resources():
    # Rich agent draws more in absolute terms for the same fraction.
    eng = GameEngine(agent_ids=["Rich", "Poor"],
                     initial_resources={"Rich": 200.0, "Poor": 50.0},
                     delta_R=1.0, mu_arm=0.0,
                     commons_enabled=True, commons_K=600.0, commons_init=600.0,
                     commons_harvest_mode="fraction_own")
    log = _harvest_round(eng, {"Rich": 0.10, "Poor": 0.10})
    grants = log["resource_breakdown"]
    assert grants["Rich"]["harvest"] == pytest.approx(20.0)   # 0.10 * 200
    assert grants["Poor"]["harvest"] == pytest.approx(5.0)    # 0.10 * 50


# --- unbounded: a large fraction can empty the pool → collapse -----------------

def test_unbounded_grab_empties_pool_and_collapses():
    # init 40 (< K so no regen-cap masking), 1 agent R=100 chooses f=10.0
    # → wants 1000 units, capped by stock 40 → harvests all 40 → 0 left < C → collapse.
    a = ["A", "B"]
    eng = _engine(a, K=100.0, init=40.0)
    log = _harvest_round(eng, {"A": 10.0})
    assert log["commons"]["harvested"] == pytest.approx(40.0)
    assert eng.state.resources["A"] == pytest.approx(140.0)
    assert eng.state.commons_collapsed is True
    assert eng.state.commons_stock == pytest.approx(0.0)


# --- rationing fires when total request > stock -------------------------------

def test_rationing_when_request_exceeds_stock():
    np.random.seed(0)
    # init 30, 5 agents R=100 each, f=0.10 → each wants 10 → 50 requested > 30.
    a = [f"A{i}" for i in range(5)]
    eng = _engine(a, K=100.0, init=30.0)
    log = _harvest_round(eng, {x: 0.10 for x in a})
    assert log["commons"]["harvested"] == pytest.approx(30.0)   # never more than stock
    total_gain = sum(eng.state.resources[x] - 100.0 for x in a)
    assert total_gain == pytest.approx(30.0)


# --- the chosen fraction is logged --------------------------------------------

def test_chosen_fraction_is_logged():
    a = ["A", "B"]
    eng = _engine(a, K=600.0, init=600.0)
    log = _harvest_round(eng, {"A": 0.07, "B": 0.0})
    # commons log records the chosen fraction per harvesting agent
    assert log["commons"]["harvest_frac"]["A"] == pytest.approx(0.07)
    assert "B" not in log["commons"]["harvest_frac"]            # chose 0 → not recorded
    # breakdown records both absolute harvest and chosen fraction
    assert log["resource_breakdown"]["A"]["harvest"] == pytest.approx(7.0)   # 0.07 * R=100
    assert log["resource_breakdown"]["A"]["harvest_frac"] == pytest.approx(0.07)


def test_negative_fraction_field_clamped_to_zero():
    a = ["A", "B"]
    eng = _engine(a, K=600.0, init=600.0)
    log = _harvest_round(eng, {"A": -0.5})
    assert log["commons"]["harvested"] == pytest.approx(0.0)
    assert eng.state.resources["A"] == pytest.approx(100.0)


# --- regression: category mode unchanged --------------------------------------

def test_category_mode_unchanged():
    # Same slice as test_commons.test_sustainable_harvest_holds_stock.
    a = [f"A{i}" for i in range(5)]
    eng = _engine(a, K=100.0, mode="category")
    log = _harvest_round(eng, {x: 10.0 for x in a})  # 10% of K each
    assert eng.state.commons_stock == pytest.approx(100.0)
    assert log["commons"]["harvested"] == pytest.approx(50.0)
    for x in a:
        assert eng.state.resources[x] == pytest.approx(110.0)
    # category mode does NOT add harvest_frac
    assert "harvest_frac" not in log["commons"]


# --- agent-side parsing convention (_snap_harvest) ----------------------------

_FRAC_GP = {"commons_enabled": True, "commons_harvest_mode": "fraction_own"}
_CAT_GP = {"commons_enabled": True, "commons_harvest_mode": "category",
           "commons_harvest_pct": [0, 1, 2, 4, 8]}


def test_parse_fraction_percent_conventions():
    # "5", "5%", and 0.05 all read as the NUMBER → /100. So "5" → 0.05.
    assert _snap(_FRAC_GP, "5") == pytest.approx(0.05)
    assert _snap(_FRAC_GP, "5%") == pytest.approx(0.05)
    assert _snap(_FRAC_GP, 5) == pytest.approx(0.05)
    assert _snap(_FRAC_GP, 0.05) == pytest.approx(0.0005)   # 0.05 → 0.0005 (it's a percent number)


def test_parse_fraction_unbounded_and_clamped():
    assert _snap(_FRAC_GP, "250") == pytest.approx(2.5)     # no upper bound
    assert _snap(_FRAC_GP, "-3") == 0.0                     # negatives clamp to 0
    assert _snap(_FRAC_GP, "garbage") == 0.0
    assert _snap(_FRAC_GP, None) == 0.0


def test_parse_fraction_off_when_commons_disabled():
    assert _snap({"commons_enabled": False, "commons_harvest_mode": "fraction_own"}, "5") == 0.0


def test_parse_category_snaps_unchanged():
    assert _snap(_CAT_GP, "3.4") == pytest.approx(4.0)      # snaps to nearest category
    assert _snap(_CAT_GP, "7") == pytest.approx(8.0)
    assert _snap(_CAT_GP, "1.2") == pytest.approx(1.0)
    assert _snap(_CAT_GP, "0") == 0.0


def test_default_mode_is_category():
    # No mode arg → default "category": harvest field read as % of K, not of R.
    eng = GameEngine(agent_ids=["A", "B"], initial_resources=100.0,
                     delta_R=1.0, mu_arm=0.0,
                     commons_enabled=True, commons_K=100.0, commons_init=100.0)
    log = _harvest_round(eng, {"A": 10.0})  # 10% of K=100 → 10 units (not 10*100)
    assert log["commons"]["harvested"] == pytest.approx(10.0)
