from textwrap import dedent
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field
from pydantic_ai.tools import RunContext
from pydantic_ai.toolsets import AbstractToolset, CombinedToolset, FunctionToolset

from fastmcp_agents.library.agents.search.agents import search_agent

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult

web_search_toolset: FunctionToolset[Any] = FunctionToolset()


@web_search_toolset.tool(name="search_webpages")
async def web_search_tool(
    queries: Annotated[list[str], Field(description="The query to search the web for.")],
    goal: Annotated[str, Field(description="The goal of the search.")],
) -> str:
    """Perform a web search for the given queries and receive a summarized answer. Use the `Goal` argument to tailor the summary
    to the goal you're trying to achieve."""
    user_prompt: str = dedent(
        f"""
        You are a Web Search Agent! You are given a list of search queries and a "goal" for the search. Your goal is to use the list of
        queries as a starting point, in consideration of the goal, and to determine the best queries to run. You should then perform the
        queries and summarize the results in accordance with the stated goal. It is extremely important that every claim you make is
        supported by a provided source.

        For example, if the user's query is, "What is the latest version of Python?", and the user's goal is "To identify the most recent
        supported version of python for my software project.", you might perform the following queries:
        - "What is the latest version of Python Software?"
        - "What is the latest version of Python Software that is supported?"
        - "What was the most recently released version of Python Software?"

        Your answer might look something like this:
        ```
        The [latest version of Python Software is x.y.z](source_url). It was released on [Month Day, Year](source_url). When it was
        released, [version a.b.c became end-of-life](source_url).

        <additional background and context>
        ```

        Here is the user's query(s):
        ```
        {"\n".join(queries)}
        ```

        Here is the goal of the search:
        ```
        {goal}
        ```

        Your response should be an "answer" to the user's query, in accordance with the goal.
        """
    )

    agent_run_result: AgentRunResult[str] = await search_agent.run(user_prompt)

    return agent_run_result.output


# async def web_search_toolset(ctx: RunContext[Any]) -> AbstractToolset[Any] | None:
#     if ctx.model.system in {"google-gla", "anthropic"}:
#         return web_search_toolset

#     return None


def supports_web_search(ctx: RunContext[Any]) -> bool:
    return ctx.model.system in {"google-gla", "anthropic"}


async def web_search_toolset_func(ctx: RunContext[Any]) -> AbstractToolset[Any]:
    if supports_web_search(ctx):
        return web_search_toolset

    return CombinedToolset(toolsets=[])


async def web_search_toolset_instructions(ctx: RunContext[Any]) -> str:
    instructions: str = ""

    if supports_web_search(ctx):
        instructions = """
        You also have access to a web search tool. You can use this tool to get background information about libraries, frameworks,
        generate ideas for how to solve a particularly challenging problem, or to find best practices for a specific topic.
        """

    return dedent(instructions.strip())
