"""Drift-guard: config/dv_thresholds.yaml (de pre-reg SSOT) moet overeenkomen met
de hardcoded classifier-constanten. Faalt zodra code en pre-reg stil uiteenlopen —
zodat het bevriezen van de pre-reg-waarden afdwingbaar is.

Dekt nu de importeerbare classify_run-constanten. enforcement.py / order_suite.py
gebruiken hun drempels nog inline (niet als top-level constant); die komen in de
drift-guard zodra ze in Fase 0 importeerbaar gemaakt zijn."""
import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import classify_run as C  # noqa: E402

_CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "dv_thresholds.yaml")


def _cfg():
    with open(_CFG_PATH) as f:
        return yaml.safe_load(f)


def test_order_type_defaults_match():
    cfg = _cfg()["order_type"]
    for k, v in cfg.items():
        assert k in C.DEFAULTS, f"config-key '{k}' ontbreekt in classify_run.DEFAULTS"
        assert C.DEFAULTS[k] == v, f"{k}: config {v!r} != code {C.DEFAULTS[k]!r}"


def test_no_orphan_defaults():
    # Elke tuneable classifier-drempel hoort in de SSOT te staan (anti-vergeet-guard).
    cfg_keys = set(_cfg()["order_type"].keys())
    assert set(C.DEFAULTS.keys()) == cfg_keys, (
        f"code-only: {set(C.DEFAULTS) - cfg_keys} ; config-only: {cfg_keys - set(C.DEFAULTS)}"
    )


def test_named_institution_match():
    ni = _cfg()["named_institution"]
    assert C.NAMED_STRUCTURE_MIN_AGENTS == ni["min_agents"]
    assert C.NAMED_STRUCTURE_MIN_OCCURRENCES == ni["min_occurrences"]


def test_institution_overlay_match():
    io = _cfg()["institution_overlay"]
    assert C.INSTITUTION_UNIVERSALITY_FRAC == io["universality_frac"]
    assert C.INSTITUTION_ROBUSTNESS_FRAC == io["robustness_frac"]
