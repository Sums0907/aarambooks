"""
ShopDeck AZM Namespace Definitions
Static definitions for ShopDeck concepts and views.

ARCHITECTURAL WARNING:
AZM NEVER CONNECTS TO A BUSINESS SYSTEM OPERATIONAL DATABASE AT RUNTIME.
Do NOT attempt to use `BUSINESS_SYSTEM_CONNECTION_URI` to establish live
database connections during AzmProvider resolution or query routing.
All persistent knowledge MUST be resolved through the AZM Knowledge DB.
"""
from src.shared.semantic_resolution_contracts import SemanticConcept

SHOPDECK_CONCEPTS = [
    SemanticConcept(
        concept_id="shopdeck.entity.order",
        concept_name="Order",
        concept_type="ENTITY",
        aliases=["order", "purchase"],
        description="A customer order placed on the Shopdeck storefront."
    ),
    SemanticConcept(
        concept_id="shopdeck.entity.customer",
        concept_name="Customer",
        concept_type="ENTITY",
        aliases=["customer", "buyer", "user"],
        description="A customer who purchases on the Shopdeck storefront."
    ),
    SemanticConcept(
        concept_id="shopdeck.entity.cancellation",
        concept_name="Cancellation",
        concept_type="ENTITY",
        aliases=["cancel", "cancelled order", "cancellation"],
        description="A customer cancelling their order."
    ),
    SemanticConcept(
        concept_id="shopdeck.entity.return",
        concept_name="Return",
        concept_type="ENTITY",
        aliases=["return", "exchange", "refund"],
        description="A customer returning or exchanging their order."
    )
]

# The ShopDeck Business System is responsible for defining and exposing the public views (e.g., vw_shopdeck_order_line_items).
# Azm reads those schemas dynamically at runtime from the Business System Database instead of hardcoding them here.
BUSINESS_SYSTEM_CONNECTION_URI = "postgresql://localhost:5432/shopdeck"
SHOPDECK_PUBLIC_VIEWS = {}
