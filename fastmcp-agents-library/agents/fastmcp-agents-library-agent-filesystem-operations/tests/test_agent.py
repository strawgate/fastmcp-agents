from fastmcp_agents.library.agent.filesystem_operations.agent import ask_read_only_filesystem_agent


def test_init():
    assert ask_read_only_filesystem_agent is not None
