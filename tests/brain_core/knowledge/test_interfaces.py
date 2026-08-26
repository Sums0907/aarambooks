import pytest
from typing import List
from src.brain_core.knowledge.interfaces import KnowledgeProvider, KnowledgeQuery, KnowledgeResult

class MockKnowledgeProvider(KnowledgeProvider):
    async def search_knowledge(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        if query.domain == "inventory":
            return [KnowledgeResult(content="stock rules", source="wiki", confidence_score=0.9, metadata={})]
        return []

@pytest.mark.asyncio
async def test_knowledge_interfaces_can_be_mocked():
    provider = MockKnowledgeProvider()
    query = KnowledgeQuery(query_text="how does stock work", domain="inventory")
    
    results = await provider.search_knowledge(query)
    assert len(results) == 1
    assert results[0].source == "wiki"

def test_knowledge_models_are_frozen():
    query = KnowledgeQuery(query_text="test", domain="test")
    with pytest.raises(Exception):
        query.domain = "changed"
