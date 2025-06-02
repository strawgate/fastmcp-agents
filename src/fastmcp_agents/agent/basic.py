from fastmcp.tools import Tool as FastMCPTool

from fastmcp_agents.agent.multi_step import MultiStepAgent
from fastmcp_agents.conversation.memory.base import MemoryFactoryProtocol, PrivateMemoryFactory
from fastmcp_agents.conversation.types import (
    Conversation,
)
from fastmcp_agents.llm_link.base import AsyncLLMLink
from fastmcp_agents.llm_link.lltellm import AsyncLitellmLLMLink

DEFAULT_SYSTEM_PROMPT = """
You are `{agent_name}`, an AI Agent that is embedded into a FastMCP Server. You act as an
interface between the remote user/agent and the tools available on the server.

The person or Agent that invoked you understood received the following as a description of your capabilities:

````````markdown
{agent_description}
````````

You will be asked to perform a task. Your tasks will be phrased in the form of either `tell {agent_name} to <task>` or just `<task>`.
You should leverage the tools available to you to perform the task. You may perform many tool calls in one go but you should always
keep in mind that the tool calls may run in any order and may run at the same time. So you should plan
for which calls you can do in parallel (multiple in a single request) and which you should do sequentially (one tool call per request).
"""

DEFAULT_STEP_LIMIT = 20
DEFAULT_MAX_PARALLEL_TOOL_CALLS = 5


class FastMCPAgent(MultiStepAgent):
    """A basic FastMCP Agent that can be used to perform tasks.

    This agent is a multi-step agent that can be used to perform tasks. It will use the provided LLM link to perform the tasks.
    It will also use the provided memory factory to store the conversation history.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str,
        system_prompt: str | Conversation = DEFAULT_SYSTEM_PROMPT,
        default_tools: list[FastMCPTool] | None = None,
        llm_link: AsyncLLMLink | None = None,
        memory_factory: MemoryFactoryProtocol | None = None,
        max_parallel_tool_calls: int | None = None,
        step_limit: int | None = None,
    ):
        """Create a new FastMCP Agent.

        Args:
            name: The name of the agent.
            description: The description of the agent.
            instructions: The instructions for the agent.
            default_tools: The default tools to use. Defaults to an empty list.
            llm_link: The LLM link to use. Defaults to a Litellm LLM link.
            system_prompt: The system prompt to use. Defaults to a default system prompt.
            memory_factory: The memory factory to use. Defaults to a private memory factory.
            max_parallel_tool_calls: The maximum number of tool calls to perform in parallel. Defaults to 5.
            step_limit: The maximum number of steps to perform. Defaults to 10.
        """

        formatted_system_prompt = (
            system_prompt.format(agent_name=name, agent_description=description) if isinstance(system_prompt, str) else system_prompt
        )

        super().__init__(
            name=name,
            description=description,
            system_prompt=formatted_system_prompt,
            llm_link=llm_link or AsyncLitellmLLMLink(),
            default_tools=default_tools or [],
            memory_factory=memory_factory or PrivateMemoryFactory(),
            max_parallel_tool_calls=max_parallel_tool_calls or DEFAULT_MAX_PARALLEL_TOOL_CALLS,
            step_limit=step_limit or DEFAULT_STEP_LIMIT,
        )
