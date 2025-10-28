"""Instrumentation helpers for common libraries - Logfire-style API."""

from typing import Optional
from opentelemetry.sdk.trace import TracerProvider


def instrument_pydantic_ai(tracer_provider: Optional[TracerProvider] = None) -> None:
    """Instrument Pydantic AI for OpenTelemetry tracing.

    Args:
        tracer_provider: Optional tracer provider. Uses global if None.
    """
    try:
        from pydantic_ai import Agent
        from pydantic_ai.models.instrumented import InstrumentationSettings
    except ImportError:
        raise ImportError(
            "pydantic-ai is required for instrumentation. "
            "Install with: pip install pydantic-ai"
        )

    if tracer_provider is None:
        from opentelemetry import trace
        tracer_provider = trace.get_tracer_provider()

    instrumentation_settings = InstrumentationSettings(tracer_provider=tracer_provider)
    Agent.instrument_all(instrumentation_settings)


def instrument_httpx(tracer_provider: Optional[TracerProvider] = None) -> None:
    """Instrument HTTPX for OpenTelemetry tracing.

    Args:
        tracer_provider: Optional tracer provider. Uses global if None.
    """
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    except ImportError:
        raise ImportError(
            "opentelemetry-instrumentation-httpx is required. "
            "Install with: pip install opentelemetry-instrumentation-httpx"
        )

    HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)


def instrument_requests(tracer_provider: Optional[TracerProvider] = None) -> None:
    """Instrument requests library for OpenTelemetry tracing.

    Args:
        tracer_provider: Optional tracer provider. Uses global if None.
    """
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
    except ImportError:
        raise ImportError(
            "opentelemetry-instrumentation-requests is required. "
            "Install with: pip install opentelemetry-instrumentation-requests"
        )

    RequestsInstrumentor().instrument(tracer_provider=tracer_provider)


def instrument_sqlite3(tracer_provider: Optional[TracerProvider] = None) -> None:
    """Instrument sqlite3 for OpenTelemetry tracing.

    Args:
        tracer_provider: Optional tracer provider. Uses global if None.
    """
    try:
        from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
    except ImportError:
        raise ImportError(
            "opentelemetry-instrumentation-sqlite3 is required. "
            "Install with: pip install opentelemetry-instrumentation-sqlite3"
        )

    SQLite3Instrumentor().instrument(tracer_provider=tracer_provider)


def instrument_asyncio(tracer_provider: Optional[TracerProvider] = None) -> None:
    """Instrument asyncio for OpenTelemetry tracing.

    Args:
        tracer_provider: Optional tracer provider. Uses global if None.
    """
    try:
        from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
    except ImportError:
        raise ImportError(
            "opentelemetry-instrumentation-asyncio is required. "
            "Install with: pip install opentelemetry-instrumentation-asyncio"
        )

    AsyncioInstrumentor().instrument(tracer_provider=tracer_provider)


def instrument_fastapi(app, tracer_provider: Optional[TracerProvider] = None) -> None:
    """Instrument FastAPI for OpenTelemetry tracing.

    Args:
        app: FastAPI application instance
        tracer_provider: Optional tracer provider. Uses global if None.
    """
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        raise ImportError(
            "opentelemetry-instrumentation-fastapi is required. "
            "Install with: pip install opentelemetry-instrumentation-fastapi"
        )

    FastAPIInstrumentor().instrument_app(app, tracer_provider=tracer_provider)


def auto_instrument(tracer_provider: Optional[TracerProvider] = None) -> None:
    """Automatically instrument all available libraries.

    This function attempts to instrument all supported libraries that are
    currently installed. It will silently skip any that are not available.

    Args:
        tracer_provider: Optional tracer provider. Uses global if None.
    """
    # List of instrumentation functions to try
    instrumentors = [
        ("pydantic-ai", instrument_pydantic_ai),
        ("httpx", instrument_httpx),
        ("requests", instrument_requests),
        ("sqlite3", instrument_sqlite3),
        ("asyncio", instrument_asyncio),
    ]

    instrumented = []
    skipped = []

    for name, instrumentor in instrumentors:
        try:
            instrumentor(tracer_provider)
            instrumented.append(name)
        except ImportError:
            skipped.append(name)
        except Exception as e:
            # Log but don't fail on instrumentation errors
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to instrument {name}: {e}"
            )
            skipped.append(name)

    if instrumented:
        import logging
        logging.getLogger(__name__).info(
            f"Auto-instrumented: {', '.join(instrumented)}"
        )