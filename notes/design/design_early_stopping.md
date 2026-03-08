# Design Decision: Early Stopping / Adaptive Round Count

**Date**: 2026-03-01
**Status**: Implemented — Two-Phase Adaptive (Option D + C)

---

## Problem

Fixed `max_rounds` wastes compute on equilibrium runs and may cut short dynamic ones:

- **L1 invest_return run**: 100% do_nothing from round 1. Ran all 10 rounds (~30 min) for zero information gain after round 2.
- **L3 invest_return run**: Attacks, arming, investment still happening at round 7. Gini still evolving. 10 rounds may not be enough to see stabilisation.

With ~8K SBU remaining and 102 OAT runs left, this matters.

---

## What We Already Have

`src/analysis/metrics.py` has post-hoc stabilisation detection:

1. **`stabilisation_round(timeseries, window=10, threshold=0.02)`**
   - Rolling window std < threshold AND stays below for all subsequent windows
   - Tracks: Gini, cooperation rate, action distribution entropy
   - Problem for early stopping: window=10 means you need 10 rounds before you can even check

2. **`action_stability`** (per-round metric)
   - Fraction of agents repeating their previous round's action
   - Available from round 2 onward
   - L1 do_nothing: stability=100% from round 2
   - L3 dynamic: stability dropped to 70%

3. **`compute_stabilisation_metrics()`**
   - Wraps stabilisation_round for Gini, coop rate, entropy
   - Currently only called post-hoc in `sweep.py`

---

## Design Questions (for Koen to decide)

### 1. What metric(s) trigger early stopping?

Options:
- **Action stability alone**: Simple. If 100% of agents repeat for N consecutive rounds → stop. Catches the do_nothing case immediately.
- **Action stability + Gini stability**: Both must be stable. Catches cases where agents cycle between actions but aggregate outcome is constant (unlikely but possible).
- **Full stabilisation check** (Gini + coop rate + entropy): Most conservative. Requires all three metrics to flatline. But needs more rounds of data.

Recommendation: action_stability + Gini std. These are the two most informative and fastest to compute.

### 2. Window size and patience

Current `stabilisation_round` uses window=10, which is too large for early stopping on short runs.

Options:
- **Small window (3-5 rounds)**: Can trigger early. Risk: might stop during a temporary lull before dynamics resume.
- **Patience-based**: "Stop after `patience` consecutive rounds where action_stability >= threshold." No windowed std, just a streak counter. Simpler and more intuitive.

Recommendation: Patience-based with patience=5. If all agents repeat the same action for 5 consecutive rounds AND Gini doesn't change, it's equilibrium.

### 3. Min/max rounds

- **min_rounds**: Floor below which early stopping never triggers. Ensures enough data for analysis (network metrics need ≥5 rounds, stabilisation window needs data).
  - Candidates: 10, 15, 20
- **max_rounds**: Safety cap.
  - Candidates: 30, 50, 100
  - At ~3 min/round for L3 with 10 agents: 50 rounds ≈ 2.5h, 100 rounds ≈ 5h

Recommendation: min_rounds=15, max_rounds=50. But this depends on compute budget per run.

### 4. What to log on early stop

- Round number where early stop triggered
- Which metric(s) were stable
- The stabilisation values (final Gini, final action distribution)
- Flag in metadata: `early_stopped: true, stop_reason: "action_stability >= 1.0 for 5 rounds"`

---

## Proposed Config

```yaml
early_stopping:
  enabled: true
  min_rounds: 15          # never stop before this
  max_rounds: 50          # always stop at this
  patience: 5             # consecutive stable rounds needed
  action_stability_threshold: 0.95  # fraction of agents repeating
  gini_std_threshold: 0.01          # rolling std of Gini over patience window
```

---

## Implementation Sketch

In `main.py` simulation loop, after computing round metrics:

```python
# Early stopping check (after min_rounds)
if early_stopping_enabled and round_num >= min_rounds:
    recent_metrics = all_round_metrics[-patience:]

    # Check action stability
    stabilities = [m['action_stability'] for m in recent_metrics
                   if m['action_stability'] is not None]
    actions_stable = (len(stabilities) == patience and
                      all(s >= action_stability_threshold for s in stabilities))

    # Check Gini stability
    ginis = [m['gini'] for m in recent_metrics]
    gini_stable = np.std(ginis) < gini_std_threshold

    if actions_stable and gini_stable:
        print(f"Early stopping at round {round_num}: equilibrium detected")
        break
```

Changes needed:
- `main.py`: add early stopping check in while loop
- `engine.py`: no changes (max_rounds already in is_game_over)
- Config: add early_stopping section to game_params
- `sweep.py`: pass early_stopping config through
- Metadata: log early_stop info

---

## Compute Impact Estimate

With early stopping on the current invest_return sweep:
- L1 runs: would stop at round 15 (min_rounds) instead of 50 → saves ~35 rounds × 3 min = ~1.75h per run
- L3 dynamic runs: would run to 50 rounds → more data, better stabilisation analysis
- Net: more informative L3 data, less wasted L1 compute

---

## Open Questions

- Should `max_rounds` be in the sweep YAML per-experiment, or global config?
- Should early stopping be reported differently in analysis? (runs have different lengths)
- Does variable run length complicate statistical comparison across conditions?
  - Possible solution: always report metrics at fixed checkpoints (round 10, 20, 30...) regardless of total length
- Should we also early-stop on "all agents broke" (resources → 0)?

---

## References

- Scheffer et al. (2009): Early warning signals for critical transitions — our EWS metrics
- The stabilisation logic already in `metrics.py` is the foundation
- Debraj's feedback: wants to see stabilised results, not arbitrary cutoffs
