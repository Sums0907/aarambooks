import pytest
from src.infrastructure.adapters.shopdeck_cem_adapter import ShopdeckCemAdapter
from src.shared.evidence_request_contracts import AbstractEvidenceRequest, BusinessRealityStatus
from src.shared.requirement_classification_contracts import ClassifiedRequirement
from src.shared.conversational_contracts import ConversationalUnderstanding
import httpx
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.fixture
def adapter():
    return ShopdeckCemAdapter(base_url="http://testserver")

@pytest.fixture
def request_with_awb():
    return AbstractEvidenceRequest(
        classified_requirement=ClassifiedRequirement(
            understanding=ConversationalUnderstanding(
                original_query="Where is AWB123?",
                intent="RETRIEVE",
                parameters=[
                    {"parameter_name": "awb", "value": "AWB123", "data_type": "STRING", "original_expression": "AWB123"}
                ]
            ),
            components=[]
        )
    )

@pytest.mark.asyncio
async def test_successful_ndr_response_mapping(adapter, request_with_awb):
    with patch('src.infrastructure.adapters.shopdeck_cem_adapter._get_shopdeck_token', new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "mock_token"
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"awb_no": "AWB123", "status": "Delivered"}
            mock_get.return_value = mock_response
            
            response = await adapter.execute_evidence_request(request_with_awb, "mock_token")
            
            assert response.status == BusinessRealityStatus.EVIDENCE_AVAILABLE
            assert response.evidence_data["awb_no"] == "AWB123"
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert "AWB123" in args[0]
            assert kwargs["headers"]["Authorization"] == "Bearer mock_token"

@pytest.mark.asyncio
async def test_genuine_unknown_awb_or_empty_db(adapter, request_with_awb):
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "AWB_NOT_FOUND"}
        mock_get.return_value = mock_response
        
        response = await adapter.execute_evidence_request(request_with_awb, "mock_token")
        
        # We mapped 404 to EVIDENCE_UNAVAILABLE to avoid contaminating semantic tests while DB is empty
        assert response.status == BusinessRealityStatus.ENTITY_NOT_FOUND
        assert "genuinely does not exist" in response.execution_limitations[0].reason

@pytest.mark.asyncio
async def test_api_unavailable(adapter, request_with_awb):
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        response = await adapter.execute_evidence_request(request_with_awb, "mock_token")
        
        assert response.status == BusinessRealityStatus.EXECUTION_LIMITATION
        assert "returned HTTP 500" in response.execution_limitations[0].reason

@pytest.mark.asyncio
async def test_network_error(adapter, request_with_awb):
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.RequestError("Connection refused")
        
        response = await adapter.execute_evidence_request(request_with_awb, "mock_token")
        
        assert response.status == BusinessRealityStatus.EXECUTION_LIMITATION
        assert "network error" in response.execution_limitations[0].reason

