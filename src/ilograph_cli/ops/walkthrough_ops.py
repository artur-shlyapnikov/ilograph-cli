"""Walkthrough slide operations."""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.index import get_single_perspective


def list_walkthrough_slides(document: CommentedMap, *, perspective: str) -> list[dict[str, object]]:
    """List walkthrough slides for perspective."""

    location = get_single_perspective(document, perspective)
    walkthrough = location.node.get("walkthrough")
    if not isinstance(walkthrough, CommentedSeq):
        return []

    rows: list[dict[str, object]] = []
    for index, slide in enumerate(walkthrough, start=1):
        if not isinstance(slide, CommentedMap):
            continue
        rows.append(
            {
                "perspective": location.identifier,
                "index": index,
                "text": _as_optional_str(slide.get("text")),
                "select": _as_optional_str(slide.get("select")),
                "expand": _as_optional_str(slide.get("expand")),
                "highlight": _as_optional_str(slide.get("highlight")),
                "hide": _as_optional_str(slide.get("hide")),
                "detail": (
                    slide.get("detail")
                    if isinstance(slide.get("detail"), (int, float))
                    else None
                ),
            }
        )
    return rows


def add_walkthrough_slide(
    document: CommentedMap,
    *,
    perspective: str,
    text: str | None,
    select: str | None,
    expand: str | None,
    highlight: str | None,
    hide: str | None,
    detail: float | None,
    index_1_based: int | None,
) -> bool:
    """Add walkthrough slide."""

    if (
        text is None
        and select is None
        and expand is None
        and highlight is None
        and hide is None
        and detail is None
    ):
        raise ValidationError("slide requires at least one field")

    location = get_single_perspective(document, perspective)
    walkthrough = _ensure_walkthrough(location.node)

    slide = CommentedMap()
    if text is not None:
        slide["text"] = text
    if select is not None:
        slide["select"] = select
    if expand is not None:
        slide["expand"] = expand
    if highlight is not None:
        slide["highlight"] = highlight
    if hide is not None:
        slide["hide"] = hide
    if detail is not None:
        slide["detail"] = detail

    if index_1_based is None:
        walkthrough.append(slide)
        return True

    insert_at = _normalize_insert_index(index_1_based, size=len(walkthrough))
    walkthrough.insert(insert_at, slide)
    return True


def edit_walkthrough_slide(
    document: CommentedMap,
    *,
    perspective: str,
    index_1_based: int,
    text: str | None,
    select: str | None,
    expand: str | None,
    highlight: str | None,
    hide: str | None,
    detail: float | None,
    clear_text: bool,
    clear_select: bool,
    clear_expand: bool,
    clear_highlight: bool,
    clear_hide: bool,
    clear_detail: bool,
) -> bool:
    """Edit walkthrough slide."""

    if (
        text is None
        and select is None
        and expand is None
        and highlight is None
        and hide is None
        and detail is None
        and not clear_text
        and not clear_select
        and not clear_expand
        and not clear_highlight
        and not clear_hide
        and not clear_detail
    ):
        raise ValidationError("set at least one update field")

    slide = _get_slide(document, perspective=perspective, index_1_based=index_1_based)
    before = tuple((str(key), value) for key, value in slide.items())

    if text is not None:
        slide["text"] = text
    if select is not None:
        slide["select"] = select
    if expand is not None:
        slide["expand"] = expand
    if highlight is not None:
        slide["highlight"] = highlight
    if hide is not None:
        slide["hide"] = hide
    if detail is not None:
        slide["detail"] = detail

    if clear_text:
        slide.pop("text", None)
    if clear_select:
        slide.pop("select", None)
    if clear_expand:
        slide.pop("expand", None)
    if clear_highlight:
        slide.pop("highlight", None)
    if clear_hide:
        slide.pop("hide", None)
    if clear_detail:
        slide.pop("detail", None)

    after = tuple((str(key), value) for key, value in slide.items())
    return before != after


def remove_walkthrough_slide(
    document: CommentedMap,
    *,
    perspective: str,
    index_1_based: int,
) -> bool:
    """Remove walkthrough slide by index."""

    location = get_single_perspective(document, perspective)
    walkthrough = location.node.get("walkthrough")
    if not isinstance(walkthrough, CommentedSeq):
        raise ValidationError(f"perspective has no walkthrough: {location.identifier}")

    idx = index_1_based - 1
    if idx < 0 or idx >= len(walkthrough):
        raise ValidationError(f"walkthrough slide index out of range: {index_1_based}")

    walkthrough.pop(idx)
    return True


def _ensure_walkthrough(perspective: CommentedMap) -> CommentedSeq:
    walkthrough = perspective.get("walkthrough")
    if isinstance(walkthrough, CommentedSeq):
        return walkthrough
    created = CommentedSeq()
    perspective["walkthrough"] = created
    return created


def _get_slide(document: CommentedMap, *, perspective: str, index_1_based: int) -> CommentedMap:
    location = get_single_perspective(document, perspective)
    walkthrough = location.node.get("walkthrough")
    if not isinstance(walkthrough, CommentedSeq):
        raise ValidationError(f"perspective has no walkthrough: {location.identifier}")

    idx = index_1_based - 1
    if idx < 0 or idx >= len(walkthrough):
        raise ValidationError(f"walkthrough slide index out of range: {index_1_based}")

    slide = walkthrough[idx]
    if not isinstance(slide, CommentedMap):
        raise ValidationError(f"walkthrough slide at index {index_1_based} is not a mapping")
    return slide


def _normalize_insert_index(index_1_based: int, *, size: int) -> int:
    if index_1_based < 1:
        raise ValidationError("index must be >= 1")
    if index_1_based > size + 1:
        raise ValidationError(f"index out of range: {index_1_based}")
    return index_1_based - 1


def _as_optional_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None
