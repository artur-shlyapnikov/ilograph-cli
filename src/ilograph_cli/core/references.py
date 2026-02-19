"""Reference parsing/rewrite helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ilograph_cli.core.constants import SPECIAL_REFERENCE_TOKENS

_IDENT_BOUNDARY_CHARS = r"A-Za-z0-9_.:-"


@dataclass(slots=True)
class ReferenceComponent:
    """Single parsed component from an Ilograph reference expression."""

    token: str
    raw: str
    relative: bool
    wildcard: bool
    namespaced: bool
    special: bool


def split_reference_list(raw: str) -> list[str]:
    """Split comma-separated references with []/()/" awareness."""

    parts: list[str] = []
    current: list[str] = []
    square_depth = 0
    paren_depth = 0
    in_single = False
    in_double = False
    escaped = False

    for char in raw:
        if escaped:
            current.append(char)
            escaped = False
            continue

        if char == "\\" and (in_single or in_double):
            current.append(char)
            escaped = True
            continue

        if char == "'" and not in_double:
            in_single = not in_single
            current.append(char)
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            current.append(char)
            continue

        if not in_single and not in_double:
            if char == "[":
                square_depth += 1
            elif char == "]" and square_depth > 0:
                square_depth -= 1
            elif char == "(":
                paren_depth += 1
            elif char == ")" and paren_depth > 0:
                paren_depth -= 1
            elif char == "," and square_depth == 0 and paren_depth == 0:
                segment = "".join(current).strip()
                if segment:
                    parts.append(segment)
                current = []
                continue

        current.append(char)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def parse_reference_components(raw: str) -> list[ReferenceComponent]:
    """Parse an expression into comparable components."""

    components: list[ReferenceComponent] = []
    for part in split_reference_list(raw):
        part_components = _parse_part_components(part)
        components.extend(part_components)
    return components


def extract_reference_tokens(raw: str) -> set[str]:
    """Extract candidate resource identifiers from a reference expression."""

    tokens: set[str] = set()
    for component in parse_reference_components(raw):
        if component.special:
            continue
        if component.wildcard:
            continue
        if not component.token:
            continue
        tokens.add(component.token)
    return tokens


def replace_reference_identifier(raw: str, old: str, new: str) -> str:
    """Replace exact identifier tokens inside reference string."""

    if old == new:
        return raw
    pattern = re.compile(
        rf"(?<![{_IDENT_BOUNDARY_CHARS}])"
        rf"{re.escape(old)}"
        rf"(?![{_IDENT_BOUNDARY_CHARS}])"
    )
    return pattern.sub(new, raw)


def contains_identifier(raw: str, identifier: str) -> bool:
    """True if identifier appears as reference component."""

    return any(component.token == identifier for component in parse_reference_components(raw))


def _parse_part_components(part: str) -> list[ReferenceComponent]:
    base = _strip_clone_suffix(part.strip())
    if not base:
        return []

    relative = False
    while True:
        if base.startswith("../"):
            relative = True
            base = base[3:].lstrip()
            continue
        if base.startswith(".../"):
            relative = True
            base = base[4:].lstrip()
            continue
        break

    if not base:
        return []

    raw_components = _split_path(base)
    parsed: list[ReferenceComponent] = []
    for raw_component in raw_components:
        token = raw_component.strip()
        if not token:
            continue

        if token.startswith("[") and token.endswith("]") and len(token) >= 2:
            token = token[1:-1].strip()

        if not token:
            continue

        lowered = token.lower()
        is_special = lowered in SPECIAL_REFERENCE_TOKENS
        is_wildcard = "*" in token and not is_special
        parsed.append(
            ReferenceComponent(
                token=token,
                raw=raw_component,
                relative=relative,
                wildcard=is_wildcard,
                namespaced="::" in token,
                special=is_special,
            )
        )
    return parsed


def _split_path(raw: str) -> list[str]:
    """Split a reference path by / and // while respecting []/()."""

    parts: list[str] = []
    current: list[str] = []
    square_depth = 0
    paren_depth = 0
    i = 0
    while i < len(raw):
        char = raw[i]
        if char == "[":
            square_depth += 1
        elif char == "]" and square_depth > 0:
            square_depth -= 1
        elif char == "(":
            paren_depth += 1
        elif char == ")" and paren_depth > 0:
            paren_depth -= 1

        if char == "/" and square_depth == 0 and paren_depth == 0:
            segment = "".join(current).strip()
            if segment:
                parts.append(segment)
            current = []
            if i + 1 < len(raw) and raw[i + 1] == "/":
                i += 1
            i += 1
            continue

        current.append(char)
        i += 1

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _strip_clone_suffix(raw: str) -> str:
    """Remove trailing clone marker (`*id`) from a reference part."""

    text = raw.rstrip()
    if not text:
        return text

    square_depth = 0
    paren_depth = 0
    for index in range(len(text) - 1, -1, -1):
        char = text[index]
        if char == "]":
            square_depth += 1
            continue
        if char == "[" and square_depth > 0:
            square_depth -= 1
            continue
        if char == ")":
            paren_depth += 1
            continue
        if char == "(" and paren_depth > 0:
            paren_depth -= 1
            continue
        if square_depth > 0 or paren_depth > 0:
            continue
        if char != "*":
            continue
        if index == 0:
            continue
        if not text[index - 1].isspace():
            continue
        suffix = text[index + 1 :].strip()
        if not suffix:
            continue
        if any(ch.isspace() or ch in {"/", ","} for ch in suffix):
            continue
        return text[: index - 1].rstrip()

    return text
