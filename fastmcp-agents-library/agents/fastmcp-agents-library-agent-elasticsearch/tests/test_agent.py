from fastmcp_agents.library.agent.elasticsearch.esql_agent import AskESQLAgent
from fastmcp_agents.library.agent.elasticsearch.esql_expert import AskESQLExpert


def test_init():
    agent = AskESQLAgent()
    assert agent is not None

    expert = AskESQLExpert()
    assert expert is not None
