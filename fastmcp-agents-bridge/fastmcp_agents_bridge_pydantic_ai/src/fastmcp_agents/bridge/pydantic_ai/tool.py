from typing import Any, Self

from fastmcp.tools import FunctionTool
from pydantic import BaseModel
from pydantic.type_adapter import TypeAdapter

from pydantic_ai.agent import Agent, AgentRunResult


class AgentTool[InputModel: BaseModel, OutputModel: BaseModel](FunctionTool):
    @classmethod
    def from_agent(cls, agent: Agent[Any, OutputModel], input_model: type[InputModel], name: str, description: str, prompt: str) -> Self:
        async def invoke_agent(input_model: InputModel) -> OutputModel:
            task = prompt.format(input_model=input_model, **input_model.model_dump())

            result: AgentRunResult[OutputModel] = await agent.run(task)
            return result.output

        return cls(
            name=name,
            fn=invoke_agent,
            description=description,
            parameters=input_model.model_json_schema(),
            output_schema=TypeAdapter(agent.output_type).json_schema(),
        )
