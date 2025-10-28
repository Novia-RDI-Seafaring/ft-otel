"""Main streaming component for FastHTML OpenTelemetry integration."""

import asyncio
import functools
import queue
from typing import Optional, Union
from fasthtml.common import FastHTML, Script, Link, Div, H2, to_xml
from sse_starlette import EventSourceResponse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry import trace

from .processors import FastHTMLSpanProcessor, ThreadSafeSpanProcessor
from .renderers import SpanRenderer, DefaultSpanRenderer


class OTelStreamer:
    """OpenTelemetry streamer for FastHTML applications."""

    def __init__(
        self,
        app: FastHTML,
        container_id: str = "telemetry-container",
        endpoint: str = "/telemetry",
        renderer: Optional[SpanRenderer] = None,
        tracer_provider: Optional[TracerProvider] = None,
        auto_setup_headers: bool = True,
        use_thread_safe_queue: bool = True
    ):
        """Initialize the OpenTelemetry streamer.

        Args:
            app: FastHTML application instance
            container_id: ID of the HTML container for telemetry data
            endpoint: SSE endpoint for streaming telemetry
            renderer: Custom span renderer (defaults to DefaultSpanRenderer)
            tracer_provider: Existing tracer provider (creates new if None)
            auto_setup_headers: Whether to automatically add required CSS/JS headers
            use_thread_safe_queue: Whether to use thread-safe queue.Queue (True) or asyncio.Queue (False)
        """
        self.app = app
        self.container_id = container_id
        self.endpoint = endpoint
        self.renderer = renderer or DefaultSpanRenderer()
        self.auto_setup_headers = auto_setup_headers
        self.use_thread_safe_queue = use_thread_safe_queue
        self.custom_renderers = []  # List of custom renderers in priority order

        # Set up queue based on preference
        if use_thread_safe_queue:
            self.queue = queue.Queue()
        else:
            self.queue = asyncio.Queue()

        # Set up tracer provider
        self.tracer_provider = tracer_provider
        if not self.tracer_provider:
            self.tracer_provider = TracerProvider()

        # Always set as global tracer provider (this is needed for spans to be processed)
        trace.set_tracer_provider(self.tracer_provider)

        # Set up processor
        if use_thread_safe_queue:
            self.processor = ThreadSafeSpanProcessor(
                self.queue, self.renderer, self.container_id
            )
        else:
            self.processor = FastHTMLSpanProcessor(
                self.queue, self.renderer, self.container_id
            )

        # Add processor to tracer provider
        self.tracer_provider.add_span_processor(self.processor)

        # Set up FastHTML integration
        self._setup_fasthtml()

    def add_renderer(self, renderer) -> None:
        """Add a custom renderer to the priority list.

        Args:
            renderer: Custom renderer that implements can_render() method
        """
        self.custom_renderers.append(renderer)
        # Update the processor to use the new renderer list
        if hasattr(self.processor, 'renderers'):
            self.processor.renderers = self.custom_renderers

    def _setup_fasthtml(self) -> None:
        """Set up FastHTML routes and headers."""
        # Add headers if requested
        if self.auto_setup_headers:
            self._add_headers()

        # Add telemetry streaming endpoint
        @self.app.get(self.endpoint)
        async def telemetry_stream():
            return EventSourceResponse(self._telemetry_generator())

    def _add_headers(self) -> None:
        """Add required CSS and JavaScript headers."""
        # Get existing headers
        existing_headers = list(getattr(self.app, 'hdrs', []) or [])

        # Import picolink from fasthtml
        try:
            from fasthtml.common import picolink
        except ImportError:
            picolink = None

        # Required headers
        required_headers = [
            Script(src="https://cdn.tailwindcss.com"),
            Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/daisyui@4.11.1/dist/full.min.css"),
            Script(src="https://unpkg.com/htmx-ext-sse@2.2.1/sse.js"),
            self._get_telemetry_script()
        ]

        # Add picolink if available
        if picolink:
            required_headers.insert(1, picolink)

        # Simply append new headers (FastHTML can handle duplicates)
        self.app.hdrs = tuple(existing_headers + required_headers)

    def _header_exists(self, header, existing_headers) -> bool:
        """Check if a header already exists."""
        header_str = str(header)
        return any(str(existing) in header_str or header_str in str(existing) for existing in existing_headers)

    def _get_telemetry_script(self) -> Script:
        """Get the telemetry JavaScript for auto-scrolling and processing."""
        return Script(f"""
            console.log('FastHTML OpenTelemetry script loaded');

            document.addEventListener('htmx:afterProcessNode', (evt) => {{
                const el = document.getElementById('{self.container_id}');
                if (!el) return;

                // Check if the event's target was inserted into the telemetry container
                if (el.contains(evt.target)) {{
                    console.log('New telemetry content added');
                    try {{
                        htmx.process(el);
                    }} catch(e) {{
                        console.warn('HTMX processing error:', e);
                    }}

                    // Auto-scroll to bottom
                    el.scrollTop = el.scrollHeight;
                }}
            }});

            // Handle SSE connection status
            document.addEventListener('htmx:sseError', (evt) => {{
                console.warn('SSE connection error:', evt.detail);
            }});

            document.addEventListener('htmx:sseOpen', (evt) => {{
                console.log('SSE connection opened');
            }});
        """)

    async def _telemetry_generator(self):
        """Generate telemetry events for SSE streaming."""
        while True:
            try:
                if self.use_thread_safe_queue:
                    # Use thread executor for blocking queue.get() with timeout
                    try:
                        msg = await asyncio.get_event_loop().run_in_executor(
                            None,
                            functools.partial(self.queue.get, block=True, timeout=1.0)
                        )
                        yield {"event": "TelemetryEvent", "data": msg}
                    except:
                        # Timeout or empty queue, yield heartbeat to keep connection alive
                        yield {"event": "heartbeat", "data": ""}
                        await asyncio.sleep(1.0)
                else:
                    # Use asyncio queue directly with timeout
                    try:
                        msg = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                        yield {"event": "TelemetryEvent", "data": msg}
                    except asyncio.TimeoutError:
                        # Timeout, yield heartbeat
                        yield {"event": "heartbeat", "data": ""}
                        await asyncio.sleep(1.0)

            except Exception as e:
                # Log error and continue
                import logging
                logging.exception(f"Error in telemetry generator: {e}")
                await asyncio.sleep(0.1)

    def create_container(
        self,
        title: str = "Live Telemetry",
        cls: str = "h-96 overflow-y-auto p-4 bg-base-300 rounded border"
    ) -> Div:
        """Create a telemetry container div with SSE connection.

        Args:
            title: Title for the telemetry section
            cls: CSS classes for the container

        Returns:
            Div element ready for inclusion in your page
        """
        return Div(
            H2(title, cls="text-xl font-bold mb-4") if title else None,
            Div(
                hx_ext="sse",
                sse_connect=self.endpoint,
                sse_swap="TelemetryEvent",
                hx_swap="beforeend",
                id=self.container_id,
                cls=cls
            )
        )

    def get_tracer_provider(self) -> TracerProvider:
        """Get the tracer provider for manual instrumentation."""
        return self.tracer_provider

    def shutdown(self) -> None:
        """Shutdown the streamer and clean up resources."""
        if self.processor:
            self.processor.shutdown()


