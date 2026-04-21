"""
LLM agent using OpenRouter API for decision making.
Uses configurable prompt styles for different experimental conditions.

Design references:
- Reasoning traces as data: thinking tokens (<think>...</think>) are extracted
  and stored as behavioral data, not as mechanistic explanations. Faithfulness
  caveats per Turpin et al. (2023), Lanham et al. (2023), Chen et al. (2025).
- Thinking model support: Qwen3/3.5 reasoning via enable_thinking chat template.
  vLLM reasoning parser separates thinking from content tokens.
- Retry with structured output: JSON follow-up prompt on parse failure,
  preserving the original reasoning trace for analysis.
"""

import os
import json
import re
import time
import sys
from typing import Dict, Optional
from openai import OpenAI
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game.engine import Action, ActionType
from agents.prompts import get_prompt_style
from agents.memory import AgentMemory


class LLMAgent:
    """LLM-based agent that makes decisions via OpenRouter API."""

    def __init__(self,
                 agent_id: str,
                 api_key: str,
                 model: str,
                 prompt_config: Optional[Dict] = None,
                 game_params: Optional[Dict] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 500,
                 timeout: int = 30,
                 retry_attempts: int = 3,
                 retry_delay: int = 2,
                 base_url: str = "https://openrouter.ai/api/v1",
                 memory_config: Optional[Dict] = None):
        """
        Initialize LLM agent.

        Args:
            agent_id: Unique identifier for this agent
            api_key: OpenRouter API key (use "none" for local vLLM)
            model: Model identifier (e.g., "deepseek/deepseek-v3.2")
            prompt_config: Dictionary with prompt toggles (objective_style, state_style, etc.)
            game_params: Game parameters dict
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds
            base_url: API base URL (OpenRouter, vLLM local, etc.)
            memory_config: Memory settings dict with 'enabled', 'window_size', etc.
        """
        self.agent_id = agent_id
        self.model = model
        self.temperature = temperature
        # Thinking models need more tokens for reasoning + JSON response.
        # Qwen3/3.5 thinking tokens count toward completion_tokens — 2048 is
        # far too low (thinking alone uses 4-6K tokens). Default to 16384.
        model_lower = model.lower()
        self.is_thinking_model = any(t in model_lower for t in ["qwq", "qwen3"])
        if self.is_thinking_model and max_tokens < 16384:
            self.max_tokens = 16384
        else:
            self.max_tokens = max_tokens
        # Thinking models need longer timeout (long reasoning chains)
        # With 8+ concurrent requests, per-request throughput drops to ~30 tok/s.
        # 6K thinking tokens / 30 tok/s = 200s decode + prefill + scheduling.
        # Qwen3.5 vLLM recipe uses 3600s. 900s is a safe practical minimum.
        if self.is_thinking_model and timeout < 900:
            self.timeout = 900
        else:
            self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        # Initialize prompt
        self.game_params = game_params or {}
        self.prompt = get_prompt_style(prompt_config or {}, game_params)

        # Initialize memory
        mem_cfg = memory_config or {}
        self.memory_enabled = mem_cfg.get('enabled', True)
        if self.memory_enabled:
            window_size = mem_cfg.get('window_size', 10)
            self.memory = AgentMemory(agent_id, window_size=window_size)
        else:
            self.memory = None

        # Initialize OpenAI-compatible client (works with OpenRouter, vLLM, etc.)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        self.reasoning_traces = []
        self._visible_agents = None
        self._last_message = None  # Last message extracted from LLM response
        self._last_note = None     # Last note-to-self extracted from LLM response
        self._last_rewire_nom = None  # {'drop': id_or_None, 'invite': id_or_None}
    
    def _format_observation(self, observation: Dict) -> str:
        """
        Format observation using unified prompt.
        """
        return self.prompt.format_observation(observation, self.agent_id)
    
    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse LLM response to extract action.

        Handles <think>...</think> blocks from reasoning models (Qwen3, QwQ, MiMo):
        extracts thinking content separately, then strips it before JSON parsing.

        Fallbacks:
        - Strips markdown code fences (```json ... ```) before JSON extraction
        - Strips trailing commas before closing braces (common LLM error)
        - Fuzzy action name matching (e.g. "invest_Others" → "invest_other")

        Returns:
            Dictionary with action, target, reasoning, and thinking, or None if parsing fails
        """
        try:
            # Extract <think> content before stripping
            think_match = re.search(r'<think>(.*?)</think>', response_text, flags=re.DOTALL)
            thinking_content = think_match.group(1).strip() if think_match else None

            # Strip <think>...</think> blocks before JSON extraction
            clean_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)

            # Strip markdown code fences (```json ... ``` or ``` ... ```)
            clean_text = re.sub(r'```(?:json)?\s*', '', clean_text)

            # Try to find JSON in cleaned response
            start_idx = clean_text.find('{')
            end_idx = clean_text.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = clean_text[start_idx:end_idx]

                # Fix trailing commas before closing braces (common LLM error)
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)

                parsed = json.loads(json_str)

                # Validate required fields
                if 'action' in parsed:
                    # Normalize action name (fuzzy match)
                    action = self._normalize_action(parsed['action'])
                    if action is None:
                        return None

                    result = {
                        'action': action,
                        'target': parsed.get('target'),
                        'reasoning': parsed.get('reasoning', ''),
                        'thinking': thinking_content,
                    }
                    # Extract communication fields if present
                    if parsed.get('message'):
                        result['message'] = parsed['message']
                        result['message_to'] = parsed.get('message_to')
                    # Extract note-to-self if present
                    if parsed.get('note_to_self'):
                        result['note_to_self'] = parsed['note_to_self']
                    # Extract rewire nomination if present
                    drop = parsed.get('rewire_drop')
                    invite = parsed.get('rewire_invite')
                    if drop is not None or invite is not None:
                        result['rewire_drop'] = drop
                        result['rewire_invite'] = invite
                    return result
        except json.JSONDecodeError:
            pass

        return None

    # Valid action names for fuzzy matching
    _VALID_ACTIONS = {
        'invest_other', 'arm_self', 'arm_other', 'attack', 'do_nothing'
    }

    def _normalize_action(self, action_raw: str) -> Optional[str]:
        """Normalize action string with fuzzy matching.

        Handles common LLM errors: extra whitespace, wrong case, trailing 's',
        underscores vs spaces, close misspellings.
        """
        action = action_raw.strip().lower().replace(' ', '_').replace('-', '_')

        # Exact match
        if action in self._VALID_ACTIONS:
            return action

        # Strip trailing 's' (e.g. "invest_others" → "invest_other")
        if action.endswith('s') and action[:-1] in self._VALID_ACTIONS:
            return action[:-1]

        # Common misspellings
        aliases = {
            'nothing': 'do_nothing',
            'donothing': 'do_nothing',
            'do_nothing': 'do_nothing',
            'invest': 'invest_other',
            'arm': 'arm_self',
            'self_arm': 'arm_self',
        }
        if action in aliases:
            return aliases[action]

        return None
    
    def _action_dict_to_action(self, action_dict: Dict) -> Optional[Action]:
        """Convert parsed action dictionary to Action object."""
        action_str = action_dict['action'].lower()
        target = action_dict['target']
        
        # Map action string to ActionType
        action_map = {
            'invest_other': ActionType.INVEST_OTHER,
            'arm_self': ActionType.ARM_SELF,
            'arm_other': ActionType.ARM_OTHER,
            'attack': ActionType.ATTACK,
            'do_nothing': ActionType.DO_NOTHING
        }
        
        if action_str not in action_map:
            return None
        
        action_type = action_map[action_str]
        
        # Validate target requirements
        if action_type in [ActionType.INVEST_OTHER, ActionType.ARM_OTHER, ActionType.ATTACK]:
            if not target or target == self.agent_id:
                return None
            # Network restriction: actions only allowed on neighbors
            if self._visible_agents is not None and target not in self._visible_agents:
                return None

        return Action(
            agent_id=self.agent_id,
            action_type=action_type,
            target_id=target if target else None
        )
    
    def _store_message(self, action_dict: Dict):
        """Store communication message from LLM response."""
        msg_text = action_dict.get('message', '')
        msg_to = action_dict.get('message_to')
        if msg_text and msg_text.strip():
            comm_scope = self.game_params.get('comm_scope', 'none')
            # Enforce scope rules
            if comm_scope == 'broadcast':
                msg_to = 'all'
            elif comm_scope == 'dm' and msg_to == 'all':
                msg_to = None  # Invalid: DM scope can't broadcast
            self._last_message = {
                'from': self.agent_id,
                'message': msg_text.strip(),
                'message_to': msg_to,
            }

    def _store_note(self, action_dict: Dict):
        """Store note-to-self from LLM response."""
        note = action_dict.get('note_to_self')
        if note and isinstance(note, str) and note.strip():
            self._last_note = note.strip()
        else:
            self._last_note = None

    def _store_rewire(self, action_dict: Dict):
        """Store rewire nomination ({drop, invite}) from LLM response."""
        drop = action_dict.get('rewire_drop')
        invite = action_dict.get('rewire_invite')

        def _norm(v):
            if v is None:
                return None
            if isinstance(v, str):
                s = v.strip()
                if not s or s.lower() in ('null', 'none', 'no_one', 'nobody'):
                    return None
                return s
            return None

        drop_n = _norm(drop)
        invite_n = _norm(invite)
        if drop_n is None and invite_n is None:
            self._last_rewire_nom = None
        else:
            self._last_rewire_nom = {'drop': drop_n, 'invite': invite_n}

    def get_last_message(self) -> Optional[Dict]:
        """Return the message from the last select_action call, or None."""
        return self._last_message

    def get_last_rewire_nomination(self) -> Optional[Dict]:
        """Return the rewire nomination from the last select_action call, or None."""
        return self._last_rewire_nom

    def select_action(self, observation: Dict) -> Action:
        """
        Select action based on observation using LLM.
        
        Args:
            observation: Game state observation
            
        Returns:
            Selected action
        """
        # Store visible agents for network target validation
        self._visible_agents = observation.get('visible_agents', None)
        self._last_message = None  # Reset each round
        self._last_rewire_nom = None  # Reset each round

        prompt = self._format_observation(observation)

        errors = []

        for attempt in range(self.retry_attempts):
            try:
                t0 = time.time()
                # Build API call kwargs
                api_kwargs = dict(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                )
                # Qwen3: enable thinking via chat template
                if "qwen3" in self.model.lower():
                    api_kwargs["extra_body"] = {
                        "chat_template_kwargs": {"enable_thinking": True}
                    }

                response = self.client.chat.completions.create(**api_kwargs)
                latency = time.time() - t0

                msg = response.choices[0].message
                response_text = msg.content or ""

                # Extract thinking from vLLM --reasoning-parser output
                # vLLM uses 'reasoning' attr (not 'reasoning_content')
                thinking_content = getattr(msg, 'reasoning_content', None) or getattr(msg, 'reasoning', None)

                # Extract token usage from response
                usage = {}
                if response.usage:
                    usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }

                # Parse response (extracts thinking + action)
                action_dict = self._parse_response(response_text)

                # If content was empty but reasoning_content has JSON, try extracting from there
                if not action_dict and thinking_content:
                    action_dict = self._parse_response(thinking_content)

                # Attach reasoning_content as thinking data
                if thinking_content and action_dict:
                    action_dict['thinking'] = thinking_content

                # Log reasoning trace (includes thinking if present)
                trace_entry = {
                    "round": observation['round'],
                    "agent_id": self.agent_id,
                    "prompt": prompt,
                    "response": response_text,
                    "model": self.model,
                    "latency_s": round(latency, 3),
                    "usage": usage,
                    "attempt": attempt + 1,
                    "errors": errors.copy(),
                }
                final_thinking = thinking_content or (action_dict.get('thinking') if action_dict else None)
                if final_thinking is not None:
                    trace_entry["thinking"] = final_thinking
                self.reasoning_traces.append(trace_entry)

                if action_dict:
                    action = self._action_dict_to_action(action_dict)
                    if action:
                        self._store_message(action_dict)
                        self._store_note(action_dict)
                        self._store_rewire(action_dict)
                        return action

                # JSON missing — send a follow-up requesting structured output
                # Use low max_tokens for retry: only need JSON, not reasoning
                if attempt < self.retry_attempts - 1:
                    try:
                        t0 = time.time()
                        retry_response = self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "user", "content": prompt},
                                {"role": "assistant", "content": response_text},
                                {"role": "user", "content": "Please respond with ONLY a JSON object in this exact format: {\"reasoning\": \"<think step by step>\", \"action\": \"<action_name>\", \"target\": \"<agent_id or null>\"}"}
                            ],
                            temperature=self.temperature,
                            max_tokens=512,
                            timeout=60
                        )
                        retry_latency = time.time() - t0
                        retry_text = retry_response.choices[0].message.content

                        retry_usage = {}
                        if retry_response.usage:
                            retry_usage = {
                                "prompt_tokens": retry_response.usage.prompt_tokens,
                                "completion_tokens": retry_response.usage.completion_tokens,
                                "total_tokens": retry_response.usage.total_tokens,
                            }

                        action_dict = self._parse_response(retry_text)
                        if action_dict:
                            action = self._action_dict_to_action(action_dict)
                            if action:
                                self._store_message(action_dict)
                                self._store_note(action_dict)
                                self._store_rewire(action_dict)
                                # Log the retry trace
                                self.reasoning_traces.append({
                                    "round": observation['round'],
                                    "agent_id": self.agent_id,
                                    "prompt": "(JSON retry)",
                                    "response": retry_text,
                                    "model": self.model,
                                    "latency_s": round(retry_latency, 3),
                                    "usage": retry_usage,
                                    "attempt": attempt + 1,
                                    "is_retry": True,
                                })
                                return action
                    except Exception:
                        pass
                    time.sleep(self.retry_delay)
                    continue

            except Exception as e:
                errors.append({"attempt": attempt + 1, "error": str(e)})
                print(f"Error in LLM request (attempt {attempt + 1}/{self.retry_attempts}): {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)

        # Try to recover intended action from thinking traces before giving up.
        # When thinking models exhaust their token budget, the thinking often
        # contains the decision ("Attack Storm", "invest in Sage") even though
        # the JSON response was never generated.
        last_trace = self.reasoning_traces[-1] if self.reasoning_traces else None
        thinking_text = last_trace.get("thinking", "") if last_trace else ""
        fallback_action = self._parse_action_from_thinking(thinking_text, observation)

        if fallback_action:
            print(f"Warning: {self.agent_id} recovered action from thinking: "
                  f"{fallback_action.action_type.name} -> {fallback_action.target_id}")
            # Log as thinking-recovered fallback
            self.reasoning_traces.append({
                "round": observation['round'],
                "agent_id": self.agent_id,
                "prompt": prompt,
                "response": None,
                "model": self.model,
                "fallback": "thinking_recovery",
                "recovered_action": fallback_action.action_type.name.lower(),
                "recovered_target": fallback_action.target_id,
                "errors": errors,
            })
            return fallback_action

        # Last resort: do_nothing (safest neutral action)
        print(f"Warning: {self.agent_id} falling back to do_nothing (no action recoverable)")
        self.reasoning_traces.append({
            "round": observation['round'],
            "agent_id": self.agent_id,
            "prompt": prompt,
            "response": None,
            "model": self.model,
            "fallback": "default",
            "errors": errors,
        })
        return Action(
            agent_id=self.agent_id,
            action_type=ActionType.DO_NOTHING,
            target_id=None
        )
    
    def _parse_action_from_thinking(self, thinking: str, observation: Dict) -> Optional[Action]:
        """Try to recover intended action from thinking text when JSON response is missing.

        When thinking models exhaust their token budget, the thinking often contains
        the intended decision even though the JSON was never generated. This method
        scans for decision patterns in the thinking text.

        Strategy: scan the TAIL (last 2000 chars) for explicit decision statements,
        then fall back to the LAST mention of an action + target pair anywhere in
        the thinking. The last mention is most likely the final decision.

        Returns Action if a clear decision is found, None otherwise.
        """
        if not thinking or len(thinking) < 50:
            return None

        # Known agent IDs from observation
        all_agents = set(observation.get('resources', {}).keys())
        all_agents.discard(self.agent_id)
        # Build case-insensitive lookup
        agent_lookup = {a.lower(): a for a in all_agents}

        def _match_agent(name: str) -> Optional[str]:
            """Match a candidate name to a known agent ID."""
            return agent_lookup.get(name.lower())

        def _try_build_action(action_name: str, target_name: Optional[str]) -> Optional[Action]:
            """Try to build a valid Action from an action name and optional target."""
            action_str = self._normalize_action(action_name)
            if not action_str:
                return None
            action_map = {
                'invest_other': ActionType.INVEST_OTHER,
                'arm_self': ActionType.ARM_SELF,
                'arm_other': ActionType.ARM_OTHER,
                'attack': ActionType.ATTACK,
                'do_nothing': ActionType.DO_NOTHING,
            }
            action_type = action_map.get(action_str)
            if not action_type:
                return None
            needs_target = action_type in (ActionType.INVEST_OTHER, ActionType.ARM_OTHER, ActionType.ATTACK)
            target_id = _match_agent(target_name) if target_name else None
            if needs_target and not target_id:
                return None
            return Action(agent_id=self.agent_id, action_type=action_type,
                          target_id=target_id if needs_target else None)

        tail = thinking[-2000:]
        tail_lower = tail.lower()

        # --- Phase 1: Explicit decision statements (high confidence) ---
        decision_prefixes = (
            r'(?:decision|final plan|final choice|final confirmation|my (?:best )?action|'
            r'plan confirmed|okay,? (?:ready|proceeding)|i\'m confident)'
        )
        # "Decision: Attack Storm" / "Final Plan: invest_other -> Sage"
        for pattern in [
            decision_prefixes + r'[:\s]*\**\s*(attack)\s+(\w+)',
            decision_prefixes + r'[:\s]*\**\s*(invest(?:[_ ]?other)?(?:[_ ]?in)?)\s+(\w+)',
            decision_prefixes + r'[:\s]*\**\s*(arm[_ ]?other)\s+(\w+)',
            decision_prefixes + r'[:\s]*\**\s*(arm[_ ]?self)',
            decision_prefixes + r'[:\s]*\**\s*(do[_ ]?nothing)',
        ]:
            match = re.search(pattern, tail_lower)
            if match:
                groups = match.groups()
                action_name = groups[0].replace(' ', '_').strip('_')
                target_name = groups[1] if len(groups) > 1 else None
                # Normalize "invest in" / "invest" to "invest_other" when target present
                if action_name.startswith('invest') and target_name and 'self' not in action_name:
                    action_name = 'invest_other'
                result = _try_build_action(action_name, target_name)
                if result:
                    return result

        # --- Phase 2: "Action: attack. Target: Storm." pattern ---
        action_target_match = re.search(
            r'action[:\s]*\**\s*(attack|invest[_ ]?other|arm[_ ]?(?:self|other)|do[_ ]?nothing)\**'
            r'.*?target[:\s]*\**\s*(\w+)',
            tail_lower, re.DOTALL
        )
        if action_target_match:
            action_name = action_target_match.group(1).replace(' ', '_')
            target_name = action_target_match.group(2)
            if target_name in ('null', 'none', 'n/a'):
                target_name = None
            result = _try_build_action(action_name, target_name)
            if result:
                return result

        # --- Phase 3: Last mention of action + agent name (lower confidence) ---
        # Scan for the LAST occurrence of "attack <Agent>" etc. in the tail
        agent_pattern = '|'.join(re.escape(a) for a in agent_lookup.keys())
        last_action_patterns = [
            (rf'(attack)\s+({agent_pattern})', 'attack'),
            (rf'(invest(?:[_ ]?(?:other|in))?)\s+({agent_pattern})', 'invest_other'),
            (rf'(arm[_ ]?other)\s+({agent_pattern})', 'arm_other'),
            (rf'(arm[_ ]?self)', 'arm_self'),
            (rf'(do[_ ]?nothing)', 'do_nothing'),
        ]
        best_match = None
        best_pos = -1
        for pattern, action_name in last_action_patterns:
            for match in re.finditer(pattern, tail_lower):
                if match.start() > best_pos:
                    groups = match.groups()
                    target_name = groups[1] if len(groups) > 1 else None
                    result = _try_build_action(action_name, target_name)
                    if result:
                        best_match = result
                        best_pos = match.start()

        return best_match

    def update_memory(self, round_num: int, action_str: str, target: Optional[str],
                      outcome: Optional[Dict], visible_agents: Optional[list],
                      round_actions: list, resource_changes: Dict,
                      combat_results: list, all_resources: Dict,
                      received_messages: Optional[list] = None):
        """Update agent memory after a round resolves.

        Args:
            round_num: Round number.
            action_str: This agent's action type string.
            target: Target agent ID or None.
            outcome: Dict with outcome details for this agent's action.
            visible_agents: List of visible agent IDs (None = all).
            round_actions: All actions from the round log.
            resource_changes: Per-agent resource changes.
            combat_results: Combat result dicts from the round.
            all_resources: Current resources for all agents (post-round).
            received_messages: Messages received this round (list of dicts).
        """
        if not self.memory_enabled or self.memory is None:
            return
        self.memory.record_action(round_num, action_str, target, outcome)
        self.memory.update_observations(
            round_num, visible_agents, round_actions,
            resource_changes, combat_results, all_resources
        )
        # Record communication (always call to log sent messages even without received)
        self.memory.record_messages(self._last_message, received_messages or [], round_num)
        # Record note-to-self (persists to next round's prompt)
        self.memory.record_note(self._last_note)

    def get_reasoning_traces(self, include_retries=False) -> list:
        """Get reasoning traces for analysis.

        By default excludes JSON-retry entries so trace count == round count.
        Set include_retries=True to get all entries (for debugging).
        """
        if include_retries:
            return self.reasoning_traces
        return [t for t in self.reasoning_traces if not t.get('is_retry')]
