"""Drift-guard + logica-tests voor de order-ladder gate (P1) en de δ-toets.

Drift-guard-principe (zie test_dv_thresholds.py): config/dv_thresholds.yaml is
de pre-reg-SSOT; code-fallbacks in .get() moeten er exact mee overeenkomen,
zodat code en pre-reg niet stil uiteenlopen."""
import json
import os
import subprocess
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import order_ladder_gate as G  # noqa: E402
from delta_equivalence import max_pairwise_tv, profile, tv  # noqa: E402

_CFG = os.path.join(os.path.dirname(__file__), "..", "config", "dv_thresholds.yaml")


def _cfg():
    with open(_CFG) as f:
        return yaml.safe_load(f)["order_ladder"]


REQUIRED_KEYS = [
    "window", "alpha", "tau",
    "coop_transfer_share", "coop_recip_dyads",
    "conv_coverage_min", "conv_q_min", "conv_cohesion_min", "conv_rewire_ratio",
    "norm_density_min", "norm_sanction_min", "norm_density_priv_min",
    "inst_co_enforce_min",
    "inst_min_structures", "inst_public_only", "inst_baseline_names",
    "inst_min_agents", "inst_min_occurrences",
]


def test_yaml_has_all_gate_keys():
    cfg = _cfg()
    for k in REQUIRED_KEYS:
        assert k in cfg, f"order_ladder-blok mist '{k}'"


def test_code_fallbacks_match_yaml():
    # .get()-defaults in de gate moeten de SSOT-waarden spiegelen.
    cfg = _cfg()
    assert cfg["norm_density_priv_min"] == 0.002
    assert cfg["inst_public_only"] is True
    assert cfg["inst_min_agents"] == 2
    assert cfg["inst_min_occurrences"] == 3
    # publieke-circulatie-eisen = named_institution-gate (zelfde pre-reg-keuze)
    ni = yaml.safe_load(open(_CFG))["named_institution"]
    assert cfg["inst_min_agents"] == ni["min_agents"]
    assert cfg["inst_min_occurrences"] == ni["min_occurrences"]


def _synthetic_log(path, comms=True):
    """10 rondes, 8 agents: drie wederkerige transfer-paren (>= coop_recip_dyads),
    twee holders."""
    rows = []
    pairs = [("A", "B"), ("C", "D"), ("E", "F")]
    for r in range(1, 11):
        agents = {}
        for x, y in pairs:
            agents[x] = {"action": "transfer", "target": y, "resources": 100}
            agents[y] = {"action": "transfer", "target": x, "resources": 100}
        agents["G"] = {"action": "hold", "resources": 80}
        agents["H"] = {"action": "hold", "resources": 80}
        msgs = ([{"from": "A", "to": "B", "text": "we must uphold the pact; "
                  "anyone who defects is punished. Join the Growth Circle."},
                 {"from": "B", "to": "A", "text": "agreed, the growth circle "
                  "holds. we must all contribute."}] if comms else [])
        rows.append({"round": r, "agents": agents, "messages": msgs})
    with open(path, "w") as f:
        for d in rows:
            f.write(json.dumps(d) + "\n")


def test_gate_runs_and_nests(tmp_path):
    p = tmp_path / "synth_log.jsonl"
    _synthetic_log(str(p), comms=True)
    thr = G.load_thresholds()
    r = G.gate_run(str(p), thr)
    assert set(G.LEVELS[1:]) <= set(r["gates"])       # sociale ladder in gates
    assert r["gates"]["cooperation"] is True          # A<->B wederkerig, share 0.5
    assert r["governance"] is None                    # aparte as; geen commons-blok
    assert r["nested_level"] >= 1
    # nesting: label mag nooit boven een gefaalde lagere poort uitkomen
    order = G.LEVELS[1:]
    failed = [i for i, l in enumerate(order, start=1) if r["gates"][l] is False]
    if failed:
        assert r["nested_level"] < min(failed) + 1


def test_gate_nocomm_no_public_institution(tmp_path):
    p = tmp_path / "synth_nocomm_log.jsonl"
    _synthetic_log(str(p), comms=False)
    thr = G.load_thresholds()
    r = G.gate_run(str(p), thr)
    # zonder berichten kan de publieke-circulatie-poort nooit passen
    assert r["gates"]["institution"] is False


def test_tv_and_profile():
    assert tv(profile([0, 0, 0]), profile([0, 0, 0])) == 0.0
    assert tv(profile([0]), profile([5])) == 1.0
    groups = {"a": [4, 4, 4], "b": [4, 4, 4], "c": [0, 0, 0]}
    assert abs(max_pairwise_tv(groups) - 1.0) < 1e-9


def test_delta_cli_verdicts(tmp_path):
    res = tmp_path / "res.jsonl"
    with open(res, "w") as f:
        for rung, lvl in (("L1", 1), ("L3", 4)):
            for _ in range(8):
                f.write(json.dumps({"run": "x", "rung": rung,
                                    "payoff": "knife", "nested_level": lvl}) + "\n")
    script = os.path.join(os.path.dirname(__file__), "..", "scripts",
                          "delta_equivalence.py")
    out = subprocess.run([sys.executable, script, str(res), "--delta", "0.2",
                          "--boot", "200"], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "NIET ondersteund" in out.stdout   # profielen verschillen maximaal
