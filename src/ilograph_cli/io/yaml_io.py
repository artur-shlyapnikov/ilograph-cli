"""YAML I/O preserving round-trip formatting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Literal

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.yaml_types import YamlNode as CoreYamlNode
from ilograph_cli.core.yaml_types import YamlScalar as CoreYamlScalar

type YamlScalar = CoreYamlScalar
type YamlNode = CoreYamlNode
type SequenceIndentStyle = Literal["indentless", "indented"]


@dataclass(slots=True)
class YamlFormatProfile:
    """Formatting hints extracted from original source text."""

    sequence_indent_style: SequenceIndentStyle
    top_level_sequence_indents: dict[str, int]
    unquoted_reference_brackets: set[tuple[str, str]]

_REFERENCE_KEYS: frozenset[str] = frozenset(
    {
        "from",
        "to",
        "via",
        "resourceId",
        "parentId",
        "for",
        "select",
        "focus",
        "highlight",
        "include",
        "exclude",
        "root",
        "center",
        "zoomTo",
        "expand",
        "hide",
        "start",
        "toAndBack",
        "toAsync",
        "restartAt",
    }
)
_KEY_VALUE_LINE_RE = re.compile(
    r"^(?P<prefix>\s*(?:-\s*)?)(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<value>\[[^\n#]*\])(?P<suffix>\s*(?:#.*)?)$"
)
_QUOTED_KEY_VALUE_LINE_RE = re.compile(
    r"^(?P<prefix>\s*(?:-\s*)?)(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*'(?P<value>\[[^'\n#]*\])'(?P<suffix>\s*(?:#.*)?)$"
)
_TOP_LEVEL_KEY_LINE_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(?:#.*)?$")
_TOP_LEVEL_KEY_PREFIX_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*\s*:")
_SEQUENCE_LINE_RE = re.compile(r"^(?P<indent>\s*)-\s")
_MAP_KEY_LINE_RE = re.compile(
    r"^(?P<indent>\s*)(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(?:#.*)?$"
)


def build_yaml(profile: YamlFormatProfile | None = None) -> YAML:
    """Round-trip YAML parser/emitter."""

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    if profile is not None and profile.sequence_indent_style == "indentless":
        yaml.indent(mapping=2, sequence=2, offset=0)
    else:
        yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096
    return yaml


def detect_format_profile(raw: str) -> YamlFormatProfile:
    """Infer emit formatting hints from source text."""

    return YamlFormatProfile(
        sequence_indent_style=_detect_sequence_indent_style(raw),
        top_level_sequence_indents=_detect_top_level_sequence_indents(raw),
        unquoted_reference_brackets=_detect_unquoted_reference_brackets(raw),
    )


def read_text(path: Path) -> str:
    """Read UTF-8 text file."""

    return path.read_text(encoding="utf-8")


def load_document(path: Path, *, format_profile: YamlFormatProfile | None = None) -> CommentedMap:
    """Load Ilograph YAML document."""

    yaml = build_yaml(format_profile)
    raw_text = read_text(path)
    normalized = _quote_reference_bracket_scalars(raw_text)
    try:
        data = yaml.load(normalized)
    except YAMLError as exc:
        raise _yaml_error(exc, path=path) from exc

    if data is None:
        return CommentedMap()
    if not isinstance(data, CommentedMap):
        raise ValidationError(
            f"yaml root must be a mapping/object (file: {path})"
        )
    return data


def load_any_yaml(path: Path) -> YamlNode:
    """Load arbitrary YAML (for ops file)."""

    yaml = build_yaml()
    try:
        loaded = yaml.load(read_text(path))
    except YAMLError as exc:
        raise ValidationError(f"yaml parse error in {path}: {exc}") from exc
    if isinstance(loaded, (CommentedMap, CommentedSeq, str, int, float, bool)) or loaded is None:
        return loaded
    loaded_type = type(loaded).__name__
    raise ValidationError(
        "yaml root type not supported: "
        f"{loaded_type} (expected mapping, sequence, scalar, or null)"
    )


def dump_document(
    document: CommentedMap,
    *,
    format_profile: YamlFormatProfile | None = None,
) -> str:
    """Dump document preserving style."""

    yaml = build_yaml(format_profile)
    stream = StringIO()
    yaml.dump(document, stream)
    dumped = stream.getvalue()

    if format_profile is None:
        return dumped

    restored = _apply_top_level_sequence_indents(
        dumped,
        format_profile.top_level_sequence_indents,
    )
    return _restore_unquoted_reference_bracket_scalars(
        restored,
        format_profile.unquoted_reference_brackets,
    )


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text file."""

    path.write_text(text, encoding="utf-8")


def _quote_reference_bracket_scalars(raw: str) -> str:
    """Quote bracket expressions where Ilograph expects scalar references."""

    out: list[str] = []
    for line in raw.splitlines(keepends=True):
        line_wo_nl = line.rstrip("\r\n")
        match = _KEY_VALUE_LINE_RE.match(line_wo_nl)
        if match is None:
            out.append(line)
            continue

        key = match.group("key")
        value = match.group("value")
        if key not in _REFERENCE_KEYS or value.startswith(("'", '"')):
            out.append(line)
            continue

        escaped = value.replace("'", "''")
        newline = "\n" if line.endswith("\n") else ""
        out.append(
            f"{match.group('prefix')}{key}: '{escaped}'{match.group('suffix')}{newline}"
        )
    return "".join(out)


