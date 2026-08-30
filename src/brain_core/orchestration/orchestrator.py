from typing import List, Dict, Any, Optional
import uuid

from src.shared.cognitive_planning_contracts import (
    EvidencePlan, 
    EvidencePackage, 
    EvidencePlanExtension,
    ContextAssemblyRequest,
    EvidenceItem,
    GapSemantics,
    ResolutionStatus
)
from src.brain_core.planning.planner import CognitivePlanner
from src.brain_core.orchestration.resolver import CapabilityResolver
from src.brain_core.context_engine.assembler import ContextAssembler
from src.brain_core.semantics.resolver import GenericSemanticResolver

class BrainOrchestrator:
    """
    Brain Orchestrator is the deterministic control layer between cognition and execution.
    It validates plans, resolves capabilities, enforces limits, and coordinates iterative retrieval.
    """
    def __init__(
        self, 
        planner: CognitivePlanner, 
        resolver: CapabilityResolver, 
        assembler: ContextAssembler,
        semantic_resolver: GenericSemanticResolver
    ):
        self._planner = planner
        self._resolver = resolver
        self._assembler = assembler
        self._semantic_resolver = semantic_resolver
        self._max_iterations = 3

    async def handle_query(self, query: str, user_id: str) -> EvidencePackage:
        # 1. Cognitive Planner proposes the initial Evidence Plan
        plan = await self._planner.propose_plan(query)
        
        # 2. Execute plan iteratively
        package = await self._execute_plan(plan, user_id)
        
        iteration = 0
        while package.sufficiency_assessment == "INSUFFICIENT" and iteration < self._max_iterations:
            # 3. Request Evidence Plan Extension
            extension = await self._planner.propose_extension(package, query)
            
            # 4. Execute extension
            new_items = await self._execute_requirements(extension.new_requirements, user_id)
            package.evidence_items.extend(new_items)
            
            # Re-evaluate sufficiency based on gaps
            package.gaps = [item.gap_semantics for item in package.evidence_items if item.gap_semantics != GapSemantics.EVIDENCE_SUFFICIENT]
            package.sufficiency_assessment = "INSUFFICIENT" if package.gaps else "SUFFICIENT"
            
            iteration += 1
            
        return package

    async def _execute_plan(self, plan: EvidencePlan, user_id: str) -> EvidencePackage:
        evidence_items = await self._execute_requirements(plan.requirements, user_id)
        
        gaps = [item.gap_semantics for item in evidence_items if item.gap_semantics != GapSemantics.EVIDENCE_SUFFICIENT]
        sufficiency = "INSUFFICIENT" if gaps else "SUFFICIENT"
        
        return EvidencePackage(
            package_id=str(uuid.uuid4()),
            plan_id=plan.plan_id,
            evidence_items=evidence_items,
            sufficiency_assessment=sufficiency,
            gaps=gaps
        )

    async def execute_requirements(
        self, 
        requirements: list, 
        authorization_context: Optional[str] = None
    ) -> EvidencePackage:
        """
        Public boundary for Intelligence Domains to submit pre-constructed EvidenceRequirements.
        This allows domains to bypass the natural-language Cognitive Planner while still
        utilizing the generic Context Assembler pipeline.
        """
        auth_ctx = authorization_context if authorization_context is not None else "system"
        
        evidence_items = await self._execute_requirements(requirements, auth_ctx)
        
        gaps = [item.gap_semantics for item in evidence_items if item.gap_semantics != GapSemantics.EVIDENCE_SUFFICIENT]
        sufficiency = "INSUFFICIENT" if gaps else "SUFFICIENT"
        
        return EvidencePackage(
            package_id=str(uuid.uuid4()),
            plan_id="direct-execution",
            evidence_items=evidence_items,
            sufficiency_assessment=sufficiency,
            gaps=gaps
        )

    async def _execute_requirements(self, requirements: list, user_id: str) -> List[EvidenceItem]:
        items = []
        for req in requirements:
            # 1. Semantic Resolution (HOW) applied using Domain Semantic Knowledge (WHAT)
            resolved_req = self._semantic_resolver.resolve(req)
            
            # If there are semantic gaps, we may want to stop or proceed. 
            # For now, pass the resolved requirement down.
            
            # 2. Resolve capability
            resolution = self._resolver.resolve(resolved_req)
            
            # 3. Create assembly request
            assembly_request = ContextAssemblyRequest(
                request_id=str(uuid.uuid4()),
                resolved_requirement=resolved_req,
                resolution_strategy=resolution.status,
                authorization_context=user_id
            )
            
            # Assemble evidence via Context Engine
            # assemble_evidence now returns a List[EvidenceItem]
            new_items = await self._assembler.assemble_evidence(assembly_request, resolution)
            items.extend(new_items)
            
        return items
