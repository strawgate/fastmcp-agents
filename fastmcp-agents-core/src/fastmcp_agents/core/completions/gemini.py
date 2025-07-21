from collections.abc import Mapping, Sequence
from typing import Any, Literal, Self, override

from fastmcp.exceptions import ToolError
from fastmcp.tools import Tool as FastMCPTool
from fastmcp.tools.tool import ToolResult
from google.genai import Client
from google.genai.types import (
    Candidate,
    Content,
    ContentUnion,
    FunctionCallingConfig,
    FunctionCallingConfigMode,
    FunctionDeclaration,
    FunctionResponse,
    GenerateContentConfig,
    GenerateContentResponse,
    Part,
    Schema,
    ThinkingConfig,
    ToolConfig,
    UserContent,
)
from google.genai.types import Tool as GeminiTool
from jsonref import replace_refs  # pyright: ignore[reportUnknownVariableType]
from mcp.types import (
    ContentBlock,
    TextContent,
)
from pydantic import Field, model_validator
from pydantic.aliases import AliasChoices
from pydantic.type_adapter import TypeAdapter

from fastmcp_agents.core.completions.base import (
    BaseCompletionExtras,
    BasePendingToolCall,
    CompletionMessageType,
    LLMCompletionsProtocol,
)
from fastmcp_agents.core.completions.options import CompletionSettings

CONTENT_TYPE_ADAPTER: TypeAdapter[Content] = TypeAdapter(Content)


class GoogleGenaiCompletionExtras(BaseCompletionExtras):
    """Google Genai completion extras."""

    raw_token_usage: dict[str, Any] | None = None


class GoogleGenaiPendingToolCall(BasePendingToolCall):
    """Google Genai pending tool call."""

    tool_call_id: str

    @override
    def _tool_error_to_completion_message(self, tool_error: ToolError) -> CompletionMessageType:
        """Convert a tool error to a chat completion tool message."""

        return Content(
            role="tool",
            parts=[
                Part(
                    function_response=FunctionResponse(
                        id=self.tool_call_id,
                        name=self.tool.name,
                        response={"error": str(tool_error)},
                    )
                )
            ],
        ).model_dump(exclude_none=True)

    @override
    def _tool_result_to_completion_message(self, tool_result: ToolResult) -> CompletionMessageType:
        """Convert a tool result to a chat completion tool message."""

        response: dict[str, Any] = {}

        if tool_result.structured_content:
            response = tool_result.structured_content
        else:
            response["output"] = [content.text for content in tool_result.content if isinstance(content, TextContent)]

        return Content(
            role="tool",
            parts=[
                Part(
                    function_response=FunctionResponse(
                        id=self.tool_call_id,
                        name=self.tool.name,
                        response=response,
                    )
                )
            ],
        ).model_dump(exclude_none=True)


