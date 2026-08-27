"""Commons-DV op synthetische logs: collapse, duurzaam, over-harvest, geen-commons.
Valideert dat de §3-claim "the stock collapses" reproduceerbaar uit de stock-serie
afleesbaar is (collapse + tijd-tot-collapse + duurzaamheid)."""
import os
import sys

# scripts/ importeerbaar maken zonder de gedeelde conftest te raken.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from commons_dv import commons_metrics


def _round(before, after_harvest, after_regen, collapsed=False, harvest_frac=None, K=120):
    b = {
        "stock_before": before,
        "K": K,
        "collapsed": collapsed,
        "stock_after_harvest": after_harvest,
        "stock_after_regen": after_regen,
    }
    if harvest_frac:
        b["harvest_frac"] = harvest_frac
    return {"commons": b}


def test_no_commons_returns_none():
    # L1-L3-runs loggen geen commons-blok -> DV geldt niet.
    assert commons_metrics([{"round": 1}, {"foo": "bar"}]) is None


def test_collapse_scenario():
    rounds = [
        _round(60, 20, 30),
        _round(30, 8, 12),
        _round(12, 3, 0, collapsed=True),
    ]
    m = commons_metrics(rounds)
    assert m["collapsed"] is True
    assert m["round_of_collapse"] == 3
    assert m["sustainability"] == 0.0
    assert m["sustained"] is False
    assert m["over_harvest_rate"] == 1.0  # elke ronde netto daling


def test_sustainable_scenario():
    # Semantiek 2026-07-15: 'sustained' = configureerbare regel (default
    # window_stock: gem. eind-stock slotvenster >= 2/3*K = 80, het
    # engine-anker voor regen x1.5). De oude K/2-grens was ongegrond.
    rounds = [
        _round(80, 30, 95),
        _round(95, 35, 105),
        _round(105, 40, 120),
    ]
    m = commons_metrics(rounds)
    assert m["collapsed"] is False
    assert m["round_of_collapse"] is None
    assert m["sustained"] is True          # gem. slotvenster (95+105+120)/3 >= 80
    assert m["sustainability"] == 1.0      # 120/120
    assert m["over_harvest_rate"] == 0.0   # stock stijgt netto elke ronde
    assert m["sustained_by_rule"]["no_collapse"] is True


def test_rules_discriminate():
    # Eindigt levend maar onder het duurzame peil: no_collapse zegt ja,
    # window_stock/final_stock zeggen nee, window_flow (oogst > 40) nee.
    rounds = [
        _round(120, 50, 75),   # oogst 70
        _round(75, 30, 45),    # oogst 45
        _round(45, 20, 30),    # oogst 25 -> gem 46.7 > debiet 40
    ]
    m = commons_metrics(rounds)
    br = m["sustained_by_rule"]
    assert br["no_collapse"] is True
    assert br["window_stock"] is False
    assert br["final_stock"] is False
    assert br["window_flow"] is False


def test_over_harvest_no_collapse():
    rounds = [
        _round(90, 40, 60),
        _round(60, 25, 37),
    ]
    m = commons_metrics(rounds)
    assert m["collapsed"] is False
    assert m["over_harvest_rate"] == 1.0   # 60<90 en 37<60
    # Frozen rule (PR #16, threshold-freeze): sustained = no_collapse.
    assert m["sustained"] is True
    assert m["sustained_by_rule"]["window_stock"] is False   # eindigt op 37 < MSY(60)
    assert m["sustained_by_rule"]["final_stock"] is False


def test_harvest_frac_aggregated():
    rounds = [
        _round(60, 40, 60, harvest_frac={"a": 0.2, "b": 0.4}),
        _round(60, 40, 60, harvest_frac={"a": 0.6}),
    ]
    m = commons_metrics(rounds)
    assert abs(m["mean_harvest_frac"] - 0.4) < 1e-9  # (0.2+0.4+0.6)/3
