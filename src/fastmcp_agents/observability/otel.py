"""OpenTelemetry configuration for FastMCP Agents."""

import os

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from fastmcp_agents.observability.logging import BASE_LOGGER


def setup_otel():
    import logging

    from opentelemetry import trace
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

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


if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None:
    setup_otel()
