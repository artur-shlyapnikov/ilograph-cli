"""Shared normalization helpers for args and ops payloads."""

from __future__ import annotations

from collections.abc import Sequence

from ilograph_cli.core.constants import RESTRICTED_RESOURCE_ID_CHARS

NONE_TOKEN = "none"


def normalize_required_str(value: str, *, field_name: str) -> str:
    """Strip and require non-empty string."""

    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{_field_label(field_name)} must not be empty")
    return cleaned


def normalize_optional_str(
    value: str | None,
    *,
    field_name: str,
    empty_is_none: bool = False,
) -> str | None:
    """Normalize optional string with configurable empty handling."""

    if value is None:
        return None
    cleaned = value.strip()
    if cleaned:
        return cleaned
    if empty_is_none:
        return None
    raise ValueError(f"{_field_label(field_name)} must not be empty")


def normalize_unique_list(values: Sequence[str], *, field_name: str) -> list[str]:
    """Normalize string list, reject empties and duplicates."""

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        normalized = normalize_required_str(item, field_name=field_name)
        if normalized in seen:
            raise ValueError(f"{_field_label(field_name)} has duplicates")
        seen.add(normalized)
        cleaned.append(normalized)
    if not cleaned:
        raise ValueError(f"{_field_label(field_name)} must not be empty")
    return cleaned


def validate_resource_id(value: str, *, field_name: str) -> str:
    """Normalize + validate resource-id character constraints."""

    identifier = normalize_required_str(value, field_name=field_name)
    for char in identifier:
        if char in RESTRICTED_RESOURCE_ID_CHARS:
            raise ValueError(
                f"{_field_label(field_name)} contains restricted character '{char}'"
            )
    return identifier


def is_none_token(value: str) -> bool:
    """True when user input means null-parent selection."""

    return value.strip().lower() == NONE_TOKEN


def _field_label(field_name: str) -> str:
    return field_name.replace("_", "-")
