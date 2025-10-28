"""OpenTelemetry span processors for FastHTML streaming."""

import asyncio
import logging
from typing import Optional, Dict, Set
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan
from opentelemetry import context as context_api
from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    attach,
    detach,
    set_value,
)
from fasthtml.common import Div, to_xml

from .renderers import SpanRenderer, DefaultSpanRenderer

logger = logging.getLogger(__name__)


class FastHTMLSpanProcessor(SpanProcessor):
    """Span processor that streams telemetry data to FastHTML via SSE."""

    def __init__(
        self,
        queue: asyncio.Queue,
        renderer: Optional[SpanRenderer] = None,
        container_id: str = "telemetry-container"
    ):
        """Initialize the processor.

        Args:
            queue: Asyncio queue for streaming span data
            renderer: Span renderer (defaults to DefaultSpanRenderer)
            container_id: ID of the container for root spans
        """
        self.queue = queue
        self.renderer = renderer or DefaultSpanRenderer()
        self.container_id = container_id

        # Track spans and their relationships
        self.spans: Dict[int, ReadableSpan] = {}
        self.parent_child_map: Dict[int, int] = {}  # child_id -> parent_id
        self.pending_updates: Set[int] = set()  # spans waiting for final updates
        self.renderer_filters = []  # List of (filter_func, renderer) tuples

    def on_start(self, span: ReadableSpan, parent_context: Optional[context_api.Context] = None) -> None:
        """Called when a span starts."""
        try:
            span_id = span.context.span_id
            self.spans[span_id] = span

            # Get parent span ID from parent_context if available
            parent_id = None
            if parent_context:
                from opentelemetry import trace
                parent_span = trace.get_current_span(parent_context)
                if parent_span and parent_span.is_recording():
                    parent_span_context = parent_span.get_span_context()
                    if parent_span_context and parent_span_context.is_valid:
                        parent_id = parent_span_context.span_id
                        self.parent_child_map[span_id] = parent_id

            # Fallback to span.parent if no parent found from context
            if not parent_id and span.parent:
                parent_id = span.parent.span_id
                self.parent_child_map[span_id] = parent_id

            # Determine target container
            target_id = f"span-children-{parent_id}" if parent_id else self.container_id
            children_container_id = f"span-children-{span_id}"

            # Render the span - root spans (no parent) should be open by default
            is_root = parent_id is None
            span_html = self.renderer.render_complete_span(span, children_container_id, is_root=is_root)

            # Wrap with HTMX out-of-band update
            wrapper = Div(
                span_html,
                hx_swap_oob="beforeend",
                id=target_id
            )

            # Queue for streaming
            self._queue_update(to_xml(wrapper))

        except Exception as e:
            logger.exception(f"Error in on_start for span {span.name}: {e}")

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span ends."""
        try:
            span_id = span.context.span_id
            self.spans[span_id] = span

            # Update the span header with final status and duration
            updated_header = self.renderer.render_header(span)
            header_wrapper = Div(
                updated_header,
                hx_swap_oob="innerHTML",
                id=f"span-header-{span_id}"
            )

            # Update attributes (might have changed)
            updated_attributes = self.renderer.render_attributes(span)
            attr_wrapper = Div(
                updated_attributes,
                hx_swap_oob="innerHTML",
                id=f"span-attributes-{span_id}"
            )

            # Update events (might have been added)
            updated_events = self.renderer.render_events(span)
            events_wrapper = Div(
                updated_events,
                hx_swap_oob="innerHTML",
                id=f"span-events-{span_id}"
            )

            # Queue all updates
            self._queue_update(to_xml(header_wrapper))
            self._queue_update(to_xml(attr_wrapper))
            self._queue_update(to_xml(events_wrapper))

        except Exception as e:
            logger.exception(f"Error in on_end for span {span.name}: {e}")

    def shutdown(self) -> None:
        """Shutdown the processor."""
        logger.info("FastHTMLSpanProcessor shutting down")

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any pending spans."""
        return True

    def _queue_update(self, html: str) -> None:
        """Queue an HTML update for streaming."""
        try:
            # Use asyncio.create_task to queue without blocking
            if asyncio.get_running_loop():
                asyncio.create_task(self.queue.put(html))
            else:
                # If no event loop is running, store for later
                logger.warning("No event loop running, update may be lost")
        except Exception as e:
            logger.exception(f"Error queuing update: {e}")


