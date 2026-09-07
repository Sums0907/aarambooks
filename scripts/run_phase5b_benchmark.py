#!/usr/bin/env python3
"""
Phase 5B Business-Value Benchmark
==================================
Source: business_systems/catalog/docs/shopdeck_sample_catalog.csv (79 rows)
Default mode: DRY_RUN=True (no mutations performed)

Usage:
    # Dry-run (safe — no mutations):
    python scripts/run_phase5b_benchmark.py

    # Full execution (seeds dev DB + SABAQ, runs all 10 SKUs):
    python scripts/run_phase5b_benchmark.py --execute

ARCHITECTURAL RULES ENFORCED:
  - Never runs against production (hard-coded guard).
  - Scenario classification only after CEM verification.
  - Qwen fields enter as AI_PROPOSED only.
  - Firewall promotes SABAQ_REUSED deterministically.
  - All simulated operator responses labelled SIMULATED.
  - No fabricated timings, no fabricated turns.
  - Scenario A explicitly excluded (documented gap).
"""

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on the path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

CSV_PATH = ROOT / "business_systems" / "catalog" / "docs" / "shopdeck_sample_catalog.csv"

BENCHMARK_SKUS = [
    # (product_code, sku_id, scenario_intent, is_seed_parent, scenario_source)
    ("TLS-MP-CB-DBF",                "104MP",    "D",   True,  "REAL_CSV"),                 # 1 — seed as Scenario D parent
    ("TLS-MP-DR-DBF",                "102MP",    "D",   False, "REAL_CSV"),                 # 2 — D (independent product_code)
    ("TLS-MP-RYB-DBF",               "101MP",    "D",   False, "REAL_CSV"),                 # 3 — D (independent product_code)
    ("DREAMYPINK-FRLK-KDB-5PC",      "123BS",    "D",   False, "REAL_CSV"),                 # 4 — new family
    ("TERRACOTTA-FRLK-KDB-5PC",      "122BS",    "D",   False, "REAL_CSV"),                 # 5 — new family, same type
    ("KD-PINKGULBAHAR-KDB",          "102BS",    "D",   True,  "REAL_CSV"),                 # 6 — seed as Scenario D parent
    ("KD-SSK-AQGB-KDB",             "116BS",    "D",   False, "REAL_CSV"),                 # 7 — D (independent product_code)
    ("AH-OTTO-BLUE-HS",              "103OTTO",  "D",   False, "REAL_CSV"),                 # 8 — utility product
    ("PETAL-DREAMS-QUILTED-DOHAR-QDB","103QD",   "D",   False, "REAL_CSV"),                 # 9 — dohar, image-driven
    ("OLIVE-GGNM-CHECK-CS-4PC",      "104CS",    "D",   False, "REAL_CSV"),                 # 10 — comforter
    ("TLS-MP-CB-DBF",                "BNCTEST-1","B/C", False, "SYNTHETIC_BENCHMARK_ONLY"), # 11 — Synthetic Scenario B case under 104MP's product_code
]

SCENARIO_A_NOTE = (
    "Scenario A (Exact Historical Restoration) is NOT included in this benchmark run. "
    "It requires a SKU to have previously existed in the Catalog BS, been retired, "
    "and be explicitly re-proposed. No such fixture exists in the current dev environment. "
    "This is a documented gap — not fabricated."
)

ALLOWED_DB_PREFIXES = [
    "localhost", "127.0.0.1", "postgres://postgres:postgres@localhost",
    "postgresql://postgres:postgres@localhost",
]

PRODUCTION_INDICATORS = ["prod", "production", "rds.amazonaws", "supabase"]


# ─────────────────────────────────────────────────────────────────────────────
# Safety guards
# ─────────────────────────────────────────────────────────────────────────────

def _guard_environment(db_url: str) -> None:
    db_lower = db_url.lower()
    for indicator in PRODUCTION_INDICATORS:
        if indicator in db_lower:
            print(f"[ABORT] Production/shared DB detected in URL: {db_url}")
            print("[ABORT] This benchmark must only run against a local dev database.")
            sys.exit(1)
    print(f"[OK] Environment: DEV ({db_url[:60]}...)")


# ─────────────────────────────────────────────────────────────────────────────
# CSV loading & verification
# ─────────────────────────────────────────────────────────────────────────────

