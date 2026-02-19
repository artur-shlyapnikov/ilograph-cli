"""Sequence step operations."""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.index import get_single_perspective

_ACTION_KEYS: tuple[str, ...] = ("to", "toAndBack", "toAsync", "restartAt")


def list_sequence_steps(document: CommentedMap, *, perspective: str) -> list[dict[str, object]]:
    """List sequence steps in perspective."""

    location = get_single_perspective(document, perspective)
    sequence = location.node.get("sequence")
    if not isinstance(sequence, CommentedMap):
        return []

    steps = sequence.get("steps")
    if not isinstance(steps, CommentedSeq):
        return []

    rows: list[dict[str, object]] = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, CommentedMap):
            continue
        row: dict[str, object] = {
            "perspective": location.identifier,
            "index": index,
            "to": _as_optional_str(step.get("to")),
            "toAndBack": _as_optional_str(step.get("toAndBack")),
            "toAsync": _as_optional_str(step.get("toAsync")),
            "restartAt": _as_optional_str(step.get("restartAt")),
            "label": _as_optional_str(step.get("label")),
            "description": _as_optional_str(step.get("description")),
            "bidirectional": bool(step.get("bidirectional"))
            if isinstance(step.get("bidirectional"), bool)
            else False,
            "color": _as_optional_str(step.get("color")),
        }
        rows.append(row)
    return rows


def add_sequence_step(
    document: CommentedMap,
    *,
    perspective: str,
    to: str | None,
    to_and_back: str | None,
    to_async: str | None,
    restart_at: str | None,
    label: str | None,
    description: str | None,
    bidirectional: bool | None,
    color: str | None,
    index_1_based: int | None,
    start_if_missing: str | None,
) -> bool:
    """Add sequence step."""

    step = _build_step_payload(
        to=to,
        to_and_back=to_and_back,
        to_async=to_async,
        restart_at=restart_at,
        label=label,
        description=description,
        bidirectional=bidirectional,
        color=color,
    )

    sequence = _ensure_sequence(
        document,
        perspective=perspective,
        start_if_missing=start_if_missing,
    )
    steps = _ensure_steps(sequence)

    if index_1_based is None:
        steps.append(step)
        return True

    insert_at = _normalize_insert_index(index_1_based, size=len(steps))
    steps.insert(insert_at, step)
    return True


def edit_sequence_step(
    document: CommentedMap,
    *,
    perspective: str,
    index_1_based: int,
    to: str | None,
    to_and_back: str | None,
    to_async: str | None,
    restart_at: str | None,
    label: str | None,
    description: str | None,
    bidirectional: bool | None,
    color: str | None,
    clear_label: bool,
    clear_description: bool,
    clear_color: bool,
) -> bool:
    """Edit sequence step."""

    step = _get_step(document, perspective=perspective, index_1_based=index_1_based)
    before = tuple((str(key), value) for key, value in step.items())

    action_updates: list[tuple[str, str]] = []
    if to is not None:
        action_updates.append(("to", to))
    if to_and_back is not None:
        action_updates.append(("toAndBack", to_and_back))
    if to_async is not None:
        action_updates.append(("toAsync", to_async))
    if restart_at is not None:
        action_updates.append(("restartAt", restart_at))

    if len(action_updates) > 1:
        raise ValidationError(
            "step action is ambiguous: "
            "set exactly one of to/to-and-back/to-async/restart-at"
        )
    if action_updates:
        for key in _ACTION_KEYS:
            step.pop(key, None)
        key, value = action_updates[0]
        step[key] = value

    if label is not None:
        step["label"] = label
    if description is not None:
        step["description"] = description
    if bidirectional is not None:
        step["bidirectional"] = bidirectional
    if color is not None:
        step["color"] = color

    if clear_label:
        step.pop("label", None)
    if clear_description:
        step.pop("description", None)
    if clear_color:
        step.pop("color", None)

    _validate_step_has_action(step)
    after = tuple((str(key), value) for key, value in step.items())
    return before != after


def remove_sequence_step(document: CommentedMap, *, perspective: str, index_1_based: int) -> bool:
    """Remove sequence step by index."""

    sequence = _get_sequence(document, perspective=perspective)
    steps = sequence.get("steps")
    if not isinstance(steps, CommentedSeq):
        raise ValidationError(f"perspective has no sequence steps: {perspective}")

    idx = index_1_based - 1
    if idx < 0 or idx >= len(steps):
        raise ValidationError(f"sequence step index out of range: {index_1_based}")

    steps.pop(idx)
    return True


def _build_step_payload(
    *,
    to: str | None,
    to_and_back: str | None,
    to_async: str | None,
    restart_at: str | None,
    label: str | None,
    description: str | None,
    bidirectional: bool | None,
    color: str | None,
) -> CommentedMap:
    action_updates: list[tuple[str, str]] = []
    if to is not None:
        action_updates.append(("to", to))
    if to_and_back is not None:
        action_updates.append(("toAndBack", to_and_back))
    if to_async is not None:
        action_updates.append(("toAsync", to_async))
    if restart_at is not None:
        action_updates.append(("restartAt", restart_at))

    if len(action_updates) != 1:
        raise ValidationError(
            "step requires exactly one action: to/to-and-back/to-async/restart-at"
        )

    step = CommentedMap()
    action_key, action_value = action_updates[0]
    step[action_key] = action_value
    if label is not None:
        step["label"] = label
    if description is not None:
        step["description"] = description
    if bidirectional is not None:
        step["bidirectional"] = bidirectional
    if color is not None:
        step["color"] = color
    return step


def _ensure_sequence(
    document: CommentedMap,
    *,
    perspective: str,
    start_if_missing: str | None,
) -> CommentedMap:
    location = get_single_perspective(document, perspective)
    sequence = location.node.get("sequence")
    if isinstance(sequence, CommentedMap):
        return sequence

    if start_if_missing is None:
        raise ValidationError(
            "perspective has no sequence; pass --start to initialize sequence"
        )

    created = CommentedMap()
    created["start"] = start_if_missing
    created["steps"] = CommentedSeq()
    location.node["sequence"] = created
    return created


def _get_sequence(document: CommentedMap, *, perspective: str) -> CommentedMap:
    location = get_single_perspective(document, perspective)
    sequence = location.node.get("sequence")
    if not isinstance(sequence, CommentedMap):
        raise ValidationError(f"perspective has no sequence: {location.identifier}")
    return sequence


def _ensure_steps(sequence: CommentedMap) -> CommentedSeq:
    steps = sequence.get("steps")
    if isinstance(steps, CommentedSeq):
        return steps

    created = CommentedSeq()
    sequence["steps"] = created
    return created


def _get_step(document: CommentedMap, *, perspective: str, index_1_based: int) -> CommentedMap:
    sequence = _get_sequence(document, perspective=perspective)
    steps = sequence.get("steps")
    if not isinstance(steps, CommentedSeq):
        raise ValidationError(f"perspective has no sequence steps: {perspective}")

    idx = index_1_based - 1
    if idx < 0 or idx >= len(steps):
        raise ValidationError(f"sequence step index out of range: {index_1_based}")

    step = steps[idx]
    if not isinstance(step, CommentedMap):
        raise ValidationError(f"sequence step at index {index_1_based} is not a mapping")
    return step


def _validate_step_has_action(step: CommentedMap) -> None:
    if not any(key in step for key in _ACTION_KEYS):
        raise ValidationError("step requires one action field")


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
