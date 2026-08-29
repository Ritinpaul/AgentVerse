"""
OpenTelemetry Bootstrap & Metrics Exporter Config.
"""
from __future__ import annotations
import os
import logging
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger("telemetry")


def setup_telemetry(service_name: str = "agentstore-backend") -> None:
    """
    Initialize OpenTelemetry TracerProvider and MeterProvider.
    Exports to OTLP endpoint if OTEL_EXPORTER_OTLP_ENDPOINT is defined,
    otherwise falls back to ConsoleSpanExporter for dev.
    """
    resource = Resource.create({"service.name": service_name, "env": os.getenv("ENVIRONMENT", "development")})

    # 1. Tracing Setup
    tracer_provider = TracerProvider(resource=resource)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OpenTelemetry OTLP trace exporter initialized -> {otlp_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to initialize OTLP exporter ({e}), using console exporter fallback.")
            tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        # Dev fallback - silent or console
        pass

    trace.set_tracer_provider(tracer_provider)

    # 2. Metrics Setup
    meter_provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(meter_provider)

    logger.info(f"OpenTelemetry telemetry initialized for '{service_name}'")


def get_tracer(name: str):
    return trace.get_tracer(name)


def get_meter(name: str):
    return metrics.get_meter(name)
