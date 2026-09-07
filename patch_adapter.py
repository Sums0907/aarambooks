import os
path = '/Users/sumatidhingra/aarambooks/src/infrastructure/adapters/shopdeck_cem_adapter.py'
with open(path, 'r') as f:
    content = f.read()

new_logic = """
                if response.status_code == 200:
                    return BusinessEvidenceResponse(
                        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
                        evidence_data=response.json()
                    )
                elif response.status_code == 404:
                    detail = response.json().get('detail', '')
                    if detail == 'AWB_NOT_FOUND':
                        return BusinessEvidenceResponse(
                            status=BusinessRealityStatus.ENTITY_NOT_FOUND,
                            execution_limitations=[ExecutionLimitation(missing_parameter="awb", reason="AWB genuinely does not exist.")]
                        )
                    elif detail == 'NO_NDR_RECORD':
                        return BusinessEvidenceResponse(
                            status=BusinessRealityStatus.EVIDENCE_UNAVAILABLE,
                            execution_limitations=[ExecutionLimitation(missing_parameter="data", reason="AWB exists but has no NDR record.")]
                        )
                    else:
                        return BusinessEvidenceResponse(
                            status=BusinessRealityStatus.EVIDENCE_UNAVAILABLE,
                            execution_limitations=[ExecutionLimitation(missing_parameter="data", reason="No NDR records found.")]
                        )
                elif response.status_code == 503:
                    return BusinessEvidenceResponse(
                        status=BusinessRealityStatus.EVIDENCE_UNAVAILABLE,
                        execution_limitations=[ExecutionLimitation(missing_parameter="data", reason="ShopDeck NDR data is unavailable/incomplete because backfill has not completed.")]
                    )
"""

start_idx = content.find('if response.status_code == 200:')
end_idx = content.find('elif response.status_code in (401, 403):')

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_logic.strip() + '\n                ' + content[end_idx:]

with open(path, 'w') as f:
    f.write(content)
print("Patched.")