# Global streamer instance for configure() pattern
_global_streamer = None

def configure(
    app: FastHTML,
    tracer_provider,
    container_id: str = "telemetry-container",
    endpoint: str = "/telemetry",
    renderer: Optional[SpanRenderer] = None,
    auto_setup_headers: bool = True,
    use_thread_safe_queue: bool = True,
    auto_expand_patterns: Optional[list] = None,
    renderers: Optional[list] = None
) -> OTelStreamer:
    """Configure FastHTML OpenTelemetry streaming (logfire-style API).

    Args:
        app: FastHTML application instance
        tracer_provider: OpenTelemetry tracer provider to use
        container_id: ID of the HTML container for telemetry data
        endpoint: SSE endpoint for streaming telemetry
        renderer: Custom span renderer (defaults to DefaultSpanRenderer)
        auto_setup_headers: Whether to automatically add required CSS/JS headers
        use_thread_safe_queue: Whether to use thread-safe queue.Queue (True) or asyncio.Queue (False)
        auto_expand_patterns: List of span name patterns to auto-expand (e.g., ["Tool:", "agent run"])
        renderers: List of custom renderers to try in order before falling back to default

    Example:
        ```python
        class CustomRenderer(ft_otel.SpanRenderer):
            def can_render(self, span):
                attrs = span.attributes or {}
                return attrs.get("foo") == "bar" and attrs.get("bax") == 123

        ft_otel.configure(
            app, provider,
            renderers=[CustomRenderer(), OtherRenderer()]
        )
        ```

    Returns:
        OTelStreamer instance for advanced usage
    """
    global _global_streamer

    # Create default renderer with auto_expand_patterns if none provided
    if renderer is None and auto_expand_patterns is not None:
        from .renderers import DefaultSpanRenderer
        renderer = DefaultSpanRenderer(auto_expand_patterns=auto_expand_patterns)

    _global_streamer = OTelStreamer(
        app=app,
        container_id=container_id,
        endpoint=endpoint,
        renderer=renderer,
        tracer_provider=tracer_provider,
        auto_setup_headers=auto_setup_headers,
        use_thread_safe_queue=use_thread_safe_queue
    )

    # Register custom renderers if provided
    if renderers:
        for custom_renderer in renderers:
            _global_streamer.add_renderer(custom_renderer)

    return _global_streamer

