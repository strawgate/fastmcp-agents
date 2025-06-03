import yaml
from fastmcp import Context
from fastmcp.tools import Tool as FastMCPTool
from pydantic import BaseModel, Field

from fastmcp_agents.agent.basic import DEFAULT_SYSTEM_PROMPT, FastMCPAgent
from fastmcp_agents.agent.multi_step import (
    DEFAULT_MAX_PARALLEL_TOOL_CALLS,
    DEFAULT_STEP_LIMIT,
    ERROR_RESPONSE_MODEL,
    SUCCESS_RESPONSE_MODEL,
    DefaultErrorResponseModel,
    DefaultSuccessResponseModel,
)
from fastmcp_agents.conversation.memory.base import MemoryFactoryProtocol, PrivateMemoryFactory
from fastmcp_agents.conversation.types import (
    Conversation,
    TextContent,
    ToolConversationEntry,
    UserConversationEntry,
)
from fastmcp_agents.llm_link.base import AsyncLLMLink
from fastmcp_agents.llm_link.lltellm import AsyncLitellmLLMLink
from fastmcp_agents.observability.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("agent.planning")

DEFAULT_PLANNING_INTERVAL = 5

FIRST_STEP_PROMPT = """
You can perform a small number of tool calls to gather initial context. After the first batch of calls, you will be asked to
create a detailed plan on how you will complete the task. The plan is not the task, the plan is just a list of steps you will
take to complete the task.
"""

INITIAL_PLANNING_PROMPT = """
You will now take a step back from the request and plan out your next steps. You will thoroughly review what you are
being asked to do. You will produce a thorough review of the current facts you understand regarding the request.

You will then produce a list of the next steps you will take to complete the request. You should plan out
as many steps as you can understanding that plans can change.

You understand that you only have {step_limit} steps to complete the request.
During this planning phase you have access to all the tools
you will have access to during the execution phase but only the tool for reporting task success or failure
will actually do anything during the planning phase.

You will then return the plan.
"""

UPDATE_PLANNING_PROMPT = """
Your original plan was:
```markdown
{last_plan}
```

But now that {step_number} steps have passed, you have new information and you will need to update the plan.
You will now update the plan. You will thoroughly review what you are being asked to do. You will produce a thorough
review of the current facts you understand regarding the request. We have made it so you can still see all of the tools
you will have access to during the execution phase but only the tool for reporting task success or failure will actually
do anything during the planning phase. All other tools are no-ops while planning.

You will then produce a plan with an updated list of the next steps you will take to complete the request.
"""


class PlanPart(BaseModel):
    missing_information: str = Field(..., description="The information that you need to complete the request.")
    intended_action: str = Field(..., description="The intended action you plan to take to gather the missing information.")
    tool_selection: list[str] = Field(..., description="Which tools you will probably use to gather the missing information.")


class Plan(BaseModel):
    goal: str = Field(..., description="The goal of the plan.")
    parts: list[PlanPart] = Field(..., description="The parts of a plan that will bring you to a complete solution for the goal..")


class PlanningFastMCPAgent(FastMCPAgent):
    """A FastMCP Agent that will occasionally pause to plan its next steps."""

    planning_interval: int
    previous_plans: list[Plan]
    original_instructions: str | Conversation
    initial_planning_prompt: str
    update_planning_prompt: str

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
        planning_interval: int = DEFAULT_PLANNING_INTERVAL,
        initial_planning_prompt: str = INITIAL_PLANNING_PROMPT,
        update_planning_prompt: str = UPDATE_PLANNING_PROMPT,
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
            planning_interval: The interval at which to plan. Defaults to 5.
            initial_planning_prompt: The prompt to use for the initial planning. Defaults to a default initial planning prompt.
            update_planning_prompt: The prompt to use for the update planning. Defaults to a default update planning prompt.
        """

        self.planning_interval = planning_interval
        self.initial_planning_prompt = initial_planning_prompt
        self.update_planning_prompt = update_planning_prompt
        self.previous_plans = []

        super().__init__(
            name=name,
            description=description,
            system_prompt=system_prompt,
            llm_link=llm_link or AsyncLitellmLLMLink(),
            default_tools=default_tools or [],
            memory_factory=memory_factory or PrivateMemoryFactory(),
            max_parallel_tool_calls=max_parallel_tool_calls or DEFAULT_MAX_PARALLEL_TOOL_CALLS,
            step_limit=step_limit or DEFAULT_STEP_LIMIT,
        )

    async def run(
        self,
        ctx: Context,
        instructions: str | Conversation,
        tools: list[FastMCPTool] | None = None,
        success_response_model: type[SUCCESS_RESPONSE_MODEL] = DefaultSuccessResponseModel,
        error_response_model: type[ERROR_RESPONSE_MODEL] = DefaultErrorResponseModel,
        raise_on_error_response: bool = True,
        step_limit: int | None = None,
    ) -> tuple[Conversation, SUCCESS_RESPONSE_MODEL | ERROR_RESPONSE_MODEL]:
        """Run the agent."""

        self.original_instructions = instructions

        return await super().run(
            ctx,
            instructions,
            tools,
            success_response_model,
            error_response_model,
            raise_on_error_response,
            step_limit or self.step_limit,
        )

    @classmethod
    def _planning_tool(cls) -> FastMCPTool:
        def produce_plan(plan: Plan) -> None:
            pass

        return FastMCPTool.from_function(
            fn=produce_plan,
            name="produce_plan",
            description="Report your detailed plan, multi-step (if needed) to completing the task.",
        )

    async def run_interruption_step(
        self,
        ctx: Context,  # noqa: ARG002
        step_number: int,
        step_limit: int,
        conversation: Conversation,
        tools: list[FastMCPTool],
    ) -> Conversation:
        """Interrupt the running agent to plan its next steps."""

        original_conversation = conversation
        available_tools: list[FastMCPTool] = [*tools, self._planning_tool()]

        if step_number == 1:
            return Conversation.add(
                conversation,
                UserConversationEntry(content=FIRST_STEP_PROMPT),
            )

        if step_number == 2:  # noqa: PLR2004
            self._logger.info("Performing initial planning")
            conversation = Conversation.add(
                conversation,
                UserConversationEntry(content=self.initial_planning_prompt.format(step_limit=step_limit)),
            )

        elif step_number % self.planning_interval == 0 and step_limit > self.planning_interval:
            self._logger.info("Performing update planning")
            conversation = Conversation.add(
                conversation,
                UserConversationEntry(
                    content=self.update_planning_prompt.format(
                        step_number=step_number, step_limit=step_limit, last_plan=self.previous_plans[-1].model_dump_json()
                    )
                ),
            )
        else:
            return original_conversation

        conversation, tool_call_requests = await self._generate_tool_call_requests(conversation, available_tools)

        if len(tool_call_requests) != 1:
            self._logger.warning(f"Agent failed to plan, got {len(tool_call_requests)} tool call requests. Skipping planning.")
            return original_conversation

        if tool_call_requests[0].name == "produce_plan":
            request = tool_call_requests[0]

            plan = Plan.model_validate(obj=request.arguments.get("plan", {}))

            self.previous_plans.append(plan)

            text_content = TextContent(type="text", text=plan.model_dump_json())

            self._logger.info(f"Reporting task success with plan:\n{yaml.safe_dump(plan.model_dump(), indent=2, sort_keys=False)}")

            conversation = Conversation.add(
                conversation,
                ToolConversationEntry(tool_call_id=request.id, name=request.name, content=[text_content]),
            )

            return conversation  # noqa: RET504

        self._logger.warning(f"Agent did not perform planning during {step_number}")

        return original_conversation
