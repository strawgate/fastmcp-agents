# LLM Link

The `LLMLink` module in FastMCP-Agents provides an abstraction layer for interacting with various Large Language Models (LLMs). This abstraction allows agents to communicate with different LLM providers without needing to know the specifics of each provider's API.

The core component is the `AsyncLLMLink` protocol, which defines the expected interface for any LLM integration.

## `AsyncLLMLink` Protocol

The `AsyncLLMLink` protocol specifies the methods and attributes that an LLM link implementation must provide.

```python
class AsyncLLMLink(Protocol):
    """Base class for all LLM links.

    This class is used to abstract the LLM link implementation from the agent.
    """

    completion_kwargs: dict[str, Any]
    """The kwargs to pass to the underlying LLM SDK when asking for a completion."""

    token_usage: int = 0
    """The number of tokens used by the LLM."""

    logger: logging.Logger = logger
    """The logger to use for the LLM link."""

    async def async_completion(
        self,
        conversation: Conversation,
        fastmcp_tools: list[FastMCPTool],
    ) -> AssistantConversationEntry: ...

    """Call the LLM with the given messages and tools.

    Args:
        conversation: The conversation to send to the LLM.
        fastmcp_tools: The tools to use.

    Returns:
        The assistant conversation entry.
    """
```

Any class implementing this protocol must provide an `async_completion` method that takes a `Conversation` object and a list of `FastMCPTool` objects and returns an `AssistantConversationEntry`. It should also manage `completion_kwargs`, `token_usage`, and a `logger`.

## `AsyncLitellmLLMLink` Implementation

`AsyncLitellmLLMLink` is a concrete implementation of the `AsyncLLMLink` protocol that uses the LiteLLM library to interact with various LLM providers. LiteLLM provides a unified API for many different models.

*   **Key Features:**
    *   Uses LiteLLM for broad model support.
    *   Handles conversion of FastMCP tools to the OpenAI tool format expected by LiteLLM.
    *   Extracts tool calls and content from the LLM's response.
    *   Includes basic validation for function calling support in the configured model.
    *   Tracks token usage.

*   **Tool Conversion:**
    The `transform_fastmcp_tool_to_openai_tool` function in `llm_link/utils.py` is used to convert `FastMCPTool` objects into the format required by LiteLLM (which is based on OpenAI's tool definition).

## Implementing a Custom LLM Link

To integrate a different LLM provider, you would create a new class that implements the `AsyncLLMLink` protocol. This class would need to:

1.  Handle authentication and initialization for the specific LLM provider's SDK.
2.  Implement the `async_completion` method to send the conversation history and tool definitions to the LLM and process the response.
3.  Convert `FastMCPTool` objects to the format required by the LLM provider (if necessary).
4.  Extract tool calls and generated text content from the LLM's response and return them as an `AssistantConversationEntry`.
5.  Track token usage if the provider's API provides this information.
6.  Raise appropriate exceptions from `fastmcp_agents.errors.llm_link` or custom exceptions for LLM-specific errors.