"""Perspective operations."""

from __future__ import annotations

from copy import deepcopy

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.index import build_perspective_locations, get_single_perspective
from ilograph_cli.core.references import replace_reference_identifier


def list_perspectives(document: CommentedMap) -> list[dict[str, object]]:
    """Return perspective metadata rows."""

    rows: list[dict[str, object]] = []
    for location in build_perspective_locations(document):
        node = location.node
        rows.append(
            {
                "index": location.index + 1,
                "identifier": location.identifier,
                "id": _as_optional_str(node.get("id")),
                "name": _as_optional_str(node.get("name")),
                "extends": _as_optional_str(node.get("extends")),
                "orientation": _as_optional_str(node.get("orientation")),
                "hasRelations": isinstance(node.get("relations"), CommentedSeq),
                "hasSequence": isinstance(node.get("sequence"), CommentedMap),
            }
        )
    return rows


def create_perspective(
    document: CommentedMap,
    *,
    perspective_id: str,
    name: str,
    extends: str | None = None,
    orientation: str | None = None,
    index_1_based: int | None = None,
) -> bool:
    """Create perspective."""

    _assert_new_perspective_identifier(document, perspective_id)
    if extends is not None:
        _validate_extends_tokens(document, extends)

    perspectives = _ensure_perspectives(document)
    perspective = CommentedMap()
    perspective["id"] = perspective_id
    perspective["name"] = name
    if extends is not None:
        perspective["extends"] = extends
    if orientation is not None:
        perspective["orientation"] = orientation

    if index_1_based is None:
        perspectives.append(perspective)
        return True

    insert_at = _normalize_insert_index(index_1_based, size=len(perspectives))
    perspectives.insert(insert_at, perspective)
    return True


def rename_perspective(
    document: CommentedMap,
    *,
    perspective: str,
    new_id: str | None,
    new_name: str | None,
) -> bool:
    """Rename perspective id/name."""

    if new_id is None and new_name is None:
        raise ValidationError("set --new-id or --new-name")

    location = get_single_perspective(document, perspective)
    node = location.node
    before = tuple((str(key), value) for key, value in node.items())

    if new_id is not None and new_id != location.identifier:
        _assert_new_perspective_identifier(document, new_id)
        old_identifier = location.identifier
        node["id"] = new_id
        _rewrite_extends_token(document, old=old_identifier, new=new_id)

    if new_name is not None:
        node["name"] = new_name

    after = tuple((str(key), value) for key, value in node.items())
    return before != after


def delete_perspective(
    document: CommentedMap,
    *,
    perspective: str,
    force: bool = False,
) -> bool:
    """Delete perspective."""

    perspectives = document.get("perspectives")
    if not isinstance(perspectives, CommentedSeq):
        raise ValidationError("diagram has no perspectives")

    location = get_single_perspective(document, perspective)
    blockers = _find_extends_references(document, target=location.identifier)
    if blockers and not force:
        blocker_list = ", ".join(blockers)
        raise ValidationError(
            "perspective is referenced in extends; "
            f"pass --force to remove references ({blocker_list})"
        )

    perspectives.pop(location.index)
    if force:
        _remove_from_extends(document, target=location.identifier)
    return True


def reorder_perspective(
    document: CommentedMap,
    *,
    perspective: str,
    index_1_based: int,
) -> bool:
    """Move perspective to 1-based index."""

    perspectives = document.get("perspectives")
    if not isinstance(perspectives, CommentedSeq):
        raise ValidationError("diagram has no perspectives")

    location = get_single_perspective(document, perspective)
    destination = _normalize_insert_index(index_1_based, size=len(perspectives), allow_end=False)
    if destination == location.index:
        return False

    node = perspectives.pop(location.index)
    perspectives.insert(destination, node)
    return True


def copy_perspective(
    document: CommentedMap,
    *,
    perspective: str,
    new_id: str,
    new_name: str | None = None,
    index_1_based: int | None = None,
) -> bool:
    """Copy perspective with a new explicit id."""

    _assert_new_perspective_identifier(document, new_id)

    source = get_single_perspective(document, perspective)
    clone = deepcopy(source.node)
    _clear_anchors(clone)
    clone["id"] = new_id
    if new_name is not None:
        clone["name"] = new_name

    perspectives = _ensure_perspectives(document)
    if index_1_based is None:
        perspectives.append(clone)
        return True

    insert_at = _normalize_insert_index(index_1_based, size=len(perspectives))
    perspectives.insert(insert_at, clone)
    return True


def _ensure_perspectives(document: CommentedMap) -> CommentedSeq:
    perspectives = document.get("perspectives")
    if isinstance(perspectives, CommentedSeq):
        return perspectives
    created = CommentedSeq()
    document["perspectives"] = created
    return created


def _assert_new_perspective_identifier(document: CommentedMap, candidate: str) -> None:
    identifiers = {location.identifier for location in build_perspective_locations(document)}
    if candidate in identifiers:
        raise ValidationError(f"perspective id already exists: {candidate}")


def _split_tokens(raw: str) -> list[str]:
    return [token.strip() for token in raw.split(",") if token.strip()]


def _validate_extends_tokens(document: CommentedMap, raw: str) -> None:
    for token in _split_tokens(raw):
        get_single_perspective(document, token)


def _find_extends_references(document: CommentedMap, *, target: str) -> list[str]:
    refs: list[str] = []
    for location in build_perspective_locations(document):
        extends = location.node.get("extends")
        if not isinstance(extends, str):
            continue
        tokens = _split_tokens(extends)
        if target in tokens:
            refs.append(location.identifier)
    return refs


def _rewrite_extends_token(document: CommentedMap, *, old: str, new: str) -> None:
    if old == new:
        return

    for location in build_perspective_locations(document):
        extends = location.node.get("extends")
        if not isinstance(extends, str):
            continue
        rewritten = replace_reference_identifier(extends, old, new)
        if rewritten != extends:
            location.node["extends"] = rewritten


def _remove_from_extends(document: CommentedMap, *, target: str) -> None:
    for location in build_perspective_locations(document):
        extends = location.node.get("extends")
        if not isinstance(extends, str):
            continue

        remaining = [token for token in _split_tokens(extends) if token != target]
        if not remaining:
            location.node.pop("extends", None)
            continue

        updated = ", ".join(remaining)
        location.node["extends"] = updated


def _normalize_insert_index(index_1_based: int, *, size: int, allow_end: bool = True) -> int:
    if index_1_based < 1:
        raise ValidationError("index must be >= 1")

    max_index = size + 1 if allow_end else size
    if index_1_based > max_index:
        raise ValidationError(f"index out of range: {index_1_based}")

    return index_1_based - 1


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


def _as_optional_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None
