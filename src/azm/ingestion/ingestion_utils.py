"""
AZM Ingestion Utilities

Shared utilities for the ingestion pipeline:
  - UUID generation
  - SHA-256 contract hashing
  - Idempotency checks (has this contract been successfully ingested?)
  - Provenance row builder
  - ISO-8601 UTC timestamp

AZM INVARIANT: These utilities never read from Business System databases.
They operate on contracts (markdown text, SQL files) and write to the AZM DB only.
"""
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional, List


def new_uuid() -> str:
    """Generate a new AZM UUID (text form, lowercase)."""
    return str(uuid.uuid4())


def utcnow() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def hash_content(content: str) -> str:
    """Return SHA-256 hex digest of the given text content."""
    return hashlib.sha256(content.encode("utf-8")).digest().hex()


def is_already_ingested(
    conn: sqlite3.Connection,
    source_bs: str,
    contract_type: str,
    contract_hash: str,
) -> bool:
    """
    Return True if a COMPLETED ingestion run already exists for this
    (source_bs, contract_type, contract_hash) combination.
    Used to enforce idempotency: same contract hash → skip.
    """
    cursor = conn.execute(
        """
        SELECT id FROM azm_ingestion_runs
        WHERE source_bs = ?
          AND contract_type = ?
          AND contract_hash = ?
          AND status = 'COMPLETED'
        LIMIT 1
        """,
        (source_bs, contract_type, contract_hash),
    )
    return cursor.fetchone() is not None


def start_ingestion_run(
    conn: sqlite3.Connection,
    source_bs: str,
    contract_type: str,
    contract_hash: str,
    contract_version: Optional[str] = None,
) -> str:
    """
    Insert a new RUNNING ingestion run. Returns the run UUID.
    """
    run_id = new_uuid()
    now = utcnow()
    conn.execute(
        """
        INSERT INTO azm_ingestion_runs
            (id, source_bs, contract_type, contract_hash, contract_version,
             status, started_at)
        VALUES (?, ?, ?, ?, ?, 'RUNNING', ?)
        """,
        (run_id, source_bs, contract_type, contract_hash, contract_version, now),
    )
    return run_id


def complete_ingestion_run(conn: sqlite3.Connection, run_id: str) -> None:
    conn.execute(
        "UPDATE azm_ingestion_runs SET status='COMPLETED', completed_at=? WHERE id=?",
        (utcnow(), run_id),
    )


def fail_ingestion_run(conn: sqlite3.Connection, run_id: str, error: str) -> None:
    conn.execute(
        "UPDATE azm_ingestion_runs SET status='FAILED', completed_at=?, error_message=? WHERE id=?",
        (utcnow(), str(error)[:2000], run_id),
    )