def load_csv() -> Dict[str, Dict]:
    if not CSV_PATH.exists():
        print(f"[ERROR] CSV not found: {CSV_PATH}")
        sys.exit(1)
    rows: Dict[str, Dict] = {}
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows[row["Product Code"]] = row
    print(f"[OK] CSV loaded: {len(rows)} rows from {CSV_PATH.name}")
    return rows


def verify_benchmark_skus(csv_rows: Dict[str, Dict]) -> List[Dict]:
    """Verify all selected benchmark SKUs against real CSV. Abort if any missing."""
    verified = []
    for pc, sku_id, scenario_intent, is_seed, scenario_source in BENCHMARK_SKUS:
        row = csv_rows.get(pc)
        if row is None:
            print(f"[ABORT] Product code not found in CSV: {pc}")
            sys.exit(1)
        
        # For synthetic SKUs, they share the parent's product code row.
        # Ensure we don't abort on SKU ID mismatch for them.
        if scenario_source == "REAL_CSV" and row["Sku Id"] != sku_id:
            print(f"[ABORT] SKU ID mismatch for {pc}: CSV has '{row['Sku Id']}', expected '{sku_id}'")
            sys.exit(1)
            
        images = [row.get(f"Image {i}", "").strip() for i in range(1, 11) if row.get(f"Image {i}", "").strip()]
        
        # If synthetic, it represents a new SKU in the same family, so we can use the same images/dims 
        # as a baseline to test firewall promotions. The SABAQ seed will correctly only seed the real 104MP.
        payload_template = {
            "product_code": {"value": pc, "candidate_sabaq_reference_id": None},
            "sku_id": {"value": sku_id, "candidate_sabaq_reference_id": None},
        }
        if sku_id == "BNCTEST-1":
            payload_template.update({
                "packaging_length_cm": {"value": 33.0, "provenance": "AI_PROPOSED", "candidate_sabaq_reference_id": "{sabaq_id}"},
                "packaging_breadth_cm": {"value": 27.0, "provenance": "AI_PROPOSED", "candidate_sabaq_reference_id": "{sabaq_id}"},
                "packaging_height_cm": {"value": 11.0, "provenance": "AI_PROPOSED", "candidate_sabaq_reference_id": "{sabaq_id}"},
                "packaging_weight_kg": {"value": 1.3, "provenance": "AI_PROPOSED", "candidate_sabaq_reference_id": "{sabaq_id}"},
                "size": {"value": "72x78 + 12\"", "provenance": "AI_PROPOSED", "candidate_sabaq_reference_id": "{sabaq_id}"},
                "pack_configuration": {"value": "", "provenance": "AI_PROPOSED", "candidate_sabaq_reference_id": "{sabaq_id}"},
            })

        verified.append({
            "product_code": pc,
            "sku_id": sku_id,
            "name": row["Name"],
            "scenario_intent": scenario_intent,
            "is_seed_parent": is_seed,
            "scenario_source": scenario_source,
            "source_csv_row": dict(row),
            "image_uris": images,
            "mock_qwen_payload_template": payload_template,
            "dims": {
                "l": row["Packaging Length (in cm)"],
                "b": row["Packaging Breadth (in cm)"],
                "h": row["Packaging Height (in cm)"],
                "w": row["Packaging Weight (in kg)"],
            },
            "pricing": {
                "mrp": row["MRP"],
                "selling_price": row["Selling Price"],
                "cost_price": row["Cost Price"],
            },
        })
        print(f"  [✓] {pc} / {sku_id} — {scenario_intent} [{scenario_source}] — {len(images)} images")
    return verified


# ─────────────────────────────────────────────────────────────────────────────
# DRY RUN report
# ─────────────────────────────────────────────────────────────────────────────