class ThreadSafeSpanProcessor(SpanProcessor):
    """Thread-safe wrapper for FastHTMLSpanProcessor using thread-safe queue."""

    def __init__(
        self,
        queue,  # Can be queue.Queue or asyncio.Queue
        renderer: Optional[SpanRenderer] = None,
        container_id: str = "telemetry-container"
    ):
        """Initialize with either a thread-safe queue.Queue or asyncio.Queue."""
        import queue as sync_queue

        self.queue = queue
        self.is_async_queue = isinstance(queue, asyncio.Queue)
        self.is_sync_queue = isinstance(queue, sync_queue.Queue)

        self.renderer = renderer or DefaultSpanRenderer()
        self.container_id = container_id
        self.spans: Dict[int, ReadableSpan] = {}
        self.parent_child_map: Dict[int, int] = {}
        self.renderers = []  # List of renderers in priority order

    def _get_renderer_for_span(self, span: ReadableSpan):
        """Get the appropriate renderer for a span.

        Tries each renderer in order and returns the first one that can handle the span.
        Falls back to the default renderer if none match.
        """
        # Check each renderer in order
        for renderer in self.renderers:
            try:
                if renderer.can_render(span):
                    return renderer
            except Exception as e:
                logger.warning(f"Error checking renderer {type(renderer).__name__}: {e}")
                continue
        return self.renderer

    def on_start(self, span: ReadableSpan, parent_context: Optional[context_api.Context] = None) -> None:
        """Called when a span starts."""
        self._suppress_instrumentation(self._handle_start, span, parent_context)

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span ends."""
        self._suppress_instrumentation(self._handle_end, span)

    def _handle_start(self, span: ReadableSpan, parent_context: Optional[context_api.Context] = None) -> None:
        """Handle span start with telemetry suppression."""
        try:
            span_id = span.context.span_id
            self.spans[span_id] = span
            print(f"DEBUG: Processing span start: {span.name} (ID: {span_id})")

            # Get parent span ID from parent_context if available
            parent_id = None
            if parent_context:
                from opentelemetry import trace
                parent_span = trace.get_current_span(parent_context)
                if parent_span and parent_span.is_recording():
                    parent_span_context = parent_span.get_span_context()
                    if parent_span_context and parent_span_context.is_valid:
                        parent_id = parent_span_context.span_id
                        self.parent_child_map[span_id] = parent_id
                        print(f"DEBUG: Found parent {parent_id} for span {span_id}")

            # Fallback to span.parent if no parent found from context
            if not parent_id and span.parent:
                parent_id = span.parent.span_id
                self.parent_child_map[span_id] = parent_id
                print(f"DEBUG: Using span.parent {parent_id} for span {span_id}")

            target_id = f"span-children-{parent_id}" if parent_id else self.container_id
            children_container_id = f"span-children-{span_id}"
            print(f"DEBUG: Targeting container {target_id} for span {span.name}")

            # Render the span - root spans (no parent) should be open by default
            is_root = parent_id is None
            renderer = self._get_renderer_for_span(span)
            span_html = renderer.render_complete_span(span, children_container_id, is_root=is_root)
            wrapper = Div(span_html, hx_swap_oob="beforeend", id=target_id)

            self._put_in_queue(to_xml(wrapper))

        except Exception as e:
            logger.exception(f"Error handling span start: {e}")
            print(f"DEBUG ERROR: {e}")

    def _handle_end(self, span: ReadableSpan) -> None:
        """Handle span end with telemetry suppression."""
        try:
            span_id = span.context.span_id
            self.spans[span_id] = span

            # Send updates immediately as they happen using the appropriate renderer
            renderer = self._get_renderer_for_span(span)

            updated_header = renderer.render_header(span)
            header_wrapper = Div(updated_header, hx_swap_oob="innerHTML", id=f"span-header-{span_id}")
            self._put_in_queue(to_xml(header_wrapper))

            updated_attributes = renderer.render_attributes(span)
            attr_wrapper = Div(updated_attributes, hx_swap_oob="innerHTML", id=f"span-attributes-{span_id}")
            self._put_in_queue(to_xml(attr_wrapper))

            updated_events = renderer.render_events(span)
            events_wrapper = Div(updated_events, hx_swap_oob="innerHTML", id=f"span-events-{span_id}")
            self._put_in_queue(to_xml(events_wrapper))

        except Exception as e:
            logger.exception(f"Error handling span end: {e}")

    def _put_in_queue(self, data: str) -> None:
        """Put data in the appropriate queue type."""
        try:
            if self.is_async_queue:
                # For asyncio.Queue, use create_task if loop is running
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.queue.put(data))
                except RuntimeError:
                    logger.warning("No event loop running for asyncio.Queue")
            elif self.is_sync_queue:
                # For queue.Queue, put directly (thread-safe)
                self.queue.put_nowait(data)
            else:
                logger.error(f"Unsupported queue type: {type(self.queue)}")
        except Exception as e:
            logger.exception(f"Error putting data in queue: {e}")

    def _suppress_instrumentation(self, func, *args, **kwargs):
        """Execute function with instrumentation suppressed to avoid recursion."""
        token = attach(set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
        try:
            return func(*args, **kwargs)
        finally:
            detach(token)

    def shutdown(self) -> None:
        """Shutdown the processor."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any pending spans."""
        return True