def build_provenance(
    conn: sqlite3.Connection,
    run_id: str,
    source_bs: str,
    contract_type: str,
    knowledge_kind: str,
    contract_hash: Optional[str] = None,
    contract_version: Optional[str] = None,
    source_element: Optional[str] = None,
    derivation_rule: Optional[str] = None,
    derivation_source_ids: Optional[List[str]] = None,
) -> str:
    """
    Insert an azm_provenance row and return its UUID.
    Every knowledge assertion must reference one provenance row.
    """
    prov_id = new_uuid()
    conn.execute(
        """
        INSERT INTO azm_provenance
            (id, ingestion_run_id, source_bs, contract_type,
             contract_hash, contract_version, source_element,
             knowledge_kind, derivation_rule, derivation_source_ids,
             created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prov_id, run_id, source_bs, contract_type,
            contract_hash, contract_version, source_element,
            knowledge_kind,
            derivation_rule,
            json.dumps(derivation_source_ids) if derivation_source_ids else None,
            utcnow(),
        ),
    )
    return prov_id


def get_or_create_namespace(
    conn: sqlite3.Connection,
    name: str,
    classification: str,
    description: Optional[str] = None,
) -> str:
    """
    Return the UUID of the namespace, creating it if it does not yet exist.
    """
    cursor = conn.execute(
        "SELECT id FROM azm_namespaces WHERE name = ?", (name,)
    )
    row = cursor.fetchone()
    if row:
        return row["id"]

    ns_id = new_uuid()
    conn.execute(
        """
        INSERT INTO azm_namespaces (id, name, classification, description, lifecycle, created_at)
        VALUES (?, ?, ?, ?, 'ACTIVE', ?)
        """,
        (ns_id, name, classification, description, utcnow()),
    )
    return ns_id


def get_concept_id_by_semantic_key(
    conn: sqlite3.Connection, semantic_key: str
) -> Optional[str]:
    """Return AZM UUID for a concept by its semantic key, or None."""
    cursor = conn.execute(
        "SELECT id FROM azm_concepts WHERE semantic_key = ? AND lifecycle = 'ACTIVE'",
        (semantic_key,),
    )
    row = cursor.fetchone()
    return row["id"] if row else None


def insert_concept(
    conn: sqlite3.Connection,
    namespace_id: str,
    semantic_key: str,
    concept_name: str,
    concept_type: str,
    knowledge_kind: str,
    provenance_id: str,
    definition: Optional[str] = None,
    capability_urn: Optional[str] = None,
    capability_constraints: Optional[List[str]] = None,
) -> str:
    """Insert one concept row. Returns its AZM UUID."""
    concept_id = new_uuid()
    conn.execute(
        """
        INSERT INTO azm_concepts
            (id, semantic_key, namespace_id, concept_name, concept_type,
             definition, knowledge_kind, version, lifecycle,
             capability_urn, capability_constraints, provenance_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'ACTIVE', ?, ?, ?, ?)
        """,
        (
            concept_id, semantic_key, namespace_id, concept_name, concept_type,
            definition, knowledge_kind,
            capability_urn,
            json.dumps(capability_constraints) if capability_constraints else None,
            provenance_id,
            utcnow(),
        ),
    )
    return concept_id



def insert_aliases(
    conn: sqlite3.Connection, concept_id: str, aliases: List[str]
) -> None:
    now = utcnow()
    for alias in aliases:
        conn.execute(
            """
            INSERT INTO azm_aliases (id, concept_id, alias, lifecycle, created_at)
            VALUES (?, ?, ?, 'ACTIVE', ?)
            """,
            (new_uuid(), concept_id, alias, now),
        )


def insert_relationship(
    conn: sqlite3.Connection,
    source_concept_id: str,
    target_concept_id: str,
    relationship_type: str,
    knowledge_kind: str,
    provenance_id: str,
) -> str:
    rel_id = new_uuid()
    conn.execute(
        """
        INSERT INTO azm_relationships
            (id, source_concept_id, target_concept_id, relationship_type,
             knowledge_kind, lifecycle, provenance_id, created_at)
        VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
        """,
        (rel_id, source_concept_id, target_concept_id, relationship_type,
         knowledge_kind, provenance_id, utcnow()),
    )
    return rel_id


def insert_schematic_ref(
    conn: sqlite3.Connection,
    namespace_id: str,
    ref_name: str,
    surface_type: str,
    provenance_id: str,
    description: Optional[str] = None,
) -> str:
    ref_id = new_uuid()
    conn.execute(
        """
        INSERT INTO azm_schematic_refs
            (id, namespace_id, ref_name, surface_type, description,
             knowledge_kind, version, lifecycle, provenance_id, created_at)
        VALUES (?, ?, ?, ?, ?, 'SOURCE_DECLARED', 1, 'ACTIVE', ?, ?)
        """,
        (ref_id, namespace_id, ref_name, surface_type, description, provenance_id, utcnow()),
    )
    return ref_id


def insert_schematic_attr(
    conn: sqlite3.Connection,
    schematic_ref_id: str,
    field_name: str,
    provenance_id: str,
    field_type: Optional[str] = None,
    description: Optional[str] = None,
    is_derived: int = 0,
    is_channel_field: int = 0,
) -> str:
    attr_id = new_uuid()
    conn.execute(
        """
        INSERT INTO azm_schematic_attrs
            (id, schematic_ref_id, field_name, field_type, description,
             is_derived, is_channel_field, knowledge_kind, version,
             lifecycle, provenance_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'SOURCE_DECLARED', 1, 'ACTIVE', ?, ?)
        """,
        (attr_id, schematic_ref_id, field_name, field_type, description,
         is_derived, is_channel_field, provenance_id, utcnow()),
    )
    return attr_id


def insert_attr_mapping(
    conn: sqlite3.Connection,
    concept_id: str,
    schematic_attr_id: str,
    provenance_id: str,
    mapping_confidence: str = "EXPLICIT",
    knowledge_kind: str = "SOURCE_DECLARED",
) -> str:
    mapping_id = new_uuid()
    conn.execute(
        """
        INSERT INTO azm_attr_mappings
            (id, concept_id, schematic_attr_id, mapping_confidence,
             knowledge_kind, version, lifecycle, provenance_id, created_at)
        VALUES (?, ?, ?, ?, ?, 1, 'ACTIVE', ?, ?)
        """,
        (mapping_id, concept_id, schematic_attr_id, mapping_confidence,
         knowledge_kind, provenance_id, utcnow()),
    )
    return mapping_id


def insert_external_mapping(
    conn: sqlite3.Connection,
    aaram_native_concept_id: str,
    external_system: str,
    external_key: str,
    provenance_id: str,
    external_display_name: Optional[str] = None,
) -> str:
    ext_id = new_uuid()
    conn.execute(
        """
        INSERT INTO azm_external_mappings
            (id, aaram_native_concept_id, external_system, external_key,
             external_display_name, knowledge_kind, lifecycle,
             provenance_id, created_at)
        VALUES (?, ?, ?, ?, ?, 'SOURCE_DECLARED', 'ACTIVE', ?, ?)
        """,
        (ext_id, aaram_native_concept_id, external_system, external_key,
         external_display_name, provenance_id, utcnow()),
    )
    return ext_id
