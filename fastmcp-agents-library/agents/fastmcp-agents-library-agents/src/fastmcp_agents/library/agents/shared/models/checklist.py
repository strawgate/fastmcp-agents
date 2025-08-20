from collections import defaultdict
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, Field, PrivateAttr
from pydantic_ai.exceptions import ModelRetry

from fastmcp_agents.library.agents.shared.helpers.markdown import MarkdownChecklistItem, MarkdownList, MarkdownTooltip


class CompleteState(BaseModel):
    """The item has been successfully completed as described."""

    phase: Literal["Completed"] = Field(default="Completed", description="The phase of the item in the checklist.")


class FailedState(BaseModel):
    """The item has been failed to complete as described due to a lack of information, tools, or other reason."""

    phase: Literal["Failed"] = Field(default="Failed", description="The phase of the item in the checklist.")
    reason: str = Field(description="The reason the item failed.")


class SkippedState(BaseModel):
    """The item as described has been skipped because it is no longer relevant or needed to complete the overall task."""

    phase: Literal["Skipped"] = Field(default="Skipped", description="The phase of the item in the checklist.")
    reason: str = Field(description="The reason the item was skipped.")


class InProgressState(BaseModel):
    """The item is currently being worked on."""

    phase: Literal["In Progress"] = Field(default="In Progress", description="The phase of the item in the checklist.")


class ToDoState(BaseModel):
    """The item has not been started yet."""

    phase: Literal["To Do"] = Field(default="To Do", description="The State of the item in the checklist.")


ChecklistStatePhases = Literal["Completed", "Failed", "Skipped", "In Progress", "To Do"]
ChecklistStateTypes = CompleteState | FailedState | SkippedState | InProgressState | ToDoState


class ChecklistItem(BaseModel):
    description: str = Field(description="The description of the item to add to the checklist.")

    state: ChecklistStateTypes = Field(default_factory=ToDoState, description="The status of the item in the checklist.")

    _history: list[ChecklistStateTypes] = PrivateAttr(default_factory=list)

    @property
    def history(self) -> list[ChecklistStateTypes]:
        """Get the history of the item in the checklist."""
        return self._history

    def mark(self, new_state: ChecklistStateTypes) -> None:
        """Mark the item as a new state."""
        self._history.append(self.state)
        self.state = new_state

    def as_markdown_list_item(self, level: int = 0) -> MarkdownChecklistItem:
        formatted_description = self.description
        tooltip: MarkdownTooltip | None = None

        match self.state:
            case SkippedState():
                tooltip = MarkdownTooltip(text="Skipped", tip=self.state.reason)
                formatted_description = f"~~{formatted_description}~~ {tooltip.render()}"
            case FailedState():
                tooltip = MarkdownTooltip(text="Failed", tip=self.state.reason)
                formatted_description = f"🔴 ~~{formatted_description}~~ {tooltip.render()}"
            case InProgressState():
                formatted_description = f"🚧 {formatted_description}"
            case ToDoState():
                formatted_description = f"💡 {formatted_description}"
            case CompleteState():
                formatted_description = f"{formatted_description}"

        return MarkdownChecklistItem(text=formatted_description, checked=self.state.phase == "Completed", level=level)


class ChecklistItemUpdateProto(BaseModel):
    description: str = Field(description="The description of the item to update.")

    new_state: ChecklistStateTypes = Field(description="The status to update the item to.")

    def apply(self, item: ChecklistItem) -> None:
        """Apply the update to the item."""
        item.mark(self.new_state)


class ChecklistItemAddProto(BaseModel):
    description: str = Field(
        description=(
            "The description of the item to add. "
            "If the checklist item has multiple parts but will be done as one step, include all the parts in the description."
        )
    )

    state: ChecklistStateTypes = Field(
        default=ToDoState(), description="The initial state of the item to add. If not provided, the item will be added as to-do."
    )

    def to_checklist_item(self) -> ChecklistItem:
        """Convert the proto to a checklist item."""
        return ChecklistItem(description=self.description, state=self.state)


class Checklist(BaseModel):
    title: str = Field(
        description=(
            "A friendly title of the checklist. "
            "A high-level description of the tasks to complete. "
            "For example, `Gather information about the issue`."
        )
    )

    items: list[ChecklistItem] = Field(default_factory=list, description="A list of items to add to the checklist.")

    @property
    def items_by_description(self) -> dict[str, ChecklistItem]:
        return {item.description: item for item in self.items}

    @property
    def items_by_state(self) -> dict[ChecklistStatePhases, list[ChecklistItem]]:
        states_to_items: dict[ChecklistStatePhases, list[ChecklistItem]] = defaultdict(list)

        for item in self.items:
            states_to_items[item.state.phase].append(item)

        return states_to_items

    @property
    def incomplete_items(self) -> list[ChecklistItem]:
        """Get the items that are not completed."""
        return [item for item in self.items if item.state.phase in ["To Do", "In Progress"]]

    @property
    def in_progress_items(self) -> list[ChecklistItem]:
        """Get the items that are in progress."""
        return [item for item in self.items if item.state.phase == "In Progress"]

    @property
    def is_complete(self) -> bool:
        """Check if the checklist is free of to-do and in-progress items."""
        return not self.incomplete_items

    def get_item_index(self, description: str) -> int:
        """Get the index of an item in the checklist."""
        return self.items.index(self.items_by_description[description])

    def update(self, items: list[ChecklistItemUpdateProto]) -> None:
        """Provide updates for existing items in the checklist.

        Items that do not exist in the checklist will be skipped."""
        for item in items:
            if not self.items_by_description.get(item.description):
                continue

            item.apply(item=self.items_by_description[item.description])

    def add(
        self,
        items: list[ChecklistItemAddProto],
        before: Annotated[
            str | None, Field(description="The description of the item that these new items should go before in the checklist.")
        ] = None,
    ) -> None:
        """Adds items to the checklist.

        Items that already exist in the checklist will be skipped."""

        if before and not self.items_by_description.get(before):
            raise ModelRetry(
                message=f"Item {before} not found in checklist. The checklist contains the following items: {self.as_yaml()}"
            )

        for item in items:
            if self.items_by_description.get(item.description):
                continue

            checklist_item: ChecklistItem = item.to_checklist_item()

            index: int = self.get_item_index(description=before) if before else len(self.items)

            self.items.insert(index, checklist_item)

    def as_markdown_list(self) -> MarkdownList:
        """Get the checklist as a markdown list."""
        return MarkdownList(items=[item.as_markdown_list_item() for item in self.items])

    def as_yaml(self) -> str:
        """Get the checklist as a yaml string."""
        return yaml.safe_dump(self.model_dump())
