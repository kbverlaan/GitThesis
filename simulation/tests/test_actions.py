"""Action-set tests: arm_other is available, arm_self is not.

Combat strength can only be raised by others arming you (no self-arming);
strength above one's own wealth is therefore inherently social.
"""

from types import SimpleNamespace

from agents.llm_agent import LLMAgent


def _norm(s):
    dummy = SimpleNamespace(_VALID_ACTIONS=LLMAgent._VALID_ACTIONS)
    return LLMAgent._normalize_action(dummy, s)


def test_arm_self_removed():
    assert "arm_self" not in LLMAgent._VALID_ACTIONS
    assert _norm("arm_self") is None
    assert _norm("arm self") is None


def test_arm_other_present():
    assert "arm_other" in LLMAgent._VALID_ACTIONS
    assert _norm("arm_other") == "arm_other"
    assert _norm("arm") == "arm_other"  # bare "arm" maps to arm_other now