def add_renderer(renderer) -> None:
    """Add a custom renderer to the global streamer.

    Args:
        renderer: Custom renderer that implements can_render() method

    Example:
        ```python
        class CustomRenderer(ft_otel.SpanRenderer):
            def can_render(self, span):
                attrs = span.attributes or {}
                return attrs.get("foo") == "bar" and attrs.get("bax") == 123

        ft_otel.add_renderer(CustomRenderer())
        ```
    """
    global _global_streamer
    if _global_streamer:
        _global_streamer.add_renderer(renderer)

def register_attribute_renderer(attribute_key: str, renderer) -> None:
    """Register a custom renderer for spans with a specific attribute.

    This is a convenience function that creates a renderer for a single attribute.

    Args:
        attribute_key: Attribute key to match (e.g., "gen_ai.operation.name")
        renderer: Base renderer to wrap with attribute filtering
    """
    class AttributeRenderer(type(renderer)):
        def __init__(self):
            # Copy all attributes from the original renderer
            for attr_name in dir(renderer):
                if not attr_name.startswith('_'):
                    setattr(self, attr_name, getattr(renderer, attr_name))

        def can_render(self, span):
            attrs = span.attributes or {}
            return attribute_key in attrs

    add_renderer(AttributeRenderer())

def telemetry_container(
    title: str = "Live OpenTelemetry Traces",
    cls: str = "h-[70vh] overflow-y-auto p-4 bg-base-300 rounded-lg border"
) -> Div:
    """Create a telemetry container div with SSE connection.

    Args:
        title: Title for the telemetry section
        cls: CSS classes for the container

    Returns:
        Div element ready for inclusion in your page
    """
    if _global_streamer is None:
        raise RuntimeError("Must call configure() before telemetry_container()")

    return _global_streamer.create_container(title=title, cls=cls)

def otel_streamer(
    app: FastHTML,
    container_id: str = "telemetry-container",
    endpoint: str = "/telemetry",
    renderer: Optional[SpanRenderer] = None,
    tracer_provider: Optional[TracerProvider] = None,
    auto_setup_headers: bool = True,
    use_thread_safe_queue: bool = True
) -> OTelStreamer:
    """One-line setup for OpenTelemetry streaming in FastHTML.

    Args:
        app: FastHTML application instance
        container_id: ID of the HTML container for telemetry data
        endpoint: SSE endpoint for streaming telemetry
        renderer: Custom span renderer (defaults to DefaultSpanRenderer)
        tracer_provider: Existing tracer provider (creates new if None)
        auto_setup_headers: Whether to automatically add required CSS/JS headers
        use_thread_safe_queue: Whether to use thread-safe queue.Queue (True) or asyncio.Queue (False)

    Returns:
        OTelStreamer instance for advanced usage

    Example:
        ```python
        from fasthtml.common import *
        from fasthtml_otel import otel_streamer

        app = FastHTML()
        otel_streamer(app)

        @app.get("/")
        def index():
            return Div("Hello World")
        ```
    """
    return OTelStreamer(
        app=app,
        container_id=container_id,
        endpoint=endpoint,
        renderer=renderer,
        tracer_provider=tracer_provider,
        auto_setup_headers=auto_setup_headers,
        use_thread_safe_queue=use_thread_safe_queue
    )