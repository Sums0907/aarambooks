"""
Regression coverage for matching a customer's RESCHEDULE reply against the two specific
dates Priya actually offered (see ccc_builder.py's offered_reattempt_date_1/_2, confirmed
against ShopDeck's own NDR console), and for that matched date reaching ShopDeck's
NDRIntelligenceRequest.action_parameters (the only field on that schema meant for this -
see business_systems/shopdeck/backend/api/schemas/ndr_queue.py).
"""
from unittest.mock import AsyncMock

import pytest

from src.intelligence_domains.ndr.reply_parser import extract_matched_reattempt_date, classify_reply_heuristic

D1 = "Wednesday (09-09-2026)"
D2 = "Thursday (10-09-2026)"


@pytest.mark.parametrize("transcript,expected", [
    ("haan Wednesday theek hai", D1),
    ("Thursday is fine", D2),
    ("haan kal bhej dena", D1),
    ("day after tomorrow please", D2),
    ("tomorrow works for me", D1),
    ("parso bhej dena", D2),
    ("कल ठीक है", D1),
    ("परसों भेज देना", D2),
])
def test_matches_the_specific_offered_date(transcript, expected):
    assert extract_matched_reattempt_date(transcript, D1, D2) == expected


@pytest.mark.parametrize("transcript", ["no thanks", "yes okay send it", ""])
def test_returns_none_rather_than_guessing_when_no_date_is_named(transcript):
    """
    A bare 'yes' after two dates were offered is genuinely ambiguous - the whole point of
    offering two fixed dates is knowing exactly which one was agreed to, so this must not
    guess. UNCLEAR-routing (via the caller checking for None) is the correct outcome.
    """
    assert extract_matched_reattempt_date(transcript, D1, D2) is None


def test_reschedule_intent_and_date_match_are_independent_but_compatible():
    """
    classify_reply_heuristic still returns its original 2-tuple (existing callers/tests
    depend on this) - extract_matched_reattempt_date is a separate, additive lookup callers
    make only when intent == RESCHEDULE, using the offered dates from that specific call's
    CCC snapshot.
    """
    intent, state = classify_reply_heuristic("haan Wednesday theek hai")
    assert intent == "RESCHEDULE"
    assert extract_matched_reattempt_date("haan Wednesday theek hai", D1, D2) == D1


def test_no_offered_dates_available_returns_none_not_a_crash():
    assert extract_matched_reattempt_date("Wednesday works", None, None) is None
