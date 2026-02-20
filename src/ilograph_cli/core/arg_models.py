"""Pydantic models for CLI argument validation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ilograph_cli.core.normalize import (
    normalize_optional_str,
    normalize_required_str,
    validate_resource_id,
)


def _normalize_optional_index(value: int | None, *, field_name: str = "index") -> int | None:
    if value is None:
        return None
    if value < 1:
        raise ValueError(f"{field_name.replace('_', '-')} must be >= 1")
    return value


def _normalize_required_index(value: int, *, field_name: str = "index") -> int:
    if value < 1:
        raise ValueError(f"{field_name.replace('_', '-')} must be >= 1")
    return value


class RenameResourceArgs(BaseModel):
    """Args for rename resource."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str

    @model_validator(mode="after")
    def _validate(self) -> RenameResourceArgs:
        self.id = normalize_required_str(self.id, field_name="id")
        self.name = normalize_required_str(self.name, field_name="name")
        return self


class ResourceCreateArgs(BaseModel):
    """Args for resource create."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    parent: str
    subtitle: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> ResourceCreateArgs:
        self.id = validate_resource_id(self.id, field_name="id")
        self.name = normalize_required_str(self.name, field_name="name")
        self.parent = normalize_required_str(self.parent, field_name="parent")
        self.subtitle = normalize_optional_str(
            self.subtitle,
            field_name="subtitle",
            empty_is_none=True,
        )
        return self


class ResourceDeleteArgs(BaseModel):
    """Args for resource delete."""

    model_config = ConfigDict(extra="forbid")

    id: str
    delete_subtree: bool = False

    @model_validator(mode="after")
    def _validate(self) -> ResourceDeleteArgs:
        self.id = normalize_required_str(self.id, field_name="id")
        return self


class ResourceCloneArgs(BaseModel):
    """Args for resource clone."""

    model_config = ConfigDict(extra="forbid")

    id: str
    new_id: str
    new_parent: str | None = None
    new_name: str | None = None
    with_children: bool = False

    @model_validator(mode="after")
    def _validate(self) -> ResourceCloneArgs:
        self.id = normalize_required_str(self.id, field_name="id")
        self.new_id = validate_resource_id(self.new_id, field_name="new_id")
        self.new_parent = normalize_optional_str(
            self.new_parent,
            field_name="new_parent",
            empty_is_none=True,
        )
        self.new_name = normalize_optional_str(
            self.new_name,
            field_name="new_name",
            empty_is_none=True,
        )
        if self.id == self.new_id:
            raise ValueError("id/new-id are identical")
        return self


class RenameResourceIdArgs(BaseModel):
    """Args for rename resource-id."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: str = Field(alias="from")
    to: str

    @model_validator(mode="after")
    def _validate(self) -> RenameResourceIdArgs:
        self.from_ = normalize_required_str(self.from_, field_name="from")
        self.to = validate_resource_id(self.to, field_name="to")
        if self.from_ == self.to:
            raise ValueError("--from and --to must be different")
        return self


class MoveResourceArgs(BaseModel):
    """Args for move resource."""

    model_config = ConfigDict(extra="forbid")

    id: str
    new_parent: str
    inherit_style_from_parent: bool = False

    @model_validator(mode="after")
    def _validate(self) -> MoveResourceArgs:
        self.id = normalize_required_str(self.id, field_name="id")
        self.new_parent = normalize_required_str(self.new_parent, field_name="new_parent")
        return self


class GroupCreateArgs(BaseModel):
    """Args for group create."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    parent: str
    subtitle: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> GroupCreateArgs:
        self.id = validate_resource_id(self.id, field_name="id")
        self.name = normalize_required_str(self.name, field_name="name")
        self.parent = normalize_required_str(self.parent, field_name="parent")
        self.subtitle = normalize_optional_str(
            self.subtitle,
            field_name="subtitle",
            empty_is_none=True,
        )
        return self


class MoveManyArgs(BaseModel):
    """Args for move-many."""

    model_config = ConfigDict(extra="forbid")

    ids: list[str]
    new_parent: str

    @model_validator(mode="after")
    def _validate(self) -> MoveManyArgs:
        clean_ids: list[str] = []
        for item in self.ids:
            clean_ids.append(normalize_required_str(item, field_name="ids"))
        if not clean_ids:
            raise ValueError("--ids must include at least one resource id")
        self.ids = clean_ids
        self.new_parent = normalize_required_str(self.new_parent, field_name="new_parent")
        return self


class PerspectiveScopeArgs(BaseModel):
    """Args for commands scoped by perspective."""

    model_config = ConfigDict(extra="forbid")

    perspective: str

    @model_validator(mode="after")
    def _validate(self) -> PerspectiveScopeArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        return self


class AliasAddArgs(BaseModel):
    """Args for alias add."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    perspective: str
    alias: str
    alias_for: str = Field(alias="for")
    index: int | None = None

    @model_validator(mode="after")
    def _validate(self) -> AliasAddArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.alias = normalize_required_str(self.alias, field_name="alias")
        self.alias_for = normalize_required_str(self.alias_for, field_name="for")
        self.index = _normalize_optional_index(self.index)
        return self


