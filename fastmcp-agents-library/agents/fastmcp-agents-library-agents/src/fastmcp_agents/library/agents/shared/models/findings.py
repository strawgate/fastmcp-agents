from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, PrivateAttr
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.toolsets import AbstractToolset, FunctionToolset

from fastmcp_agents.library.agents.shared.models.files import DeleteFileLines, InsertFileLines, ReplaceFileLines

TLDR = Annotated[str, Field(description="A summary of the finding. This field must be unique across all findings.")]


class CodeRecommendation(BaseModel):
    tldr: TLDR = Field(
        default=...,
        description="A summary of the recommendation. This field must be unique across all recommendations under the same finding.",
    )
    details: str = Field(default=..., description="A detailed description of the recommendation.")
    action: Literal["fix", "refactor", "implement", "document", "ignore", "external"] = Field(
        default=...,
        description=(
            "The action to take to remediate the finding. `External` means the code change is not part of this code base but part of "
            "another code base. `Ignore` means the finding is not a problem and you do not need to take any action."
        ),
    )
    patches: list[InsertFileLines | ReplaceFileLines | DeleteFileLines] | None = Field(
        default=None,
        description="If applicable, provide the line-by-line patches that would resolve the finding.",
    )


class NoRecommendationReason(BaseModel):
    """The reason you have no recommendation for a finding."""

    reason: str = Field(default=..., description="The reason you have no recommendation for the finding.")


class SignificantFileSection(BaseModel):
    significance: str = Field(default=..., description="A description of the significance of the section in relation to the finding.")
    start: int = Field(default=..., description="The index-1 starting line number of the file.")
    end: int = Field(default=..., description="The index-1 ending line number of the file.")
    lines: list[str] = Field(default=..., description="The actual lines between `start` and `end`.")


class CodeFinding(BaseModel):
    tldr: TLDR
    file: str = Field(default=..., description="The path to the file that relates to the finding.")
    significant_sections: list[SignificantFileSection] = Field(default=..., description="The specific sections that relate to the finding.")

    details: str = Field(
        default=...,
        description=(
            "A detailed breakdown of the finding and why it is a finding in relation to the task. "
            "This should be the full finding, not a summary, the source lines that generated the finding should be placed in `source_lines`."
        ),
    )
    confidence: Literal["high", "medium", "low"] = Field(default=..., description="The confidence you have in this finding.")

    recommendations: list[CodeRecommendation] | NoRecommendationReason = Field(
        default=...,
        description=(
            "The recommendations for remediating the finding."
            "If you have no recommendation, you must provide a reason for why you are not providing a recommendation."
        ),
    )

    @property
    def recommendations_by_tldr(self) -> dict[TLDR, CodeRecommendation]:
        """The recommendations by tldr."""
        if isinstance(self.recommendations, NoRecommendationReason):
            return {}

        return {recommendation.tldr: recommendation for recommendation in self.recommendations}

    def get_recommendation(self, tldr: TLDR) -> CodeRecommendation | None:
        """Get a recommendation from the finding."""
        return self.recommendations_by_tldr.get(tldr)

    def add_recommendation(self, recommendation: CodeRecommendation) -> None:
        """Add a recommendation to the finding."""
        if isinstance(self.recommendations, NoRecommendationReason):
            self.recommendations = []

        if recommendation.tldr in self.recommendations_by_tldr:
            msg = f"Recommendation with tldr {recommendation.tldr} already exists."
            raise ModelRetry(msg)

        self.recommendations.append(recommendation)

    def remove_recommendation(self, tldr: TLDR) -> None:
        """Remove a recommendation from the finding."""
        if isinstance(self.recommendations, NoRecommendationReason):
            return

        self.recommendations = [recommendation for recommendation in self.recommendations if recommendation.tldr != tldr]


class FindingDependency(BaseModel):
    _findings: list[CodeFinding] = PrivateAttr(default_factory=list)

    @property
    def findings(self) -> list[CodeFinding]:
        """The list of findings."""
        return self._findings

    def add_finding(self, finding: CodeFinding) -> None:
        """Add a finding to the list of findings.

        You can include recommendations in the finding or add them later if needed. If you have the recommendation already, just add it!"""
        self._findings.append(finding)

    def remove_finding(self, tldr: TLDR) -> None:
        """Remove a finding from the list of findings."""
        self._findings = [finding for finding in self._findings if finding.tldr != tldr]

    def get_finding(self, tldr: TLDR) -> CodeFinding | None:
        """Get a finding from the list of findings."""
        return next(finding for finding in self._findings if finding.tldr == tldr)

    def add_recommendations_to_finding(self, tldr: TLDR, recommendations: list[CodeRecommendation]) -> None:
        """Add a recommendation to a finding that was previously identified."""
        if not (finding := self.get_finding(tldr)):
            msg = f"Finding with tldr {tldr} not found."
            raise ModelRetry(msg)

        for recommendation in recommendations:
            finding.add_recommendation(recommendation)

    def remove_recommendation_from_finding(self, tldr: TLDR, recommendation_tldr: TLDR) -> None:
        """Remove a recommendation from a finding."""
        if not (finding := self.get_finding(tldr)):
            msg = f"Finding with tldr {tldr} not found."
            raise ModelRetry(msg)

        finding.remove_recommendation(recommendation_tldr)

    def to_findings_toolset(self, recommendations: bool = True) -> AbstractToolset[Any]:
        toolset = FunctionToolset[Any]()

        toolset.add_function(self.add_finding)
        toolset.add_function(self.remove_finding)

        if recommendations:
            toolset.add_function(self.add_recommendations_to_finding)
            toolset.add_function(self.remove_recommendation_from_finding)

        return toolset
