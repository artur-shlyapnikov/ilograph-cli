"""Shared relation typing primitives."""

from __future__ import annotations

from typing import Literal

RelationArrowDirection = Literal["forward", "backward", "bidirectional"]
RelationClearField = Literal[
    "from",
    "to",
    "via",
    "label",
    "description",
    "arrowDirection",
    "color",
    "secondary",
]
type RelationTemplateValue = str | bool
type RelationTemplate = dict[str, RelationTemplateValue]
