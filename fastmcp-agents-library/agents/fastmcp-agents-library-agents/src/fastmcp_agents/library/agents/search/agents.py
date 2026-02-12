import os

from pydantic_ai import Agent
from pydantic_ai.builtin_tools import WebSearchTool
from pydantic_ai.settings import ModelSettings

search_agent: Agent = Agent(
    model=os.getenv("MODEL_SEARCH_AGENT") or os.getenv("MODEL"),
    instructions=[
        "You are a search agent. You are given a query and you need to search the web for the most relevant information.",
    ],
    builtin_tools=[WebSearchTool()],
    output_type=str,
    model_settings=ModelSettings(
        temperature=0.1,
    ),
)
