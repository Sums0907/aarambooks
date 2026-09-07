import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

import src.shared.config
# Force API mode
src.shared.config.settings.shopdeck_ndr_transport = "api"

from src.main import rabta_orch, text_to_sql_engine
from src.shared.evidence_request_contracts import BusinessRealityStatus

@pytest.mark.asyncio
async def test_end_to_end_api_mode():
    with patch('src.infrastructure.adapters.shopdeck_cem_adapter.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"awb_no": "123456789", "status": "Delivered"}
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client_class.return_value = mock_client
        
        with patch.object(text_to_sql_engine, 'generate_sql', new_callable=AsyncMock) as mock_sql:
            response = await rabta_orch.process_query(
                query="What is the NDR status for AWB 123456789 ?",
                id_urn="urn:aarambooks:intelligence:ndr",
                cem_urn="urn:aarambooks:cem:ndr",
                auth_context="mock_token"
            )
            
            # Proof 1: API was invoked
            print("RESPONSE:", response)
            mock_client.get.assert_called_once()
            
            # Proof 2: SQL engine was NOT invoked
            mock_sql.assert_not_called()
            
            # Proof 3: Successful interpretation
            assert "NDR shipment record located" in response.message

