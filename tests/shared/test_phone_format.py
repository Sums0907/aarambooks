import pytest

from src.shared.phone_format import to_e164_india


@pytest.mark.parametrize("raw,expected", [
    ("9876543210", "+919876543210"),
    ("09876543210", "+919876543210"),
    ("919876543210", "+919876543210"),
    ("+919876543210", "+919876543210"),
    ("+91 98765 43210", "+919876543210"),
    ("98765-43210", "+919876543210"),
])
def test_to_e164_india_normalizes_known_formats(raw, expected):
    assert to_e164_india(raw) == expected


@pytest.mark.parametrize("raw", ["", None])
def test_to_e164_india_passes_through_empty(raw):
    assert to_e164_india(raw) == raw


def test_to_e164_india_leaves_unexpected_format_unchanged():
    # Not 10/11/12/13 digits after stripping - genuinely ambiguous, must not guess.
    assert to_e164_india("12345") == "12345"
