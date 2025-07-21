"""Logging configuration for FastMCP Agents."""

import asyncio
import logging
import os
from typing import Literal, override

import cyclopts
import fastmcp
import mcp
import pydantic
from rich.console import Console
from rich.logging import RichHandler

BASE_LOGGER = logging.getLogger("fastmcp_agents")


class ContextFilter:
    def filter(self, record: logging.LogRecord) -> bool:
        split_name = record.name.split(".")
        if split_name[0] == "fastmcp_agents":
            record.name = split_name[-1]
        return True


class NoTracebackFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(fmt="[bold blue]{name}[/bold blue]: {message}", style="{")

    @override
    def format(self, record: logging.LogRecord):
        if record.exc_info:
            record.stack_info = None
            # record.exc_text = self.formatException(record.exc_text)
            # record.exc_info = None  # Prevent default traceback formatting
        return super().format(record)


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO",
):
    if not BASE_LOGGER.propagate:
        return

    handler = RichHandler(
        console=Console(stderr=True),
        rich_tracebacks=True,
        markup=True,
        show_path=False,
        tracebacks_suppress=[cyclopts, fastmcp, fastmcp.client.client, mcp, asyncio],
        tracebacks_width=100,
        tracebacks_word_wrap=False,
        tracebacks_max_frames=3,
        log_time_format="%x %X",
    )

    handler.setFormatter(NoTracebackFormatter())
    handler.addFilter(ContextFilter())

    BASE_LOGGER.setLevel(level)
    BASE_LOGGER.addHandler(handler)
    BASE_LOGGER.propagate = False

    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None:
        setup_otel()

    reduce_fastmcp_logging()


def reduce_fastmcp_logging():
    logging.getLogger("mcp").setLevel("ERROR")
    logging.getLogger("FastMCP.fastmcp.tools").setLevel("ERROR")
    logging.getLogger("FastMCP.fastmcp.tools.tool_manager").setLevel("CRITICAL")
    logging.getLogger("fastmcp").setLevel("ERROR")
    logging.getLogger("FastMCP.fastmcp.client.transports").setLevel("ERROR")

    fastmcp_logger = logging.getLogger("FastMCP")

    for handler in fastmcp_logger.handlers:
        if isinstance(handler, RichHandler):
            handler.tracebacks_max_frames = 3
            handler.tracebacks_suppress = [pydantic, fastmcp]


# def patched_configure_logging(
#     level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO",
#     logger: logging.Logger | None = None,
#     enable_rich_tracebacks: bool = True,
# ) -> None:
#     """
#     Configure logging for FastMCP.

#     Args:
#         logger: the logger to configure
#         level: the log level to use
#     """

#     if logger is None:
#         logger = logging.getLogger("FastMCP")

#     # Only configure the FastMCP logger namespace
#     handler = RichHandler(
#         console=Console(stderr=True),
#         rich_tracebacks=enable_rich_tracebacks,
#         tracebacks_suppress=[pydantic, fastmcp],
#         tracebacks_width=100,
#         tracebacks_word_wrap=False,
#         tracebacks_max_frames=4,
#         log_time_format="%x %X",
#     )
#     formatter = logging.Formatter("%(message)s")
#     handler.setFormatter(formatter)

#     logger.setLevel(level)

#     # Remove any existing handlers to avoid duplicates on reconfiguration
#     for hdlr in logger.handlers[:]:
#         logger.removeHandler(hdlr)

#     logger.addHandler(handler)

#     # Don't propagate to the root logger
#     logger.propagate = False


# fastmcp_logging.configure_logging = patched_configure_logging


def hide_tracebacks():
    """Hide tracebacks from a logger."""


def setup_otel():
    from opentelemetry import trace
    from opentelemetry._logs import set_logger_provider  # type: ignore
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter  # type: ignore
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler  # type: ignore
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor  # type: ignore
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)

    # Sets the global default tracer provider
    trace.set_tracer_provider(provider)

    logger_provider = LoggerProvider()
    set_logger_provider(logger_provider)

    exporter = OTLPLogExporter()
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

    # Attach OTLP handler to root logger
    BASE_LOGGER.addHandler(handler)
