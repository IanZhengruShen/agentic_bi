"""
Prompt Template System

This module provides a centralized prompt management system for agents with:
- Template definition and versioning
- Variable substitution using Jinja2
- Prompt validation
- Easy template updates without code changes
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum
from jinja2 import Template, TemplateError

logger = logging.getLogger(__name__)


class PromptType(str, Enum):
    """Enum for different prompt types."""

    SQL_GENERATION = "sql_generation"
    QUERY_INTENT = "query_intent"  # Simple: data analysis vs other
    INTENT_CLASSIFICATION = "intent_classification"  # Detailed: aggregate, filter, etc.
    QUERY_VALIDATION = "query_validation"
    DATA_ANALYSIS = "data_analysis"


class PromptTemplate:
    """
    A prompt template with variable substitution.

    Attributes:
        name: Template name/identifier
        template_str: Jinja2 template string
        description: Template description
        required_vars: List of required template variables
        version: Template version for tracking changes
    """

    def __init__(
        self,
        name: str,
        template_str: str,
        description: str = "",
        required_vars: Optional[list[str]] = None,
        version: str = "1.0",
    ):
        """
        Initialize prompt template.

        Args:
            name: Template name
            template_str: Jinja2 template string
            description: Template description
            required_vars: List of required variable names
            version: Template version
        """
        self.name = name
        self.template_str = template_str
        self.description = description
        self.required_vars = required_vars or []
        self.version = version

        try:
            self.template = Template(template_str)
        except TemplateError as e:
            logger.error(f"Invalid template '{name}': {e}")
            raise ValueError(f"Invalid Jinja2 template: {e}")

    def render(self, **kwargs) -> str:
        """
        Render template with provided variables.

        Args:
            **kwargs: Template variables

        Returns:
            Rendered prompt string

        Raises:
            ValueError: If required variables are missing
        """
        # Check for required variables
        missing = [var for var in self.required_vars if var not in kwargs]
        if missing:
            raise ValueError(f"Missing required variables for template '{self.name}': {missing}")

        try:
            return self.template.render(**kwargs)
        except TemplateError as e:
            logger.error(f"Error rendering template '{self.name}': {e}")
            raise ValueError(f"Template rendering error: {e}")


# ============================================
# SQL Generation Prompt
# ============================================

SQL_GENERATION_TEMPLATE = PromptTemplate(
    name="sql_generation",
    description="Generate SQL query from natural language with schema context",
    required_vars=["schema", "query"],
    version="1.0",
    template_str="""You are an expert SQL query generator. Your task is to convert natural language questions into sqlite SQL queries.

Database Schema:
{{ schema }}

User Query: {{ query }}

{% if context %}
Previous Context:
{{ context }}
{% endif %}

Requirements:
1. Use ONLY tables and columns from the provided schema
2. Generate syntactically correct SQL for the target database
3. Include appropriate JOINs if multiple tables are needed
4. Add reasonable LIMIT clause if not specified (default: 1000 rows)
5. Optimize for query performance
6. Use proper SQL formatting with clear indentation
7. Include comments for complex logic
8. ALWAYS include the database name in table references (e.g., database.table_name)

Return your response in the following JSON format:
{
  "sql": "your SQL query here",
  "explanation": "brief explanation of what the query does",
  "tables_used": ["database.table1", "database.table2"],
  "confidence": 0.95,
  "warnings": ["any warnings or caveats"],
  "needs_review": false
}

Set "confidence" between 0.0 and 1.0 based on:
- How well the schema matches the query requirements
- Ambiguity in the natural language query
- Complexity of the required query

Set "needs_review" to true if:
- Confidence is below 0.8
- Query contains UPDATE, DELETE, or DROP operations
- Schema is ambiguous or unclear
- Multiple interpretations are possible

Now generate the SQL query:""",
)


# ============================================
# Query Intent Prompt (Data Analysis vs Other)
# ============================================

QUERY_INTENT_TEMPLATE = PromptTemplate(
    name="query_intent",
    description="Classify if query is data analysis related or not",
    required_vars=["query"],
    version="1.0",
    template_str="""You are an intent classifier for a business intelligence data analyst AI assistant.

Your task is to determine if the user query is requesting data analysis or something else.

User Query: {{ query }}

Classification Categories:
1. DATA_ANALYSIS - User wants to query, analyze, visualize, or understand data from databases
   Examples:
   - "Show me total sales last month"
   - "What are the top 10 customers by revenue?"
   - "Compare sales between regions"
   - "How many active users do we have?"
   - "Visualize revenue trends over time"
   - "Calculate average order value"
   - "Show me the product performance metrics"

2. OTHER - User is asking about something unrelated to data analysis
   Examples:
   - "Hello" / "Hi" / "How are you?"
   - "What's the weather today?"
   - "Tell me a joke"
   - "Who is the president?"
   - "Help me write code"
   - "What can you do?" (general capability question, not about data)
   - "Explain quantum physics"
   - "Write me an email"

Return your response in the following JSON format:
{
  "intent": "DATA_ANALYSIS" or "OTHER",
  "confidence": 0.95,
  "reasoning": "brief explanation of classification"
}

Classify the query:""",
)


# ============================================
# Intent Classification Prompt
# ============================================

INTENT_CLASSIFICATION_TEMPLATE = PromptTemplate(
    name="intent_classification",
    description="Classify the intent of a natural language query",
    required_vars=["query"],
    version="1.0",
    template_str="""You are a query intent classifier. Analyze the following natural language query and classify its intent.

Query: {{ query }}

{% if schema %}
Available Schema Context:
{{ schema }}
{% endif %}

