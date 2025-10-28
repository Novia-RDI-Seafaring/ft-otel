"""Pydantic AI instrumentation for OpenTelemetry."""

from typing import Optional
from opentelemetry.sdk.trace import TracerProvider


def instrument_pydantic_ai(tracer_provider: Optional[TracerProvider] = None) -> None:
    """Instrument Pydantic AI for OpenTelemetry tracing.

    This function only handles the instrumentation setup. To customize rendering,
    use attribute_renderers in configure() or register_attribute_renderer().

    Example:
        ```python
        # Configure with AI renderer for gen_ai spans
        ft_otel.configure(
            app, provider,
            attribute_renderers={
                "gen_ai.operation.name": ft_otel.AISpanRenderer()
            }
        )

        # Then instrument Pydantic AI
        ft_otel.instrument_pydantic_ai(provider)
        ```

    Args:
        tracer_provider: Optional tracer provider. Uses global if None.

    Raises:
        ImportError: If pydantic-ai is not installed.
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