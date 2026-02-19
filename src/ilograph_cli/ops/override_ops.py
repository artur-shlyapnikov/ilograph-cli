"""Perspective override operations."""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.index import get_single_perspective


def list_overrides(document: CommentedMap, *, perspective: str) -> list[dict[str, object]]:
    """List overrides for a perspective."""

    location = get_single_perspective(document, perspective)
    overrides = location.node.get("overrides")
    rows: list[dict[str, object]] = []
    if not isinstance(overrides, CommentedSeq):
        return rows

    for index, item in enumerate(overrides, start=1):
        if not isinstance(item, CommentedMap):
            continue
        resource_id = item.get("resourceId")
        if not isinstance(resource_id, str):
            continue
        rows.append(
            {
                "perspective": location.identifier,
                "index": index,
                "resourceId": resource_id,
                "parentId": item.get("parentId") if isinstance(item.get("parentId"), str) else None,
                "scale": item.get("scale") if isinstance(item.get("scale"), (int, float)) else None,
            }
        )
    return rows


def add_override(
    document: CommentedMap,
    *,
    perspective: str,
    resource_id: str,
    parent_id: str | None,
    scale: float | None,
    index_1_based: int | None = None,
) -> bool:
    """Add override row."""

    if parent_id is None and scale is None:
        raise ValidationError("override requires --parent-id or --scale")

    location = get_single_perspective(document, perspective)
    overrides = _ensure_overrides(location.node)
    if _find_override_index(overrides, resource_id) is not None:
        raise ValidationError(f"override already exists for resourceId: {resource_id}")

    payload = CommentedMap()
    payload["resourceId"] = resource_id
    if parent_id is not None:
        payload["parentId"] = parent_id
    if scale is not None:
        payload["scale"] = scale

    if index_1_based is None:
        overrides.append(payload)
        return True

    insert_at = _normalize_insert_index(index_1_based, size=len(overrides))
    overrides.insert(insert_at, payload)
    return True


def edit_override(
    document: CommentedMap,
    *,
    perspective: str,
    resource_id: str,
    new_resource_id: str | None,
    parent_id: str | None,
    scale: float | None,
    clear_parent_id: bool,
    clear_scale: bool,
) -> bool:
    """Edit override row selected by resourceId."""

    if (
        new_resource_id is None
        and parent_id is None
        and scale is None
        and not clear_parent_id
        and not clear_scale
    ):
        raise ValidationError("set at least one update field")

    location = get_single_perspective(document, perspective)
    overrides = location.node.get("overrides")
    if not isinstance(overrides, CommentedSeq):
        raise ValidationError(f"perspective has no overrides: {location.identifier}")

    target_index = _find_override_index(overrides, resource_id)
    if target_index is None:
        raise ValidationError(f"override not found for resourceId: {resource_id}")

    target = overrides[target_index]
    if not isinstance(target, CommentedMap):
        raise ValidationError(f"override entry is not a mapping: {resource_id}")

    changed = False
    if new_resource_id is not None and new_resource_id != resource_id:
        existing_index = _find_override_index(overrides, new_resource_id)
        if existing_index is not None and existing_index != target_index:
            raise ValidationError(
                f"override already exists for resourceId: {new_resource_id}"
            )
        target["resourceId"] = new_resource_id
        changed = True

    if clear_parent_id:
        if "parentId" in target:
            target.pop("parentId", None)
            changed = True
    elif parent_id is not None and target.get("parentId") != parent_id:
        target["parentId"] = parent_id
        changed = True

    if clear_scale:
        if "scale" in target:
            target.pop("scale", None)
            changed = True
    elif scale is not None and target.get("scale") != scale:
        target["scale"] = scale
        changed = True

    if "parentId" not in target and "scale" not in target:
        raise ValidationError("override requires parentId or scale")

    return changed


def remove_override(document: CommentedMap, *, perspective: str, resource_id: str) -> bool:
    """Remove override by resourceId."""

    location = get_single_perspective(document, perspective)
    overrides = location.node.get("overrides")
    if not isinstance(overrides, CommentedSeq):
        raise ValidationError(f"perspective has no overrides: {location.identifier}")

    target_index = _find_override_index(overrides, resource_id)
    if target_index is None:
        raise ValidationError(f"override not found for resourceId: {resource_id}")

    overrides.pop(target_index)
    return True


def _ensure_overrides(perspective: CommentedMap) -> CommentedSeq:
    overrides = perspective.get("overrides")
    if isinstance(overrides, CommentedSeq):
        return overrides
    created = CommentedSeq()
    perspective["overrides"] = created
    return created


def _find_override_index(overrides: CommentedSeq, resource_id: str) -> int | None:
    for index, item in enumerate(overrides):
        if not isinstance(item, CommentedMap):
            continue
        raw_resource_id = item.get("resourceId")
        if isinstance(raw_resource_id, str) and raw_resource_id == resource_id:
            return index
    return None


def _normalize_insert_index(index_1_based: int, *, size: int) -> int:
    if index_1_based < 1:
        raise ValidationError("index must be >= 1")
    if index_1_based > size + 1:
        raise ValidationError(f"index out of range: {index_1_based}")
    return index_1_based - 1