class AliasEditArgs(BaseModel):
    """Args for alias edit."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    alias: str
    new_alias: str | None = None
    new_for: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> AliasEditArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.alias = normalize_required_str(self.alias, field_name="alias")
        self.new_alias = normalize_optional_str(
            self.new_alias,
            field_name="new_alias",
            empty_is_none=True,
        )
        self.new_for = normalize_optional_str(
            self.new_for,
            field_name="new_for",
            empty_is_none=True,
        )
        return self


class AliasRemoveArgs(BaseModel):
    """Args for alias remove."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    alias: str

    @model_validator(mode="after")
    def _validate(self) -> AliasRemoveArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.alias = normalize_required_str(self.alias, field_name="alias")
        return self


class PerspectiveCreateArgs(BaseModel):
    """Args for perspective create."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str | None = None
    extends: str | None = None
    orientation: str | None = None
    index: int | None = None

    @model_validator(mode="after")
    def _validate(self) -> PerspectiveCreateArgs:
        self.id = normalize_required_str(self.id, field_name="id")
        self.name = normalize_optional_str(self.name, field_name="name", empty_is_none=True)
        if self.name is None:
            self.name = self.id
        self.extends = normalize_optional_str(
            self.extends,
            field_name="extends",
            empty_is_none=True,
        )
        self.orientation = normalize_optional_str(
            self.orientation,
            field_name="orientation",
            empty_is_none=True,
        )
        self.index = _normalize_optional_index(self.index)
        return self


class PerspectiveRenameArgs(BaseModel):
    """Args for perspective rename."""

    model_config = ConfigDict(extra="forbid")

    id: str
    new_id: str | None = None
    new_name: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> PerspectiveRenameArgs:
        self.id = normalize_required_str(self.id, field_name="id")
        self.new_id = normalize_optional_str(self.new_id, field_name="new_id", empty_is_none=True)
        self.new_name = normalize_optional_str(
            self.new_name,
            field_name="new_name",
            empty_is_none=True,
        )
        return self


class PerspectiveDeleteArgs(BaseModel):
    """Args for perspective delete."""

    model_config = ConfigDict(extra="forbid")

    id: str
    force: bool = False

    @model_validator(mode="after")
    def _validate(self) -> PerspectiveDeleteArgs:
        self.id = normalize_required_str(self.id, field_name="id")
        return self


class PerspectiveReorderArgs(BaseModel):
    """Args for perspective reorder."""

    model_config = ConfigDict(extra="forbid")

    id: str
    index: int

    @model_validator(mode="after")
    def _validate(self) -> PerspectiveReorderArgs:
        self.id = normalize_required_str(self.id, field_name="id")
        self.index = _normalize_required_index(self.index)
        return self


class PerspectiveCopyArgs(BaseModel):
    """Args for perspective copy."""

    model_config = ConfigDict(extra="forbid")

    id: str
    new_id: str
    new_name: str | None = None
    index: int | None = None

    @model_validator(mode="after")
    def _validate(self) -> PerspectiveCopyArgs:
        self.id = normalize_required_str(self.id, field_name="id")
        self.new_id = normalize_required_str(self.new_id, field_name="new_id")
        self.new_name = normalize_optional_str(
            self.new_name,
            field_name="new_name",
            empty_is_none=True,
        )
        self.index = _normalize_optional_index(self.index)
        return self


class SequenceAddArgs(BaseModel):
    """Args for sequence add."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    to: str | None = None
    to_and_back: str | None = None
    to_async: str | None = None
    restart_at: str | None = None
    label: str | None = None
    description: str | None = None
    bidirectional: bool | None = None
    color: str | None = None
    index: int | None = None
    start: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> SequenceAddArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.to = normalize_optional_str(self.to, field_name="to", empty_is_none=True)
        self.to_and_back = normalize_optional_str(
            self.to_and_back,
            field_name="to_and_back",
            empty_is_none=True,
        )
        self.to_async = normalize_optional_str(
            self.to_async,
            field_name="to_async",
            empty_is_none=True,
        )
        self.restart_at = normalize_optional_str(
            self.restart_at,
            field_name="restart_at",
            empty_is_none=True,
        )
        self.label = normalize_optional_str(self.label, field_name="label", empty_is_none=True)
        self.description = normalize_optional_str(
            self.description,
            field_name="description",
            empty_is_none=True,
        )
        self.color = normalize_optional_str(self.color, field_name="color", empty_is_none=True)
        self.start = normalize_optional_str(self.start, field_name="start", empty_is_none=True)
        self.index = _normalize_optional_index(self.index)
        return self


