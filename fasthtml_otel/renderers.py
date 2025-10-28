"""Span renderers for converting OpenTelemetry spans to FastHTML components."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from fasthtml.common import Div, Span, Ul, Li, Input, Label, to_xml
from opentelemetry.sdk.trace import ReadableSpan


class SpanRenderer(ABC):
    """Abstract base class for span renderers."""

    def can_render(self, span: ReadableSpan) -> bool:
        """Check if this renderer can handle the given span.

        Override this method in custom renderers to provide conditional rendering.
        The default implementation always returns True (fallback renderer).

        Args:
            span: The span to check

        Returns:
            True if this renderer can handle the span, False otherwise
        """
        return True

    @abstractmethod
    def render_header(self, span: ReadableSpan) -> Any:
        """Render the span header (name, status, duration)."""
        pass

    @abstractmethod
    def render_attributes(self, span: ReadableSpan) -> Any:
        """Render the span attributes."""
        pass

    @abstractmethod
    def render_events(self, span: ReadableSpan) -> Any:
        """Render the span events."""
        pass

    @abstractmethod
    def render_complete_span(self, span: ReadableSpan, children_container_id: str) -> Any:
        """Render a complete span with all its components."""
        pass


class DefaultSpanRenderer(SpanRenderer):
    """Default span renderer with collapsible DaisyUI components."""

    def __init__(self, theme: str = "base", auto_expand_patterns: Optional[list] = None):
        """Initialize renderer with optional theme and auto-expand patterns."""
        self.theme = theme
        self.auto_expand_patterns = auto_expand_patterns or []
        self.status_colors = {
            "OK": "text-success",
            "ERROR": "text-error",
            "UNSET": "text-warning",
        }

    def render_header(self, span: ReadableSpan) -> Any:
        """Render span header with name, status and duration."""
        status_name = span.status.status_code.name if span.status.status_code else "UNSET"
        color = self.status_colors.get(status_name, "text-neutral")

        # Calculate duration if span is ended
        duration_text = "..."
        if span.end_time and span.start_time:
            duration_ms = (span.end_time - span.start_time) / 1e6
            duration_text = f"{duration_ms:.1f} ms"

        return Div(
            Span(span.name, cls=f"font-semibold {color}"),
            Span(f" • {status_name}", cls="text-xs opacity-70 ml-1"),
            Span(duration_text, cls="ml-auto text-xs text-neutral-content/60"),
            id=f"span-header-{span.context.span_id}",
            cls="flex justify-between items-center",
        )

    def render_attributes(self, span: ReadableSpan) -> Any:
        """Render span attributes as a list."""
        if not span.attributes:
            return Div()

        return Ul(
            *[
                Li(
                    Span(str(k), cls="text-neutral-content/70 mr-1"),
                    Span(str(v), cls="font-mono text-xs text-base-content/80 break-all"),
                    cls="flex text-xs py-[1px]"
                )
                for k, v in span.attributes.items()
            ],
            cls="pl-1 space-y-[1px]",
            id=f"span-attributes-{span.context.span_id}"
        )

    def render_events(self, span: ReadableSpan) -> Any:
        """Render span events."""
        if not span.events:
            return Div()

        return Div(
            *[
                Div(
                    Span(event.name, cls="font-medium text-xs"),
                    Span(f" @ {event.timestamp}", cls="text-xs opacity-60"),
                    cls="border-l-2 border-info pl-2 py-1"
                )
                for event in span.events
            ],
            cls="space-y-1",
            id=f"span-events-{span.context.span_id}"
        )

    def render_complete_span(self, span: ReadableSpan, children_container_id: str, is_root: bool = False) -> Any:
        """Render a span with collapsible details and visible hierarchy."""
        span_id = span.context.span_id

        # Container for child spans (always visible for hierarchy)
        children_container = Div(
            cls="pl-4 space-y-1 border-l border-base-300",
            id=children_container_id
        )

        # Collapsible details section
        details_id = f"span-details-{span_id}"
        details_content = Div(
            self.render_attributes(span),
            self.render_events(span),
            id=details_id,
            cls="collapse-content pl-4 space-y-2"
        )

        # Determine if this span should be expanded by default
        should_expand = is_root

        # Check if span name matches any auto-expand patterns
        for pattern in self.auto_expand_patterns:
            if pattern.lower() in span.name.lower():
                should_expand = True
                break

        # Collapsible span with header and details
        checkbox_id = f"span-checkbox-{span_id}"
        collapse_wrapper = Div(
            Input(type="checkbox", cls="collapse-checkbox", checked=should_expand, id=checkbox_id),
            # Make the entire header clickable by using a label as the collapse-title
            Label(
                self.render_header(span),
                for_=checkbox_id,
                cls="collapse-title text-sm font-medium p-2 hover:bg-base-200 transition-colors cursor-pointer"
            ),
            details_content,
            cls="collapse collapse-arrow bg-base-100 border border-base-300 rounded-lg my-1"
        )

        # The complete span with details and children
        return Div(
            collapse_wrapper,
            children_container,
            id=f"span-{span_id}",
            cls="my-1"
        )


class CompactSpanRenderer(SpanRenderer):
    """Compact span renderer for minimal UI."""

    def render_header(self, span: ReadableSpan) -> Any:
        status_name = span.status.status_code.name if span.status.status_code else "UNSET"
        color = "text-green-500" if status_name == "OK" else "text-red-500" if status_name == "ERROR" else "text-yellow-500"

        return Div(
            Span("●", cls=f"{color} mr-2"),
            Span(span.name, cls="font-medium text-sm"),
            cls="flex items-center",
            id=f"span-header-{span.context.span_id}"
        )

    def render_attributes(self, span: ReadableSpan) -> Any:
        return Div()  # No attributes in compact mode

    def render_events(self, span: ReadableSpan) -> Any:
        return Div()  # No events in compact mode

    def render_complete_span(self, span: ReadableSpan, children_container_id: str) -> Any:
        return Div(
            self.render_header(span),
            Div(id=children_container_id, cls="pl-6"),
            id=f"span-{span.context.span_id}",
            cls="py-1"
        )


