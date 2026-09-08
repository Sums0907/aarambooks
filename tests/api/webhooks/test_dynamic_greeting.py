import pytest
from src.api.webhooks.exotel_webhooks import generate_dynamic_greeting

def test_greeting_avoids_courier_when_constrained():
    engagement = {
        "call_context": {
            "customer_name": "Sumati",
            "product_name": "Premium Bedsheet",
            "domain_constraints": ["Do not mention courier"]
        }
    }
    greeting = generate_dynamic_greeting(engagement)
    
    assert "courier" not in greeting.lower()
    assert "partner" not in greeting.lower()
    assert "delivery partner" not in greeting.lower()
    assert "logistics" not in greeting.lower()
    
def test_greeting_never_asks_for_a_date_even_when_a_date_is_constrained():
    """
    Inverted deliberately. This test previously asserted the greeting ASKS about tomorrow.
    That is the pushy opening the NDR mission contract forbids: the opening states why the
    call is happening and asks for consent to talk. Any delivery-date discussion belongs
    later in the call, after the customer has responded. The "tomorrow only" constraint
    still governs the resolution phase - it is carried in session_constants, not the greeting.
    """
    engagement = {
        "call_context": {
            "customer_name": "Sumati",
            "domain_constraints": ["Only offer tomorrow as an option"]
        }
    }
    greeting = generate_dynamic_greeting(engagement)

    assert "tomorrow" not in greeting.lower()
    # "कल" itself is not banned: Hindi "कल" is tense-ambiguous (yesterday/tomorrow), and the
    # greeting legitimately uses it in the past tense to describe WHEN delivery failed
    # ("delivery कल नहीं हो पाई"), not to propose a future reschedule date. What must never
    # appear is an actual forward-looking date proposal.
    assert "reschedule" not in greeting.lower()
    assert greeting.rstrip().endswith("क्या अभी बात करना सुविधाजनक है?")

def test_greeting_uses_product_name():
    engagement = {
        "call_context": {
            "customer_name": "Sumati",
            "product_name": "Pure Mulmul Kids Dohar",
            "domain_constraints": []
        }
    }
    greeting = generate_dynamic_greeting(engagement)
    
    assert "Pure Mulmul Kids Dohar" in greeting
