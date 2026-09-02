"""
Universal AZM Ingestion Engine

Provides a generic framework for ingesting Business System semantic and schematic
public contracts into the AZM Persistent Database. It separates the mechanics
of DB persistence and idempotency from the domain-specific configurations.
"""
import sqlite3
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass

from src.azm.db import get_connection, execute_schema
from src.azm.config import AZM_DATABASE_URL
from src.azm.ingestion.ingestion_utils import (
    hash_content,
    is_already_ingested,
    start_ingestion_run,
    complete_ingestion_run,
    fail_ingestion_run,
    build_provenance,
    get_or_create_namespace,
    insert_concept,
    insert_aliases,
    insert_relationship,
    insert_schematic_ref,
    insert_schematic_attr,
    insert_attr_mapping,
    insert_external_mapping,
)


@dataclass
class AzmConceptDef:
    semantic_key: str
    concept_name: str
    concept_type: str
    definition: str
    source_element: str
    aliases: List[str]


@dataclass
class AzmRelationshipDef:
    source_key: str
    target_key: str
    relationship_type: str
    derivation_rule: str
    source_element: str


@dataclass
class AzmSchematicFieldDef:
    field_name: str
    field_type: str
    description: str
    is_derived: bool = False
    is_channel_field: bool = False
    mapped_concept_key: Optional[str] = None


@dataclass
class AzmSchematicViewDef:
    view_name: str
    description: str
    surface_type: str
    fields: List[AzmSchematicFieldDef]


@dataclass
class AzmExternalMappingDef:
    native_concept_key: str
    external_system: str
    external_key: str
    display_name: str


@dataclass
class AzmIngestionConfig:
    source_bs: str
    namespace_name: str
    namespace_classification: str
    namespace_description: str
    contract_version: str
    semantic_contract_content: str
    schematic_contract_content: str
    semantic_source_element: str
    schematic_source_element: str
    concepts: List[AzmConceptDef]
    relationships: List[AzmRelationshipDef]
    views: List[AzmSchematicViewDef]
    external_mappings: List[AzmExternalMappingDef]


