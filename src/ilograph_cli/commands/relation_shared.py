"""Shared relation filter helpers."""

from __future__ import annotations

import typer

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.normalize import normalize_optional_str
from ilograph_cli.core.relation_types import RelationArrowDirection, RelationTemplate

_ALLOWED_DIRECTIONS: set[str] = {"forward", "backward", "bidirectional"}

perspective_filter_option = typer.Option(
    None,
    "--perspective",
    help="Perspective id/name filter. Repeat or pass comma-separated values.",
)
context_filter_option = typer.Option(
    None,
    "--context",
    help="Context for {context} template expansion. Repeat/comma-separated.",
)


def _parse_multi_values(values: list[str] | None) -> list[str]:
    if not values:
        return []
    parsed: list[str] = []
    for raw in values:
        for token in raw.split(","):
            candidate = token.strip()
            if candidate:
                parsed.append(candidate)
    return parsed


def _build_relation_template(
    *,
    from_ref: str | None,
    to_ref: str | None,
    via: str | None,
    label: str | None,
    description: str | None,
    arrow_direction: str | None,
    color: str | None,
    secondary: bool | None,
) -> RelationTemplate:
    payload: RelationTemplate = {}

    normalized_from = _normalize_relation_value(from_ref, field_name="from")
    normalized_to = _normalize_relation_value(to_ref, field_name="to")
    normalized_via = _normalize_relation_value(via, field_name="via")
    normalized_label = _normalize_relation_value(label, field_name="label")
    normalized_description = _normalize_relation_value(description, field_name="description")
    normalized_color = _normalize_relation_value(color, field_name="color")

    normalized_direction: RelationArrowDirection | None = None
    if arrow_direction is not None:
        cleaned_direction = _normalize_relation_value(
            arrow_direction,
            field_name="arrow_direction",
        )
        if cleaned_direction is None:
            raise ValidationError("arrow-direction must not be empty")
        lowered = cleaned_direction.lower()
        if lowered not in _ALLOWED_DIRECTIONS:
            raise ValidationError(
                "arrow-direction must be one of: forward, backward, bidirectional"
            )
        normalized_direction = lowered  # type: ignore[assignment]

    if normalized_from is not None:
        payload["from"] = normalized_from
    if normalized_to is not None:
        payload["to"] = normalized_to
    if normalized_via is not None:
        payload["via"] = normalized_via
    if normalized_label is not None:
        payload["label"] = normalized_label
    if normalized_description is not None:
        payload["description"] = normalized_description
    if normalized_direction is not None:
        payload["arrowDirection"] = normalized_direction
    if normalized_color is not None:
        payload["color"] = normalized_color
    if secondary is not None:
        payload["secondary"] = secondary

    return payload


def _normalize_relation_value(value: str | None, *, field_name: str) -> str | None:
    try:
        return normalize_optional_str(value, field_name=field_name)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
