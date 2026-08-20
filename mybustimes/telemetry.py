import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)


def setup_telemetry():
    if not isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
        return

    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", "mybustimes"),
            "deployment.environment": os.getenv(
                "OTEL_ENVIRONMENT",
                "development",
            ),
        }
    )

    provider = TracerProvider(resource=resource)

    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
            "https://data.nextstoplabs.org/v1/traces",
        )
    )

    provider.add_span_processor(
        BatchSpanProcessor(otlp_exporter)
    )

    # TEMPORARY: print spans to the terminal too.
    provider.add_span_processor(
        BatchSpanProcessor(ConsoleSpanExporter())
    )

    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument()


setup_telemetry()