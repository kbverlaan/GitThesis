# Phase 1 Completion: System Characterization

**Date**: 2026-02-13
**Deadline**: Feb 27 (Debraj meeting)
**Status**: Design approved

---

## Context

Phase 1 goal: understand the game as a system before varying prompts (Phase 2).

### What's done
- 85+ parameter sweep runs with Nova Micro (invest_other_cost, invest_other_return, T, arm_multiplier, arm_duration)
- Finding: Nova Micro behavior is fixed at ~65% attack / ~28% arm / ~3% cooperate regardless of parameters
- T (attack_take_percent) affects Gini but not behavior
- Gemini Flash shows 10x more cooperation and IS parameter sensitive
- Objective framing (maximize vs avoid_last) flips equilibrium entirely
- Metrics pipeline working (Gini, Palma, action stability, distributions)
- Zero-cost regime eliminates bankruptcy stalemate

### What remains
Parameter sweeps only characterize one dimension. Debraj asked about game design variations too. Need to test those before declaring Phase 1 complete.

---

## Design

### 1. Gemini Flash Lite Parameter Sweeps (running)

Same sweeps as Nova Micro for direct comparison:
- T sweep: 5, 10, 20, 30, 40 (3 reps each)
- invest_other_return sweep: 2, 5, 10, 15, 20 (3 reps each)

Answers: is Gemini parameter-sensitive where Nova Micro wasn't?

### 2. Initial Wealth Distributions

Test 3 distributions, all with same total resources (250 for 10 agents):
- **Equal**: everyone starts at 25.0 (current baseline)
- **Unequal**: 1 rich agent at 100.0, 9 poor agents at ~16.7
- **Random**: drawn from uniform(5, 45), normalized to sum=250

Implementation: add `initial_distribution` param to game_params.yaml. Engine reads it at initialization.

Run each 3x with Gemini Flash Lite, compare Gini trajectories.

Question answered: does starting inequality persist, amplify, or get corrected?

### 3. Action Order

Two modes:
- **Simultaneous** (current): all agents choose, then all resolve at once
- **Sequential random**: random order each round, each agent sees all previous actions from that round before choosing

Implementation: add `action_order` param to game_params.yaml. Engine resolves actions one-by-one in sequential mode, updating state between each.

Run each 3x with Gemini Flash Lite, compare.

Question answered: does information about others' current-round actions change strategy?

### 4. Spatial Field

2D grid where agents occupy cells and can only interact with neighbors.

- Grid size: ceil(sqrt(num_agents * 4)) -- sparse enough for movement to matter
- Agents placed randomly at start
- Each round: agents move to random adjacent cell (8-directional + stay), then choose action
- Interaction radius R (configurable, default 2): can only target agents within R cells
- If no valid targets in range, agent can only arm_self or no_action

Implementation:
- New `SpatialField` class managing grid positions and neighbor queries
- Engine integration: filter available targets by proximity before agent decision
- Agent prompt: show only nearby agents and their resources (not global state)
- New params in game_params: `spatial_enabled`, `grid_size`, `interaction_radius`

Run at 10 and 30 agents, compare with non-spatial baseline.

Question answered: does locality produce local hegemons instead of global ones?

### 5. Scale to 30 Agents

Pick the most interesting game config from sweep results. Run at 30 agents with both Nova Micro and Gemini Flash Lite (3 reps each).

Question answered: does scaling change structure?

### 6. Visualization

Python plotting script producing:
- Gini trajectory over time (mean + std band across repeats)
- Action distribution stacked bar per round
- Final resource distribution bar chart

Output to `data/plots/`. Use matplotlib.

### 7. Meeting Prep

- Update experiment log with all new results
- Write `notes/meeting_prep_20260227.md`
- Summary of findings, open questions, proposed Phase 2 direction
- If time: architecture comparison story (Nova Micro vs Gemini at 30 agents)

---

## Implementation Order

1. ~~Gemini Flash Lite sweeps~~ (running in background)
2. Wealth distribution test (config + engine change, quick)
3. Action order test (engine change, medium)
4. Spatial field (new class + engine integration, largest piece)
5. Visualization script
6. 30-agent runs
7. Log results + meeting prep

---

## Success Criteria

Before Feb 27, we can confidently tell Debraj:
- "The game supports both war and cooperation depending on the agent"
- "Here's how each parameter affects dynamics, for two different model capabilities"
- "Here's how distributions, action order, and spatial locality affect structure"
- "Here's the configuration we propose for Phase 2 prompt experiments, and why"
