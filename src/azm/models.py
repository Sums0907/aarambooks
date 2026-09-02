"""
AZM Internal Database Row Models

These are AZM-internal dataclasses used to represent DB rows during ingestion
and provider queries. They are NOT the public API models.

The public API uses SemanticConcept from src.shared.semantic_resolution_contracts.
These internal models carry the full provenance, versioning, and AZM-specific
metadata that the public interface does not expose.

DO NOT confuse:
  - AzmConceptRow.id (AZM physical UUID — internal DB PK)
  - AzmConceptRow.semantic_key (stable public API identity, e.g. 'catalog.entity.sku')
  - BS operational identity (e.g. Catalog internal_id — NOT stored in AZM)
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class AzmNamespaceRow:
    id: str                   # AZM UUID
    name: str                 # e.g. 'catalog'
    classification: str       # 'AARAM_NATIVE' | 'EXTERNAL_CHANNEL'
    description: Optional[str]
    lifecycle: str            # 'ACTIVE' | 'DEPRECATED' | 'ARCHIVED'
    created_at: str           # ISO-8601 UTC


@dataclass
class AzmIngestionRunRow:
    id: str
    source_bs: str
    contract_type: str        # 'SEMANTIC' | 'SCHEMATIC' | 'FULL' | 'DERIVED'
    contract_hash: str
    contract_version: Optional[str]
    status: str               # 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED'
    started_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class AzmProvenanceRow:
    id: str
    ingestion_run_id: str
    source_bs: str
    contract_type: str
    knowledge_kind: str       # 'SOURCE_DECLARED' | 'AZM_DERIVED'
    created_at: str
    contract_hash: Optional[str] = None
    contract_version: Optional[str] = None
    source_element: Optional[str] = None
    derivation_rule: Optional[str] = None
    derivation_source_ids: Optional[str] = None  # JSON string


@dataclass
class AzmConceptRow:
    id: str                         # AZM UUID — internal DB PK
    semantic_key: str               # 'catalog.entity.sku' — public API key
    namespace_id: str
    concept_name: str
    concept_type: str               # 'ENTITY' | 'VOCABULARY' | 'CAPABILITY' | etc.
    knowledge_kind: str             # 'SOURCE_DECLARED' | 'AZM_DERIVED'
    created_at: str
    definition: Optional[str] = None
    version: int = 1
    lifecycle: str = 'ACTIVE'
    capability_urn: Optional[str] = None
    capability_constraints: Optional[str] = None  # JSON
    extra_metadata: Optional[str] = None          # JSON
    provenance_id: Optional[str] = None
    archived_at: Optional[str] = None
    aliases: List[str] = field(default_factory=list)  # populated post-query


@dataclass
class AzmAliasRow:
    id: str
    concept_id: str
    alias: str
    lifecycle: str
    created_at: str


@dataclass
class AzmRelationshipRow:
    id: str
    source_concept_id: str
    target_concept_id: str
    relationship_type: str
    knowledge_kind: str
    lifecycle: str
    created_at: str
    provenance_id: Optional[str] = None


@dataclass
class AzmSchematicRefRow:
    id: str
    namespace_id: str
    ref_name: str
    surface_type: str             # 'SQL_VIEW' | 'REST_API' | 'MCP_SCHEMA'
    knowledge_kind: str
    created_at: str
    description: Optional[str] = None
    version: int = 1
    lifecycle: str = 'ACTIVE'
    provenance_id: Optional[str] = None


@dataclass
class AzmSchematicAttrRow:
    id: str
    schematic_ref_id: str
    field_name: str
    knowledge_kind: str = 'SOURCE_DECLARED'
    created_at: str = ''
    field_type: Optional[str] = None
    description: Optional[str] = None
    is_derived: int = 0           # 0 | 1
    is_channel_field: int = 0     # 0 | 1
    version: int = 1
    lifecycle: str = 'ACTIVE'
    provenance_id: Optional[str] = None


@dataclass
class AzmAttrMappingRow:
    id: str
    concept_id: str
    schematic_attr_id: str
    mapping_confidence: str       # 'EXPLICIT' | 'INFERRED'
    knowledge_kind: str
    created_at: str
    version: int = 1
    lifecycle: str = 'ACTIVE'
    provenance_id: Optional[str] = None


@dataclass
class AzmExternalMappingRow:
    id: str
    aaram_native_concept_id: str
    external_system: str
    external_key: str
    knowledge_kind: str
    created_at: str
    external_display_name: Optional[str] = None
    lifecycle: str = 'ACTIVE'
    provenance_id: Optional[str] = None