class SequenceEditArgs(BaseModel):
    """Args for sequence edit."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    index: int
    to: str | None = None
    to_and_back: str | None = None
    to_async: str | None = None
    restart_at: str | None = None
    label: str | None = None
    description: str | None = None
    bidirectional: bool | None = None
    color: str | None = None
    clear_label: bool = False
    clear_description: bool = False
    clear_color: bool = False

    @model_validator(mode="after")
    def _validate(self) -> SequenceEditArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.index = _normalize_required_index(self.index)
        self.to = normalize_optional_str(self.to, field_name="to", empty_is_none=True)
        self.to_and_back = normalize_optional_str(
            self.to_and_back,
            field_name="to_and_back",
            empty_is_none=True,
        )
        self.to_async = normalize_optional_str(
            self.to_async,
            field_name="to_async",
            empty_is_none=True,
        )
        self.restart_at = normalize_optional_str(
            self.restart_at,
            field_name="restart_at",
            empty_is_none=True,
        )
        self.label = normalize_optional_str(self.label, field_name="label", empty_is_none=True)
        self.description = normalize_optional_str(
            self.description,
            field_name="description",
            empty_is_none=True,
        )
        self.color = normalize_optional_str(self.color, field_name="color", empty_is_none=True)
        return self


class SequenceRemoveArgs(BaseModel):
    """Args for sequence remove."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    index: int

    @model_validator(mode="after")
    def _validate(self) -> SequenceRemoveArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.index = _normalize_required_index(self.index)
        return self


class WalkthroughAddArgs(BaseModel):
    """Args for walkthrough add."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    text: str | None = None
    select: str | None = None
    expand: str | None = None
    highlight: str | None = None
    hide: str | None = None
    detail: float | None = None
    index: int | None = None

    @model_validator(mode="after")
    def _validate(self) -> WalkthroughAddArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.text = normalize_optional_str(self.text, field_name="text", empty_is_none=True)
        self.select = normalize_optional_str(self.select, field_name="select", empty_is_none=True)
        self.expand = normalize_optional_str(self.expand, field_name="expand", empty_is_none=True)
        self.highlight = normalize_optional_str(
            self.highlight,
            field_name="highlight",
            empty_is_none=True,
        )
        self.hide = normalize_optional_str(self.hide, field_name="hide", empty_is_none=True)
        self.index = _normalize_optional_index(self.index)
        return self


class WalkthroughEditArgs(BaseModel):
    """Args for walkthrough edit."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    index: int
    text: str | None = None
    select: str | None = None
    expand: str | None = None
    highlight: str | None = None
    hide: str | None = None
    detail: float | None = None
    clear_text: bool = False
    clear_select: bool = False
    clear_expand: bool = False
    clear_highlight: bool = False
    clear_hide: bool = False
    clear_detail: bool = False

    @model_validator(mode="after")
    def _validate(self) -> WalkthroughEditArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.index = _normalize_required_index(self.index)
        self.text = normalize_optional_str(self.text, field_name="text", empty_is_none=True)
        self.select = normalize_optional_str(self.select, field_name="select", empty_is_none=True)
        self.expand = normalize_optional_str(self.expand, field_name="expand", empty_is_none=True)
        self.highlight = normalize_optional_str(
            self.highlight,
            field_name="highlight",
            empty_is_none=True,
        )
        self.hide = normalize_optional_str(self.hide, field_name="hide", empty_is_none=True)
        return self


