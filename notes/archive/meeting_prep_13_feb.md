# Meeting Prep - Debraj - 13 Feb 2026

**Sprint 1**: Feb 9 - Feb 13 (first week after proposal submission)

---

## Agenda

### 1. Since Last Meeting (Jan 30)
- Submitted proposal (v1, Jan 30)
- Built and tested LLM simulation: game engine, LLM agents via OpenRouter, configurable prompts
- Ran 28 simulation runs (Feb 4) with varying models, objectives, agent counts
- Analyzed all runs -- key findings below
- Set up project roadmap and sprint-based working structure
- Literature reading didn't happen this week (be honest about this)

### 2. Simulation Results to Show (the meat of the meeting)

**Finding 1: Objective framing drives emergent behavior**
Same game, same model, different goal sentence → completely different social structures:
- "shared win" → perfect reciprocal cooperation pairs, zero conflict
- "avoid last" → cautious/defensive play, low inequality
- "finish first" → aggressive, frequent attacks
- "maximize absolute" → bandwagoning toward leader, extreme inequality

This is the strongest result. Three demo runs below (all same model: Gemini-3-Flash):

#### Demo Run A: Perfect Cooperation (`20260204_181830`)
- **Objective**: shared_win (paired agents maximize combined resources)
- **Config**: 6 agents, 10 rounds, invest_self cost 0 / return +2, invest_other cost 0 / return +5
- **Result**: 3 stable pairs form instantly (1↔2, 3↔4, 5↔6), maintained all 10 rounds
- **Final resources**: ALL agents at exactly 175.0 -- perfect equality
- **Actions**: 100% invest_other, 0% conflict
- **Reasoning trace**: agent_1 round 2: "agent_2 and I successfully established a reciprocal investment relationship. The other agents (3/4 and 5/6) also formed pairs, creating a stable, peaceful environment."

#### Demo Run B: War and Destruction (`20260204_181002`)
- **Objective**: become_first (finish in first place)
- **Config**: 6 agents, 10 rounds, same game params as Run A
- **Result**: arms race cascade, pre-emptive strikes, coalition pile-on against leader
- **Final resources**: agent_1: 14.5, agent_2: 6.4, agent_3: 4.9, agent_4: 5.4, agent_5: 0.7, agent_6: 4.2
- **76% of all resources destroyed** through warfare (150 start → 36 end)
- **Actions**: 28% attack, 23% arm_self, 48% invest_self, 0% invest_other
- **Reasoning trace**: agent_4 round 2: "I am currently the only armed agent, giving me a massive combat power advantage. Since I am in last place, I must attack now while my advantage is active."
- Round 9: ALL 5 other agents attack agent_4 (the leader) simultaneously

#### Demo Run C: Benevolent Hegemon (`20260204_164621`)
- **Objective**: narrative ("end with the most resources through strategic decisions")
- **Config**: 5 agents, 10 rounds, same game params
- **Result**: all agents spontaneously invest in agent_1, who reciprocates only with agent_2
- **Final resources**: agent_1: 291.1, agent_5: 192.5, agent_2: 84.0, agent_3: 46.2, agent_4: 46.2
- Agents 3 and 4 ended POORER than they started (46.2 < starting resources)
- **Actions**: 88% invest_other, 10% attack (late-game revolt), 2% arm_self
- **Reasoning trace**: agent_1 round 5: "This 'benevolent hegemon' strategy is highly [effective]..."
- agent_5 revolts in round 8, attacks agent_1 and wins against 21% odds

#### Contrast Summary
| | Cooperation | War | Hegemon |
|---|---|---|---|
| Objective | shared_win | become_first | narrative |
| invest_other | 100% | 0% | 88% |
| attack | 0% | 28% | 10% |
| Final Gini | 0.000 | 0.351 | 0.386 |
| Resources preserved | 700% | 24% | 528% |
| Structure | Mutual pairs | Arms race | Tribute system |

#### Live Demo
Current config (`simulation/config/`): shared_win, Gemini-3-Flash, 6 agents, 10 rounds.
To demo conflict: change `objective_style` to `become_first` in `openrouter_config.yaml`.
Run with: `cd simulation && python src/main.py`

