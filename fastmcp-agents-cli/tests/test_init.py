from fastmcp_agents.cli.main import root


def test_init():
    assert root.help is not None
