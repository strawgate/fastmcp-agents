from fastmcp_agents.library.agent.elasticsearch.esql_agent import ask_esql_agent
from fastmcp_agents.library.agent.elasticsearch.esql_expert import ask_esql_expert


def test_init():
    assert ask_esql_agent is not None

    assert ask_esql_expert is not None
