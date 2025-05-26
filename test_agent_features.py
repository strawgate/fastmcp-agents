# In test_agent_features.py
import asyncio

from fastmcp.tools import Tool
from instructor import AsyncInstructor
from openai import AsyncOpenAI  # Assuming OpenAI client for Instructor
from pydantic import BaseModel, Field

from fastmcp_agents.agent.base import FastMCPAgent
from fastmcp_agents.agent.types import DefaultResponseModel
from fastmcp_agents.llm_link.instructor import AsyncInstructorLLMLink


class DummyToolRequest(BaseModel):
    query: str = Field(..., description="A query string for the dummy tool")


class DummyToolResponse(BaseModel):
    result: str = Field(..., description="The result from the dummy tool")


async def dummy_tool_function(query: str) -> DummyToolResponse:
    print(f"Dummy tool received query: {query}")
    return DummyToolResponse(result=f"Processed: {query.upper()}")


dummy_tool = Tool(
    fn=dummy_tool_function,
    name="dummy_tool",
    description="A simple dummy tool for testing.",
    parameters=DummyToolRequest.model_json_schema(),
    annotations=None,
    serializer=None,
)


async def run_test_agent():
    # Mock or use a real OpenAI client for Instructor
    # For testing, you might mock this or use a very cheap model
    # IMPORTANT: Replace "sk-dummy" with a valid API key or mock the client appropriately
    # if you intend to run this against a live OpenAI service.
    # For local testing without actual LLM calls, this setup might need adjustment
    # or a more sophisticated mocking strategy for the LLM responses,
    # especially for tool_calls.
    try:
        mock_openai_client = AsyncOpenAI(api_key="sk-dummy")
        instructor_client = AsyncInstructor(client=mock_openai_client)
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        print("Please ensure you have a valid OpenAI API key or a proper mock setup.")
        return

    llm_link = AsyncInstructorLLMLink(client=instructor_client)

    test_agent = FastMCPAgent(
        name="TestAgent",
        description="An agent for testing memory and tool calling.",
        system_prompt="You are a helpful assistant. Use the dummy_tool when asked to process a query.",
        llm_link=llm_link,
        tools=[dummy_tool],
    )

    print(f"Initial memory: {test_agent.memory.get()}")

    # Test 1: Simple instruction without tool call
    # This test will likely fail or hang if sk-dummy is not a valid key
    # and no mocking is in place for the LLM call.
    print("\n--- Test 1: Simple Instruction ---")
    try:
        response1, completion1 = await test_agent.run_async(
            instructions="Hello, how are you?",
            response_model=DefaultResponseModel,
        )
        print(f"Response 1: {response1.model_dump_json()}")
        print(f"Memory after Test 1: {test_agent.memory.get()}")
    except Exception as e:
        print(f"Error during Test 1: {e}")
        print("This test requires a functioning LLM link or mock.")

    # Test 2: Instruction that should trigger a tool call
    # This test also depends on the LLM correctly generating a tool_call.
    # With a dummy API key, the LLM call will fail.
    # A proper mock of `llm_link.run_async` would be needed to simulate a tool call.
    print("\n--- Test 2: Tool Call Instruction ---")
    try:
        response2, completion2 = await test_agent.run_async(
            instructions="Please process the query 'hello world' using the dummy tool.",
            response_model=DefaultResponseModel,
        )
        print(f"Response 2: {response2.model_dump_json()}")
        print(f"Memory after Test 2: {test_agent.memory.get()}")
    except Exception as e:
        print(f"Error during Test 2: {e}")
        print("This test requires the LLM to generate a tool call, which needs a functioning LLM link or mock.")


if __name__ == "__main__":
    asyncio.run(run_test_agent())
