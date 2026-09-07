import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.azm.interfaces import AzmProvider
from src.shared.semantic_resolution_contracts import SemanticConcept

logger = logging.getLogger(__name__)

@dataclass
class SemanticEvidenceResult:
    """The strict output contract for semantic evidence mapping."""
    original_raw: Dict[str, Any]
    provenance: Dict[str, Any]
    mapped_canonical: Dict[str, Any] = field(default_factory=dict)
    unmapped_physical: Dict[str, Any] = field(default_factory=dict)
    ambiguous_physical: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class SemanticEvidenceMapper:
    """
    Generic Brain Core capability that converts raw physical evidence keys 
    into canonical AZM semantic concept IDs using declarative AZM alias knowledge.
    
    It enforces the strict separation of:
    RAW OBSERVATION -> SEMANTIC MAPPING -> BUSINESS INTERPRETATION
    """
    
    def __init__(self, azm_provider: AzmProvider):
        self.azm = azm_provider
        
    def map_evidence(self, raw_payload: Dict[str, Any], provenance: Dict[str, Any]) -> SemanticEvidenceResult:
        """
        Maps a flat or lightly nested dictionary of raw physical evidence to canonical semantic concepts.
        """
        result = SemanticEvidenceResult(
            original_raw=raw_payload.copy(),
            provenance=provenance.copy()
        )
        
        self._map_recursive(raw_payload, result)
        return result
        
    def _map_recursive(self, current_payload: Dict[str, Any], result: SemanticEvidenceResult, prefix: str = ""):
        """
        Recursively process the evidence dictionary. 
        Nested keys are flattened using dot notation for mapping purposes if they don't map directly, 
        but we attempt to map the exact physical key first.
        """
        for key, value in current_payload.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # We do not map the dictionary object itself typically, but let's try just in case 
                # there's a concept for the container. However, for simplicity and determinism,
                # we just recurse and flatten.
                self._map_recursive(value, result, prefix=full_key)
                continue
                
            # Attempt to resolve the physical key using strict alias matching
            candidates = self.azm.resolve_concepts_by_alias(key)
            
            # If the leaf key doesn't resolve, and there's a prefix, maybe the full path resolves?
            if not candidates and prefix:
                candidates = self.azm.resolve_concepts_by_alias(full_key)
                if candidates:
                    key_to_record = full_key
                else:
                    key_to_record = key # Default back to the leaf key for reporting
            else:
                key_to_record = key
                
            if not candidates:
                # 0 matches -> UNMAPPED
                result.unmapped_physical[full_key] = value
            elif len(candidates) == 1:
                # 1 match -> CANONICAL
                canonical_id = candidates[0].concept_id
                # Avoid silent overwrites if multiple physical keys map to the same canonical concept
                if canonical_id in result.mapped_canonical:
                    # Treat as ambiguous if canonical collision occurs
                    if canonical_id not in result.ambiguous_physical:
                        result.ambiguous_physical[canonical_id] = {
                            "value": [result.mapped_canonical.pop(canonical_id), value],
                            "candidate_concepts": [canonical_id],
                            "reason": "Multiple physical keys mapped to same canonical concept"
                        }
                    else:
                        result.ambiguous_physical[canonical_id]["value"].append(value)
                else:
                    result.mapped_canonical[canonical_id] = value
            else:
                # >1 match -> AMBIGUOUS
                result.ambiguous_physical[full_key] = {
                    "value": value,
                    "candidate_concepts": [c.concept_id for c in candidates]
                }
