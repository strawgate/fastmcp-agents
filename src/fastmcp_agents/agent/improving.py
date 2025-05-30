# import asyncio
# from datetime import UTC, datetime
# from pathlib import Path

# from fastmcp import Context
# from litellm import PrivateAttr
# from mcp import Tool as MCPTool
# from pydantic import BaseModel, Field

# from fastmcp_agents.agent.single_step import ERROR_RESPONSE_MODEL, SUCCESS_RESPONSE_MODEL
# from fastmcp_agents.agent.multi_step import BasicFastMCPAgent
# from fastmcp_agents.types import CallToolRequest, DefaultErrorResponseModel, DefaultSuccessResponseModel, UserConversationEntry


# class CriticalFastMCPAgent(BasicFastMCPAgent):

#     background_tasks: list[asyncio.Task] = PrivateAttr(default_factory=list)

#     async def arun(
#         self,
#         ctx: Context,
#         instructions: str,
#         success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
#         error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
#     ) -> SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL:

#         result = await super().arun(ctx, instructions, success_response_model, error_response_model)

#         # Complete the suggestion improvement in a background thread
#         self.background_tasks.append(asyncio.create_task(self._suggest_prompt_improvements()))

#         return result

#     async def _suggest_prompt_improvements(self) -> None:
#         """Once the LLM is done with its work, ask it to suggest improvements to its own prompt."""

#         if self.suggest_prompt_improvements is None:
#             self._logger.debug("Prompt improvements are not enabled")
#             return

#         messages = self.memory.get()

#         class PartSuggestion(BaseModel):
#             part: str = Field(description="The part of the existing prompt that the suggestion is about.")
#             suggestion: str = Field(description="The improvement to the existing prompt.")

#         class SuggestPromptImprovements(BaseModel):
#             user_question: str = Field(description="The user's original question that was answered by the agent.")
#             part_suggestions: list[PartSuggestion] = Field(description="A list of suggestions to improve the prompt.")

#         suggest_prompt_improvements = MCPTool(
#             name="suggest_prompt_improvements",
#             inputSchema=SuggestPromptImprovements.model_json_schema(),
#             description="Suggest improvements to the prompt.",
#         )

#         no_improvements = MCPTool(
#             name="no_improvements",
#             inputSchema=DefaultSuccessResponseModel.model_json_schema(),
#             description="No improvements to the prompt are needed.",
#         )

#         add_message = UserConversationEntry(
#             role="user",
#             content=f"""
#             Here at FastMCP-Agents Incorporated we value feedback above all else.

#             If you look back at the instructions you were given:
#             `````````markdown
#             {self.system_prompt}
#             `````````
#             they were pretty basic yet you tried your hardest and we appreciate it. Now it's time to think critically
#             about how the task went! What changes to the instructions could have yielded a better or faster result?

#             You can suggest improvements to the prompt by calling the `suggest_prompt_improvements` tool.
#             If you do not see any improvements to the prompt, you can call the `no_improvements` tool.

#             For example, if the instructions are not clear, you can suggest to improve the clarity of the instructions.
#             If knowing a piece of information is important, you can suggest to add it to the info we request before calling you.
#             If additional information about the tools or parameters for those tools would have been helpful, you can suggest updates
#             to the tool descriptions or parameter descriptions.

#             If you had any tool calls error out, you can suggest improvements to the tool descriptions or parameter descriptions.

#             You now have hindsight to answer the question: What changes to the instructions could have yielded a better or faster result?
#         """,
#         )

#         self._logger.info(
#             f"Asking for prompt improvements with messages: {messages} and available tools: {[tool.name for tool in self.tools]}"
#         )
#         assistant_conversation_entry, tool_call_requests = await self.llm_link.async_completion(
#             messages=[message.model_dump() for message in messages] + [add_message.model_dump()],
#             tools=[suggest_prompt_improvements, no_improvements],
#         )

#         suggestions_dir: Path = Path(self.suggest_prompt_improvements)
#         suggestions_dir.mkdir(parents=True, exist_ok=True)
#         suggestions_file = suggestions_dir / f"{self.name}_{datetime.now(tz=UTC).strftime('%Y-%m-%d_%H-%M-%S')}.md"

#         if len(tool_call_requests) == 0:
#             self._logger.warning("No tool calls were made to suggest prompt improvements")
#             return

#         tool_call_request = tool_call_requests[0]

#         suggestions_file.write_text(f"""
#             # Prompt Suggestions for {self.name}
#             {datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S")}
#             {assistant_conversation_entry.content}
#             {tool_call_request.arguments}
#         """)


# class PlanEntry(BaseModel):
#     """A plan entry is a plan for the agent to follow."""

#     tool: str = Field(..., description="The name of the tool I plan to call.")
#     plan: str = Field(..., description="The plan for the agent to follow.")
#     tool_calls: list[CallToolRequest] = Field(..., description="The tool calls that were made in the plan.")


# class PlanningResponse(BaseModel):
#     """A planning response is a response to a planning request."""

#     problem: str = Field(..., description="The problem the agent is trying to solve.")
#     strategy: str = Field(..., description="The strategy for the agent to follow.")
#     plan: list[PlanEntry] = Field(..., description="The plan for the agent to follow.")
