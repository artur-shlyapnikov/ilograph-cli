"""Domain errors."""

from __future__ import annotations


class IlographCliError(Exception):
    """Base CLI error."""


class ValidationError(IlographCliError):
    """Validation error for user-visible failures."""
