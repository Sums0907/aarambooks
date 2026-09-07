import asyncio
from src.infrastructure.adapters.shopdeck_cem_adapter import ShopdeckCemAdapter
from src.shared.evidence_request_contracts import AbstractEvidenceRequest, BusinessRealityStatus
from src.shared.requirement_classification_contracts import ClassifiedRequirement
from src.shared.conversational_contracts import ConversationalUnderstanding, NormalizedParameter, ParameterDataType

async def main():
    shopdeck_cem = ShopdeckCemAdapter(base_url="http://localhost:8200")
    req = AbstractEvidenceRequest(
        classified_requirement=ClassifiedRequirement(
            understanding=ConversationalUnderstanding(
                original_query="Internal CCC Hydration for AWB 142285239995710",
                parameters=[NormalizedParameter(parameter_name="awb_no", data_type=ParameterDataType.STRING, value="142285239995710", original_expression="142285239995710")]
            )
        )
    )
    res = await shopdeck_cem.execute_evidence_request(req)
    print("Status:", res.status)
    print("Limitations:", res.execution_limitations)

if __name__ == "__main__":
    asyncio.run(main())
