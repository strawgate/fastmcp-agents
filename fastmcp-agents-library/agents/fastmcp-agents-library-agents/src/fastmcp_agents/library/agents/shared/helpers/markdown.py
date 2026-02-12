from typing import Literal

from pydantic import BaseModel, Field


def to_link(title: str, url: str) -> str:
    return f"[{title}]({url})"


def to_tooltip(title: str, url: str) -> str:
    return f'[{title} ⓘ](## "{url}")'


def list_to_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    dicts: list[dict[str, str]] = [dict[str, str](zip[tuple[str, str]](headers, row)) for row in rows]
    return dicts_to_markdown_table(dicts, headers)


def dicts_to_markdown_table(dicts: list[dict[str, str]], headers: list[str] | None = None) -> str:
    if headers is None:
        headers = list(dicts[0].keys())

    rows: list[str] = []

    header_row: str = "| " + " | ".join(headers) + " |"

    rows.append(header_row)

    for row in dicts:
        row_cells: list[str] = [row.get(header, "") for header in headers]
        row_markdown: str = "| " + " | ".join(row_cells) + " |"
        rows.append(row_markdown)

    return "\n".join(rows)


def to_markdown_section(level: int, name: str, lines: list[str]) -> str:
    return f"{'#' * level} {name}\n\n" + "\n".join(lines)


class MarkdownComponent(BaseModel):
    """A component of markdown."""

    def render(self) -> str:
        raise NotImplementedError


class MarkdownTooltip(MarkdownComponent):
    """A tooltip in markdown."""

    text: str = Field(description="The text of the tooltip.")
    tip: str = Field(description="The tip of the tooltip.")

    def render(self) -> str:
        return f'[{self.text} ⓘ](## "{self.tip}")'


class MarkdownLink(MarkdownComponent):
    """A link in markdown."""

    text: str = Field(description="The text of the link.")
    url: str = Field(description="The URL of the link.")

    def render(self) -> str:
        return f"[{self.text}]({self.url})"


class MarkdownTableCell(MarkdownComponent):
    """A cell of a markdown table."""

    text: str = Field(description="The text of the cell.")

    def render(self) -> str:
        return self.text


class MarkdownTableRow(MarkdownComponent):
    """A row of a markdown table."""

    cells: list[MarkdownTableCell] = Field(description="The cells of the row.")

    def render(self) -> str:
        return "| " + " | ".join([cell.render() for cell in self.cells]) + " |"


class MarkdownTable(MarkdownComponent):
    """A table of markdown."""

    headers: list[str] = Field(description="The headers of the table.")

    rows: list[MarkdownTableRow] = Field(description="The rows of the table.")

    def render(self) -> str:
        header_row: str = "| " + " | ".join(self.headers) + " |"
        separator_row: str = "| " + " | ".join(["---"] * len(self.headers)) + " |"

        rows: list[str] = [header_row, separator_row]
        rows.extend([row.render() for row in self.rows])
        return "\n".join(rows)

    @classmethod
    def from_dicts(cls, headers: list[str], dicts: list[dict[str, str]]) -> "MarkdownTable":
        rows: list[MarkdownTableRow] = [
            MarkdownTableRow(cells=[MarkdownTableCell(text=str(value)) for value in row.values()]) for row in dicts
        ]
        return cls(headers=headers, rows=rows)

    @classmethod
    def from_rows(cls, headers: list[str], rows: list[list[str]]) -> "MarkdownTable":
        return cls(headers=headers, rows=[MarkdownTableRow(cells=[MarkdownTableCell(text=str(value)) for value in row]) for row in rows])

    def add_row(self, row: MarkdownTableRow) -> None:
        self.rows = [*self.rows, row]

    def add_dict(self, row: dict[str, str]) -> None:
        self.rows.append(MarkdownTableRow(cells=[MarkdownTableCell(text=str(value)) for value in row.values()]))


class MarkdownHeader(MarkdownComponent):
    """A header of a markdown document."""

    level: int = Field(description="The level of the header.")

    text: str = Field(description="The text of the header.")

    def render(self) -> str:
        return f"{'#' * self.level} {self.text}"


class MarkdownSection(MarkdownComponent):
    """A section of a markdown document."""

    contents: list[MarkdownComponent] = Field(default_factory=list, description="The contents of the section.")

    def render(self) -> str:
        return "\n\n".join([component.render() for component in self.contents])

    def add(self, component: MarkdownComponent) -> None:
        self.contents.append(component)


class MarkdownChecklistItem(MarkdownComponent):
    """A checklist item in markdown."""

    text: str = Field(description="The text of the checklist item.")

    level: int = Field(default=0, description="The level of the checklist item.")

    checked: bool = Field(description="Whether the checklist item is checked.")

    def render(self) -> str:
        """Render the checklist item as a string."""
        if self.checked:
            return f"{'  ' * self.level}- [x] {self.text}"
        return f"{'  ' * self.level}- [ ] {self.text}"


class MarkdownList(MarkdownComponent):
    """A list of markdown."""

    items: list[MarkdownChecklistItem] = Field(description="The items of the list.")

    def render(self) -> str:
        """Render the list as a string."""
        return "\n".join([item.render() for item in self.items])


class MarkdownHorizontalRule(MarkdownComponent):
    """A horizontal rule in markdown."""

    def render(self) -> str:
        return "---"


class MarkdownParagraph(MarkdownComponent):
    """A paragraph of markdown."""

    text: str = Field(description="The text of the paragraph.")

    def render(self) -> str:
        return self.text

    @classmethod
    def from_lines(cls, lines: list[str]) -> "MarkdownParagraph":
        return cls(text="\n".join(lines))


class GitHubMarkdownAlert(MarkdownComponent):
    """An alert in GitHub markdown."""

    type: Literal["NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"] = Field(description="The type of alert.")

    lines: list[str] = Field(description="The content of the alert.")

    def render(self) -> str:
        lines: list[str] = [f"> {line}" for line in self.lines]
        return f"> [!{self.type}]\n{'\n'.join(lines)}"


class MarkdownDocument(BaseModel):
    """A document of markdown."""

    sections: list[MarkdownSection] = Field(default_factory=list, description="The sections of the document.")

    def add(self, section: MarkdownSection) -> None:
        self.sections.append(section)

    def render(self) -> str:
        return "\n\n".join([section.render() for section in self.sections])
