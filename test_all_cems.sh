echo "--- Testing BALANCE ---"
curl -s -X POST http://localhost:8100/api/v1/context/resolve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mock_user_token" \
  -d '{
    "capability_urn": "urn:aarambooks:inventory:capability:balance",
    "requirement": {
      "requirement_id": "req-1",
      "original_requirement": {"requirement_id": "req-1", "necessity": "REQUIRED", "semantic_intent": "stock balance"},
      "core_identities": ["inventory.capability.balance", "inventory.entity.sku"],
      "semantic_constraints": [
        {"identity": "inventory.capability.balance", "constraint_type": "CAPABILITY", "operator": "EQUALS", "bound_value": "126BS"},
        {"identity": "inventory.entity.sku", "constraint_type": "ENTITY", "operator": "EQUALS", "bound_value": "126BS"}
      ],
      "semantic_gaps": []
    }
  }' | jq .

echo -e "\n--- Testing LEDGER ---"
curl -s -X POST http://localhost:8100/api/v1/context/resolve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mock_user_token" \
  -d '{
    "capability_urn": "urn:aarambooks:inventory:capability:ledger",
    "requirement": {
      "requirement_id": "req-2",
      "original_requirement": {"requirement_id": "req-2", "necessity": "REQUIRED", "semantic_intent": "ledger"},
      "core_identities": ["inventory.capability.ledger", "inventory.entity.sku"],
      "semantic_constraints": [
        {"identity": "inventory.capability.ledger", "constraint_type": "CAPABILITY", "operator": "EQUALS", "bound_value": "126BS"},
        {"identity": "inventory.entity.sku", "constraint_type": "ENTITY", "operator": "EQUALS", "bound_value": "126BS"}
      ],
      "semantic_gaps": []
    }
  }' | jq .

echo -e "\n--- Testing JOBWORK STATUS ---"
curl -s -X POST http://localhost:8100/api/v1/context/resolve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mock_user_token" \
  -d '{
    "capability_urn": "urn:aarambooks:inventory:capability:jobwork_status",
    "requirement": {
      "requirement_id": "req-3",
      "original_requirement": {"requirement_id": "req-3", "necessity": "REQUIRED", "semantic_intent": "jobwork status"},
      "core_identities": ["inventory.capability.jobwork_status", "inventory.entity.sku", "inventory.entity.jobwork_vendor"],
      "semantic_constraints": [
        {"identity": "inventory.capability.jobwork_status", "constraint_type": "CAPABILITY", "operator": "EQUALS", "bound_value": "126BS"},
        {"identity": "inventory.entity.sku", "constraint_type": "ENTITY", "operator": "EQUALS", "bound_value": "126BS"},
        {"identity": "inventory.entity.jobwork_vendor", "constraint_type": "ENTITY", "operator": "EQUALS", "bound_value": "V-101"}
      ],
      "semantic_gaps": []
    }
  }' | jq .

echo -e "\n--- Testing EXCEPTION STATUS ---"
curl -s -X POST http://localhost:8100/api/v1/context/resolve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mock_user_token" \
  -d '{
    "capability_urn": "urn:aarambooks:inventory:capability:exception_status",
    "requirement": {
      "requirement_id": "req-4",
      "original_requirement": {"requirement_id": "req-4", "necessity": "REQUIRED", "semantic_intent": "exceptions"},
      "core_identities": ["inventory.capability.exception_status", "inventory.entity.sku"],
      "semantic_constraints": [
        {"identity": "inventory.capability.exception_status", "constraint_type": "CAPABILITY", "operator": "EQUALS", "bound_value": "126BS"},
        {"identity": "inventory.entity.sku", "constraint_type": "ENTITY", "operator": "EQUALS", "bound_value": "126BS"}
      ],
      "semantic_gaps": []
    }
  }' | jq .