def _yaml_error(exc: YAMLError, *, path: Path) -> ValidationError:
    base = f"yaml parse error in {path}: {exc}"
    raw = str(exc)
    if "found undefined alias" in raw:
        return ValidationError(
            f"{base}\n"
            "hint: quote Ilograph bracket references (example: from: '[*.cloudfront.net]')"
        )
    return ValidationError(base)


def _detect_sequence_indent_style(raw: str) -> SequenceIndentStyle:
    deltas: list[int] = []
    lines = raw.splitlines()

    for index, line in enumerate(lines):
        key_match = _MAP_KEY_LINE_RE.match(line)
        if key_match is None:
            continue
        key_indent = len(key_match.group("indent"))
        cursor = index + 1
        while cursor < len(lines):
            candidate = lines[cursor]
            stripped = candidate.strip()
            if not stripped or stripped.startswith("#"):
                cursor += 1
                continue
            sequence_match = _SEQUENCE_LINE_RE.match(candidate)
            if sequence_match is not None:
                item_indent = len(sequence_match.group("indent"))
                deltas.append(item_indent - key_indent)
            break

    if not deltas:
        return "indented"
    zero_delta = sum(1 for delta in deltas if delta == 0)
    indented_delta = sum(1 for delta in deltas if delta >= 2)
    return "indentless" if zero_delta >= indented_delta else "indented"


def _detect_top_level_sequence_indents(raw: str) -> dict[str, int]:
    result: dict[str, int] = {}
    lines = raw.splitlines()

    for index, line in enumerate(lines):
        key_match = _TOP_LEVEL_KEY_LINE_RE.match(line)
        if key_match is None:
            continue
        key = key_match.group("key")
        cursor = index + 1
        while cursor < len(lines):
            candidate = lines[cursor]
            stripped = candidate.strip()
            if not stripped or stripped.startswith("#"):
                cursor += 1
                continue
            sequence_match = _SEQUENCE_LINE_RE.match(candidate)
            if sequence_match is not None:
                result[key] = len(sequence_match.group("indent"))
            break

    return result


def _detect_unquoted_reference_brackets(raw: str) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for line in raw.splitlines(keepends=False):
        match = _KEY_VALUE_LINE_RE.match(line)
        if match is None:
            continue
        key = match.group("key")
        value = match.group("value")
        if key not in _REFERENCE_KEYS or value.startswith(("'", '"')):
            continue
        result.add((key, value.strip()))
    return result


def _apply_top_level_sequence_indents(
    raw: str,
    top_level_sequence_indents: dict[str, int],
) -> str:
    if not top_level_sequence_indents:
        return raw

    lines = raw.splitlines(keepends=True)
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        key_match = _TOP_LEVEL_KEY_LINE_RE.match(line.rstrip("\r\n"))
        if key_match is None:
            output.append(line)
            index += 1
            continue

        key = key_match.group("key")
        output.append(line)
        index += 1

        block_start = index
        while index < len(lines) and _TOP_LEVEL_KEY_PREFIX_RE.match(lines[index]) is None:
            index += 1
        block = lines[block_start:index]

        desired_indent = top_level_sequence_indents.get(key)
        if desired_indent is None:
            output.extend(block)
            continue

        current_indent: int | None = None
        for block_line in block:
            stripped = block_line.strip()
            if not stripped or block_line.lstrip().startswith("#"):
                continue
            sequence_match = _SEQUENCE_LINE_RE.match(block_line)
            if sequence_match is not None:
                current_indent = len(sequence_match.group("indent"))
            break

        if current_indent is None or current_indent == desired_indent:
            output.extend(block)
            continue

        delta = desired_indent - current_indent
        for block_line in block:
            if not block_line.strip():
                output.append(block_line)
                continue
            if delta > 0:
                output.append((" " * delta) + block_line)
                continue

            removable = min(-delta, len(block_line) - len(block_line.lstrip(" ")))
            output.append(block_line[removable:])

    return "".join(output)


def _restore_unquoted_reference_bracket_scalars(
    raw: str,
    original_unquoted_values: set[tuple[str, str]],
) -> str:
    if not original_unquoted_values:
        return raw

    output: list[str] = []
    for line in raw.splitlines(keepends=True):
        line_wo_nl = line.rstrip("\r\n")
        match = _QUOTED_KEY_VALUE_LINE_RE.match(line_wo_nl)
        if match is None:
            output.append(line)
            continue

        key = match.group("key")
        value = match.group("value").strip()
        if (key, value) not in original_unquoted_values:
            output.append(line)
            continue

        newline = "\n" if line.endswith("\n") else ""
        output.append(
            f"{match.group('prefix')}{key}: {value}{match.group('suffix')}{newline}"
        )
    return "".join(output)
