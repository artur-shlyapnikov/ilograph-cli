"""Context operations."""

from __future__ import annotations

from copy import deepcopy

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.references import replace_reference_identifier


def list_contexts(document: CommentedMap) -> list[dict[str, object]]:
    """Return context metadata rows."""

    rows: list[dict[str, object]] = []
    contexts = document.get("contexts")
    if not isinstance(contexts, CommentedSeq):
        return rows

    for index, context in enumerate(contexts, start=1):
        if not isinstance(context, CommentedMap):
            continue
        name = context.get("name")
        if not isinstance(name, str):
            continue
        hidden = context.get("hidden")
        rows.append(
            {
                "index": index,
                "name": name,
                "extends": _as_optional_str(context.get("extends")),
                "hidden": bool(hidden) if isinstance(hidden, bool) else False,
                "hasRoots": isinstance(context.get("roots"), CommentedSeq),
            }
        )
    return rows


def create_context(
    document: CommentedMap,
    *,
    name: str,
    extends: str | None = None,
    hidden: bool | None = None,
    index_1_based: int | None = None,
) -> bool:
    """Create context."""

    _assert_context_name_not_exists(document, name)
    if extends is not None:
        _validate_extends_tokens(document, extends)

    context = CommentedMap()
    context["name"] = name
    if extends is not None:
        context["extends"] = extends
    if hidden is not None:
        context["hidden"] = hidden

    contexts = _ensure_contexts(document)
    if index_1_based is None:
        contexts.append(context)
        return True

    insert_at = _normalize_insert_index(index_1_based, size=len(contexts))
    contexts.insert(insert_at, context)
    return True


def rename_context(document: CommentedMap, *, name: str, new_name: str) -> bool:
    """Rename context by name."""

    if name == new_name:
        return False

    _assert_context_name_not_exists(document, new_name)
    context = _get_single_context(document, name)
    context["name"] = new_name
    _rewrite_context_extends(document, old=name, new=new_name)
    return True


def delete_context(document: CommentedMap, *, name: str, force: bool = False) -> bool:
    """Delete context by name."""

    contexts = document.get("contexts")
    if not isinstance(contexts, CommentedSeq):
        raise ValidationError("diagram has no contexts")

    index, _node = _get_single_context_with_index(document, name)
    blockers = _find_extends_references(document, target=name)
    if blockers and not force:
        blocker_list = ", ".join(blockers)
        raise ValidationError(
            "context is referenced in extends; "
            f"pass --force to remove references ({blocker_list})"
        )

    contexts.pop(index)
    if force:
        _remove_from_extends(document, target=name)
    return True


def reorder_context(document: CommentedMap, *, name: str, index_1_based: int) -> bool:
    """Move context to 1-based index."""

    contexts = document.get("contexts")
    if not isinstance(contexts, CommentedSeq):
        raise ValidationError("diagram has no contexts")

    source_index, node = _get_single_context_with_index(document, name)
    destination = _normalize_insert_index(index_1_based, size=len(contexts), allow_end=False)
    if destination == source_index:
        return False

    contexts.pop(source_index)
    contexts.insert(destination, node)
    return True


def copy_context(
    document: CommentedMap,
    *,
    name: str,
    new_name: str,
    index_1_based: int | None = None,
) -> bool:
    """Copy context with a new name."""

    _assert_context_name_not_exists(document, new_name)
    source = _get_single_context(document, name)

    clone = deepcopy(source)
    _clear_anchors(clone)
    clone["name"] = new_name

    contexts = _ensure_contexts(document)
    if index_1_based is None:
        contexts.append(clone)
        return True

    insert_at = _normalize_insert_index(index_1_based, size=len(contexts))
    contexts.insert(insert_at, clone)
    return True


def _ensure_contexts(document: CommentedMap) -> CommentedSeq:
    contexts = document.get("contexts")
    if isinstance(contexts, CommentedSeq):
        return contexts
    created = CommentedSeq()
    document["contexts"] = created
    return created


def _all_context_names(document: CommentedMap) -> list[str]:
    names: list[str] = []
    contexts = document.get("contexts")
    if not isinstance(contexts, CommentedSeq):
        return names

    for context in contexts:
        if not isinstance(context, CommentedMap):
            continue
        name = context.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return names


def _assert_context_name_not_exists(document: CommentedMap, name: str) -> None:
    if name in set(_all_context_names(document)):
        raise ValidationError(f"context already exists: {name}")


def _get_single_context(document: CommentedMap, name: str) -> CommentedMap:
    _index, context = _get_single_context_with_index(document, name)
    return context


def _get_single_context_with_index(document: CommentedMap, name: str) -> tuple[int, CommentedMap]:
    contexts = document.get("contexts")
    if not isinstance(contexts, CommentedSeq):
        raise ValidationError("diagram has no contexts")

    matches: list[tuple[int, CommentedMap]] = []
    for index, context in enumerate(contexts):
        if not isinstance(context, CommentedMap):
            continue
        raw_name = context.get("name")
        if not isinstance(raw_name, str):
            continue
        if raw_name.strip() == name:
            matches.append((index, context))

    if not matches:
        raise ValidationError(f"context not found: {name}")
    if len(matches) > 1:
        indices = ", ".join(str(item[0]) for item in matches)
        raise ValidationError(f"context name not unique: {name} ({indices})")
    return matches[0]


def _split_tokens(raw: str) -> list[str]:
    return [token.strip() for token in raw.split(",") if token.strip()]


def _validate_extends_tokens(document: CommentedMap, raw: str) -> None:
    available = set(_all_context_names(document))
    missing = [token for token in _split_tokens(raw) if token not in available]
    if missing:
        raise ValidationError(f"unknown extends context(s): {', '.join(missing)}")


def _rewrite_context_extends(document: CommentedMap, *, old: str, new: str) -> None:
    if old == new:
        return

    contexts = document.get("contexts")
    if not isinstance(contexts, CommentedSeq):
        return

    for context in contexts:
        if not isinstance(context, CommentedMap):
            continue
        extends = context.get("extends")
        if not isinstance(extends, str):
            continue
        rewritten = replace_reference_identifier(extends, old, new)
        if rewritten != extends:
            context["extends"] = rewritten


def _find_extends_references(document: CommentedMap, *, target: str) -> list[str]:
    refs: list[str] = []
    contexts = document.get("contexts")
    if not isinstance(contexts, CommentedSeq):
        return refs

    for context in contexts:
        if not isinstance(context, CommentedMap):
            continue
        name = context.get("name")
        extends = context.get("extends")
        if not isinstance(name, str) or not isinstance(extends, str):
            continue
        if target in _split_tokens(extends):
            refs.append(name)
    return refs


def _remove_from_extends(document: CommentedMap, *, target: str) -> None:
    contexts = document.get("contexts")
    if not isinstance(contexts, CommentedSeq):
        return

    for context in contexts:
        if not isinstance(context, CommentedMap):
            continue
        extends = context.get("extends")
        if not isinstance(extends, str):
            continue

        remaining = [token for token in _split_tokens(extends) if token != target]
        if not remaining:
            context.pop("extends", None)
            continue

        context["extends"] = ", ".join(remaining)


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
