"""Perspective alias operations."""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.index import get_single_perspective


def list_aliases(document: CommentedMap, *, perspective: str) -> list[dict[str, object]]:
    """List aliases for a perspective."""

    location = get_single_perspective(document, perspective)
    aliases = location.node.get("aliases")
    rows: list[dict[str, object]] = []
    if not isinstance(aliases, CommentedSeq):
        return rows

    for index, item in enumerate(aliases, start=1):
        if not isinstance(item, CommentedMap):
            continue
        alias_name = item.get("alias")
        alias_for = item.get("for")
        if not isinstance(alias_name, str):
            continue
        rows.append(
            {
                "perspective": location.identifier,
                "index": index,
                "alias": alias_name,
                "for": alias_for if isinstance(alias_for, str) else None,
            }
        )
    return rows


def add_alias(
    document: CommentedMap,
    *,
    perspective: str,
    alias: str,
    alias_for: str,
    index_1_based: int | None = None,
) -> bool:
    """Add alias to perspective."""

    location = get_single_perspective(document, perspective)
    aliases = _ensure_aliases(location.node)
    if _find_alias_index(aliases, alias) is not None:
        raise ValidationError(f"alias already exists: {alias}")

    payload = CommentedMap()
    payload["alias"] = alias
    payload["for"] = alias_for

    if index_1_based is None:
        aliases.append(payload)
        return True

    insert_at = _normalize_insert_index(index_1_based, size=len(aliases))
    aliases.insert(insert_at, payload)
    return True


def edit_alias(
    document: CommentedMap,
    *,
    perspective: str,
    alias: str,
    new_alias: str | None,
    new_for: str | None,
) -> bool:
    """Edit alias name/value."""

    if new_alias is None and new_for is None:
        raise ValidationError("set --new-alias or --new-for")

    location = get_single_perspective(document, perspective)
    aliases = location.node.get("aliases")
    if not isinstance(aliases, CommentedSeq):
        raise ValidationError(f"perspective has no aliases: {location.identifier}")

    target_index = _find_alias_index(aliases, alias)
    if target_index is None:
        raise ValidationError(f"alias not found: {alias}")

    target = aliases[target_index]
    if not isinstance(target, CommentedMap):
        raise ValidationError(f"alias entry is not a mapping: {alias}")

    changed = False
    if new_alias is not None and new_alias != alias:
        existing_index = _find_alias_index(aliases, new_alias)
        if existing_index is not None and existing_index != target_index:
            raise ValidationError(f"alias already exists: {new_alias}")
        target["alias"] = new_alias
        changed = True

    if new_for is not None and target.get("for") != new_for:
        target["for"] = new_for
        changed = True

    return changed


def remove_alias(document: CommentedMap, *, perspective: str, alias: str) -> bool:
    """Remove alias by name."""

    location = get_single_perspective(document, perspective)
    aliases = location.node.get("aliases")
    if not isinstance(aliases, CommentedSeq):
        raise ValidationError(f"perspective has no aliases: {location.identifier}")

    target_index = _find_alias_index(aliases, alias)
    if target_index is None:
        raise ValidationError(f"alias not found: {alias}")

    aliases.pop(target_index)
    return True


def _ensure_aliases(perspective: CommentedMap) -> CommentedSeq:
    aliases = perspective.get("aliases")
    if isinstance(aliases, CommentedSeq):
        return aliases
    created = CommentedSeq()
    perspective["aliases"] = created
    return created


def _find_alias_index(aliases: CommentedSeq, alias: str) -> int | None:
    for index, item in enumerate(aliases):
        if not isinstance(item, CommentedMap):
            continue
        raw_alias = item.get("alias")
        if isinstance(raw_alias, str) and raw_alias == alias:
            return index
    return None


def _normalize_insert_index(index_1_based: int, *, size: int) -> int:
    if index_1_based < 1:
        raise ValidationError("index must be >= 1")
    if index_1_based > size + 1:
        raise ValidationError(f"index out of range: {index_1_based}")
    return index_1_based - 1