class GoogleGenaiCompletions(LLMCompletionsProtocol):
    """Google Genai completions."""

    client: Client
    default_model: str
    completion_settings: CompletionSettings

    def __init__(
        self,
        default_model: str,
        client: Client | None = None,
        completion_settings: CompletionSettings | None = None,
    ) -> None:
        self.client = client or Client()
        self.default_model = default_model
        self.completion_settings = completion_settings or CompletionSettings.from_environment()

    @override
    async def text(
        self,
        system_prompt: str,
        messages: Sequence[CompletionMessageType] | CompletionMessageType,
        **kwargs: Any,  # pyright: ignore[reportAny]
    ) -> tuple[GoogleGenaiCompletionExtras, CompletionMessageType, ContentBlock]:
        """Text completion."""

        contents: list[ContentUnion] = convert_messages_to_gemini_content(messages)

        response: GenerateContentResponse = await self.client.aio.models.generate_content(
            model=self.default_model,
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=self.completion_settings.temperature,
                max_output_tokens=self.completion_settings.max_tokens,
                top_p=self.completion_settings.top_p,
                frequency_penalty=self.completion_settings.frequency_penalty,
                thinking_config=reasoning_effort_to_thinking_config(self.completion_settings.reasoning_effort),
                **kwargs,  # pyright: ignore[reportAny]
            ),
        )

        message: Content = get_content_from_generate_content_response(response)

        extras = get_extras(generate_content_response=response, message=message)

        if not (text := response.text):
            msg = "No text in the response."
            raise ValueError(msg)

        return (
            extras,
            message.model_dump(exclude_none=True),
            TextContent(type="text", text=text),
        )

    async def _tool(
        self,
        system_prompt: str,
        messages: Sequence[CompletionMessageType] | CompletionMessageType,
        tools: Sequence[FastMCPTool] | dict[str, FastMCPTool],
        **kwargs: Any,  # pyright: ignore[reportAny]
    ) -> tuple[
        GoogleGenaiCompletionExtras,
        CompletionMessageType,
        list[GoogleGenaiPendingToolCall],
    ]:
        """Tool completion."""

        if isinstance(tools, dict):
            tools = list(tools.values())

        genai_tools: GeminiTool = convert_fastmcp_tools_to_gemini_tool(tools)

        contents: list[ContentUnion] = convert_messages_to_gemini_content(messages)

        response: GenerateContentResponse = await self.client.aio.models.generate_content(
            model=self.default_model,
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[genai_tools],
                tool_config=ToolConfig(
                    function_calling_config=FunctionCallingConfig(
                        mode=FunctionCallingConfigMode.ANY,
                    ),
                ),
                temperature=self.completion_settings.temperature,
                max_output_tokens=self.completion_settings.max_tokens,
                top_p=self.completion_settings.top_p,
                frequency_penalty=self.completion_settings.frequency_penalty,
                thinking_config=reasoning_effort_to_thinking_config(self.completion_settings.reasoning_effort),
                **kwargs,  # pyright: ignore[reportAny]
            ),
        )

        content: Content = get_content_from_generate_content_response(response)

        extras = get_extras(generate_content_response=response, message=content)

        if not response.function_calls:
            msg = "No function calls in the response."
            raise ValueError(msg)

        pending_tool_calls: list[GoogleGenaiPendingToolCall] = []

        tools_by_name: dict[str, FastMCPTool] = {tool.name: tool for tool in tools}

        for function_call in response.function_calls:
            if not function_call.name:
                msg = "No function name in the function call."
                raise ValueError(msg)

            pending_tool_calls.append(
                GoogleGenaiPendingToolCall(
                    tool_call_id=function_call.id or "",
                    tool=tools_by_name[function_call.name],
                    arguments=function_call.args or {},
                )
            )

        return extras, content.model_dump(exclude_none=True), pending_tool_calls

    @override
    async def tool(
        self,
        system_prompt: str,
        messages: Sequence[CompletionMessageType] | CompletionMessageType,
        tools: Sequence[FastMCPTool] | dict[str, FastMCPTool],
        **kwargs: Any,  # pyright: ignore[reportAny]
    ) -> tuple[GoogleGenaiCompletionExtras, CompletionMessageType, GoogleGenaiPendingToolCall]:
        """Tool completion."""

        extras, message, pending_tool_calls = await self._tool(system_prompt, messages, tools, **kwargs)
        return extras, message, pending_tool_calls[0]

    @override
    async def tools(
        self,
        system_prompt: str,
        messages: Sequence[CompletionMessageType] | CompletionMessageType,
        tools: Sequence[FastMCPTool] | dict[str, FastMCPTool],
        **kwargs: Any,  # pyright: ignore[reportAny]
    ) -> tuple[
        GoogleGenaiCompletionExtras,
        CompletionMessageType,
        list[GoogleGenaiPendingToolCall],
    ]:
        """Tools completion."""

        extras, message, pending_tool_calls = await self._tool(system_prompt, messages, tools, **kwargs)
        return extras, message, pending_tool_calls


