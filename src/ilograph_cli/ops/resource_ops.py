"""Resource operations: create/rename/move/delete/clone."""

from __future__ import annotations

from copy import deepcopy

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.index import (
    build_resource_id_index,
    ensure_children,
    get_single_resource_by_id,
    resource_identifier,
)
from ilograph_cli.core.normalize import is_none_token
from ilograph_cli.core.reference_fields import iter_reference_fields
from ilograph_cli.core.references import replace_reference_identifier


def create_resource(
    document: CommentedMap,
    *,
    resource_id: str,
    name: str,
    parent_id: str,
    subtitle: str | None = None,
) -> bool:
    """Create resource under parent or root."""

    existing = build_resource_id_index(document)
    if resource_id in existing:
        raise ValidationError(f"resource id already exists: {resource_id}")

    resource = CommentedMap()
    resource["id"] = resource_id
    resource["name"] = name
    if subtitle is not None:
        resource["subtitle"] = subtitle

    if is_none_token(parent_id):
        root = _ensure_root_resources(document)
        root.append(resource)
        return True

    parent = get_single_resource_by_id(document, parent_id)
    children = ensure_children(parent.node)
    children.append(resource)
    return True


def rename_resource(document: CommentedMap, *, resource_id: str, new_name: str) -> bool:
    """Rename resource display name."""

    location = get_single_resource_by_id(document, resource_id)
    current_name = location.node.get("name")
    if isinstance(current_name, str) and current_name == new_name:
        return False
    location.node["name"] = new_name
    return True


def rename_resource_id(document: CommentedMap, *, old_id: str, new_id: str) -> bool:
    """Rename resource identifier and rewrite all references."""

    if old_id == new_id:
        raise ValidationError(
            "old/new ids are identical (choose a different value for --to)"
        )

    existing = build_resource_id_index(document)
    if new_id in existing:
        raise ValidationError(
            f"target id already exists: {new_id} (resource ids must be unique)"
        )

    location = get_single_resource_by_id(document, old_id)
    old_identifier = resource_identifier(location.node)
    if old_identifier is None:
        raise ValidationError(
            f"resource has no identifier: {old_id} (set an explicit id before rename)"
        )

    anchor = location.node.yaml_anchor()
    location.node["id"] = new_id
    if anchor is not None and anchor.value is not None:
        # Keep explicit anchor labels even if node content changes.
        location.node.yaml_set_anchor(anchor.value, always_dump=True)

    _rewrite_reference_strings(document, old_identifier, new_id)
    return True


def move_resource(
    document: CommentedMap,
    *,
    resource_id: str,
    new_parent_id: str,
    inherit_style_from_parent: bool = False,
) -> bool:
    """Move resource subtree under new parent."""

    location = get_single_resource_by_id(document, resource_id)
    target_parent = get_single_resource_by_id(document, new_parent_id)

    if location.node is target_parent.node:
        raise ValidationError("resource cannot be parent of itself (same --id and --new-parent)")
    if _is_descendant(location.node, target_parent.node):
        raise ValidationError(
            "resource cannot be moved under its own descendant (would create a cycle)"
        )

    target_children = ensure_children(target_parent.node)
    if location.container is target_children and location.index == len(location.container) - 1:
        if not inherit_style_from_parent:
            return False
        return _clear_resource_style_for_inheritance(location.node)

    source_container = location.container
    source_container.pop(location.index)
    target_children.append(location.node)
    if inherit_style_from_parent:
        _clear_resource_style_for_inheritance(location.node)
    return True


def delete_resource(
    document: CommentedMap,
    *,
    resource_id: str,
    delete_subtree: bool = False,
) -> bool:
    """Delete resource by explicit id."""

    location = get_single_resource_by_id(document, resource_id)
    children = location.node.get("children")
    has_children = isinstance(children, CommentedSeq) and len(children) > 0
    if has_children and not delete_subtree:
        raise ValidationError("resource has children; pass --delete-subtree")

    location.container.pop(location.index)
    return True


