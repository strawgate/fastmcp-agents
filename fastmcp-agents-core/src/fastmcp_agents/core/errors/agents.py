class StepLimitReachedError(Exception):
    """An error that is raised when the step limit is reached."""

    def __init__(self, agent_name: str, step_limit: int):
        """Initialize the error."""
        super().__init__(f"Step limit reached for agent {agent_name} with step limit {step_limit}.")
