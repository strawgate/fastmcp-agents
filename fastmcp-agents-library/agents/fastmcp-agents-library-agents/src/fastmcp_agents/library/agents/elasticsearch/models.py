from typing import Any

from pydantic import BaseModel, Field


class QueryExplanation(BaseModel):
    """The explanation of a query."""

    step: str = Field(description="The step of the query. Each pipe `|` is a step.")
    explanation: str = Field(description="The explanation of the step.")
    reference: str = Field(description="A reference to the documentation for the step.")


class AskESQLExpertResponse(BaseModel):
    """The response from the ask_esql_agent."""

    query: str = Field(description="The query that would answer the question.")
    explanation: list[QueryExplanation] = Field(description="The explanation of the query.")


class AskESQLAgentResponse(BaseModel):
    """The response from the ask_esql_agent."""

    answer: str = Field(description="A summary of the results of the query.")
    query: str = Field(description="The query that was run.")
    explanation: list[QueryExplanation] = Field(description="The explanation of the query.")
    results: list[dict[str, Any]] = Field(description="The results of the query.")
