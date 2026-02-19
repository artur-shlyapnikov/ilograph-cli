"""Core constants."""

from __future__ import annotations

RESTRICTED_RESOURCE_ID_CHARS: frozenset[str] = frozenset({"/", "^", "*", "[", "]", ","})
SPECIAL_REFERENCE_TOKENS: frozenset[str] = frozenset({"*", "none", "^"})

# Walkthrough schema has multiple reference-like keys. We validate a practical subset.
WALKTHROUGH_REFERENCE_KEYS: frozenset[str] = frozenset(
    {
        "select",
        "expand",
        "hide",
        "focus",
        "highlight",
        "include",
        "exclude",
        "root",
        "center",
        "zoomTo",
    }
)
