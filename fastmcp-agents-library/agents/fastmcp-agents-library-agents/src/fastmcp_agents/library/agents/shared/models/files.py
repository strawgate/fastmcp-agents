from pydantic import BaseModel, Field

# class FileLines(RootModel[dict[int, str]]):
#     root: dict[int, str] = Field(
#         default_factory=dict,
#         description=(
#             "A set of key-value pairs where the key is the line number (indexed from 1) "
#             "and the value is the line of text at that line number."
#         ),
#     )


class FileLines(BaseModel):
    line_number: int = Field(description="The starting line number of the file `lines`.")
    lines: list[str] = Field(description="The relevant lines of text.")


class InsertFileLines(BaseModel):
    line_number: int = Field(description="The starting line number of the recommended insert.")
    lines: list[str] = Field(description="The relevant lines of text.")


class ReplaceFileLines(BaseModel):
    line_number: int = Field(description="The starting line number of the recommended replacement.")
    before_lines: list[str] = Field(description="The lines of text before the replacement.")
    after_lines: list[str] = Field(description="The lines of text after the replacement.")


class DeleteFileLines(BaseModel):
    line_number: int = Field(description="The starting line number of the recommended deletion.")
    lines: list[str] = Field(description="The lines of text to delete.")
