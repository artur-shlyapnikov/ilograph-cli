"""YAML style and anchor preservation helpers."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from ruamel.yaml.comments import CommentedMap, CommentedSeq

_BLOCK_HEADER_STYLE_RE = re.compile(r":\s*([|>])\d*([+-]?)$")
_FLOW_STYLE_PUNCTUATION: frozenset[str] = frozenset("{}[],:")


def restore_style_only_replacements(before: str, after: str) -> str:
    """Reuse original lines when replacements are style-equivalent."""

    if before == after:
        return after

    before_lines = before.splitlines()
    after_lines = after.splitlines()
    matcher = SequenceMatcher(a=before_lines, b=after_lines, autojunk=False)

    merged: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            merged.extend(before_lines[i1:i2])
            continue
        if tag == "replace":
            original_block = before_lines[i1:i2]
            emitted_block = after_lines[j1:j2]
            if _style_equivalent_block(original_block, emitted_block):
                merged.extend(original_block)
            else:
                merged.extend(emitted_block)
            continue
        if tag == "insert":
            merged.extend(after_lines[j1:j2])
            continue
        if tag == "delete":
            continue

    joined = "\n".join(merged)
    if after.endswith("\n"):
        return joined + "\n"
    return joined


def snapshot_document_anchors(document: CommentedMap) -> dict[int, str]:
    """Capture anchor names by node identity before mutation."""

    snapshot: dict[int, str] = {}
    for node in _iter_yaml_nodes(document):
        anchor = _anchor_name(node)
        if anchor is None:
            continue
        snapshot[id(node)] = anchor
    return snapshot


def restore_document_anchors(document: CommentedMap, snapshot: dict[int, str]) -> None:
    """Restore snapshot anchors and clear conflicting generated anchors."""

    if not snapshot:
        return

    preserved_names = set(snapshot.values())
    for node in _iter_yaml_nodes(document):
        node_id = id(node)
        expected_name = snapshot.get(node_id)
        if expected_name is not None:
            _set_anchor(node, expected_name)
            continue

        current_name = _anchor_name(node)
        if current_name is None:
            continue
        if current_name in preserved_names:
            _clear_anchor(node)


def _style_equivalent_block(before_lines: list[str], after_lines: list[str]) -> bool:
    if len(before_lines) != len(after_lines):
        return False

    for before_line, after_line in zip(before_lines, after_lines, strict=True):
        if _normalize_style_line(before_line) != _normalize_style_line(after_line):
            return False
    return True


def _normalize_style_line(line: str) -> str:
    normalized = line.lstrip(" ")
    normalized = _BLOCK_HEADER_STYLE_RE.sub(r": \1\2", normalized)
    if "{" not in normalized and "[" not in normalized:
        return normalized
    return _normalize_flow_style_spacing(normalized)


def _normalize_flow_style_spacing(line: str) -> str:
    output: list[str] = []
    pending_space = False
    in_single_quotes = False
    in_double_quotes = False
    escape_next = False

    for char in line:
        if in_single_quotes:
            output.append(char)
            if char == "'":
                in_single_quotes = False
            continue

        if in_double_quotes:
            output.append(char)
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == '"':
                in_double_quotes = False
            continue

        if char == "'":
            if pending_space and output and output[-1] not in _FLOW_STYLE_PUNCTUATION:
                output.append(" ")
            pending_space = False
            output.append(char)
            in_single_quotes = True
            continue

        if char == '"':
            if pending_space and output and output[-1] not in _FLOW_STYLE_PUNCTUATION:
                output.append(" ")
            pending_space = False
            output.append(char)
            in_double_quotes = True
            continue

        if char.isspace():
            pending_space = True
            continue

        if char in _FLOW_STYLE_PUNCTUATION:
            if output and output[-1] == " ":
                output.pop()
            output.append(char)
            pending_space = False
            continue

        if pending_space and output and output[-1] not in _FLOW_STYLE_PUNCTUATION:
            output.append(" ")
        pending_space = False
        output.append(char)

    return "".join(output)


def _iter_yaml_nodes(node: object) -> list[object]:
    stack = [node]
    visited: set[int] = set()
    nodes: list[object] = []

    while stack:
        current = stack.pop()
        current_id = id(current)
        if current_id in visited:
            continue
        visited.add(current_id)
        nodes.append(current)

        if isinstance(current, CommentedMap):
            stack.extend(reversed(list(current.values())))
            continue
        if isinstance(current, CommentedSeq):
            stack.extend(reversed(list(current)))
            continue
    return nodes


def _anchor_name(node: object) -> str | None:
    anchor_getter = getattr(node, "yaml_anchor", None)
    if not callable(anchor_getter):
        return None
    anchor = anchor_getter()
    if anchor is None:
        return None
    value = getattr(anchor, "value", None)
    if isinstance(value, str) and value:
        return value
    return None


def _set_anchor(node: object, name: str) -> None:
    anchor_setter = getattr(node, "yaml_set_anchor", None)
    if not callable(anchor_setter):
        return
    anchor_setter(name, always_dump=True)


def _clear_anchor(node: object) -> None:
    anchor_setter = getattr(node, "yaml_set_anchor", None)
    if not callable(anchor_setter):
        return
    anchor_setter(None)
