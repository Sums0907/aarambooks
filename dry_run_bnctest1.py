import asyncio
import os
import json
from src.infrastructure.adapters.postgres_sabaq import PostgresSabaqProvider
from src.infrastructure.adapters.catalog_cem_adapter import CatalogCemAdapter
from src.intelligence_domains.catalog_intelligence.orchestrator import CatalogIntelligenceOrchestrator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

class DummyResolver:
    def __init__(self, adapter):
        self.adapter = adapter
    def resolve(self, domain):
        return self.adapter

async def main():
    db_url = "postgresql://postgres:postgres@localhost:5434/aarambooks_brain_core_dev"
    engine = create_async_engine(db_url.replace("postgresql://", "postgresql+asyncpg://"))
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    sabaq_provider = PostgresSabaqProvider(session_factory=Session)
    cem_adapter = CatalogCemAdapter(db_url.replace("postgresql://", "postgresql+asyncpg://"))
    await cem_adapter._ensure_initialized()
    
    orch = CatalogIntelligenceOrchestrator(
        sabaq_provider=sabaq_provider,
        cem_resolver=DummyResolver(cem_adapter)
    )
    
    import sys
    sys.path.append(os.getcwd())
    from scripts.run_phase5b_benchmark import _run_sku_benchmark, verify_benchmark_skus, load_csv
    
    csv_rows = load_csv()
    skus = verify_benchmark_skus(csv_rows)
    bnc = next(s for s in skus if s["sku_id"] == "BNCTEST-1")
    
    # Get seeded parent
    sabaq_seeds_map = {"TLS-MP-CB-DBF": "d9fb1c54-b1dd-4ab4-8d2c-68d894eb5413"} # From previous execution output
    seeded_parents = {"TLS-MP-CB-DBF": "fe6dc6f2-d61d-4152-9e4b-b416a7558508"} # From previous execution output
    
    report = await _run_sku_benchmark(bnc, orch, cem_adapter, seeded_parents, sabaq_seeds_map)
    
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
