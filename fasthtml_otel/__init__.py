"""FastHTML OpenTelemetry Streamer - Real-time telemetry streaming for FastHTML apps."""

from .streamer import otel_streamer, OTelStreamer, configure, telemetry_container, register_attribute_renderer, add_renderer
from .renderers import SpanRenderer, DefaultSpanRenderer
from .processors import FastHTMLSpanProcessor
from .instrument import instrument_pydantic_ai

__version__ = "0.1.0"
__all__ = [
    "otel_streamer",
    "OTelStreamer",
    "configure",
    "telemetry_container",
    "register_attribute_renderer",
    "add_renderer",
    "SpanRenderer",
    "DefaultSpanRenderer",
    "FastHTMLSpanProcessor",
    "instrument_pydantic_ai",
]