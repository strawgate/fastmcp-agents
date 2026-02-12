from typing import Any

from pydantic import BaseModel, Field, PrivateAttr
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.toolsets import FunctionToolset

from fastmcp_agents.library.agents.shared.helpers.markdown import MarkdownChecklistItem, MarkdownList
from fastmcp_agents.library.agents.shared.models.checklist import (
    Checklist,
    ChecklistItem,
    ChecklistItemAddProto,
    ChecklistItemUpdateProto,
    SkippedState,
)


class ChecklistDependency(BaseModel):
    """A dependency for tracking a checklist."""

    all_checklists: list[Checklist] = Field(default_factory=list, description="A list of inactive checklists.")

    _active_checklist_title: str | None = PrivateAttr(default=None)

    @property
    def active_checklist(self) -> Checklist:
        """Get the active checklist."""
        if not self._active_checklist_title:
            raise ModelRetry(message="No active checklist found. Create a Checklist first.")

        return self.checklist_by_title[self._active_checklist_title]

    @property
    def checklist_by_title(self) -> dict[str, Checklist]:
        """Get the checklist by title."""
        return {checklist.title: checklist for checklist in self.all_checklists}

    @property
    def checklist_is_complete(self) -> bool:
        """Check if the checklist is complete."""
        return all(checklist.is_complete for checklist in self.all_checklists)

    @property
    def all_checklist_items(self) -> list[ChecklistItem]:
        """Get all checklist items."""
        return [item for checklist in self.all_checklists for item in checklist.items]

    @property
    def in_progress_checklist_items(self) -> list[ChecklistItem]:
        """Get the checklist items that are in progress."""
        return [item for checklist in self.all_checklists for item in checklist.in_progress_items]

    @property
    def incomplete_checklists(self) -> list[Checklist]:
        """Get the sections that are not complete."""
        return [checklist for checklist in self.all_checklists if not checklist.is_complete]

    def new_checklist(self, title: str, items: list[ChecklistItemAddProto]) -> None:
        """Create a checklist with the given title and descriptions."""
        checklist: Checklist = Checklist(title=title)

        if title in self.checklist_by_title:
            raise ModelRetry(message=f"Checklist {title} already exists.")

        checklist.add(items=items)

        self.all_checklists.append(checklist)

    def skip_checklist(self, title: str, reason: str) -> None:
        """Skip a checklist."""
        if checklist := self.checklist_by_title.get(title):
            [item.mark(new_state=SkippedState(reason=reason)) for item in checklist.incomplete_items]
        else:
            raise ModelRetry(message=f"Checklist {title} not found")

    def update_items(self, items: list[ChecklistItemUpdateProto]) -> None:
        """Bulk update existing items in the checklist."""
        self.active_checklist.update(items=items)

    def add_items(self, items: list[ChecklistItemAddProto], before: str | None = None) -> None:
        """Add to-do items to the checklist."""
        self.active_checklist.add(items=items, before=before)

    def add_items_to_checklist(self, title: str, items: list[ChecklistItemAddProto], before: str | None = None) -> None:
        """Add items to the checklist with the given title."""
        if title not in self.checklist_by_title:
            raise ModelRetry(message=f"Checklist {title} not found")

        self.checklist_by_title[title].add(items=items, before=before)

    def update_items_in_checklist(self, title: str, items: list[ChecklistItemUpdateProto]) -> None:
        """Update items in the checklist with the given title."""
        if title not in self.checklist_by_title:
            raise ModelRetry(message=f"Checklist {title} not found")

        self.checklist_by_title[title].update(items=items)

    def set_active_checklist(self, title: str) -> None:
        """Set the active checklist."""
        if title not in self.checklist_by_title:
            raise ModelRetry(message=f"Checklist {title} not found")

        self._active_checklist_title = title

    def get_checklists(self) -> list[Checklist]:
        """Get all checklists."""
        return self.all_checklists

    def get_items(self) -> list[ChecklistItem]:
        """Get all items in the active checklist."""
        return self.active_checklist.items

    def checklist_as_markdown_list(self) -> MarkdownList:
        """Get the checklist as a markdown list."""
        markdown_list: MarkdownList = MarkdownList(items=[])

        for checklist in self.all_checklists:
            markdown_list.items.append(MarkdownChecklistItem(text=checklist.title, checked=checklist.is_complete))

            sub_items: list[MarkdownChecklistItem] = [item.as_markdown_list_item(level=1) for item in checklist.items]

            for sub_item in sub_items:
                markdown_list.items.append(sub_item)

        return markdown_list

    def active_checklist_as_yaml(self) -> str:
        """Get the checklist as a yaml string."""
        return self.active_checklist.as_yaml()

    def to_checklist_toolset(self) -> FunctionToolset[Any]:
        toolset: FunctionToolset[Any] = FunctionToolset[Any](max_retries=3)

        toolset.add_function(func=self.new_checklist, name="new_checklist")

        toolset.add_function(func=self.skip_checklist, name="skip_checklist")

        toolset.add_function(func=self.add_items_to_checklist, name="add_checklist_items_to_checklist")
        toolset.add_function(func=self.update_items_in_checklist, name="update_checklist_items_in_checklist")

        toolset.add_function(func=self.get_checklists, name="get_checklists")

        return toolset

    def to_active_checklist_toolset(self) -> FunctionToolset[Any]:
        toolset: FunctionToolset[Any] = FunctionToolset[Any](max_retries=3)

        toolset.add_function(func=self.add_items, name="add_checklist_items")
        toolset.add_function(func=self.update_items, name="update_checklist_items")
        toolset.add_function(func=self.get_items, name="get_checklist_items")

        return toolset
