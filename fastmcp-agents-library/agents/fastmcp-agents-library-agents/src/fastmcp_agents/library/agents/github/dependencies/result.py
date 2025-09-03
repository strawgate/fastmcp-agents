from pydantic import BaseModel, Field

from fastmcp_agents.library.agents.shared.helpers.markdown import (
    GitHubMarkdownAlert,
    MarkdownParagraph,
    MarkdownSection,
)

RESULT_TLDR_DESCRIPTION: str = (
    "A very concise summary of the full response. Skip this if a tl;dr is not applicable/appropriate for the response."
)

RESULT_RESPONSE_DESCRIPTION: str = (
    "The Markdown-formatted, detailed, response to the task covering your findings, recommendations, etc. "
    "The user will provide a title for your response. You should not include a markdown title at the beginning of your response."
    "There is no limit to the length of the response. Any changes you've made will be represented in the corresponding pull request. "
    "So your response here should cover your findings, research, recommendations, high level info about your proposed approach, etc while "
    "the pull request body and title should cover the changes you've made."
)


class PullRequestInfo(BaseModel):
    """Information about a pull request."""

    title: str = Field(description="The title of the pull request.")

    body: str = Field(description="The proposed body of the pull request.")


class AgentResult(BaseModel):
    """The result of an Agent run."""

    success: bool = Field(
        default=False,
        description=("Whether you succeeded in completing the task as requested."),
    )

    tldr: str = Field(description=RESULT_TLDR_DESCRIPTION)

    details: str = Field(description=RESULT_RESPONSE_DESCRIPTION)

    pull_request: PullRequestInfo | None = Field(
        default=None,
        description=(
            "Providing this will recommend to the user that a pull request be created with your work. "
            "If you don't provide this, the user will not be recommended to create a pull request."
        ),
    )

    def as_markdown_alert(self) -> GitHubMarkdownAlert:
        """Convert the result to a markdown alert."""
        if self.success:
            return GitHubMarkdownAlert(type="NOTE", lines=[self.tldr])

        return GitHubMarkdownAlert(type="CAUTION", lines=[self.tldr])

    def details_as_markdown_paragraph(self) -> MarkdownParagraph:
        """Convert the details to a markdown paragraph."""
        return MarkdownParagraph(text=self.details)

    def as_markdown_section(self) -> MarkdownSection:
        """Convert the result to a markdown string."""
        alert: GitHubMarkdownAlert = self.as_markdown_alert()

        return MarkdownSection(contents=[alert, self.details_as_markdown_paragraph()])


class ResultDependency(BaseModel):
    """A dependency for tracking a result."""

    result: AgentResult | None = Field(default=None, description="The result of the task.")

    allow_pull_request: bool = Field(default=False, description="Whether to allow the creation of a pull request.")

    def set_result(self, result: AgentResult) -> None:
        """Set the result."""
        self.result = result
        # self.on_result_update(result)

    def on_result_update(self, result: AgentResult) -> None:
        """Report an update to the issue."""
