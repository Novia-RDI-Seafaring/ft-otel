"""Example AI span renderer for OpenTelemetry spans."""

from typing import Optional, Any
import sys
sys.path.insert(0, '..')

import fasthtml_otel as ft_otel
from fasthtml.common import Div, Span, Ul, Li, Input, Label
from opentelemetry.sdk.trace import ReadableSpan


class AISpanRenderer(ft_otel.SpanRenderer):
    """Specialized renderer for AI/GenAI spans with rich attribute display."""

    def __init__(self, auto_expand_patterns: Optional[list] = None):
        """Initialize AI renderer with auto-expand patterns."""
        self.auto_expand_patterns = auto_expand_patterns or []

    def can_render(self, span):
        """Check if this renderer can handle AI/GenAI spans."""
        attrs = span.attributes or {}
        return "gen_ai.operation.name" in attrs

    def render_header(self, span: ReadableSpan) -> Any:
        """Render AI span header with model and operation info."""
        attributes = span.attributes or {}

        # Extract key AI attributes
        operation = attributes.get("gen_ai.operation.name", span.name)
        model = attributes.get("gen_ai.request.model", "")
        system = attributes.get("gen_ai.system", "")

        # Build display name
        display_parts = [operation]
        if model:
            display_parts.append(f"({model})")

        display_name = " ".join(display_parts)

        # Status and color
        status_name = span.status.status_code.name if span.status.status_code else "UNSET"
        color = "text-success" if status_name == "OK" else "text-error" if status_name == "ERROR" else "text-warning"

        # Calculate duration
        duration_text = "..."
        if span.end_time and span.start_time:
            duration_ms = (span.end_time - span.start_time) / 1e6
            duration_text = f"{duration_ms:.1f} ms"

        return Div(
            Span(display_name, cls=f"font-semibold {color}"),
            Span(f" • {system}" if system else "", cls="text-xs opacity-70 ml-1"),
            Span(duration_text, cls="ml-auto text-xs text-neutral-content/60"),
            id=f"span-header-{span.context.span_id}",
            cls="flex justify-between items-center",
        )

    def render_attributes(self, span: ReadableSpan) -> Any:
        """Render AI attributes with special formatting for GenAI fields."""
        if not span.attributes:
            return Div()

        attributes = span.attributes
        ai_attrs = {}
        other_attrs = {}

        # Separate AI-specific attributes
        for k, v in attributes.items():
            if k.startswith("gen_ai."):
                ai_attrs[k] = v
            else:
                other_attrs[k] = v

        content = []

        # Render AI attributes with special formatting
        if ai_attrs:
            content.append(
                Div(
                    Span("AI Metrics", cls="font-medium text-sm text-primary"),
                    cls="mb-2"
                )
            )

            for k, v in ai_attrs.items():
                display_key = k.replace("gen_ai.", "").replace("_", " ").title()
                if k == "gen_ai.usage.input_tokens":
                    display_val = f"{v} tokens"
                elif k == "gen_ai.usage.output_tokens":
                    display_val = f"{v} tokens"
                elif k == "operation.cost":
                    display_val = f"${float(v):.6f}"
                elif isinstance(v, (list, dict)):
                    display_val = f"{len(v)} items" if isinstance(v, list) else "object"
                else:
                    display_val = str(v)

                content.append(
                    Li(
                        Span(display_key, cls="text-primary/70 mr-2 text-xs"),
                        Span(display_val, cls="font-mono text-xs text-base-content/80"),
                        cls="flex text-xs py-[1px]"
                    )
                )

        # Render other attributes
        if other_attrs:
            if ai_attrs:
                content.append(Div(cls="mt-3"))
            for k, v in other_attrs.items():
                content.append(
                    Li(
                        Span(str(k), cls="text-neutral-content/70 mr-1"),
                        Span(str(v), cls="font-mono text-xs text-base-content/80 break-all"),
                        cls="flex text-xs py-[1px]"
                    )
                )

        return Ul(*content, cls="pl-1 space-y-[1px]", id=f"span-attributes-{span.context.span_id}")

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
        """Render AI span with enhanced formatting."""
        span_id = span.context.span_id

        # Container for child spans
        children_container = Div(
            cls="pl-4 space-y-1 border-l border-primary/30",
            id=children_container_id
        )

        # Determine if this span should be expanded
        should_expand = is_root
        for pattern in self.auto_expand_patterns:
            if pattern.lower() in span.name.lower():
                should_expand = True
                break

        # Collapsible details section
        details_id = f"span-details-{span_id}"
        details_content = Div(
            self.render_attributes(span),
            self.render_events(span),
            id=details_id,
            cls="collapse-content pl-4 space-y-2"
        )

        # Collapsible span with header and details
        checkbox_id = f"span-checkbox-{span_id}"
        collapse_wrapper = Div(
            Input(type="checkbox", cls="collapse-checkbox", checked=should_expand, id=checkbox_id),
            Label(
                self.render_header(span),
                for_=checkbox_id,
                cls="collapse-title text-sm font-medium p-2 hover:bg-primary/10 transition-colors cursor-pointer"
            ),
            details_content,
            cls="collapse collapse-arrow bg-primary/5 border border-primary/20 rounded-lg my-1"
        )

        return Div(
            collapse_wrapper,
            children_container,
            id=f"span-{span_id}",
            cls="my-1"
        )