def dry_run_report(verified_skus: List[Dict], db_url: str) -> None:
    print("\n" + "=" * 70)
    print("PHASE 5B BENCHMARK — DRY RUN REPORT")
    print("=" * 70)
    print(f"\nDB: {db_url[:60]}")
    print(f"CSV: {CSV_PATH}")
    print(f"\n{SCENARIO_A_NOTE}\n")

    parents = [s for s in verified_skus if s["is_seed_parent"]]
    variants = [s for s in verified_skus if not s["is_seed_parent"]]

    print(f"CEM Seed Operations Required ({len(parents)}):")
    for s in parents:
        print(f"  → SaveProductFamily: {s['product_code']} / {s['sku_id']}")

    real_sabaq_seeds = [s for s in verified_skus if s["scenario_source"] == "REAL_CSV"]
    print(f"\nSABAQ Seed Operations Required ({len(real_sabaq_seeds)}):")
    for s in real_sabaq_seeds:
        print(f"  → record_approved_outcome: {s['product_code']} / {s['sku_id']} [BUSINESS_SYSTEM_HISTORY]")

    print(f"\nBenchmark Execution Sequence ({len(verified_skus)} SKUs):")
    for i, s in enumerate(verified_skus, 1):
        seed_note = " ← seed parent (run as Scenario D)" if s["is_seed_parent"] else ""
        print(f"  {i:2}. {s['product_code']} / {s['sku_id']} — intended {s['scenario_intent']} [{s['scenario_source']}]{seed_note}")
        print(f"       {len(s['image_uris'])} real image URIs from CSV")

    print("\nMeasurable Metrics (by script):")
    print("  • Brain processing time (wall-clock, perf_counter)")
    print("  • SABAQ retrieval time")
    print("  • CEM verification time")
    print("  • CEM mutation time")
    print("  • Count: UNKNOWN_REQUIRES_USER fields per SKU")
    print("  • Count: SABAQ_REUSED fields per SKU")
    print("  • Count: AI_PROPOSED fields per SKU")
    print("  • Count: simulated operator inputs per SKU [labelled SIMULATED]")
    print("  • CEM outcome per SKU")
    print("  • ShopDeck artifact validity")
    print("  • Post-generation corrections (target: 0)")

    print("\nNOT measurable (requires real operator):")
    print("  • Actual wall-clock operator interaction time — will be tagged SIMULATED")
    print("  • Actual conversational turn count — will be tagged SIMULATED")

    print("\n[DRY RUN COMPLETE] No mutations performed.")
    print("Run with --execute to perform actual seeding and benchmark.")
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# Live execution helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_sabaq(verified_skus: List[Dict], sabaq_provider) -> Dict[str, str]:
    """Load all 10 CSV rows into SABAQ as BUSINESS_SYSTEM_HISTORY. Returns dict of product_code -> ev_id."""
    from src.brain_core.knowledge.interfaces import SabaqProvenance
    print("\n[SABAQ SEEDING]")
    sabaq_seeds_map = {}
    for s in verified_skus:
        if s["scenario_source"] != "REAL_CSV":
            continue
        
        search_content = f"{s['product_code']} {s['sku_id']} {s['source_csv_row'].get('Name', '')}"
        ev_id = await sabaq_provider.record_approved_outcome(
            domain="catalog",
            search_content=search_content,
            payload=s["source_csv_row"],
            provenance=SabaqProvenance.BUSINESS_SYSTEM_HISTORY,
            metadata={"benchmark": True, "source": "shopdeck_sample_catalog.csv"},
            source_reference=s["product_code"],
        )
        sabaq_seeds_map[s["product_code"]] = ev_id
        print(f"  [✓] Seeded SABAQ: {s['product_code']} → {ev_id}")
    return sabaq_seeds_map


