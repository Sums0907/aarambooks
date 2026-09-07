from typing import List, Dict, Any, Tuple
from .models import (
    IntakeRequest,
    ResolutionDecision,
    DecisionStatus,
    CandidateProduct,
    CandidateSKU,
)

class CognitiveResolutionEngine:
    """
    Evaluates evidence (extracted attributes) and authorized boundary context to propose 
    a Product/SKU candidate or request human intervention.
    This component NEVER accesses Catalog BS databases or makes authoritative uniqueness checks.
    """
    
    def resolve(self, request: IntakeRequest) -> ResolutionDecision:
        context = request.authorized_context
        attrs = request.extracted_attributes
        
        # 1. Evaluate Authorized Context
        has_authorized_target = bool(context and context.authorized_parent_internal_id)
        is_authoritative_new = bool(context and context.authoritative_new_product_flag)
        
        if has_authorized_target and is_authoritative_new:
            return ResolutionDecision(
                status=DecisionStatus.INSUFFICIENT_EVIDENCE,
                reasoning="Conflicting authorized context: target provided alongside new product flag.",
                proposed_parent_internal_id=None,
                candidate_product=None
            )
            
        # 2. Extract key fields for proposal
        category = str(attrs.get("product_type", "GEN"))
        color = str(attrs.get("colour", "XX"))
        
        # 3. Formulate Candidate SKU
        sku_candidates = self.generate_sku_candidates(category, color)
        
        # We only return the FIRST candidate in the proposal. 
        # The orchestration handles SKU_COLLISION by asking for the next.
        # But for the initial decision, we pack it into the candidate.
        candidate_sku = CandidateSKU(
            proposed_sku_id=sku_candidates[0],
            attributes={"colour": color}
        )
        
        candidate_product = CandidateProduct(
            proposed_product_code=None, # Inherited or generated later
            attributes={"product_type": category},
            candidate_skus=[candidate_sku]
        )
        
        # 4. Formulate Cognitive Decision
        if has_authorized_target:
            return ResolutionDecision(
                status=DecisionStatus.PROPOSE_ATTACH,
                reasoning="Authorized parent internal_id was explicitly provided via the boundary.",
                proposed_parent_internal_id=context.authorized_parent_internal_id,
                candidate_product=candidate_product
            )
            
        if is_authoritative_new:
            return ResolutionDecision(
                status=DecisionStatus.PROPOSE_NEW,
                reasoning="Authoritative new product context was explicitly provided via the boundary.",
                proposed_parent_internal_id=None,
                candidate_product=candidate_product
            )
            
        # 5. Without an authorized context, we CANNOT assume the product is new.
        # We also cannot attach because we don't have an authorized internal_id target.
        return ResolutionDecision(
            status=DecisionStatus.HUMAN_APPROVAL_REQUIRED,
            reasoning="No authorized context provided. Cannot autonomously determine new vs attach.",
            proposed_parent_internal_id=None,
            candidate_product=None
        )


    def generate_sku_candidates(self, category: str, color: str) -> List[str]:
        """
        Deterministic, bounded proposal heuristic (max 3 variants).
        This is NOT a canonical standard and does NOT guarantee uniqueness.
        """
        cat_part = "".join([c for c in category if c.isalnum()]).upper()[:3]
        col_part = "".join([c for c in color if c.isalnum()]).upper()[:2]
        
        # Ensure minimum length by padding if needed
        base = f"{cat_part}{col_part}"
        if len(base) < 5:
            base = base.ljust(5, 'X')
            
        base = base[:10]
        
        candidates = [base]
        
        # Candidate 2: base-1
        c2 = f"{base}-1"
        if len(c2) > 10:
            c2 = f"{base[:8]}-1"
        candidates.append(c2)
        
        # Candidate 3: base-2
        c3 = f"{base}-2"
        if len(c3) > 10:
            c3 = f"{base[:8]}-2"
        candidates.append(c3)
            
        return candidates

