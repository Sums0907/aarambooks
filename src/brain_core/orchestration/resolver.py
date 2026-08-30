from src.shared.cognitive_planning_contracts import CapabilityResolutionResult, ResolutionStatus
from src.shared.semantic_resolution_contracts import ResolvedSemanticRequirement
from src.brain_core.context_engine.registry import ProviderRegistry

class CapabilityResolver:
    def __init__(self, registry: ProviderRegistry):
        self._registry = registry

    def resolve(self, requirement: ResolvedSemanticRequirement) -> CapabilityResolutionResult:
        if requirement.semantic_gaps or (not requirement.core_identities and not requirement.semantic_constraints):
            return CapabilityResolutionResult(
                requirement_id=requirement.requirement_id,
                status=ResolutionStatus.UNRESOLVABLE
            )

        matching_capabilities = []
        
        req_identities = requirement.core_identities
        req_constraint_types = {c.constraint_type for c in requirement.semantic_constraints}
        
        for capability_urn, metadata in self._registry.get_all_metadata().items():
            print(f"[RESOLVER DEBUG] Eval {capability_urn} with {metadata.provides_identities} vs {req_identities}", flush=True)
            print(f"[RESOLVER DEBUG] Eval types {metadata.supported_constraint_types} vs {req_constraint_types}", flush=True)
            # MANDATORY MATCHING RULE: subset intersection
            if req_identities.issubset(metadata.provides_identities) and req_constraint_types.issubset(metadata.supported_constraint_types):
                matching_capabilities.append(capability_urn)
                
        if matching_capabilities:
            return CapabilityResolutionResult(
                requirement_id=requirement.requirement_id,
                status=ResolutionStatus.EXACT_MATCH_CAPABILITY,
                resolved_capabilities=matching_capabilities
            )
            
        # If no capabilities match
        return CapabilityResolutionResult(
            requirement_id=requirement.requirement_id,
            status=ResolutionStatus.DYNAMIC_DISCOVERY_REQUIRED
        )