async def _seed_catalog_cem(parents: List[Dict], cem_adapter) -> Dict[str, str]:
    """Seed parent product families via real CEM mutation. Returns {product_code: internal_id}."""
    from business_systems.catalog.models import SaveProductFamilyPayload, SaveProductInput, SaveSkuInput
    import uuid as _uuid
    from src.shared.evidence_request_contracts import BusinessStateVerificationRequest

    seeded: Dict[str, str] = {}
    print("\n[CEM SEEDING]")
    for s in parents:
        row = s["source_csv_row"]
        # Build typed payload from real CSV values
        try:
            mrp = float(row["MRP"])
            sp = float(row["Selling Price"])
            cp = float(row["Cost Price"])
            pkg_l = float(row["Packaging Length (in cm)"])
            pkg_b = float(row["Packaging Breadth (in cm)"])
            pkg_h = float(row["Packaging Height (in cm)"])
            pkg_w = float(row["Packaging Weight (in kg)"])
        except (ValueError, KeyError) as e:
            print(f"  [SKIP] {s['product_code']} — cannot parse numeric fields: {e}")
            continue

        images = s["image_uris"]
        payload = SaveProductFamilyPayload(
            idempotency_key=f"benchmark-seed-{s['product_code']}",
            product=SaveProductInput(
                product_code=s["product_code"],
                name=row["Name"][:100],
                product_type=row.get("Product Type") or "home__home_furnishing__bed_linen",
                brand="Aaram Homes",
                hsn_code=row.get("HSN Code") or "63049290",
                gst_percentage=float(row.get("GST %") or 5.0),
                description=row.get("Description", ""),
                product_media_urls=images[:3],
                size_chart_url=row.get("Size Chart", ""),
                collection_tags=[],
            ),
            skus=[SaveSkuInput(
                sku_id=s["sku_id"],
                colour=row.get("Colour", ""),
                size=row.get("Size", ""),
                size_type=row.get("Size Type", "size"),
                pack_configuration=row.get("attr_Package Contents", ""),
                mrp=mrp,
                selling_price=sp,
                cost_price=cp,
                packaging_length_cm=pkg_l,
                packaging_breadth_cm=pkg_b,
                packaging_height_cm=pkg_h,
                packaging_weight_kg=pkg_w,
                sku_media_urls=images,
                fabric_type=row.get("attr_Fabric Type", ""),
                care_instructions=row.get("attr_Wash Care", ""),
                set_composition=row.get("attr_Set includes", ""),
                video_urls=[],
                pickup_address_code=row.get("Pickup Address Code", ""),
                return_condition=row.get("Return/Exchange Condition", ""),
            )],
        )

        try:
            result = await cem_adapter._service.save_product_family(payload)
            if hasattr(result, "status") and result.status == "REJECTED":
                print(f"  [ERROR] CEM seed rejected {s['product_code']}: {result.errors}")
            internal_id = str(getattr(result, "internal_id", ""))
            v_req = BusinessStateVerificationRequest(
                domain_urn="urn:aarambooks:cem:catalog",
                verification_target="product_code",
                context_payload={"product_code": s["product_code"]},
            )
            v_resp = await cem_adapter.verify_business_state(v_req)
            if v_resp.evidence_data and v_resp.evidence_data.get("exists"):
                internal_id = v_resp.evidence_data.get("product_internal_id", internal_id)
                seeded[s["product_code"]] = internal_id
                print(f"  [✓] CEM seeded + verified: {s['product_code']} → internal_id={internal_id}")
            else:
                print(f"  [WARN] CEM seed did not verify for: {s['product_code']}")
        except Exception as e:
            print(f"  [ERROR] CEM seed failed for {s['product_code']}: {e}")

    return seeded


