from __future__ import annotations

import string

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from ilograph_cli.core.references import (
    contains_identifier,
    replace_reference_identifier,
    split_reference_list,
)

_IDENT_BOUNDARY_CHARS = string.ascii_letters + string.digits + "_.:-"
_IDENTIFIER = st.from_regex(r"[A-Za-z][A-Za-z0-9_.-]{0,8}", fullmatch=True)
_SEGMENT_TEXT = st.from_regex(r"[A-Za-z][A-Za-z0-9_./\-]{0,12}", fullmatch=True)


@st.composite
def _reference_segment(draw: st.DrawFn) -> str:
    variant = draw(st.sampled_from(("plain", "paren", "bracket", "single-quoted", "path")))
    head = draw(_SEGMENT_TEXT)

    if variant == "plain":
        return head
    if variant == "paren":
        left = draw(_SEGMENT_TEXT)
        right = draw(_SEGMENT_TEXT)
        return f"{head}({left},{right})"
    if variant == "bracket":
        left = draw(_SEGMENT_TEXT)
        right = draw(_SEGMENT_TEXT)
        return f"[{left},{right}]"
    if variant == "single-quoted":
        left = draw(_SEGMENT_TEXT)
        right = draw(_SEGMENT_TEXT)
        return f"{head} '{left},{right}'"

    tail = draw(_SEGMENT_TEXT)
    return f"{head}/{tail}"


@settings(max_examples=120)
@given(parts=st.lists(_reference_segment(), min_size=1, max_size=8))
def test_split_reference_list_round_trips_joined_segments(parts: list[str]) -> None:
    raw = ", ".join(parts)
    assert split_reference_list(raw) == parts


@settings(max_examples=120)
@given(
    tokens=st.lists(_IDENTIFIER, min_size=1, max_size=12),
    old=_IDENTIFIER,
    new=_IDENTIFIER,
)
def test_replace_reference_identifier_updates_exact_comma_tokens(
    tokens: list[str],
    old: str,
    new: str,
) -> None:
    assume(old != new)
    assume(new not in tokens)

    raw = ", ".join(tokens)
    replaced = replace_reference_identifier(raw, old, new)
    replaced_twice = replace_reference_identifier(replaced, old, new)

    expected = [new if token == old else token for token in tokens]
    assert split_reference_list(replaced) == expected
    assert replaced_twice == replaced
    assert contains_identifier(replaced, old) is False
    assert contains_identifier(replaced, new) is (old in tokens)


@settings(max_examples=120)
@given(
    old=_IDENTIFIER,
    new=_IDENTIFIER,
    left_boundary=st.sampled_from(tuple(_IDENT_BOUNDARY_CHARS)),
    right_boundary=st.sampled_from(tuple(_IDENT_BOUNDARY_CHARS)),
)
def test_replace_reference_identifier_respects_identifier_boundaries(
    old: str,
    new: str,
    left_boundary: str,
    right_boundary: str,
) -> None:
    assume(old != new)

    left_blocked = f"{left_boundary}{old}"
    right_blocked = f"{old}{right_boundary}"

    assert replace_reference_identifier(left_blocked, old, new) == left_blocked
    assert replace_reference_identifier(right_blocked, old, new) == right_blocked
