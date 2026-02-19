from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

from ilograph_cli.io.yaml_io import detect_format_profile, dump_document, load_document

_IDENTIFIER = st.from_regex(r"[a-z][a-z0-9_-]{0,8}", fullmatch=True)
_REFERENCE_KEY = st.sampled_from(("from", "to", "via"))
_BRACKET_ATOM = st.from_regex(r"[A-Za-z0-9_.*/-]{1,10}", fullmatch=True)
_BRACKET_VALUE = st.lists(_BRACKET_ATOM, min_size=1, max_size=4, unique=True).map(
    lambda atoms: "[" + ", ".join(atoms) + "]"
)


def _top_level_sequence_indent(raw: str, key: str) -> int | None:
    lines = raw.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != f"{key}:":
            continue
        cursor = index + 1
        while cursor < len(lines):
            candidate = lines[cursor]
            stripped = candidate.strip()
            if not stripped or stripped.startswith("#"):
                cursor += 1
                continue
            if stripped.startswith("- "):
                return len(candidate) - len(candidate.lstrip(" "))
            return None
    return None


@settings(max_examples=60, deadline=None)
@given(
    key=_REFERENCE_KEY,
    bracket_value=_BRACKET_VALUE,
    resource_id=_IDENTIFIER,
    perspective_id=_IDENTIFIER,
)
def test_load_dump_round_trip_keeps_unquoted_reference_brackets(
    key: str,
    bracket_value: str,
    resource_id: str,
    perspective_id: str,
) -> None:
    relation_lines = [f"      - {key}: {bracket_value}"]
    if key != "from":
        relation_lines.append(f"        from: {resource_id}")
    if key != "to":
        relation_lines.append(f"        to: {resource_id}")

    raw = (
        "resources:\n"
        f"  - id: {resource_id}\n"
        "    name: App\n"
        "perspectives:\n"
        f"  - id: {perspective_id}\n"
        "    relations:\n"
        + "\n".join(relation_lines)
        + "\n"
    )

    with TemporaryDirectory() as raw_tmp_dir:
        diagram = Path(raw_tmp_dir) / "diagram.yaml"
        diagram.write_text(raw, encoding="utf-8")

        profile = detect_format_profile(raw)
        document = load_document(diagram, format_profile=profile)
        dumped = dump_document(document, format_profile=profile)

        relation = document["perspectives"][0]["relations"][0]
        assert isinstance(relation[key], str)
        assert relation[key] == bracket_value
        assert f"{key}: {bracket_value}" in dumped
        assert f"{key}: '{bracket_value}'" not in dumped


@settings(max_examples=50, deadline=None)
@given(
    indentless=st.booleans(),
    resource_id=_IDENTIFIER,
    perspective_id=_IDENTIFIER,
    bracket_value=_BRACKET_VALUE,
)
def test_format_profile_round_trip_is_stable(
    indentless: bool,
    resource_id: str,
    perspective_id: str,
    bracket_value: str,
) -> None:
    if indentless:
        raw = (
            "resources:\n"
            f"- id: {resource_id}\n"
            "  name: App\n"
            "perspectives:\n"
            f"- id: {perspective_id}\n"
            "  relations:\n"
            f"  - from: {resource_id}\n"
            f"    to: {bracket_value}\n"
        )
    else:
        raw = (
            "resources:\n"
            f"  - id: {resource_id}\n"
            "    name: App\n"
            "perspectives:\n"
            f"  - id: {perspective_id}\n"
            "    relations:\n"
            f"      - from: {resource_id}\n"
            f"        to: {bracket_value}\n"
        )

    original_resources_indent = _top_level_sequence_indent(raw, "resources")
    original_perspectives_indent = _top_level_sequence_indent(raw, "perspectives")

    with TemporaryDirectory() as raw_tmp_dir:
        input_path = Path(raw_tmp_dir) / "input.yaml"
        input_path.write_text(raw, encoding="utf-8")
        profile = detect_format_profile(raw)
        first_document = load_document(input_path, format_profile=profile)
        first_dump = dump_document(first_document, format_profile=profile)

        assert _top_level_sequence_indent(first_dump, "resources") == original_resources_indent
        assert (
            _top_level_sequence_indent(first_dump, "perspectives")
            == original_perspectives_indent
        )

        second_path = Path(raw_tmp_dir) / "second.yaml"
        second_path.write_text(first_dump, encoding="utf-8")
        second_profile = detect_format_profile(first_dump)
        second_document = load_document(second_path, format_profile=second_profile)
        second_dump = dump_document(second_document, format_profile=second_profile)
        assert second_dump == first_dump