**Finding 2: Nobody ever used arm_other (coalition formation)**
Across all 28 runs, zero coalition formation. Agents don't plan multi-agent coordination.
- Could be reasoning limitation, could be cost/benefit issue
- Possible fix: tune parameters (cheaper arm_other, better payoff)
- Question: is coalition formation worth pursuing or accept the finding?

**Finding 3: invest_self creates boring stalemates**
When available, agents default to the safe option. Disabling it forces social interaction.
- Decision: disable invest_self for main experiments

**Finding 4: Model differences**
- Llama-8B: minimal reasoning, accidental hierarchies
- DeepSeek: strategic but falls into appeasement traps
- Gemini-3-Flash: most sophisticated, does probability calculations

**Finding 5: End-game conflict**
When agents know when the game ends, conflict spikes in final rounds (backward induction).

### 3. The Big Question: Thesis Direction

I'm torn between two directions and want your honest take:

**Option A (current proposal)**: RL vs LLM comparison
- Pro: clean RQ, publishable either way, extends Axelrod
- Con: RL is big engineering effort, comparison may not be clean (LSTM vs context window)
- The objective framing results make this interesting: does RL show the same sensitivity to objective wording?

**Option B (emerging instinct)**: LLM-only ablation study
- Systematically vary: objectives, semantic framing (Dubey-style), CoT, model scale
- Pro: I already have results showing strong effects, my simulation is ready, aligns with Debraj's interest in language/prompt variation
- Con: risk of "just prompt engineering", Larooij critique, is this CLS enough?

**Option C (middle ground)**: RL as lightweight baseline, main contribution is LLM ablation
- Quick RL agent as anchor point, then deep dive into what drives LLM emergent behavior

### 4. Questions for Debraj
- Which direction? He was excited about prompt/language variation (Jan 30) -- as extension or as core?
- Prompt sensitivity paper he mentioned -- reference?
- How many runs per condition for statistical validity?
- Coalition formation: worth pursuing through parameter tuning?
- If RL: any recommendations for LSTM-PPO in multi-agent settings?

### 5. Planning
- Show roadmap: phases Feb-Jul, weekly sprints
- Propose: lock thesis direction today, next sprint focused on that direction
- Literature: needs to happen next week (Debraj's instruction from Jan 30)

---

## After Meeting Notes

### Key Takeaways
- Debraj doesn't care about specific results yet -- first understand the SYSTEM
- Without knowing how the system behaves, can't say anything meaningful about prompt variation later
- Two clear phases now:
  - **Phase 1**: Characterize the system. One metric, one prompt, vary cost/benefit (theta). Does it stabilize?
  - **Phase 2**: Vary prompting and measure effects on the metrics from Phase 1
- RL might not be needed. If used, keep it as a simple baseline. LLM prompt variations might be all we investigate.
- Scale to 30 agents -- research suggests significant distribution changes at scale

### Action Items
- Pick one metric: hierarchy (Gini, top 10% vs bottom 50%)
- Pick one parameter set + one prompt as baseline
- Measure agent action stability over time: do they converge on optimal actions?
- Define theta = cost/benefit per action, systematically vary it
- Test sensitivity of game stability to theta
- If time: vary initial wealth distribution, simultaneous vs random action order
- Check papers/tools:
  - TextGrad (Zou group): https://github.com/zou-group/textgrad
  - EGG (Facebook, emergence of language): https://github.com/facebookresearch/EGG
  - Debraj's own paper (similar game, RL, published): https://dl.acm.org/doi/10.5555/3635637.3662962

### Decisions Made
- Phase 1 before Phase 2: understand the system before varying prompts
- RL is optional/lightweight, not the main contribution
- Focus on LLM prompt variation as main investigation (confirms Option B/C direction)
- Need to scale up to 30 agents

### Next Sprint Goals (Feb 13-20)
- [ ] Read Debraj's paper (the similar game with RL)
- [ ] Define theta = c/b for each action in current game
- [ ] Set up baseline: one prompt, one model, 30 agents
- [ ] Run baseline and measure: do agents stabilize? What does Gini look like over time?
- [ ] Literature: catch up on reading list from Sprint 1
- [ ] Check TextGrad and EGG repos
