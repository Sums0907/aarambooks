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
    
def test_greeting_obeys_tomorrow_only():
    engagement = {
        "call_context": {
            "customer_name": "Sumati",
            "domain_constraints": ["Only offer tomorrow as an option"]
        }
    }
    greeting = generate_dynamic_greeting(engagement)
    
    assert "tomorrow" in greeting.lower()
    assert "schedule another date" not in greeting.lower()
    assert "different date in mind" not in greeting.lower()

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
