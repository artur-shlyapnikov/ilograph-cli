"""Relation operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.index import build_perspective_locations, get_single_perspective
from ilograph_cli.core.relation_types import (
    RelationClearField,
    RelationTemplate,
    RelationTemplateValue,
)

_CONTEXT_TOKEN = "{context}"

_RELATION_EDITABLE_FIELDS: frozenset[RelationClearField] = frozenset(
    {
        "from",
        "to",
        "via",
        "label",
        "description",
        "arrowDirection",
        "color",
        "secondary",
    }
)


@dataclass(slots=True)
class _EditSpec:
    match: RelationTemplate
    set_values: RelationTemplate | None


def add_relation(
    document: CommentedMap,
    *,
    perspective_id: str,
    from_ref: str | None,
    to_ref: str | None,
    via: str | None,
    label: str | None,
    description: str | None,
    arrow_direction: str | None,
    color: str | None,
    secondary: bool | None,
) -> bool:
    """Add relation to perspective."""

    if from_ref is None and to_ref is None:
        raise ValidationError(
            "relation requires from or to (set --from and/or --to)"
        )

    perspective = get_single_perspective(document, perspective_id)
    relations = perspective.node.get("relations")
    if not isinstance(relations, CommentedSeq):
        relations = CommentedSeq()
        perspective.node["relations"] = relations

    relation = CommentedMap()
    if from_ref is not None:
        relation["from"] = from_ref
    if to_ref is not None:
        relation["to"] = to_ref
    if via is not None:
        relation["via"] = via
    if label is not None:
        relation["label"] = label
    if description is not None:
        relation["description"] = description
    if arrow_direction is not None:
        relation["arrowDirection"] = arrow_direction
    if color is not None:
        relation["color"] = color
    if secondary is not None:
        relation["secondary"] = secondary

    relations.append(relation)
    return True


def add_relation_many(
    document: CommentedMap,
    *,
    perspectives: list[str] | str,
    contexts: list[str] | None,
    template: RelationTemplate,
) -> int:
    """Add same templated relation to multiple perspectives/contexts."""

    perspective_ids = _resolve_perspectives(document, perspectives)
    context_names = _resolve_contexts(document, contexts)
    payloads = _expand_payload_templates(template, context_names)

    added = 0
    for perspective_id in perspective_ids:
        for payload in payloads:
            add_relation(
                document,
                perspective_id=perspective_id,
                from_ref=_as_str(payload.get("from")),
                to_ref=_as_str(payload.get("to")),
                via=_as_str(payload.get("via")),
                label=_as_str(payload.get("label")),
                description=_as_str(payload.get("description")),
                arrow_direction=_as_str(payload.get("arrowDirection")),
                color=_as_str(payload.get("color")),
                secondary=_as_bool(payload.get("secondary")),
            )
            added += 1
    return added


def remove_relation(document: CommentedMap, *, perspective_id: str, index_1_based: int) -> bool:
    """Remove relation by 1-based index."""

    perspective = get_single_perspective(document, perspective_id)
    relations = perspective.node.get("relations")
    if not isinstance(relations, CommentedSeq):
        raise ValidationError(
            f"perspective has no relations: {perspective_id} "
            "(nothing to remove)"
        )

    idx = index_1_based - 1
    if idx < 0 or idx >= len(relations):
        raise ValidationError(
            f"relation index out of range: {index_1_based} "
            f"(valid range: 1..{len(relations)})"
        )
    relations.pop(idx)
    return True


def remove_relations_match_many(
    document: CommentedMap,
    *,
    perspectives: list[str] | str,
    contexts: list[str] | None,
    match_template: RelationTemplate,
    require_match: bool,
) -> int:
    """Remove relations matched by templates across many perspectives."""

    perspective_ids = _resolve_perspectives(document, perspectives)
    context_names = _resolve_contexts(document, contexts)
    match_payloads = _expand_payload_templates(match_template, context_names)

    removed = 0
    for perspective_id in perspective_ids:
        relations = _get_relations_seq(document, perspective_id, create=False)
        if relations is None:
            continue

        to_delete: list[int] = []
        for index, relation in enumerate(relations):
            if not isinstance(relation, CommentedMap):
                continue
            if any(_relation_matches(relation, payload) for payload in match_payloads):
                to_delete.append(index)

        for index in reversed(to_delete):
            relations.pop(index)
            removed += 1

    if require_match and removed == 0:
        raise ValidationError(
            "no relations matched for relation.remove-match "
            "(adjust match/target or set requireMatch=false)"
        )
    return removed


def edit_relation(
    document: CommentedMap,
    *,
    perspective_id: str,
    index_1_based: int,
    from_ref: str | None,
    to_ref: str | None,
    via: str | None,
    label: str | None,
    description: str | None,
    arrow_direction: str | None,
    color: str | None,
    secondary: bool | None,
    clear_from: bool,
    clear_to: bool,
    clear_via: bool,
    clear_label: bool,
    clear_description: bool,
) -> bool:
    """Edit relation by 1-based index."""

    perspective = get_single_perspective(document, perspective_id)
    relations = perspective.node.get("relations")
    if not isinstance(relations, CommentedSeq):
        raise ValidationError(
            f"perspective has no relations: {perspective_id} "
            "(nothing to edit)"
        )

    idx = index_1_based - 1
    if idx < 0 or idx >= len(relations):
        raise ValidationError(
            f"relation index out of range: {index_1_based} "
            f"(valid range: 1..{len(relations)})"
        )

    relation = relations[idx]
    if not isinstance(relation, CommentedMap):
        raise ValidationError(
            f"relation at index {index_1_based} is not a mapping/object"
        )

    before = _relation_snapshot(relation)

    _apply_edit(relation, "from", from_ref, clear_from)
    _apply_edit(relation, "to", to_ref, clear_to)
    _apply_edit(relation, "via", via, clear_via)
    _apply_edit(relation, "label", label, clear_label)
    _apply_edit(relation, "description", description, clear_description)

    if arrow_direction is not None:
        relation["arrowDirection"] = arrow_direction
    if color is not None:
        relation["color"] = color
    if secondary is not None:
        relation["secondary"] = secondary

    _validate_relation_integrity(relation)
    return before != _relation_snapshot(relation)


def edit_relations_match_many(
    document: CommentedMap,
    *,
    perspectives: list[str] | str,
    contexts: list[str] | None,
    match_template: RelationTemplate,
    set_template: RelationTemplate | None,
    clear_fields: Sequence[RelationClearField],
    require_match: bool,
) -> int:
    """Edit all relations that match template across perspectives/contexts."""

    _validate_clear_fields(clear_fields)

    perspective_ids = _resolve_perspectives(document, perspectives)
    context_names = _resolve_contexts(document, contexts)
    edit_specs = _expand_edit_specs(match_template, set_template, context_names)

    edited = 0
    for perspective_id in perspective_ids:
        relations = _get_relations_seq(document, perspective_id, create=False)
        if relations is None:
            continue
        for relation in relations:
            if not isinstance(relation, CommentedMap):
                continue
            for spec in edit_specs:
                if not _relation_matches(relation, spec.match):
                    continue
                changed = _apply_patch(
                    relation,
                    set_values=spec.set_values,
                    clear_fields=clear_fields,
                )
                if changed:
                    edited += 1
                break

    if require_match and edited == 0:
        raise ValidationError(
            "no relations matched for relation.edit-match "
            "(adjust match/target or set requireMatch=false)"
        )
    return edited


def _as_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _as_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _get_relations_seq(
    document: CommentedMap,
    perspective_id: str,
    *,
    create: bool,
) -> CommentedSeq | None:
    perspective = get_single_perspective(document, perspective_id)
    relations = perspective.node.get("relations")
    if isinstance(relations, CommentedSeq):
        return relations
    if not create:
        return None
    created = CommentedSeq()
    perspective.node["relations"] = created
    return created


def _relation_matches(
    relation: Mapping[str, object],
    expected: Mapping[str, RelationTemplateValue],
) -> bool:
    for key, expected_value in expected.items():
        if key == "secondary":
            actual = relation.get("secondary")
            actual_bool = actual if isinstance(actual, bool) else False
            if expected_value != actual_bool:
                return False
            continue
        if relation.get(key) != expected_value:
            return False
    return True


def _apply_patch(
    relation: CommentedMap,
    *,
    set_values: RelationTemplate | None,
    clear_fields: Sequence[RelationClearField],
) -> bool:
    before = _relation_snapshot(relation)

    for field in clear_fields:
        relation.pop(field, None)

    if set_values is not None:
        for key, value in set_values.items():
            relation[key] = value

    _validate_relation_integrity(relation)
    return before != _relation_snapshot(relation)


def _validate_relation_integrity(relation: Mapping[str, object]) -> None:
    if "from" not in relation and "to" not in relation:
        raise ValidationError("relation must define from or to")


def _apply_edit(relation: CommentedMap, key: str, value: str | None, clear: bool) -> None:
    if clear:
        relation.pop(key, None)
        return
    if value is not None:
        relation[key] = value


def _relation_snapshot(relation: Mapping[str, object]) -> tuple[tuple[str, object], ...]:
    return tuple((str(key), value) for key, value in relation.items())


def _resolve_perspectives(document: CommentedMap, target: list[str] | str) -> list[str]:
    available = [item.identifier for item in build_perspective_locations(document)]
    if not available:
        raise ValidationError(
            "diagram has no perspectives (cannot apply relation operation)"
        )

    if target == "*":
        return available

    selected: list[str] = []
    seen: set[str] = set()
    for perspective_id in target:
        if perspective_id in seen:
            raise ValidationError(
                f"target.perspectives has duplicate: {perspective_id}"
            )
        get_single_perspective(document, perspective_id)
        seen.add(perspective_id)
        selected.append(perspective_id)
    return selected


def _resolve_contexts(document: CommentedMap, target: list[str] | None) -> list[str] | None:
    if target is None:
        return None

    available_contexts = _available_context_names(document)
    missing = [context for context in target if context not in available_contexts]
    if missing:
        missing_list = ", ".join(missing)
        raise ValidationError(
            f"unknown context(s): {missing_list} "
            "(expected values from contexts[].name)"
        )
    return target


def _available_context_names(document: CommentedMap) -> set[str]:
    contexts = document.get("contexts")
    if not isinstance(contexts, CommentedSeq):
        return set()

    names: set[str] = set()
    for context in contexts:
        if not isinstance(context, CommentedMap):
            continue
        name = context.get("name")
        if isinstance(name, str):
            names.add(name)
    return names


def _expand_payload_templates(
    template: RelationTemplate,
    contexts: list[str] | None,
) -> list[RelationTemplate]:
    if contexts is None:
        return [_render_template(template, context=None)]

    payloads: list[RelationTemplate] = []
    seen: set[tuple[tuple[str, RelationTemplateValue], ...]] = set()
    for context in contexts:
        rendered = _render_template(template, context=context)
        signature = tuple(sorted(rendered.items(), key=lambda item: item[0]))
        if signature in seen:
            continue
        seen.add(signature)
        payloads.append(rendered)
    return payloads


def _expand_edit_specs(
    match_template: RelationTemplate,
    set_template: RelationTemplate | None,
    contexts: list[str] | None,
) -> list[_EditSpec]:
    if contexts is None:
        return [
            _EditSpec(
                match=_render_template(match_template, context=None),
                set_values=_render_template(set_template, context=None)
                if set_template is not None
                else None,
            )
        ]

    specs: list[_EditSpec] = []
    seen = set()
    for context in contexts:
        rendered_match = _render_template(match_template, context=context)
        rendered_set = (
            _render_template(set_template, context=context)
            if set_template is not None
            else None
        )
        signature = (
            tuple(sorted(rendered_match.items(), key=lambda item: item[0])),
            tuple(sorted(rendered_set.items(), key=lambda item: item[0]))
            if rendered_set is not None
            else None,
        )
        if signature in seen:
            continue
        seen.add(signature)
        specs.append(_EditSpec(match=rendered_match, set_values=rendered_set))
    return specs


def _render_template(
    payload: RelationTemplate | None,
    *,
    context: str | None,
) -> RelationTemplate:
    if payload is None:
        return {}

    rendered: RelationTemplate = {}
    for key, value in payload.items():
        if isinstance(value, str) and _CONTEXT_TOKEN in value:
            if context is None:
                raise ValidationError(
                    "template contains '{context}' but target.contexts is not set "
                    "(set target.contexts or remove template token)"
                )
            rendered[key] = value.replace(_CONTEXT_TOKEN, context)
            continue
        rendered[key] = value
    return rendered


def _validate_clear_fields(clear_fields: Sequence[RelationClearField]) -> None:
    invalid = [field for field in clear_fields if field not in _RELATION_EDITABLE_FIELDS]
    if invalid:
        invalid_list = ", ".join(invalid)
        allowed = ", ".join(sorted(_RELATION_EDITABLE_FIELDS))
        raise ValidationError(
            f"invalid clear field(s): {invalid_list} (allowed: {allowed})"
        )
