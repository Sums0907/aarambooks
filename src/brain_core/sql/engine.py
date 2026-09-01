import json
import re
from typing import Dict, Any

from src.brain_core.gateway.interfaces import ModelGatewayProvider

class SecurityViolationError(Exception):
    pass

class TextToSqlEngine:
    """
    Shared Text-to-SQL Engine in Container 1 (Brain Core).
    This engine converts natural language to SQL queries using the model gateway,
    validates them through an AST/regex safety gate to ensure they are SELECT-only,
    and returns the safe SQL string to the calling Intelligence Domain.
    """
    def __init__(self, gateway: ModelGatewayProvider):
        self.gateway = gateway
        
        # Simple safety gate for MVP until we add sqlglot
        self.forbidden_keywords = [
            r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b', r'\bDROP\b', 
            r'\bALTER\b', r'\bTRUNCATE\b', r'\bGRANT\b', r'\bREVOKE\b',
            r'\bCOMMIT\b', r'\bROLLBACK\b', r'\bEXEC\b', r'\bCALL\b'
        ]

    def _safety_gate(self, sql: str) -> None:
        """
        Validates that the SQL query is strictly a read operation.
        Raises SecurityViolationError if mutation keywords are found.
        """
        sql_upper = sql.upper()
        for keyword in self.forbidden_keywords:
            if re.search(keyword, sql_upper):
                raise SecurityViolationError(f"Security Policy Violation: SQL contains forbidden mutation keyword '{keyword}'. Only SELECT is allowed.")
        
        if not sql_upper.strip().startswith("SELECT"):
            raise SecurityViolationError("Security Policy Violation: SQL must begin with SELECT.")

    async def generate_sql(self, intent_query: str, schemas: Dict[str, dict], dialect: str = "PostgreSQL") -> str:
        """
        Generates a valid, read-only SQL query against the provided schema definitions.
        
        Args:
            intent_query: The natural language intent from the user.
            schemas: The Azm schema dictionaries (e.g. vw_stock_balances).
            dialect: The target SQL dialect (PostgreSQL or Shopdeck MCP SQL).
        """
        
        schema_json = json.dumps(schemas, indent=2)
        
        prompt = f"""You are an expert SQL generator for {dialect}.
You have access to the following public read schemas:
{schema_json}

Write a SQL query that answers the following business query:
"{intent_query}"

Rules:
1. ONLY use the tables and columns provided in the schema.
2. DO NOT make up columns.
3. The query MUST be a SELECT statement. No mutations allowed.
4. Output ONLY the raw SQL string without markdown formatting or code blocks.
"""
        
        from src.brain_core.gateway.interfaces import GatewayGenerationRequest, GatewayMessage
        
        req = GatewayGenerationRequest(
            messages=[
                GatewayMessage(role="system", content="You are a strict Text-to-SQL engine."),
                GatewayMessage(role="user", content=prompt)
            ],
            model="gpt-4o",  # or any default configured
            temperature=0.0
        )
        
        response_obj = await self.gateway.generate(req)
        response_content = response_obj.content
        
        # Clean up the response in case the LLM returned markdown code blocks
        clean_sql = response_content.strip()
        if clean_sql.startswith("```sql"):
            clean_sql = clean_sql[6:]
        if clean_sql.startswith("```"):
            clean_sql = clean_sql[3:]
        if clean_sql.endswith("```"):
            clean_sql = clean_sql[:-3]
            
        clean_sql = clean_sql.strip()
        
        # Pass through the AST safety gate
        self._safety_gate(clean_sql)
        
        return clean_sql