Intent Categories:
1. AGGREGATE - Summarizing data (sum, count, average, min, max, group by)
   Examples: "total sales", "average price", "count of users"

2. FILTER - Finding specific records based on conditions
   Examples: "show users in California", "orders after Jan 2024"

3. JOIN - Combining data from multiple related tables
   Examples: "customers with their orders", "products and categories"

4. TREND - Time-based analysis and patterns
   Examples: "sales over time", "monthly growth", "daily active users"

5. COMPARISON - Comparing groups, periods, or categories
   Examples: "sales by region", "this month vs last month", "product performance"

Return your response in the following JSON format:
{
  "intent": "one of: aggregate, filter, join, trend, comparison",
  "confidence": 0.95,
  "reasoning": "brief explanation of why this intent was chosen",
  "secondary_intent": "optional secondary intent if applicable"
}

Classify the intent:""",
)


# ============================================
# Query Validation Prompt
# ============================================

QUERY_VALIDATION_TEMPLATE = PromptTemplate(
    name="query_validation",
    description="Validate SQL query for safety and correctness",
    required_vars=["query"],
    version="1.0",
    template_str="""You are a SQL query validator. Analyze the following SQL query for potential issues, safety concerns, and syntax errors.

SQL Query:
{{ query }}

{% if schema %}
Database Schema:
{{ schema }}
{% endif %}

Validation Checks:
1. Syntax correctness
2. Dangerous operations (DROP, DELETE, UPDATE without WHERE, TRUNCATE)
3. SQL injection vulnerabilities
4. Performance issues (missing LIMIT on large tables, SELECT *)
5. Invalid table or column references
6. Missing JOINs or incorrect JOIN conditions

Return your response in the following JSON format:
{
  "valid": true,
  "safety_level": "safe|warning|dangerous",
  "errors": [],
  "warnings": ["performance warning: no LIMIT clause"],
  "suggestions": ["consider adding WHERE clause", "add index on column X"],
  "dangerous_operations": []
}

safety_level guidelines:
- "safe": Query is safe to execute
- "warning": Query has concerns but may be acceptable
- "dangerous": Query should NOT be executed without review

Validate the query:""",
)


# ============================================
# Data Analysis Prompt
# ============================================

DATA_ANALYSIS_TEMPLATE = PromptTemplate(
    name="data_analysis",
    description="Generate insights and analysis from query results",
    required_vars=["data_summary", "query"],
    version="1.0",
    template_str="""You are a data analyst. Analyze the following query results and provide meaningful insights.

Original Query: {{ query }}

Data Summary:
{{ data_summary }}

{% if statistics %}
Statistical Summary:
{{ statistics }}
{% endif %}

Your task:
1. Identify key patterns and trends in the data
2. Highlight notable findings or anomalies
3. Provide actionable insights
4. Suggest potential follow-up questions
5. Flag any data quality issues

Return your response in the following JSON format:
{
  "insights": [
    "insight 1: description",
    "insight 2: description"
  ],
  "key_findings": [
    "finding 1",
    "finding 2"
  ],
  "anomalies": [
    "anomaly description if any"
  ],
  "data_quality_notes": [
    "any data quality concerns"
  ],
  "recommendations": [
    "recommendation 1",
    "recommendation 2"
  ],
  "follow_up_questions": [
    "suggested question 1",
    "suggested question 2"
  ]
}

Provide your analysis:""",
)


# ============================================
# Prompt Registry
# ============================================

class PromptRegistry:
    """
    Central registry for all prompt templates.

    Usage:
        prompts = PromptRegistry()
        sql_prompt = prompts.get(PromptType.SQL_GENERATION)
        rendered = sql_prompt.render(schema=schema, query=query)
    """

    def __init__(self):
        """Initialize prompt registry with default templates."""
        self._templates: Dict[PromptType, PromptTemplate] = {
            PromptType.SQL_GENERATION: SQL_GENERATION_TEMPLATE,
            PromptType.QUERY_INTENT: QUERY_INTENT_TEMPLATE,
            PromptType.INTENT_CLASSIFICATION: INTENT_CLASSIFICATION_TEMPLATE,
            PromptType.QUERY_VALIDATION: QUERY_VALIDATION_TEMPLATE,
            PromptType.DATA_ANALYSIS: DATA_ANALYSIS_TEMPLATE,
        }

    def get(self, prompt_type: PromptType) -> PromptTemplate:
        """
        Get prompt template by type.

        Args:
            prompt_type: Type of prompt to retrieve

        Returns:
            PromptTemplate instance

        Raises:
            KeyError: If prompt type not found
        """
        if prompt_type not in self._templates:
            raise KeyError(f"Prompt template not found: {prompt_type}")
        return self._templates[prompt_type]

    def register(self, prompt_type: PromptType, template: PromptTemplate):
        """
        Register or update a prompt template.

        Args:
            prompt_type: Type of prompt
            template: PromptTemplate instance
        """
        self._templates[prompt_type] = template
        logger.info(f"Registered prompt template: {prompt_type} (version {template.version})")

    def list_templates(self) -> Dict[PromptType, Dict[str, Any]]:
        """
        List all registered templates with metadata.

        Returns:
            Dict mapping prompt types to template metadata
        """
        return {
            prompt_type: {
                "name": template.name,
                "description": template.description,
                "version": template.version,
                "required_vars": template.required_vars,
            }
            for prompt_type, template in self._templates.items()
        }


# Global prompt registry instance
prompts = PromptRegistry()


def get_prompt(prompt_type: PromptType) -> PromptTemplate:
    """
    Convenience function to get prompt template.

    Args:
        prompt_type: Type of prompt to retrieve

    Returns:
        PromptTemplate instance
    """
    return prompts.get(prompt_type)
