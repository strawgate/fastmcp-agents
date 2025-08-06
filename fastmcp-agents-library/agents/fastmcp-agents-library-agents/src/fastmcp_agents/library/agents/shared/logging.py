import json
import sys
from datetime import UTC, datetime

import logfire
from logfire import ConsoleOptions
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from pydantic_ai import Agent


def get_tool_names_from_span(span: ReadableSpan) -> list[str]:
    if not span.attributes:
        return []

    if not (model_request_parameters := span.attributes.get("model_request_parameters")):
        return []

    if not isinstance(model_request_parameters, str):
        return []

    deserialized_model_request_parameters = json.loads(model_request_parameters)

    if not (function_tools := deserialized_model_request_parameters.get("function_tools")):
        return []

    return [tool["name"] for tool in function_tools]


def get_picked_tools_from_span(span: ReadableSpan) -> list[str]:
    if not span.attributes:
        return []

    if not (events := span.attributes.get("events")):
        return []

    if not isinstance(events, str):
        return []

    deserialized_events = json.loads(events)

    assistant_event = deserialized_events[-1]

    if not (message := assistant_event.get("message")):
        return []

    if not (tool_calls := message.get("tool_calls")):
        return []

    return [
        tool_call.get(
            "function",
            {},
        ).get(
            "name",
            "<unknown>",
        )
        for tool_call in tool_calls
        if tool_call.get("type") == "function"
    ]


ADDT_FORMAT_SPAN_NAMES = {"running tool"}


RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RESET = "\033[0m"


def format_span(span: ReadableSpan) -> str:
    timestamp: str | None = (
        datetime.fromtimestamp(span.start_time / 1_000_000_000, tz=UTC).strftime("[%m/%d/%y %H:%M:%S]") if span.start_time else None
    )

    span_message = span.name

    message = BLUE + "{timestamp}" + " SPAN     " + RESET + "{span_message}" + "\n"
    default_message = message.format(timestamp=timestamp, span_message=span_message)
    model_name: str | None = None

    if not span.attributes:
        return default_message

    if not span.name.startswith("chat ") and span.name not in ADDT_FORMAT_SPAN_NAMES:
        return default_message

    match span.name:
        case "running tool":
            model_name = str(span.attributes.get("gen_ai.request.model"))
            tool_name: str | None = str(span.attributes.get("gen_ai.tool.name"))
            tool_arguments: str | None = str(span.attributes.get("tool_arguments"))
            tool_response: str | None = str(span.attributes.get("tool_response"))

            span_message = (
                f"Model called {GREEN}{tool_name}{RESET}"
                + f" with arguments: {GREEN}{tool_arguments}{RESET}"
                + f" returned: {GREEN}{tool_response[:200]}{RESET}"
            )

        case _ if span.name.startswith("chat "):
            model_name = str(span.attributes.get("gen_ai.request.model"))
            picked_tools: list[str] = get_picked_tools_from_span(span)
            span_message = f"Model: {YELLOW}{model_name}{RESET} -- Picked tools: [{GREEN}{', '.join(picked_tools)}{RESET}]"

        case _:
            span_message = span.name

    return message.format(timestamp=timestamp, span_message=span_message)


def configure_console_logging():
    Agent.instrument_all()

    _ = logfire.configure(
        send_to_logfire=False,
        console=ConsoleOptions(),
        additional_span_processors=[SimpleSpanProcessor(span_exporter=ConsoleSpanExporter(formatter=format_span, out=sys.stderr))],
    )
