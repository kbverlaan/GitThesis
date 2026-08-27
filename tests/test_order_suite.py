"""economy()-regime-kwadrant (order_suite.py) — de P2-DV: payoff selecteert het
regime binnen een niveau. Verankert de vier kwadranten (groei x concentratie)
zodat de pre-reg-drempels (pr +/-0.3, top-share 15%) niet stil verschuiven."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from order_suite import economy


def _pr(sumR, Rs, rnd=0):
    # economy() gebruikt alleen sumR van eerste+laatste en Rs van de laatste.
    return {"round": rnd, "counts": {}, "sumR": sumR, "Rs": Rs}


def _reg(first_sum, last_sum, last_Rs):
    return economy([_pr(first_sum, {}), _pr(last_sum, last_Rs, 1)])[-1]


def test_bloei_growth_low_concentration():
    # groei (pr>0.3) + gelijk verdeeld (top<15%) -> BLOEI
    assert _reg(100, 150, {f"a{i}": 15 for i in range(10)}) == "BLOEI"


def test_hegemonie_growth_high_concentration():
    # groei + geconcentreerd (top>=15%) -> HEGEMONIE
    assert _reg(100, 150, {"a": 100, "b": 10, "c": 10, "d": 10, "e": 10, "f": 10}) == "HEGEMONIE"


def test_verovering_shrink_high_concentration():
    # krimp (pr<-0.3) + geconcentreerd -> VEROVERING
    assert _reg(200, 100, {"a": 70, "b": 10, "c": 10, "d": 10}) == "VEROVERING"


def test_nivellering_shrink_low_concentration():
    # krimp + gelijk -> NIVELLERING
    assert _reg(200, 100, {f"a{i}": 10 for i in range(10)}) == "NIVELLERING"


def test_vlak_flat_low_concentration():
    # geen netto groei (|pr|<=0.3) + gelijk -> VLAK-gelijk
    assert _reg(100, 100, {f"a{i}": 10 for i in range(10)}) == "VLAK-gelijk"
