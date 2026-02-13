"""
LLM agent using OpenRouter API for decision making.
Uses configurable prompt styles for different experimental conditions.
"""

import os
import json
import time
import sys
from typing import Dict, Optional
from openai import OpenAI
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game.engine import Action, ActionType
from agents.prompts import get_prompt_style, UnifiedPrompt


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
                 retry_delay: int = 2):
        """
        Initialize LLM agent.
        
        Args:
            agent_id: Unique identifier for this agent
            api_key: OpenRouter API key
            model: Model identifier (e.g., "deepseek/deepseek-v3.2")
            prompt_config: Dictionary with prompt toggles (objective_style, state_style, etc.)
            game_params: Game parameters dict
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        self.agent_id = agent_id
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Initialize unified prompt
        self.prompt = get_prompt_style(prompt_config or {}, game_params)
        # Initialize unified prompt
        self.prompt = get_prompt_style(prompt_config or {}, game_params)
        
        # Initialize OpenRouter client (OpenAI-compatible)
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        self.reasoning_traces = []
    
    def _format_observation(self, observation: Dict) -> str:
        """
        Format observation using unified prompt.
        """
        return self.prompt.format_observation(observation, self.agent_id)
    
    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse LLM response to extract action.
        
        Returns:
            Dictionary with action, target, and reasoning, or None if parsing fails
        """
        try:
            # Try to find JSON in response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed = json.loads(json_str)
                
                # Validate required fields
                if 'action' in parsed:
                    return {
                        'action': parsed['action'],
                        'target': parsed.get('target'),
                        'reasoning': parsed.get('reasoning', '')
                    }
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _action_dict_to_action(self, action_dict: Dict) -> Optional[Action]:
        """Convert parsed action dictionary to Action object."""
        action_str = action_dict['action'].lower()
        target = action_dict['target']
        
        # Map action string to ActionType
        action_map = {
            'invest_self': ActionType.INVEST_SELF,
            'invest_other': ActionType.INVEST_OTHER,
            'arm_self': ActionType.ARM_SELF,
            'arm_other': ActionType.ARM_OTHER,
            'attack': ActionType.ATTACK
        }
        
        if action_str not in action_map:
            return None
        
        action_type = action_map[action_str]
        
        # Validate target requirements
        if action_type in [ActionType.INVEST_OTHER, ActionType.ARM_OTHER, ActionType.ATTACK]:
            if not target or target == self.agent_id:
                return None
        
        return Action(
            agent_id=self.agent_id,
            action_type=action_type,
            target_id=target if target else None
        )
    
    def select_action(self, observation: Dict) -> Action:
        """
        Select action based on observation using LLM.
        
        Args:
            observation: Game state observation
            
        Returns:
            Selected action
        """
        prompt = self._format_observation(observation)
        
        for attempt in range(self.retry_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout
                )
                
                response_text = response.choices[0].message.content
                
                # Log reasoning trace
                self.reasoning_traces.append({
                    "round": observation['round'],
                    "agent_id": self.agent_id,
                    "prompt": prompt,
                    "response": response_text,
                    "model": self.model
                })
                
                # Parse response
                action_dict = self._parse_response(response_text)
                if action_dict:
                    action = self._action_dict_to_action(action_dict)
                    if action:
                        return action
                
                # If parsing failed, try again
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                    continue
                
            except Exception as e:
                print(f"Error in LLM request (attempt {attempt + 1}/{self.retry_attempts}): {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
        
        # Fallback: invest_self if all else fails
        print(f"Warning: {self.agent_id} falling back to invest_self")
        return Action(
            agent_id=self.agent_id,
            action_type=ActionType.INVEST_SELF,
            target_id=None
        )
    
    def get_reasoning_traces(self) -> list:
        """Get all reasoning traces for analysis."""
        return self.reasoning_traces