def clone_resource(
    document: CommentedMap,
    *,
    resource_id: str,
    new_id: str,
    new_parent_id: str | None,
    new_name: str | None = None,
    with_children: bool = False,
) -> bool:
    """Clone resource under parent or root."""

    existing = build_resource_id_index(document)
    if new_id in existing:
        raise ValidationError(f"resource id already exists: {new_id}")

    source = get_single_resource_by_id(document, resource_id)
    clone = deepcopy(source.node)
    _clear_anchors(clone)

    clone["id"] = new_id
    if new_name is not None:
        clone["name"] = new_name
    if not with_children:
        clone.pop("children", None)
    else:
        duplicate_descendant = _first_explicit_descendant_id(clone, existing_ids=set(existing))
        if duplicate_descendant is not None:
            raise ValidationError(
                "cannot clone subtree with explicit child ids; "
                f"conflicting id: {duplicate_descendant}. "
                "Use --shallow or rename child ids after clone."
            )

    if new_parent_id is None:
        source.container.append(clone)
        return True

    if is_none_token(new_parent_id):
        root = _ensure_root_resources(document)
        root.append(clone)
        return True

    parent = get_single_resource_by_id(document, new_parent_id)
    children = ensure_children(parent.node)
    children.append(clone)
    return True


def move_resource_to_root(document: CommentedMap, *, resource_id: str) -> bool:
    """Move resource subtree to top-level resources."""

    location = get_single_resource_by_id(document, resource_id)
    if location.parent is None:
        return False
    source_container = location.container
    source_container.pop(location.index)
    root = _ensure_root_resources(document)
    root.append(location.node)
    return True


def _ensure_root_resources(document: CommentedMap) -> CommentedSeq:
    resources = document.get("resources")
    if isinstance(resources, CommentedSeq):
        return resources
    new_resources = CommentedSeq()
    document["resources"] = new_resources
    return new_resources


def _is_descendant(ancestor: CommentedMap, node: CommentedMap) -> bool:
    children = ancestor.get("children")
    if not isinstance(children, CommentedSeq):
        return False
    for child in children:
        if not isinstance(child, CommentedMap):
            continue
        if child is node:
            return True
        if _is_descendant(child, node):
            return True
    return False


def _rewrite_reference_strings(document: CommentedMap, old: str, new: str) -> None:
    for field in iter_reference_fields(document):
        value = field.container.get(field.key)
        if not isinstance(value, str):
            continue
        updated = replace_reference_identifier(value, old, new)
        if updated != value:
            field.container[field.key] = updated

    _rewrite_context_strings(document, old, new)


def _rewrite_context_strings(document: CommentedMap, old: str, new: str) -> None:
    contexts = document.get("contexts")
    if not isinstance(contexts, CommentedSeq):
        return
    for context in contexts:
        if not isinstance(context, CommentedMap):
            continue
        for key, value in list(context.items()):
            if not isinstance(value, str):
                continue
            updated = replace_reference_identifier(value, old, new)
            if updated != value:
                context[key] = updated


def _first_explicit_descendant_id(node: CommentedMap, *, existing_ids: set[str]) -> str | None:
    children = node.get("children")
    if not isinstance(children, CommentedSeq):
        return None

    for child in children:
        if not isinstance(child, CommentedMap):
            continue
        raw_id = child.get("id")
        if isinstance(raw_id, str) and raw_id.strip():
            child_id = raw_id.strip()
            if child_id in existing_ids:
                return child_id
        nested = _first_explicit_descendant_id(child, existing_ids=existing_ids)
        if nested is not None:
            return nested
    return None


def _clear_resource_style_for_inheritance(resource: CommentedMap) -> bool:
    """Drop explicit style so resource follows parent styling."""

    if "style" not in resource:
        return False
    resource.pop("style", None)
    return True


def _clear_anchors(node: CommentedMap | CommentedSeq) -> None:
    if isinstance(node, CommentedMap):
        node.yaml_set_anchor(None)
        for value in node.values():
            if isinstance(value, (CommentedMap, CommentedSeq)):
                _clear_anchors(value)
        return

    node.yaml_set_anchor(None)
    for item in node:
        if isinstance(item, (CommentedMap, CommentedSeq)):
            _clear_anchors(item)
