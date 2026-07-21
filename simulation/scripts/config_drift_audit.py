#!/usr/bin/env python3
"""Config-drift-audit voor de registered grid (pre-deposit QA).

Verifieert de load-bearing design-claim (§3/§5): "each cell freezes one base
configuration and changes a single parameter, so drift between conditions is
impossible." Checkt:
  1. WITHIN-TREDE — de 3 payoff-cellen (scar/knife/abund) verschillen alleen in g_inv.
  2. CROSS-TREDE — L1->L2->L3->L4 (knife-spoor) verschilt alleen in additieve
     affordance-flags (nested-additief).
  3. COMMS-OFF — nocomm-cellen verschillen alleen in het comms-veld van hun base-cel.

Herdraaien na elke config-wijziging (bv. na de T4-mechaniek-beslissing).
Gebruik: python3 config_drift_audit.py
"""
import yaml, glob, os, sys

# Verwachte additieve delta per trede-stap (knife-spoor). Commons-params komen mee
# met de commons-affordance; ze zijn inert zolang commons_enabled false is.
EXPECTED_STEP = {
    ("L1", "L2"): {"arm_enabled", "take_enabled"},
    ("L2", "L3"): {"assoc_enabled", "rewiring_prob"},
    ("L3", "L4"): {"commons_enabled", "commons_init", "commons_regen",
                   "commons_K", "commons_collapse_frac", "commons_open_round",
                   "c_harvest", "harvest_frac_cap"},
}
COMMS_KEYS = {"comm_scope", "comm_enabled", "messaging_enabled"}


def flat(d, pre=""):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out.update(flat(v, pre + k + "."))
        else:
            out[pre + k] = v
    return out


def load_all():
    cfgs = {}
    for p in glob.glob("config/prod_L*.yaml"):
        name = os.path.basename(p).replace("prod_", "").replace(".yaml", "")
        with open(p) as f:
            cfgs[name] = flat(yaml.safe_load(f))
    return cfgs


def diff(a, b):
    keys = set(a) | set(b)
    return {k: (a.get(k), b.get(k)) for k in keys if a.get(k) != b.get(k)}


def main():
    cfgs = load_all()
    ok = True

    print("=== 1. WITHIN-TREDE: cellen mogen ALLEEN in g_inv verschillen ===")
    for L in ["L1", "L2", "L3", "L4"]:
        cells = [f"{L}_scar", f"{L}_knife", f"{L}_abund"]
        present = [c for c in cells if c in cfgs]
        if len(present) < 2:
            continue
        allk = set()
        for i in range(1, len(present)):
            allk |= set(diff(cfgs[present[0]], cfgs[present[i]]))
        unexpected = allk - {"g_inv"}
        if unexpected:
            ok = False
            print(f"  {L}: DRIFT: {sorted(unexpected)}")
        else:
            print(f"  {L}: OK (alleen g_inv)")

    print("\n=== 2. CROSS-TREDE (knife-spoor): alleen additieve affordances ===")
    chain = ["L1_knife", "L2_knife", "L3_knife", "L4_knife"]
    for i in range(1, len(chain)):
        a, b = chain[i - 1], chain[i]
        if a not in cfgs or b not in cfgs:
            continue
        d = set(diff(cfgs[a], cfgs[b])) - {"g_inv"}
        exp = EXPECTED_STEP.get((a[:2], b[:2]), set())
        unexpected = d - exp
        tag = "OK" if not unexpected else f"ONVERWACHT: {sorted(unexpected)}"
        if unexpected:
            ok = False
        print(f"  {a} -> {b}: {sorted(d)}  [{tag}]")

    print("\n=== 3. COMMS-OFF: alleen comms-veld(en) t.o.v. base-knife ===")
    for base, nc in [("L1_knife", "L1_knife_nocomm"), ("L3_knife", "L3_knife_nocomm")]:
        if nc not in cfgs:
            continue
        d = set(diff(cfgs[base], cfgs[nc]))
        unexpected = d - COMMS_KEYS
        tag = "OK" if not unexpected else f"ONVERWACHT: {sorted(unexpected)}"
        if unexpected:
            ok = False
        print(f"  {base} -> {nc}: {sorted(d)}  [{tag}]")

    print("\n" + ("ALLE CHECKS GROEN — no-drift-claim geverifieerd." if ok
                  else "DRIFT GEVONDEN — zie hierboven."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
