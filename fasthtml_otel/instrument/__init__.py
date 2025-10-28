"""Instrumentation helpers for common libraries - Logfire-style API."""

from .pydantic_ai import instrument_pydantic_ai

__all__ = [
    "instrument_pydantic_ai",
]