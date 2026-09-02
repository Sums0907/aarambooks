"""
Persistent AZM Provider

Implements the AzmProvider Protocol, answering queries against the
AZM Persistent Database. It never connects to Business System databases.

Translates internal DB row formats back into the shared SemanticConcept
Pydantic model that the Intelligence Domains expect.
"""
import json
from typing import List, Optional, Dict

from src.shared.semantic_resolution_contracts import SemanticConcept
from src.azm.interfaces import AzmProvider
from src.azm.db import get_connection, is_initialized
from src.azm.config import AZM_DATABASE_URL


class PersistentAzmProvider(AzmProvider):
    def __init__(self, db_url: Optional[str] = None, legacy_fallback: Optional[AzmProvider] = None):
        self.db_url = db_url or AZM_DATABASE_URL
        self.legacy_fallback = legacy_fallback
        self._check_db()

    def _check_db(self) -> None:
        """Verify DB exists and schema is initialized. Raises RuntimeError if not."""
        conn = get_connection(self.db_url)
        try:
            if not is_initialized(conn):
                raise RuntimeError(f"AZM database at {self.db_url} is not initialized.")
        finally:
            conn.close()

    def get_concept_by_id(self, concept_id: str) -> SemanticConcept:
        """
        Retrieve a specific concept definition by its semantic_key.
        Raises ValueError if not found (matches bootstrap behavior).
        """
        conn = get_connection(self.db_url)
        try:
            row = conn.execute(
                "SELECT * FROM azm_concepts WHERE semantic_key = ? AND lifecycle = 'ACTIVE'",
                (concept_id,)
            ).fetchone()

            if not row:
                if self.legacy_fallback:
                    return self.legacy_fallback.get_concept_by_id(concept_id)
                raise ValueError(f"Concept {concept_id} not found in Azm")

            alias_rows = conn.execute(
                "SELECT alias FROM azm_aliases WHERE concept_id = ? AND lifecycle = 'ACTIVE'",
                (row["id"],)
            ).fetchall()
            aliases = [r["alias"] for r in alias_rows]

            metadata = None
            if row["concept_type"] == "CAPABILITY" and row["capability_urn"]:
                metadata = {"urn": row["capability_urn"]}
                if row["capability_constraints"]:
                    metadata["required_constraints"] = json.loads(row["capability_constraints"])
            
            if row["extra_metadata"]:
                extra = json.loads(row["extra_metadata"])
                if metadata:
                    metadata.update(extra)
                else:
                    metadata = extra

            return SemanticConcept(
                concept_id=row["semantic_key"],
                concept_name=row["concept_name"],
                concept_type=row["concept_type"],
                aliases=aliases,
                description=row["definition"],
                metadata=metadata,
            )
        finally:
            conn.close()

    def search_concepts_by_namespace(self, namespace: str, query: str) -> List[SemanticConcept]:
        conn = get_connection(self.db_url)
        try:
            ns_row = conn.execute(
                "SELECT id FROM azm_namespaces WHERE name = ? AND lifecycle = 'ACTIVE'",
                (namespace,)
            ).fetchone()

            if not ns_row:
                if self.legacy_fallback:
                    return self.legacy_fallback.search_concepts_by_namespace(namespace, query)
                raise ValueError(f"Unknown namespace: {namespace}")
            
            ns_id = ns_row["id"]
            query_lower = query.lower()

            sql = """
            SELECT DISTINCT c.semantic_key
            FROM azm_concepts c
            LEFT JOIN azm_aliases a ON c.id = a.concept_id AND a.lifecycle = 'ACTIVE'
            WHERE c.namespace_id = ? AND c.lifecycle = 'ACTIVE'
              AND (LOWER(c.concept_name) LIKE ? OR LOWER(a.alias) LIKE ?)
            """
            like_query = f"%{query_lower}%"
            rows = conn.execute(sql, (ns_id, like_query, like_query)).fetchall()
            
            results = []
            for row in rows:
                results.append(self.get_concept_by_id(row["semantic_key"]))
                
            return results
        finally:
            conn.close()

    def get_namespace_schema(self, namespace: str) -> dict:
        conn = get_connection(self.db_url)
        try:
            ns_row = conn.execute(
                "SELECT id FROM azm_namespaces WHERE name = ? AND lifecycle = 'ACTIVE'",
                (namespace,)
            ).fetchone()

            if not ns_row:
                if self.legacy_fallback:
                    return self.legacy_fallback.get_namespace_schema(namespace)
                raise ValueError(f"Unknown namespace: {namespace}")

            ns_id = ns_row["id"]

            refs = conn.execute(
                "SELECT id, ref_name, description FROM azm_schematic_refs "
                "WHERE namespace_id = ? AND lifecycle = 'ACTIVE'",
                (ns_id,)
            ).fetchall()

            schema_dict = {}
            for ref in refs:
                ref_id = ref["id"]
                ref_name = ref["ref_name"]
                
                attrs = conn.execute(
                    "SELECT field_name, field_type, description FROM azm_schematic_attrs "
                    "WHERE schematic_ref_id = ? AND lifecycle = 'ACTIVE'",
                    (ref_id,)
                ).fetchall()
                
                columns = {}
                for attr in attrs:
                    type_str = attr["field_type"] or "UNKNOWN"
                    desc = attr["description"] or ""
                    val = f"{type_str} - {desc}" if desc else type_str
                    columns[attr["field_name"]] = val
                
                schema_dict[ref_name] = {
                    "description": ref["description"] or "",
                    "columns": columns
                }
                
            return schema_dict
        finally:
            conn.close()

    def get_schematic_attr(self, namespace: str, view_name: str, field_name: str) -> Optional[dict]:
        conn = get_connection(self.db_url)
        try:
            # We don't have a direct fallback for this since the legacy provider didn't implement it,
            # but if it did, we'd add it here.
            sql = """
            SELECT sa.field_type, sa.description, sa.is_derived, sa.is_channel_field, c.semantic_key
            FROM azm_namespaces ns
            JOIN azm_schematic_refs sr ON ns.id = sr.namespace_id
            JOIN azm_schematic_attrs sa ON sr.id = sa.schematic_ref_id
            LEFT JOIN azm_attr_mappings am ON sa.id = am.schematic_attr_id AND am.lifecycle = 'ACTIVE'
            LEFT JOIN azm_concepts c ON am.concept_id = c.id AND c.lifecycle = 'ACTIVE'
            WHERE ns.name = ? AND ns.lifecycle = 'ACTIVE'
              AND sr.ref_name = ? AND sr.lifecycle = 'ACTIVE'
              AND sa.field_name = ? AND sa.lifecycle = 'ACTIVE'
            """
            row = conn.execute(sql, (namespace, view_name, field_name)).fetchone()
            if not row:
                return None
                
            return {
                "field_type": row["field_type"],
                "description": row["description"],
                "is_derived": bool(row["is_derived"]),
                "is_channel_field": bool(row["is_channel_field"]),
                "mapped_concept": row["semantic_key"],
            }
        finally:
            conn.close()
