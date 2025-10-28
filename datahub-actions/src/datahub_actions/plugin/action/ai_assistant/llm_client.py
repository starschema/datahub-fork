"""LLM client for generating SQL assertions using Gemini."""

import json
import logging
import os
from typing import Any, Dict, Optional

import google.generativeai as genai

from datahub_actions.plugin.action.ai_assistant.models import DatasetSchema

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM providers (Gemini)."""

    def __init__(
        self,
        provider: str = "gemini",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider = provider
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

        if self.provider == "gemini":
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is required")
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
            logger.info(f"Initialized Gemini client with model: {self.model}")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def validate_rule(
        self, nl_rule: str, schema: DatasetSchema
    ) -> tuple[bool, list[str]]:
        """
        Validate if an NL rule is feasible given the dataset schema.

        Returns:
            (feasible: bool, reasons: List[str])
        """
        prompt = self._build_validation_prompt(nl_rule, schema)

        try:
            response = self.client.generate_content(prompt)
            result = self._parse_json_response(response.text)

            feasible = result.get("feasible", False)
            reasons = result.get("reasons", [])

            logger.info(
                f"Validation result for rule '{nl_rule[:50]}...': feasible={feasible}"
            )
            return feasible, reasons

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return False, [f"LLM error: {str(e)}"]

    def generate_sql_assertion(
        self, nl_rule: str, schema: DatasetSchema
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate SQL query and assertion config from NL rule.

        Returns:
            (sql: str, config: Dict)
        """
        prompt = self._build_generation_prompt(nl_rule, schema)

        try:
            response = self.client.generate_content(prompt)
            result = self._parse_json_response(response.text)

            sql = result.get("sql", "")
            config = result.get("config", {})

            logger.info(f"Generated SQL for rule '{nl_rule[:50]}...'")
            logger.debug(f"Generated SQL: {sql}")

            return sql, config

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise ValueError(f"SQL generation failed: {str(e)}")

    def _build_validation_prompt(self, nl_rule: str, schema: DatasetSchema) -> str:
        """Build prompt for validation phase."""
        columns_desc = "\n".join(
            [
                f"  - {col.name}: {col.type} (nullable={col.nullable}, pk={col.primary_key})"
                for col in schema.columns
            ]
        )

        return f"""You are a data quality expert. Validate if the following quality rule can be implemented given the dataset schema.

Dataset: {schema.platform}.{schema.database or ''}.{schema.schema_name or ''}.{schema.table}
Columns:
{columns_desc}

Quality Rule: "{nl_rule}"

Analyze:
1. Are the required columns present?
2. Are the column types compatible with the rule (e.g., no avg() on STRING)?
3. Is the logic sound and implementable in SQL?

Respond ONLY with valid JSON:
{{
  "feasible": true/false,
  "reasons": ["reason 1", "reason 2", ...]
}}

If feasible=true, reasons should be empty or contain confirmations.
If feasible=false, explain what's missing or incompatible."""

    def _build_generation_prompt(self, nl_rule: str, schema: DatasetSchema) -> str:
        """Build prompt for SQL generation phase."""
        columns_desc = "\n".join(
            [f"  - {col.name} ({col.type})" for col in schema.columns]
        )

        full_table_name = self._get_full_table_name(schema)

        return f"""You are a SQL expert. Generate a read-only SQL assertion query for the following quality rule.

Dataset: {full_table_name}
Columns:
{columns_desc}

Quality Rule: "{nl_rule}"

REQUIREMENTS:
1. SQL must be read-only (SELECT only, no DDL/DML)
2. Use fully-qualified table names: {full_table_name}
3. Include LIMIT 1000 for safety
4. Return a single scalar value or aggregate
5. Query should validate the rule (return 1 if pass, 0 if fail, or relevant metric)

Respond ONLY with valid JSON:
{{
  "sql": "SELECT ... FROM {full_table_name} ...",
  "config": {{
    "type": "custom_sql" or "column_assertion" or "table_assertion",
    "params": {{
      "threshold": <number if applicable>,
      "operator": ">" or "<" or "=" or "between",
      "expected_value": <value>
    }}
  }}
}}

Example for "Ensure revenue column has no negative values":
{{
  "sql": "SELECT COUNT(*) FROM table WHERE revenue < 0 LIMIT 1000",
  "config": {{
    "type": "custom_sql",
    "params": {{
      "expected_value": 0,
      "operator": "="
    }}
  }}
}}"""

    def _get_full_table_name(self, schema: DatasetSchema) -> str:
        """Construct fully-qualified table name."""
        parts = []
        if schema.database:
            parts.append(schema.database)
        if schema.schema_name:
            parts.append(schema.schema_name)
        parts.append(schema.table)
        return ".".join(parts)

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = response_text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {text}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