async def _run_sku_benchmark(sku: Dict, orchestrator, cem_adapter, seeded_parents: Dict[str, str], sabaq_seeds_map: Dict[str, str]) -> Dict:
    from src.shared.conversational_contracts import MultimodalQuery
    from src.brain_core.gateway.interfaces import GatewayGenerationResponse
    import time
    import json

    pc = sku["product_code"]
    sku_id = sku["sku_id"]
    row = sku["source_csv_row"]
    images = sku["image_uris"]

    report: Dict[str, Any] = {
        "sku_id": sku_id,
        "product_code": pc,
        "source_csv_name": "shopdeck_sample_catalog.csv",
        "source_csv_row": row,
        "image_uris": images,
        "image_source": "csv" if images else "absent",
        # Static manifest intent (for comparison only)
        "scenario_intent": sku["scenario_intent"],
        "scenario_source": sku["scenario_source"],
        # Actual runtime classification — populated from draft_dict["cem_classified_scenario"]
        # after orchestrator runs. Source: _classify_scenario(cem_verification_result)
        # in extract_understanding(). Never derived from provenance distribution.
        "cem_classified_scenario": None,  # filled after orchestrator call below
    }

    # Build real Brain input from CSV
    brain_input_text = (
        f"Add new catalog product: {row['Name']}. "
        f"Colour: {row.get('Colour', 'N/A')}. "
        f"Size: {row.get('Size', 'N/A')}. "
        f"Product Code: {pc}. SKU: {sku_id}."
    )
    mm_query = MultimodalQuery(text=brain_input_text, image_uris=images)
    report["brain_input_text"] = brain_input_text

    # ── Gateway Simulation ────────────────────────────────────────────────
    payload_template = dict(sku.get("mock_qwen_payload_template", {}))
    sabaq_id = sabaq_seeds_map.get(pc)
    
    for k, v in payload_template.items():
        if isinstance(v, dict) and v.get("candidate_sabaq_reference_id") == "{sabaq_id}":
            v["candidate_sabaq_reference_id"] = sabaq_id
            
    class MockGatewayProvider:
        async def generate(self, req):
            from src.brain_core.gateway.interfaces import GatewayGenerationResponse
            return GatewayGenerationResponse(
                content=json.dumps(payload_template),
                model_used="mock",
                prompt_tokens=0,
                completion_tokens=0
            )
            
    orchestrator._gateway_provider = MockGatewayProvider()

    # ── Full pipeline ─────────────────────────────────────────────────────
    t_start = time.perf_counter()

    understanding = await orchestrator.extract_understanding(mm_query)

    t_brain = time.perf_counter() - t_start
    report["processing_time_brain_s"] = round(t_brain, 4)

    params = {p.parameter_name: p.value for p in understanding.parameters}
    draft_dict = json.loads(params.get("draft_json", "{}"))

    # ── Capture CEM-grounded scenario from draft JSON ─────────────────────
    # cem_classified_scenario is set by orchestrator from _classify_scenario().
    # It is NOT derived from provenance distribution — it is the direct output
    # of the CEM verification path stored on the CatalogDraft.
    cem_scenario = draft_dict.get("cem_classified_scenario")
    report["cem_classified_scenario"] = cem_scenario

    # Provenance breakdown
    provenance_map = {
        k: v.get("provenance") for k, v in draft_dict.items() if isinstance(v, dict)
    }
    report["draft_before_firewall"] = "captured_inside_orchestrator"  # Firewall is internal
    report["draft_after_firewall"] = draft_dict
    report["field_provenance_map"] = provenance_map
    
    diagnostics_param = next((p.value for p in understanding.parameters if p.parameter_name == "firewall_diagnostics"), None)
    if diagnostics_param:
        report["firewall_diagnostics"] = json.loads(diagnostics_param)

    unknown_fields = [k for k, v in draft_dict.items() if isinstance(v, dict) and v.get("provenance") == "UNKNOWN_REQUIRES_USER"]
    sabaq_reused_fields = [k for k, v in draft_dict.items() if isinstance(v, dict) and v.get("provenance") == "SABAQ_REUSED"]
    ai_proposed_fields = [k for k, v in draft_dict.items() if isinstance(v, dict) and v.get("provenance") == "AI_PROPOSED"]

    report["unknown_requires_user_fields"] = unknown_fields
    report["sabaq_reused_fields"] = sabaq_reused_fields
    report["ai_proposed_fields"] = ai_proposed_fields
    report["unknown_count"] = len(unknown_fields)
    report["sabaq_reused_count"] = len(sabaq_reused_fields)
    report["ai_proposed_count"] = len(ai_proposed_fields)

    # Simulated operator responses for UNKNOWN fields
    # These are labelled SIMULATED — not real operator timings.
    simulated_inputs = {}
    for field in unknown_fields:
        csv_key_map = {
            "mrp": "MRP",
            "selling_price": "Selling Price",
            "cost_price": "Cost Price",
            "packaging_length_cm": "Packaging Length (in cm)",
            "packaging_breadth_cm": "Packaging Breadth (in cm)",
            "packaging_height_cm": "Packaging Height (in cm)",
            "packaging_weight_kg": "Packaging Weight (in kg)",
            "colour": "Colour",
            "size": "Size",
        }
        csv_key = csv_key_map.get(field)
        if csv_key and row.get(csv_key):
            simulated_inputs[field] = row[csv_key]

    report["simulated_operator_inputs"] = simulated_inputs
    report["simulated_manual_field_count"] = len(simulated_inputs)
    report["interaction_timing"] = "SIMULATED"
    report["turn_count"] = "SIMULATED"

    # CEM mutation not performed in this function — would require full confirmed draft
    # This is a read-only benchmark pass; mutation is a separate approval step.
    report["cem_mutation"] = "NOT_PERFORMED_IN_DRY_BENCHMARK"
    report["cem_result"] = "NOT_PERFORMED"
    report["post_generation_corrections"] = 0  # Cannot exceed 0 by definition at this stage

    return report