class WalkthroughRemoveArgs(BaseModel):
    """Args for walkthrough remove."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    index: int

    @model_validator(mode="after")
    def _validate(self) -> WalkthroughRemoveArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.index = _normalize_required_index(self.index)
        return self


class ContextCreateArgs(BaseModel):
    """Args for context create."""

    model_config = ConfigDict(extra="forbid")

    name: str
    extends: str | None = None
    hidden: bool | None = None
    index: int | None = None

    @model_validator(mode="after")
    def _validate(self) -> ContextCreateArgs:
        self.name = normalize_required_str(self.name, field_name="name")
        self.extends = normalize_optional_str(
            self.extends,
            field_name="extends",
            empty_is_none=True,
        )
        self.index = _normalize_optional_index(self.index)
        return self


class ContextRenameArgs(BaseModel):
    """Args for context rename."""

    model_config = ConfigDict(extra="forbid")

    name: str
    new_name: str

    @model_validator(mode="after")
    def _validate(self) -> ContextRenameArgs:
        self.name = normalize_required_str(self.name, field_name="name")
        self.new_name = normalize_required_str(self.new_name, field_name="new_name")
        return self


class ContextDeleteArgs(BaseModel):
    """Args for context delete."""

    model_config = ConfigDict(extra="forbid")

    name: str
    force: bool = False

    @model_validator(mode="after")
    def _validate(self) -> ContextDeleteArgs:
        self.name = normalize_required_str(self.name, field_name="name")
        return self


class ContextReorderArgs(BaseModel):
    """Args for context reorder."""

    model_config = ConfigDict(extra="forbid")

    name: str
    index: int

    @model_validator(mode="after")
    def _validate(self) -> ContextReorderArgs:
        self.name = normalize_required_str(self.name, field_name="name")
        self.index = _normalize_required_index(self.index)
        return self


class ContextCopyArgs(BaseModel):
    """Args for context copy."""

    model_config = ConfigDict(extra="forbid")

    name: str
    new_name: str
    index: int | None = None

    @model_validator(mode="after")
    def _validate(self) -> ContextCopyArgs:
        self.name = normalize_required_str(self.name, field_name="name")
        self.new_name = normalize_required_str(self.new_name, field_name="new_name")
        self.index = _normalize_optional_index(self.index)
        return self


class OverrideAddArgs(BaseModel):
    """Args for override add."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    resource_id: str
    parent_id: str | None = None
    scale: float | None = None
    index: int | None = None

    @model_validator(mode="after")
    def _validate(self) -> OverrideAddArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.resource_id = normalize_required_str(self.resource_id, field_name="resource_id")
        self.parent_id = normalize_optional_str(
            self.parent_id,
            field_name="parent_id",
            empty_is_none=True,
        )
        self.index = _normalize_optional_index(self.index)
        return self


class OverrideEditArgs(BaseModel):
    """Args for override edit."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    resource_id: str
    new_resource_id: str | None = None
    parent_id: str | None = None
    scale: float | None = None
    clear_parent_id: bool = False
    clear_scale: bool = False

    @model_validator(mode="after")
    def _validate(self) -> OverrideEditArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.resource_id = normalize_required_str(self.resource_id, field_name="resource_id")
        self.new_resource_id = normalize_optional_str(
            self.new_resource_id,
            field_name="new_resource_id",
            empty_is_none=True,
        )
        self.parent_id = normalize_optional_str(
            self.parent_id,
            field_name="parent_id",
            empty_is_none=True,
        )
        return self


class OverrideRemoveArgs(BaseModel):
    """Args for override remove."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    resource_id: str

    @model_validator(mode="after")
    def _validate(self) -> OverrideRemoveArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.resource_id = normalize_required_str(self.resource_id, field_name="resource_id")
        return self


class RelationAddArgs(BaseModel):
    """Args for relation add."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    perspective: str
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    via: str | None = None
    label: str | None = None
    description: str | None = None
    arrow_direction: Literal["forward", "backward", "bidirectional"] | None = None
    color: str | None = None
    secondary: bool | None = None

    @model_validator(mode="after")
    def _validate(self) -> RelationAddArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        self.from_ = normalize_optional_str(self.from_, field_name="from")
        self.to = normalize_optional_str(self.to, field_name="to")
        self.via = normalize_optional_str(self.via, field_name="via")
        if self.from_ is None and self.to is None:
            raise ValueError("relation must define from or to (set --from and/or --to)")
        return self


class RelationRemoveArgs(BaseModel):
    """Args for relation remove."""

    model_config = ConfigDict(extra="forbid")

    perspective: str
    index: int

    @model_validator(mode="after")
    def _validate(self) -> RelationRemoveArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        if self.index < 1:
            raise ValueError("--index must be >= 1 (1-based relation index)")
        return self


class RelationEditArgs(BaseModel):
    """Args for relation edit."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    perspective: str
    index: int
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    via: str | None = None
    label: str | None = None
    description: str | None = None
    arrow_direction: Literal["forward", "backward", "bidirectional"] | None = None
    color: str | None = None
    secondary: bool | None = None
    clear_from: bool = False
    clear_to: bool = False
    clear_via: bool = False
    clear_label: bool = False
    clear_description: bool = False

    @model_validator(mode="after")
    def _validate(self) -> RelationEditArgs:
        self.perspective = normalize_required_str(self.perspective, field_name="perspective")
        if self.index < 1:
            raise ValueError("--index must be >= 1 (1-based relation index)")
        self.from_ = normalize_optional_str(self.from_, field_name="from")
        self.to = normalize_optional_str(self.to, field_name="to")
        self.via = normalize_optional_str(self.via, field_name="via")
        return self
