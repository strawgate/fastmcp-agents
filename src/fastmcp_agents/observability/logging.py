"""Logging configuration for FastMCP Agents."""

import logging
import os
from typing import Literal

import asyncclick
import fastmcp
import mcp
from rich.console import Console
from rich.logging import RichHandler

BASE_LOGGER = logging.getLogger("agents")


class NoTracebackFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("[bold blue]{name}[/bold blue]: {message}", style="{")

    def format(self, record):
        if record.exc_info:
            record.stack_info = None
            # record.exc_text = self.formatException(record.exc_text)
            # record.exc_info = None  # Prevent default traceback formatting
        return super().format(record)


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO",
    show_tracebacks: bool = False,
):
    handler = RichHandler(
        console=Console(stderr=True),
        rich_tracebacks=True,
        markup=True,
        show_path=False,
        tracebacks_suppress=[asyncclick, fastmcp.client.client, mcp],
        tracebacks_width=70,
        tracebacks_word_wrap=False,
        tracebacks_max_frames=10,
        log_time_format="%x %X",
    )

    if not show_tracebacks:
        handler.setFormatter(NoTracebackFormatter())

    BASE_LOGGER.setLevel(level)
    BASE_LOGGER.addHandler(handler)
    BASE_LOGGER.propagate = False

    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None:
        setup_otel()

    logging.getLogger("mcp").setLevel("WARNING")
    logging.getLogger("FastMCP.fastmcp.tools").setLevel("CRITICAL")
    logging.getLogger("fastmcp").setLevel("CRITICAL")


def get_logger(name: str) -> logging.Logger:
    """Get a logger nested under FastMCP namespace.

    Args:
        name: the name of the logger, which will be prefixed with 'FastMCP.'

    Returns:
        a configured logger instance
    """
    return BASE_LOGGER.getChild(name)


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
