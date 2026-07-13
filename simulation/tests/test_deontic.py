"""Norm-classificatie (deontic.py) — valideert het Bicchieri-kernonderscheid
(individueel-deontisch != norm; deontisch + collectief = norm) en de Aoki
first/other-party moral-split. Lexicale marker, niet perfecte NLP — de tests
verankeren het bedoelde gedrag zodat lexicon-tuning niet stil regresseert."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from deontic import classify


def test_individual_deontic_is_not_norm():
    # deontisch van vorm, maar individueel EV-redeneren -> GEEN norm (Bicchieri).
    c = classify("I should attack Copper this round.")
    assert c["deontic"] is True
    assert c["norm"] is False


def test_collective_obligation_is_norm():
    c = classify("We must hold the line together.")
    assert c["deontic"] is True
    assert c["norm"] is True


def test_collective_prohibition_is_norm():
    c = classify("Members may not attack the pact.")
    assert c["deontic"] is True
    assert c["norm"] is True


def test_sanction_detected():
    c = classify("Traitors will be purged and cast out.")
    assert c["sanction"] is True


def test_moral_first_party():
    # geinternaliseerde morele kracht, zelf-referentieel (Aoki first-party).
    c = classify("I am ashamed of what I did.")
    assert c["moral_first"] is True
    assert c["moral_other"] is False
    assert c["moral"] is True


def test_moral_other_party():
    # gericht-veroordelend (Aoki second/third-party).
    c = classify("You deserve blame for that.")
    assert c["moral_other"] is True
    assert c["moral_first"] is False


def test_neutral_sentence_is_empty():
    c = classify("The stock is at sixty units.")
    assert not any(c.values())
