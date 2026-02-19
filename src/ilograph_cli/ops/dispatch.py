"""Operation dispatch for ops.yaml application."""

from __future__ import annotations

from functools import singledispatch

from ruamel.yaml.comments import CommentedMap

from ilograph_cli.core.ops_models import (
    FmtStableOp,
    GroupCreateOp,
    MoveManyOp,
    MoveResourceOp,
    Operation,
    RelationAddManyOp,
    RelationAddOp,
    RelationEditMatchOp,
    RelationEditOp,
    RelationRemoveMatchOp,
    RelationRemoveOp,
    RenameResourceIdOp,
    RenameResourceOp,
    ResourceCloneOp,
    ResourceCreateOp,
    ResourceDeleteOp,
)
from ilograph_cli.ops.group_ops import create_group, move_many
from ilograph_cli.ops.relation_ops import (
    add_relation,
    add_relation_many,
    edit_relation,
    edit_relations_match_many,
    remove_relation,
    remove_relations_match_many,
)
from ilograph_cli.ops.resource_ops import (
    clone_resource,
    create_resource,
    delete_resource,
    move_resource,
    rename_resource,
    rename_resource_id,
)


@singledispatch
def apply_op(op: object, document: CommentedMap) -> bool:
    """Apply single validated operation."""

    raise TypeError(f"unsupported op: {type(op).__name__}")


@apply_op.register
def _apply_rename_resource(op: RenameResourceOp, document: CommentedMap) -> bool:
    return rename_resource(document, resource_id=op.id, new_name=op.name)


@apply_op.register
def _apply_resource_create(op: ResourceCreateOp, document: CommentedMap) -> bool:
    return create_resource(
        document,
        resource_id=op.id,
        name=op.name,
        parent_id=op.parent,
        subtitle=op.subtitle,
    )


@apply_op.register
def _apply_resource_delete(op: ResourceDeleteOp, document: CommentedMap) -> bool:
    return delete_resource(
        document,
        resource_id=op.id,
        delete_subtree=op.delete_subtree,
    )


@apply_op.register
def _apply_resource_clone(op: ResourceCloneOp, document: CommentedMap) -> bool:
    return clone_resource(
        document,
        resource_id=op.id,
        new_id=op.new_id,
        new_parent_id=op.new_parent,
        new_name=op.new_name,
        with_children=op.with_children,
    )


@apply_op.register
def _apply_rename_resource_id(op: RenameResourceIdOp, document: CommentedMap) -> bool:
    return rename_resource_id(document, old_id=op.from_, new_id=op.to)


@apply_op.register
def _apply_move_resource(op: MoveResourceOp, document: CommentedMap) -> bool:
    return move_resource(
        document,
        resource_id=op.id,
        new_parent_id=op.new_parent,
        inherit_style_from_parent=op.inherit_style_from_parent,
    )


@apply_op.register
def _apply_group_create(op: GroupCreateOp, document: CommentedMap) -> bool:
    return create_group(
        document,
        group_id=op.id,
        name=op.name,
        parent_id=op.parent,
        subtitle=op.subtitle,
    )


@apply_op.register
def _apply_move_many(op: MoveManyOp, document: CommentedMap) -> bool:
    return move_many(document, ids=op.ids, new_parent_id=op.new_parent)


@apply_op.register
def _apply_relation_add(op: RelationAddOp, document: CommentedMap) -> bool:
    return add_relation(
        document,
        perspective_id=op.perspective,
        from_ref=op.from_,
        to_ref=op.to,
        via=op.via,
        label=op.label,
        description=op.description,
        arrow_direction=op.arrow_direction,
        color=op.color,
        secondary=op.secondary,
    )


@apply_op.register
def _apply_relation_add_many(op: RelationAddManyOp, document: CommentedMap) -> bool:
    return (
        add_relation_many(
            document,
            perspectives=op.target.perspectives,
            contexts=op.target.contexts,
            template=op.to_payload(),
        )
        > 0
    )


@apply_op.register
def _apply_relation_remove(op: RelationRemoveOp, document: CommentedMap) -> bool:
    return remove_relation(document, perspective_id=op.perspective, index_1_based=op.index)


@apply_op.register
def _apply_relation_remove_match(op: RelationRemoveMatchOp, document: CommentedMap) -> bool:
    return (
        remove_relations_match_many(
            document,
            perspectives=op.target.perspectives,
            contexts=op.target.contexts,
            match_template=op.match.to_payload(),
            require_match=op.require_match,
        )
        > 0
    )


@apply_op.register
def _apply_relation_edit(op: RelationEditOp, document: CommentedMap) -> bool:
    return edit_relation(
        document,
        perspective_id=op.perspective,
        index_1_based=op.index,
        from_ref=op.from_,
        to_ref=op.to,
        via=op.via,
        label=op.label,
        description=op.description,
        arrow_direction=op.arrow_direction,
        color=op.color,
        secondary=op.secondary,
        clear_from=op.clear_from,
        clear_to=op.clear_to,
        clear_via=op.clear_via,
        clear_label=op.clear_label,
        clear_description=op.clear_description,
    )


@apply_op.register
def _apply_relation_edit_match(op: RelationEditMatchOp, document: CommentedMap) -> bool:
    return (
        edit_relations_match_many(
            document,
            perspectives=op.target.perspectives,
            contexts=op.target.contexts,
            match_template=op.match.to_payload(),
            set_template=op.set_.to_payload() if op.set_ is not None else None,
            clear_fields=op.clear,
            require_match=op.require_match,
        )
        > 0
    )


@apply_op.register
def _apply_fmt_stable(op: FmtStableOp, document: CommentedMap) -> bool:
    del op
    del document
    return False


def apply_ops_batch(document: CommentedMap, ops: list[Operation]) -> bool:
    """Apply a validated operation list in order."""

    changed = False
    for op in ops:
        changed = apply_op(op, document) or changed
    return changed