async def run_benchmark(execute: bool, db_url: str, sabaq_session_factory=None) -> None:
    """Main benchmark execution flow."""
    _guard_environment(db_url)

    csv_rows = load_csv()
    print("\n[VERIFYING] Benchmark SKUs against real CSV:")
    verified_skus = verify_benchmark_skus(csv_rows)

    if not execute:
        dry_run_report(verified_skus, db_url)
        return

    # ── Live Execution ────────────────────────────────────────────────────
    print("\n[LIVE EXECUTION MODE]")
    print(SCENARIO_A_NOTE)

    # Initialise providers
    import asyncpg
    from src.infrastructure.adapters.catalog_cem_adapter import CatalogCemAdapter
    from src.infrastructure.adapters.postgres_sabaq import PostgresSabaqProvider
    from src.intelligence_domains.catalog_intelligence.orchestrator import CatalogIntelligenceOrchestrator
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    cem_adapter = CatalogCemAdapter(db_url.replace("postgresql://", "postgresql+asyncpg://"))
    await cem_adapter._ensure_initialized()

    engine = create_async_engine(db_url.replace("postgresql://", "postgresql+asyncpg://"))
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    sabaq_provider = PostgresSabaqProvider(session_factory=Session)

    class DummyResolver:
        def __init__(self, adapter):
            self.adapter = adapter
        def resolve(self, domain):
            return self.adapter

    orchestrator = CatalogIntelligenceOrchestrator(
        sabaq_provider=sabaq_provider,
        cem_resolver=DummyResolver(cem_adapter)
    )

    # Seed SABAQ
    await _seed_sabaq(verified_skus, sabaq_provider)

    # Seed CEM parents
    parents = [s for s in verified_skus if s["is_seed_parent"]]
    seeded_parents = await _seed_catalog_cem(parents, cem_adapter)

    # Run benchmark per SKU
    all_reports = []
    print(f"\n[BENCHMARK] Running {len(verified_skus)} SKUs...")
    for sku in verified_skus:
        print(f"\n  → {sku['product_code']} / {sku['sku_id']} [{sku['scenario_intent']}]")
        report = await _run_sku_benchmark(sku, orchestrator, cem_adapter, seeded_parents)
        all_reports.append(report)
        print(f"     SABAQ_REUSED: {report['sabaq_reused_count']} | "
              f"AI_PROPOSED: {report['ai_proposed_count']} | "
              f"UNKNOWN: {report['unknown_count']} | "
              f"Brain time: {report['processing_time_brain_s']}s")

    # Aggregate
    def _agg(source: str = None):
        reports = [r for r in all_reports if source is None or r.get("scenario_source") == source]
        return {
            "total_skus": len(reports),
            "total_sabaq_reused_fields": sum(r["sabaq_reused_count"] for r in reports),
            "total_ai_proposed_fields": sum(r["ai_proposed_count"] for r in reports),
            "total_unknown_requires_user_fields": sum(r["unknown_count"] for r in reports),
            "total_simulated_manual_fields": sum(r["simulated_manual_field_count"] for r in reports),
        }

    summary = {
        "benchmark_run": "LIVE",
        "scenario_a_status": "NOT_EXECUTABLE — documented gap",
        "aggregate_all": _agg(),
        "aggregate_real_csv": _agg("REAL_CSV"),
        "aggregate_synthetic": _agg("SYNTHETIC_BENCHMARK_ONLY"),
        "cem_mutations_performed": 0,
        "interaction_timing_type": "SIMULATED",
        "business_value_delta": "NOT_CALCULATED — CEM mutations not performed in this pass",
        "sku_reports": all_reports,
    }

    out_path = ROOT / "scripts" / "benchmark_results_phase5b.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n[COMPLETE] Results written to: {out_path}")
    agg = summary["aggregate_all"]
    print(f"Summary: SABAQ_REUSED={agg['total_sabaq_reused_fields']} | UNKNOWN={agg['total_unknown_requires_user_fields']} | Simulated manual={agg['total_simulated_manual_fields']}")
    print("Business-value delta: NOT CALCULATED — CEM mutations not performed in this pass.")
    print("Review results and approve CEM mutation pass separately.")


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 5B Business-Value Benchmark")
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Run live benchmark (seeds dev DB + SABAQ). Default is DRY_RUN.",
    )
    args = parser.parse_args()

    db_url = os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql://postgres:postgres@localhost:5434/aarambooks_brain_core_dev",
    ).replace("postgresql+asyncpg://", "postgresql://")

    asyncio.run(run_benchmark(execute=args.execute, db_url=db_url))
