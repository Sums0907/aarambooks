import re
import os

# 1. Patch tests/intelligence_domains/ndr/test_ndr_orchestration.py
fpath = "tests/intelligence_domains/ndr/test_ndr_orchestration.py"
with open(fpath, "r") as f:
    content = f.read()

# Delete test_ndr_execute_read_query_text_to_sql
content = re.sub(r'@pytest\.mark\.asyncio\nasync def test_ndr_execute_read_query_text_to_sql.*?(?=@pytest\.mark\.asyncio\nasync def test_ndr_rabta_end_to_end_conversational_routing)', '', content, flags=re.DOTALL)

# Update test_ndr_rabta_end_to_end_conversational_routing
# Remove mock_sql_engine from signature
content = content.replace(
    "async def test_ndr_rabta_end_to_end_conversational_routing(mock_gateway, mock_memory, mock_sql_engine, mock_azm_provider):",
    "async def test_ndr_rabta_end_to_end_conversational_routing(mock_gateway, mock_memory, mock_azm_provider):"
)
# Remove AsyncSessionLocal patching block
block_to_remove = """    from unittest.mock import patch
    
    # Patch the database session specifically for this test
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings().all.return_value = [{"query_executed": "SELECT * FROM public.vw_shopdeck_shipment_ndr_reports", "status": "simulated_read"}]
    mock_session.execute.return_value = mock_result
    
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    
    with patch("src.infrastructure.database.AsyncSessionLocal", mock_session_local):
        ndr_orch = NDRIntelligenceOrchestrator(
            gateway=mock_gateway,
            knowledge=AsyncMock(),
            memory=mock_memory,
            sql_engine=mock_sql_engine,
            azm_provider=mock_azm_provider
        )"""

replacement = """    ndr_orch = NDRIntelligenceOrchestrator(
        gateway=mock_gateway,
        knowledge=AsyncMock(),
        memory=mock_memory,
        azm_provider=mock_azm_provider
    )"""

content = content.replace(block_to_remove, replacement)

# Remove any remaining sql_engine=mock_sql_engine in this file
content = content.replace("            sql_engine=mock_sql_engine,\n", "")
content = content.replace("        sql_engine=mock_sql_engine,\n", "")

with open(fpath, "w") as f:
    f.write(content)


# 2. Patch tests/intelligence_domains/ndr/test_ndr_real_integration.py
fpath = "tests/intelligence_domains/ndr/test_ndr_real_integration.py"
with open(fpath, "r") as f:
    content = f.read()

# Remove mock_sql_engine fixture
content = re.sub(r'@pytest\.fixture\ndef mock_sql_engine\(\).*?return engine\n\n', '', content, flags=re.DOTALL)

# Update test_real_ndr_query_path
content = content.replace(
    "async def test_real_ndr_query_path(mock_gateway, mock_memory, mock_sql_engine, mock_azm_provider):",
    "async def test_real_ndr_query_path(mock_gateway, mock_memory, mock_azm_provider):"
)
content = content.replace("        sql_engine=mock_sql_engine,\n", "")

with open(fpath, "w") as f:
    f.write(content)

# 3. Patch tests/test_end_to_end_ndr.py
fpath = "tests/test_end_to_end_ndr.py"
with open(fpath, "r") as f:
    content = f.read()

# Since we don't know the exact content of test_end_to_end_ndr.py, let's fix the sql_engine reference in it if it has one.
# It probably initializes NDRIntelligenceOrchestrator or uses the fixture.
content = content.replace("sql_engine=mock_sql_engine,", "")
content = content.replace("sql_engine=AsyncMock(),", "")
content = content.replace("mock_sql_engine, ", "")
content = content.replace("mock_sql_engine,", "")
content = content.replace(", mock_sql_engine", "")
content = content.replace("mock_sql_engine", "None") # Just in case

# Make sure we don't pass sql_engine to NDRIntelligenceOrchestrator
content = re.sub(r'\s*sql_engine=[^,]+,?', '', content)

with open(fpath, "w") as f:
    f.write(content)