def get_extras(generate_content_response: GenerateContentResponse, message: Content) -> GoogleGenaiCompletionExtras:
    """Get the extras from a completion."""

    thinking = extract_thinking_from_message(message)

    return GoogleGenaiCompletionExtras(
        raw=generate_content_response.model_dump(),
        thinking=thinking,
        token_usage=generate_content_response.usage_metadata.total_token_count if generate_content_response.usage_metadata else None,
        raw_token_usage=generate_content_response.usage_metadata.model_dump() if generate_content_response.usage_metadata else None,
    )


def extract_thinking_from_message(message: Content | Mapping[str, Any]) -> str | None:
    """Extract the thinking from a message."""

    if not (thinking_parts := extract_thinking_parts_from_message(message)):
        return None

    return "".join([part.text for part in thinking_parts if part.text])


def extract_thinking_parts_from_message(
    message: Content | Mapping[str, Any],
) -> list[Part] | None:
    """Extract the thinking from a message."""

    if isinstance(message, Mapping):
        message = Content(**message)  # pyright: ignore[reportAny]

    if not (parts := message.parts):
        return None

    return [part for part in parts if part.thought]


def reasoning_effort_to_thinking_config(
    reasoning_effort: Literal["low", "medium", "high"] | None,
) -> ThinkingConfig | None:
    """Convert a reasoning effort to a thinking config."""
    if not reasoning_effort:
        return None

    thinking_budget: int = 0

    match reasoning_effort:
        case "low":
            thinking_budget = 1024
        case "medium":
            thinking_budget = 2048
        case "high":
            thinking_budget = 4096

    return ThinkingConfig(
        include_thoughts=True,
        thinking_budget=thinking_budget,
    )


def get_candidate_from_content_response(
    response: GenerateContentResponse,
) -> Candidate:
    """Get a candidate from a content response."""

    if not response.candidates:
        msg = "No candidates in the response."
        raise ValueError(msg)

    if not (first_candidate := response.candidates[0]):
        msg = "No candidates in the response."
        raise ValueError(msg)

    return first_candidate


def get_content_from_generate_content_response(
    response: GenerateContentResponse,
) -> Content:
    """Get content from a generate content response."""

    if not (candidate := get_candidate_from_content_response(response)):
        msg = "No candidates in the response."
        raise ValueError(msg)

    if not (content := candidate.content):
        msg = "No content in the candidate."
        raise ValueError(msg)

    return content


def convert_messages_to_gemini_content(
    messages: Sequence[CompletionMessageType] | CompletionMessageType,
) -> list[ContentUnion]:
    """Convert messages to Gemini messages."""

    new_contents: list[Content] = []

    for message in messages:
        if isinstance(message, str):
            new_contents.append(UserContent(parts=[Part(text=message)]))
        else:
            new_contents.append(CONTENT_TYPE_ADAPTER.validate_python(message))

    merged_contents: list[ContentUnion] = []

    # We need to find adjacent tool call messages and merge them into a single message, there can be more than 2
    current_tool_message: Content | None = None

    for i in range(len(new_contents)):
        current_message: ContentUnion = new_contents[i]

        if not current_tool_message and current_message.role == "tool":
            current_tool_message = current_message
        elif current_tool_message and current_message.role == "tool":
            if not current_tool_message.parts:
                msg = "No parts in the accumulator message."
                raise ValueError(msg)

            if not current_message.parts:
                msg = "No parts in the current message."
                raise ValueError(msg)

            current_tool_message.parts.extend(current_message.parts)
        elif current_tool_message:
            merged_contents.append(current_tool_message)
            current_tool_message = None
            merged_contents.append(current_message)
        else:
            merged_contents.append(current_message)

    if current_tool_message:
        merged_contents.append(current_tool_message)

    return merged_contents


