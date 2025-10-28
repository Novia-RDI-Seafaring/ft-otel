"""Math renderer for displaying mathematical reasoning as a continuous paper."""

from typing import Optional, Any
import sys
sys.path.insert(0, '..')

import fasthtml_otel as ft_otel
from fasthtml.common import Div, Span, P, Ul, Li, Pre, Code, Hr
from opentelemetry.sdk.trace import ReadableSpan


class MathRenderer(ft_otel.SpanRenderer):
    """Specialized renderer for mathematical reasoning spans displayed as paper."""

    def __init__(self):
        """Initialize math renderer."""
        pass

    def can_render(self, span):
        """Check if this renderer can handle math reasoning spans."""
        attrs = span.attributes or {}
        return (
            "math.step_type" in attrs or
            "math.problem" in attrs or
            span.name.startswith("Math:") or
            span.name.startswith("Step:") or
            span.name == "Math Problem Solving Session" or
            "math.operation" in attrs or
            # Also render AI agent decision-making spans
            "gen_ai.operation.name" in attrs or
            span.name.startswith("🤖") or
            "AI Mathematical Reasoning" in span.name or
            "model" in attrs
        )

    def render_header(self, span: ReadableSpan) -> Any:
        """Don't render headers - we'll handle everything in complete_span."""
        return Div()  # Empty div

    def render_attributes(self, span: ReadableSpan) -> Any:
        """Don't render attributes separately - handled in complete_span."""
        return Div()  # Empty div

    def render_events(self, span: ReadableSpan) -> Any:
        """Don't render events separately - handled in complete_span."""
        return Div()  # Empty div

    def render_complete_span(self, span: ReadableSpan, children_container_id: str, is_root: bool = False) -> Any:
        """Render span as continuous paper format with selective filtering."""
        span_id = span.context.span_id
        attributes = span.attributes or {}

        # Always create containers for children, even if we don't render the span content
        children_container = Div(
            cls="",  # No special styling - continuous flow
            id=children_container_id
        )

        # Skip rendering content for certain spans but always provide container structure
        if not self._should_render_span(span):
            return Div(
                children_container,
                id=f"span-{span_id}",
                style="display: contents;"  # Act as if this div doesn't exist for layout
            )

        content_parts = []

        # 1. PROBLEM SEPARATOR - Add horizontal line and problem statement for new problems
        if span.name == "Math Problem Solving Session":
            problem_text = attributes.get("math.problem", "Mathematical Problem")
            content_parts.extend([
                Hr(cls="border-2 border-gray-400 my-6"),
                Div(
                    P("Problem:", cls="font-bold text-lg mb-2"),
                    P(problem_text, cls="text-base mb-4 p-3 bg-blue-50 border border-blue-200 rounded"),
                    cls="mb-6"
                )
            ])

        # 2. AI REASONING - Show only the reasoning text, clean format
        elif attributes.get("math.step_type") == "reasoning" and "math.reasoning" in attributes:
            reasoning_text = attributes.get("math.reasoning", "")
            if reasoning_text:
                content_parts.append(
                    Div(
                        P(reasoning_text, cls="text-base leading-relaxed mb-4 font-serif"),
                        cls="mb-4"
                    )
                )

        # 3. MATHEMATICAL OPERATIONS - Format as proof steps
        elif "math.operation" in attributes:
            operation = attributes.get("math.operation", "")
            formula = attributes.get("math.formula", "")
            calculation = attributes.get("math.calculation", "")
            result = attributes.get("math.result", "")
            variable_name = attributes.get("math.variable_name", "")

            step_content = []

            # Skip header if we have a variable assignment (make it cleaner)
            if not variable_name:
                # Operation header only for non-variable operations
                if operation == "addition":
                    step_content.append(P("Addition:", cls="font-medium text-blue-600 mb-1"))
                elif operation == "subtraction":
                    step_content.append(P("Subtraction:", cls="font-medium text-blue-600 mb-1"))
                elif operation == "multiplication":
                    step_content.append(P("Multiplication:", cls="font-medium text-blue-600 mb-1"))
                elif operation == "division":
                    step_content.append(P("Division:", cls="font-medium text-blue-600 mb-1"))
                elif operation == "exponentiation":
                    step_content.append(P("Exponentiation:", cls="font-medium text-blue-600 mb-1"))
                elif operation == "square_root":
                    step_content.append(P("Square Root:", cls="font-medium text-blue-600 mb-1"))
                elif operation == "discriminant":
                    step_content.append(P("Discriminant Calculation:", cls="font-medium text-blue-600 mb-1"))
                elif operation == "quadratic_roots":
                    step_content.append(P("Quadratic Root Calculation:", cls="font-medium text-blue-600 mb-1"))

            # Formula (only if no calculation, to avoid duplication)
            if formula and not calculation:
                step_content.append(
                    Pre(formula, cls="text-center font-mono text-lg bg-gray-50 p-2 border rounded mb-2")
                )

            # Calculation work - this will include variable assignments
            if calculation:
                # For variable assignments, show them prominently
                if variable_name:
                    step_content.append(
                        P(calculation, cls="font-mono text-xl font-bold text-center text-blue-800 py-3")
                    )
                else:
                    step_content.append(
                        Pre(calculation, cls="font-mono text-lg bg-gray-50 p-3 border rounded mb-2 whitespace-pre-wrap text-center")
                    )

            # Result (only if no variable assignment - avoid duplication)
            elif result and not variable_name:
                step_content.append(
                    P(f"= {result}", cls="font-bold text-lg text-green-700 text-center py-2")
                )

            if step_content:
                # Use different styling for variable assignments
                if variable_name:
                    content_parts.append(
                        Div(
                            *step_content,
                            cls="mb-3 p-2 bg-blue-50 border border-blue-200 rounded"
                        )
                    )
                else:
                    content_parts.append(
                        Div(
                            *step_content,
                            cls="mb-4 p-3 border-l-4 border-blue-300 bg-blue-50/30"
                        )
                    )

        # 4. PROBLEM ANALYSIS STEPS
        elif attributes.get("math.step_type") == "problem_analysis":
            explanation = attributes.get("math.explanation", "")
            if explanation:
                content_parts.append(
                    Div(
                        P("Analysis:", cls="font-medium text-purple-600 mb-1"),
                        P(explanation, cls="text-base mb-3 italic"),
                        cls="mb-4"
                    )
                )

        # 5. CONCLUSION STEPS
        elif attributes.get("math.step_type") == "conclusion":
            result = attributes.get("math.result", "")
            if result:
                content_parts.append(
                    Div(
                        P("Final Answer:", cls="font-bold text-green-600 text-lg mb-2"),
                        P(result, cls="text-lg font-semibold bg-green-50 p-3 border border-green-300 rounded"),
                        cls="mb-6"
                    )
                )

        # 6. AI AGENT REASONING - Show the agent's thought process
        elif "gen_ai.operation.name" in attributes or "AI Mathematical Reasoning" in span.name or "model" in attributes:
            # Get agent reasoning details
            operation = attributes.get("gen_ai.operation.name", "")
            model = attributes.get("model", "")
            reasoning = attributes.get("math.reasoning", "")
            input_problem = attributes.get("input_problem", "")
            result = attributes.get("math.result", "")

            # Show agent thinking process
            if operation == "chat" or "Mathematical Reasoning" in span.name:
                agent_content = []

                if input_problem and input_problem != reasoning:
                    agent_content.append(
                        P(f"Analyzing: {input_problem}", cls="text-sm text-gray-600 mb-2 italic")
                    )

                if reasoning and "Applied mathematical reasoning" not in reasoning:
                    agent_content.append(
                        P(reasoning, cls="text-base leading-relaxed mb-3 text-gray-700 bg-gray-50 p-3 rounded italic")
                    )

                if model:
                    agent_content.append(
                        P(f"Using: {model}", cls="text-xs text-gray-500 mb-2")
                    )

                if agent_content:
                    content_parts.append(
                        Div(
                            P("🤖 AI Reasoning:", cls="font-medium text-blue-600 text-sm mb-2"),
                            *agent_content,
                            cls="mb-4 p-3 bg-blue-50/50 border border-blue-200 rounded"
                        )
                    )

        # Return the content if we have anything to show
        if content_parts:
            return Div(
                Div(*content_parts, cls=""),
                children_container,
                id=f"span-{span_id}",
                cls="math-paper-section"
            )
        else:
            # Just return children container for spans we don't render content for
            return Div(
                children_container,
                id=f"span-{span_id}",
                style="display: contents;"  # Act as if this div doesn't exist for layout
            )

    def _should_render_span(self, span: ReadableSpan) -> bool:
        """Determine if we should render this span based on its attributes."""
        attributes = span.attributes or {}

        # Always render problem sessions
        if span.name == "Math Problem Solving Session":
            return True

        # Render reasoning steps
        if attributes.get("math.step_type") == "reasoning" and "math.reasoning" in attributes:
            return True

        # Render mathematical operations
        if "math.operation" in attributes:
            return True

        # Render problem analysis
        if attributes.get("math.step_type") == "problem_analysis":
            return True

        # Render conclusions
        if attributes.get("math.step_type") == "conclusion":
            return True

        # Render AI agent reasoning
        if "gen_ai.operation.name" in attributes:
            return True

        # Render AI mathematical reasoning spans
        if "AI Mathematical Reasoning" in span.name:
            return True

        # Render spans with model information (agent spans)
        if "model" in attributes and attributes.get("model") == "gpt-4o-mini":
            return True

        # Skip other spans
        return False