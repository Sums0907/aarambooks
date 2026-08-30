# Architectural Integrity Over Integration Speed

**STRICT RULE:**
Prioritizing short-term functional integration over long-term architectural integrity is strictly prohibited. 

**Behavioral Constraint:**
- You must stay **BLOCKED** and halt implementation if long-term architectural integrity is being compromised.
- Do NOT introduce domain-specific middleware patches in generic infrastructure to force an integration.
- Do NOT assume legacy code can be deleted without a full dependency trace confirming no remaining consumers.
- If an external system breaks a canonical contract, you must report the contract mismatch and refuse to build normalization hacks inside the generic core.
- You must always choose the strict enforcement of system boundaries over the speed of getting a feature to compile.
