import pytest
from src.shared.semantic_resolution_contracts import SemanticConstraint

def test_semantic_constraint_supports_rich_operators():
    # EQUALS
    c1 = SemanticConstraint(identity="id1", constraint_type="type1", operator="EQUALS", bound_value="50")
    assert c1.operator == "EQUALS"

    # GREATER_THAN
    c2 = SemanticConstraint(identity="id1", constraint_type="type1", operator="GREATER_THAN", bound_value="50")
    assert c2.operator == "GREATER_THAN"

    # BETWEEN
    c3 = SemanticConstraint(identity="id1", constraint_type="type1", operator="BETWEEN", bound_value="[10, 20]")
    assert c3.operator == "BETWEEN"
