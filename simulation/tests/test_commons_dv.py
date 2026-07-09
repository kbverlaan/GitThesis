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
    rounds = [
        _round(60, 45, 67),
        _round(67, 50, 75),
        _round(75, 60, 90),
    ]
    m = commons_metrics(rounds)
    assert m["collapsed"] is False
    assert m["round_of_collapse"] is None
    assert m["sustained"] is True          # eindigt op 90 >= MSY(60)
    assert m["sustainability"] == 0.75     # 90/120
    assert m["over_harvest_rate"] == 0.0   # stock stijgt netto elke ronde


def test_over_harvest_no_collapse():
    rounds = [
        _round(90, 40, 60),
        _round(60, 25, 37),
    ]
    m = commons_metrics(rounds)
    assert m["collapsed"] is False
    assert m["over_harvest_rate"] == 1.0   # 60<90 en 37<60
    assert m["sustained"] is False         # eindigt op 37 < MSY(60)


def test_harvest_frac_aggregated():
    rounds = [
        _round(60, 40, 60, harvest_frac={"a": 0.2, "b": 0.4}),
        _round(60, 40, 60, harvest_frac={"a": 0.6}),
    ]
    m = commons_metrics(rounds)
    assert abs(m["mean_harvest_frac"] - 0.4) < 1e-9  # (0.2+0.4+0.6)/3
