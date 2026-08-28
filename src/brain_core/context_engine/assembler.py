import asyncio
from datetime import datetime, UTC
import uuid
from typing import List

from src.brain_core.context_engine.registry import ProviderRegistry
from src.shared.context_contracts.capability import CapabilityURN
from src.shared.context_contracts.source import ContextSourceURN
from src.shared.context_contracts.provider import ContextRetrievalStatus, ContextCapabilityResult
from src.brain_core.context_engine.registry import ProviderNotRegisteredError

from src.shared.cognitive_planning_contracts import (
    ContextAssemblyRequest,
    CapabilityResolutionResult,
    EvidenceItem,
    GapSemantics,
    ProvenanceMetadata,
    ResolutionStatus
)

class ContextAssembler:
    """
    Context Assembler is responsible for assembling contextual snapshots from authoritative business systems and internal intelligence state to provide a grounded context for AI reasoning.
    """

    def __init__(self, registry: ProviderRegistry):
        self._registry = registry

    async def assemble_evidence(self, request: ContextAssemblyRequest, resolution: CapabilityResolutionResult) -> List[EvidenceItem]:
        """
        New dynamic context retrieval boundary. Retrieves evidence based on the deterministic Orchestrator request.
        """
        # Gap Semantic Handling
        if resolution.status == ResolutionStatus.UNRESOLVABLE:
            provenance = ProvenanceMetadata(
                source_system="system:aaram_identity", # Default opaque string
                retrieval_timestamp=datetime.now(UTC),
                derivation_metadata="Raw"
            )
            return [EvidenceItem(
                item_id=str(uuid.uuid4()),
                semantic_identity=request.resolved_requirement.original_requirement.semantic_description,
                data_payload=None,
                provenance=provenance,
                gap_semantics=GapSemantics.SEMANTIC_KNOWLEDGE_GAP
            )]
            
        elif resolution.status == ResolutionStatus.DYNAMIC_DISCOVERY_REQUIRED:
            provenance = ProvenanceMetadata(
                source_system="system:aaram_identity",
                retrieval_timestamp=datetime.now(UTC),
                derivation_metadata="Raw"
            )
            return [EvidenceItem(
                item_id=str(uuid.uuid4()),
                semantic_identity=request.resolved_requirement.original_requirement.semantic_description,
                data_payload=None,
                provenance=provenance,
                gap_semantics=GapSemantics.CONTEXT_CAPABILITY_UNAVAILABLE
            )]
            
        elif resolution.status == ResolutionStatus.EXACT_MATCH_CAPABILITY:
            evidence_items = []
            for capability_urn in resolution.resolved_capabilities:
                try:
                    provider = self._registry.resolve(capability_urn)
                    result: ContextCapabilityResult = await provider.invoke_capability(
                        capability_urn=capability_urn,
                        requirement=request.resolved_requirement,
                        authorization_context=request.authorization_context
                    )
                    
                    gap = GapSemantics.EVIDENCE_SUFFICIENT
                    if result.status == ContextRetrievalStatus.DATA_UNAVAILABLE:
                        gap = GapSemantics.DATA_UNAVAILABLE
                    elif result.status == ContextRetrievalStatus.UNAUTHORIZED:
                        gap = GapSemantics.DATA_INACCESSIBLE
                    elif result.status == ContextRetrievalStatus.ERROR:
                        gap = GapSemantics.PROVIDER_EXECUTION_ERROR
                    
                    # Structural validation: if provider says SUCCESS but returned no data, it is actually DATA_UNAVAILABLE
                    if gap == GapSemantics.EVIDENCE_SUFFICIENT and not result.data:
                        gap = GapSemantics.DATA_UNAVAILABLE
                        
                    provenance = result.provenance_metadata
                    if provenance is None and gap != GapSemantics.EVIDENCE_SUFFICIENT:
                        provenance = ProvenanceMetadata(
                            source_system="system:provider_error",
                            retrieval_timestamp=datetime.now(UTC),
                            derivation_metadata=f"Fallback due to {gap.value}"
                        )

                    evidence_items.append(EvidenceItem(
                        item_id=str(uuid.uuid4()),
                        semantic_identity=request.resolved_requirement.original_requirement.semantic_description,
                        data_payload=result.data,
                        provenance=provenance,
                        gap_semantics=gap,
                        confidence_quality="HIGH" if gap == GapSemantics.EVIDENCE_SUFFICIENT else "UNKNOWN"
                    ))
                except ProviderNotRegisteredError:
                    provenance = ProvenanceMetadata(
                        source_system="system:aaram_identity",
                        retrieval_timestamp=datetime.now(UTC),
                        derivation_metadata="Provider not found"
                    )
                    evidence_items.append(EvidenceItem(
                        item_id=str(uuid.uuid4()),
                        semantic_identity=request.resolved_requirement.original_requirement.semantic_description,
                        data_payload=None,
                        provenance=provenance,
                        gap_semantics=GapSemantics.CONTEXT_CAPABILITY_UNAVAILABLE
                    ))
            return evidence_items
            
        # Fallback
        provenance = ProvenanceMetadata(
            source_system="system:aaram_identity",
            retrieval_timestamp=datetime.now(UTC),
            derivation_metadata="Raw"
        )
        return [EvidenceItem(
            item_id=str(uuid.uuid4()),
            semantic_identity=request.resolved_requirement.original_requirement.semantic_description,
            data_payload=None,
            provenance=provenance,
            gap_semantics=GapSemantics.DATA_UNAVAILABLE
        )]
