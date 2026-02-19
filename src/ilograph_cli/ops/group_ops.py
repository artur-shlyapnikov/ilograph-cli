"""Group operations."""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.index import (
    build_resource_id_index,
    ensure_children,
    get_single_resource_by_id,
)
from ilograph_cli.core.normalize import is_none_token
from ilograph_cli.ops.resource_ops import move_resource, move_resource_to_root


def create_group(
    document: CommentedMap,
    *,
    group_id: str,
    name: str,
    parent_id: str,
    subtitle: str | None = None,
) -> bool:
    """Create group resource under parent."""

    index = build_resource_id_index(document)
    if group_id in index:
        raise ValidationError(
            f"resource id already exists: {group_id} (group id must be unique)"
        )

    group = CommentedMap()
    group["id"] = group_id
    group["name"] = name
    if subtitle:
        group["subtitle"] = subtitle

    if is_none_token(parent_id):
        resources = document.get("resources")
        if resources is None:
            resources = CommentedSeq()
            document["resources"] = resources
        if not isinstance(resources, CommentedSeq):
            raise ValidationError("resources is not an array/list (invalid diagram structure)")
        resources.append(group)
        return True

    parent = get_single_resource_by_id(document, parent_id)
    children = ensure_children(parent.node)
    children.append(group)
    return True


def move_many(document: CommentedMap, *, ids: list[str], new_parent_id: str) -> bool:
    """Move multiple resources under the same parent."""

    seen: set[str] = set()
    for resource_id in ids:
        if resource_id in seen:
            raise ValidationError(
                f"duplicate id in --ids: {resource_id} "
                "(each resource id must appear once)"
            )
        seen.add(resource_id)

    changed = False
    for resource_id in ids:
        if is_none_token(new_parent_id):
            changed = move_resource_to_root(document, resource_id=resource_id) or changed
            continue
        changed = (
            move_resource(document, resource_id=resource_id, new_parent_id=new_parent_id)
            or changed
        )
    return changed
