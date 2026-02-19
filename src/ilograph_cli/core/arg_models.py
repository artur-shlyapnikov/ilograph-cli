"""Pydantic models for CLI argument validation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ilograph_cli.core.normalize import (
    normalize_optional_str,
    normalize_required_str,
    validate_resource_id,
)


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
