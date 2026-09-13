import logging
import os

try:
    from opentelemetry import trace
    from opentelemetry._logs import set_logger_provider

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.exporter.otlp.proto.http._log_exporter import (
        OTLPLogExporter,
    )

    from opentelemetry.instrumentation.django import DjangoInstrumentor

    from opentelemetry.sdk.resources import Resource

    from opentelemetry.sdk.trace import (
        TracerProvider,
    )
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

    from opentelemetry.sdk._logs import (
        LoggerProvider,
        LoggingHandler,
    )
    from opentelemetry.sdk._logs.export import (
        BatchLogRecordProcessor,
    )
    _OTEL_AVAILABLE = True
except ImportError as _otel_err:
    trace = None
    set_logger_provider = None
    OTLPSpanExporter = OTLPLogExporter = DjangoInstrumentor = Resource = None
    TracerProvider = BatchSpanProcessor = ConsoleSpanExporter = None
    LoggerProvider = LoggingHandler = BatchLogRecordProcessor = None
    _OTEL_AVAILABLE = False
    logging.getLogger(__name__).warning(f"OpenTelemetry not available, telemetry disabled: {_otel_err}")


def setup_telemetry():
    if not _OTEL_AVAILABLE or trace is None:
        return
    try:
        if not isinstance(
            trace.get_tracer_provider(),
            trace.ProxyTracerProvider,
        ):
            return
    except Exception:
        return

    resource = Resource.create(
        {
            "service.name": os.getenv(
                "OTEL_SERVICE_NAME",
                "mybustimes",
            ),
            "deployment.environment": os.getenv(
                "OTEL_ENVIRONMENT",
                "development",
            ),
        }
    )

    # ============================================================
    # TRACING
    # ============================================================

    tracer_provider = TracerProvider(
        resource=resource,
    )

    trace_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "https://data.nextstoplabs.org/v1/traces",
    )

    otlp_trace_exporter = OTLPSpanExporter(
        endpoint=trace_endpoint,
    )

    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            otlp_trace_exporter,
        )
    )

    # NOTE: temporarily removed the ConsoleSpanExporter that used to print
    # every span to the terminal -- it flooded the console with Signoz span
    # output and drowned out normal Django logs. Reporting is unaffected:
    # spans still flow to Signoz via the OTLP exporter above.

    trace.set_tracer_provider(
        tracer_provider,
    )

    # ============================================================
    # LOGGING
    # ============================================================

    log_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT",
        "https://data.nextstoplabs.org/v1/logs",
    )

    otlp_log_exporter = OTLPLogExporter(
        endpoint=log_endpoint,
    )

    logger_provider = LoggerProvider(
        resource=resource,
    )

    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            otlp_log_exporter,
        )
    )

    set_logger_provider(
        logger_provider,
    )

    # Send normal Python/Django logging records through OpenTelemetry.
    #
    # The LoggingHandler automatically associates the log with the
    # currently active OpenTelemetry trace/span when one exists.
    otel_handler = LoggingHandler(
        level=logging.INFO,
        logger_provider=logger_provider,
    )

    root_logger = logging.getLogger()

    root_logger.addHandler(
        otel_handler,
    )

    # ============================================================
    # DJANGO INSTRUMENTATION
    # ============================================================

    DjangoInstrumentor().instrument()


setup_telemetry()