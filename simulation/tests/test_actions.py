"""Action-vocabulary tests.

Canonical actions: transfer / strengthen / take / hold. Legacy names
(invest_other / arm_other / attack / do_nothing) are accepted on input and
normalized to canonical. arm_self is not an available action.
"""

from types import SimpleNamespace

from agents.llm_agent import LLMAgent


def _norm(s):
    dummy = SimpleNamespace(_VALID_ACTIONS=LLMAgent._VALID_ACTIONS,
                            _ACTION_ALIASES=LLMAgent._ACTION_ALIASES)
    return LLMAgent._normalize_action(dummy, s)


def test_canonical_action_set():
    # 'harvest' is only a real action under commons_harvest_mode="action_own"
    # (gated in _action_dict_to_action); it is in the canonical vocabulary so the
    # normaliser recognises it rather than dropping it.
    assert LLMAgent._VALID_ACTIONS == {'transfer', 'strengthen', 'take', 'hold', 'harvest'}
    for a in ('transfer', 'strengthen', 'take', 'hold', 'harvest'):
        assert _norm(a) == a


def test_legacy_names_map_to_canonical():
    assert _norm('invest_other') == 'transfer'
    assert _norm('arm_other') == 'strengthen'
    assert _norm('attack') == 'take'
    assert _norm('do_nothing') == 'hold'


def test_shorthands_and_fuzz():
    assert _norm('invest') == 'transfer'
    assert _norm('arm') == 'strengthen'
    assert _norm('Take ') == 'take'
    assert _norm('transfers') == 'transfer'   # trailing-s strip
    assert _norm('do nothing') == 'hold'


def test_arm_self_not_available():
    assert 'arm_self' not in LLMAgent._VALID_ACTIONS
    assert _norm('arm_self') is None
    assert _norm('arm self') is None