class FlexibleSchema(Schema):
    """A flexible schema that can be used to convert FastMCP tools to Gemini tools."""

    defs: dict[str, "FlexibleSchema"] | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        default=None,
        validation_alias=AliasChoices("$defs"),
        description="""Optional. A map of definitions for use by `ref` Only allowed at the root of the schema.""",
    )
    ref: str | None = Field(
        default=None,
        validation_alias=AliasChoices("$ref"),
        description="""Optional. Allows indirect references between schema nodes. The value should be a valid reference to a child of the root `defs`. For example, the following schema defines a reference to a schema node named "Pet": type: object properties: pet: ref: #/defs/Pet defs: Pet: type: object properties: name: type: string The value of the "pet" property is a reference to the schema node named "Pet". See details in https://json-schema.org/understanding-json-schema/structuring""",  # noqa: E501
    )
    properties: dict[str, "FlexibleSchema"] | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        default=None,
        description="""Optional. SCHEMA FIELDS FOR TYPE OBJECT Properties of Type.OBJECT.""",
    )

    items: "FlexibleSchema | None" = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        default=None,
        description="""Optional. SCHEMA FIELDS FOR TYPE ARRAY Items of Type.ARRAY.""",
    )

    const: Any | None = Field(
        default=None,
        description="""Optional. Constant value. The value must be a constant. For example, if you want to specify a constant value for a string, you can use the following schema: type: string const: "Hello, world!""",  # noqa: E501
        exclude=True,
    )

    examples: list[Any] | None = Field(
        default=None,
        description="""Optional. Examples of the schema.""",
        exclude=True,
    )

    any_of: list["FlexibleSchema"] | None = Field(
        default=None,
        description="""Optional. The value should be validated against any (one or more) of the subschemas in the list.""",
    )
    # @field_validator("format")
    # @classmethod
    # def validate_format(cls, v: str | None) -> str | None:
    #     """Validate the format."""
    #     if v and v not in ["float", "double", "int32", "int64", "email", "byte"]:
    #         return None

    #     return v

    @model_validator(mode="after")
    def normalize(self) -> Self:
        """Remove the default if anyOf is present."""
        if self.any_of:
            del self.default

        if self.const:
            self.default: Any = self.const  # pyright: ignore[reportAny]
            del self.const

        if self.format and self.format not in ["float", "double", "int32", "int64", "email", "byte"]:
            del self.format

        return self

    def to_schema(self) -> Schema:
        """Convert the FlexibleSchema to a Schema."""
        return Schema(
            **self.model_dump(exclude_none=True),  # pyright: ignore[reportAny]
        )


def convert_fastmcp_tools_to_gemini_tool(
    fastmcp_tools: Sequence[FastMCPTool] | dict[str, FastMCPTool],
) -> GeminiTool:
    """Convert FastMCP tools to Gemini tools."""

    if isinstance(fastmcp_tools, dict):
        fastmcp_tools = list(fastmcp_tools.values())

    return GeminiTool(function_declarations=[convert_fastmcp_tool_parameters_to_function_declaration(tool) for tool in fastmcp_tools])


def convert_fastmcp_tool_parameters_to_function_declaration(
    fastmcp_tool: FastMCPTool,
) -> FunctionDeclaration:
    """Convert a FastMCP tool parameters to a Gemini function declaration."""

    parameters: dict[str, Any] = fastmcp_tool.parameters.copy()

    parameters = replace_refs(
        obj=parameters,
        lazy_load=False,
        proxies=False,
        merge_props=True,
        jsonschema=True,
    )  # pyright: ignore[reportAssignmentType, reportUnknownVariableType]

    parameters.pop("$defs", None)

    schema = FlexibleSchema(
        **parameters,  # pyright: ignore[reportAny]
    ).model_dump(exclude_none=True)

    return FunctionDeclaration(name=fastmcp_tool.name, description=fastmcp_tool.description, parameters=schema)  # pyright: ignore[reportArgumentType]