class UniversalAzmIngester:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or AZM_DATABASE_URL

    def ingest(self, config: AzmIngestionConfig) -> dict:
        """
        Idempotent transactional ingestion of a Business System's contracts.
        """
        db_path = self.db_url.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        conn.isolation_level = None  # autocommit
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA journal_mode=WAL;")

        execute_schema(conn)

        semantic_hash = hash_content(config.semantic_contract_content)
        schematic_hash = hash_content(config.schematic_contract_content)
        combined_hash = hash_content(config.semantic_contract_content + config.schematic_contract_content)

        if is_already_ingested(conn, config.source_bs, "FULL", combined_hash):
            conn.close()
            return {
                "status": "SKIPPED",
                "run_id": None,
                "message": f"Namespace {config.namespace_name} already ingested (hash={combined_hash[:12]}…). No changes made.",
            }

        run_id = start_ingestion_run(
            conn, config.source_bs, "FULL", combined_hash, config.contract_version
        )

        try:
            conn.execute("BEGIN")

            # 1. Namespace
            ns_id = get_or_create_namespace(
                conn,
                name=config.namespace_name,
                classification=config.namespace_classification,
                description=config.namespace_description,
            )

            # 2. Semantic Concepts
            concept_ids = {}
            for c_def in config.concepts:
                prov_id = build_provenance(
                    conn, run_id,
                    source_bs=config.source_bs,
                    contract_type="SEMANTIC",
                    knowledge_kind="SOURCE_DECLARED",
                    contract_hash=semantic_hash,
                    contract_version=config.contract_version,
                    source_element=c_def.source_element,
                )
                cid = insert_concept(
                    conn,
                    namespace_id=ns_id,
                    semantic_key=c_def.semantic_key,
                    concept_name=c_def.concept_name,
                    concept_type=c_def.concept_type,
                    knowledge_kind="SOURCE_DECLARED",
                    provenance_id=prov_id,
                    definition=c_def.definition,
                )
                if c_def.aliases:
                    insert_aliases(conn, cid, c_def.aliases)
                concept_ids[c_def.semantic_key] = cid

            # 3. Derived Relationships
            for r_def in config.relationships:
                source_cid = concept_ids.get(r_def.source_key)
                target_cid = concept_ids.get(r_def.target_key)
                if not source_cid or not target_cid:
                    raise ValueError(f"Invalid relationship keys: {r_def.source_key} -> {r_def.target_key}")

                prov_id = build_provenance(
                    conn, run_id,
                    source_bs=config.source_bs,
                    contract_type="DERIVED",
                    knowledge_kind="AZM_DERIVED",
                    source_element=r_def.source_element,
                    derivation_rule=r_def.derivation_rule,
                    derivation_source_ids=[source_cid, target_cid],
                )
                insert_relationship(
                    conn,
                    source_concept_id=source_cid,
                    target_concept_id=target_cid,
                    relationship_type=r_def.relationship_type,
                    knowledge_kind="AZM_DERIVED",
                    provenance_id=prov_id,
                )

            # 4. Schematic References (Views)
            prov_schematic = build_provenance(
                conn, run_id,
                source_bs=config.source_bs,
                contract_type="SCHEMATIC",
                knowledge_kind="SOURCE_DECLARED",
                contract_hash=schematic_hash,
                contract_version=config.contract_version,
                source_element=config.schematic_source_element,
            )

            for v_def in config.views:
                ref_id = insert_schematic_ref(
                    conn, ns_id, v_def.view_name, v_def.surface_type, prov_schematic,
                    description=v_def.description,
                )

                for f_def in v_def.fields:
                    attr_id = insert_schematic_attr(
                        conn, ref_id, f_def.field_name, prov_schematic,
                        field_type=f_def.field_type,
                        description=f_def.description,
                        is_derived=1 if f_def.is_derived else 0,
                        is_channel_field=1 if f_def.is_channel_field else 0,
                    )

                    if f_def.mapped_concept_key:
                        cid = concept_ids.get(f_def.mapped_concept_key)
                        if cid:
                            insert_attr_mapping(
                                conn,
                                concept_id=cid,
                                schematic_attr_id=attr_id,
                                provenance_id=prov_schematic,
                                mapping_confidence="EXPLICIT",
                                knowledge_kind="SOURCE_DECLARED",
                            )

            # 5. External Mappings
            for m_def in config.external_mappings:
                cid = concept_ids.get(m_def.native_concept_key)
                if cid:
                    insert_external_mapping(
                        conn,
                        aaram_native_concept_id=cid,
                        external_system=m_def.external_system,
                        external_key=m_def.external_key,
                        provenance_id=prov_schematic,
                        external_display_name=m_def.display_name,
                    )

            complete_ingestion_run(conn, run_id)
            conn.execute("COMMIT")

            concepts_count = conn.execute("SELECT COUNT(*) FROM azm_concepts WHERE namespace_id=?", (ns_id,)).fetchone()[0]
            refs_count = conn.execute("SELECT COUNT(*) FROM azm_schematic_refs WHERE namespace_id=?", (ns_id,)).fetchone()[0]
            attrs_count = conn.execute(
                "SELECT COUNT(*) FROM azm_schematic_attrs sa JOIN azm_schematic_refs sr ON sa.schematic_ref_id=sr.id WHERE sr.namespace_id=?", (ns_id,)
            ).fetchone()[0]

            conn.close()
            return {
                "status": "COMPLETED",
                "run_id": run_id,
                "message": f"{config.namespace_name} namespace ingested successfully. Concepts: {concepts_count}, Views: {refs_count}, Attrs: {attrs_count}",
            }

        except Exception as exc:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            fail_ingestion_run(conn, run_id, str(exc))
            conn.close()
            return {
                "status": "FAILED",
                "run_id": run_id,
                "message": str(exc),
            }
