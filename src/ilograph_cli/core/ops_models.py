"""Pydantic schema for ops.yaml."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator
from pydantic import ValidationError as PydanticValidationError

from ilograph_cli.core.arg_models import (
    GroupCreateArgs,
    MoveManyArgs,
    MoveResourceArgs,
    RelationAddArgs,
    RelationEditArgs,
    RelationRemoveArgs,
    RenameResourceArgs,
    RenameResourceIdArgs,
    ResourceCloneArgs,
    ResourceCreateArgs,
    ResourceDeleteArgs,
)
from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.normalize import normalize_optional_str, normalize_unique_list
from ilograph_cli.core.relation_types import (
    RelationArrowDirection,
    RelationClearField,
    RelationTemplate,
)
from ilograph_cli.core.yaml_types import YamlNode


class RelationTarget(BaseModel):
    """Target selector for bulk relation operations."""

    model_config = ConfigDict(extra="forbid")

    perspectives: list[str] | Literal["*"] = "*"
    contexts: list[str] | None = None

    @model_validator(mode="after")
    def _validate(self) -> RelationTarget:
        if isinstance(self.perspectives, list):
            self.perspectives = normalize_unique_list(
                self.perspectives,
                field_name="target.perspectives",
            )
        if self.contexts is not None:
            self.contexts = normalize_unique_list(
                self.contexts,
                field_name="target.contexts",
            )
        return self


class RelationPayloadBase(BaseModel):
    """Shared relation payload fields."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    via: str | None = None
    label: str | None = None
    description: str | None = None
    arrow_direction: RelationArrowDirection | None = Field(
        default=None,
        alias="arrowDirection",
        validation_alias=AliasChoices("arrowDirection", "arrow_direction"),
    )
    color: str | None = None
    secondary: bool | None = None

    @model_validator(mode="after")
    def _normalize(self) -> RelationPayloadBase:
        self.from_ = normalize_optional_str(self.from_, field_name="from")
        self.to = normalize_optional_str(self.to, field_name="to")
        self.via = normalize_optional_str(self.via, field_name="via")
        self.label = normalize_optional_str(self.label, field_name="label")
        self.description = normalize_optional_str(
            self.description,
            field_name="description",
        )
        self.color = normalize_optional_str(self.color, field_name="color")
        return self

    def to_payload(self) -> RelationTemplate:
        """Convert to relation dictionary using spec keys."""

        payload: RelationTemplate = {}
        if self.from_ is not None:
            payload["from"] = self.from_
        if self.to is not None:
            payload["to"] = self.to
        if self.via is not None:
            payload["via"] = self.via
        if self.label is not None:
            payload["label"] = self.label
        if self.description is not None:
            payload["description"] = self.description
        if self.arrow_direction is not None:
            payload["arrowDirection"] = self.arrow_direction
        if self.color is not None:
            payload["color"] = self.color
        if self.secondary is not None:
            payload["secondary"] = self.secondary
        return payload


class RelationMatchSpec(RelationPayloadBase):
    """Matcher for relation rows."""

    @model_validator(mode="after")
    def _validate_has_fields(self) -> RelationMatchSpec:
        if not self.to_payload():
            raise ValueError("match must define at least one field to compare")
        return self


class RelationSetSpec(RelationPayloadBase):
    """Set payload for relation edit-match."""

    @model_validator(mode="after")
    def _validate_has_fields(self) -> RelationSetSpec:
        if not self.to_payload():
            raise ValueError("set must define at least one field to update")
        return self


class RenameResourceOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["rename.resource"]
    id: str
    name: str

    @model_validator(mode="after")
    def _validate(self) -> RenameResourceOp:
        RenameResourceArgs(id=self.id, name=self.name)
        return self


class RenameResourceIdOp(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    op: Literal["rename.resource-id"]
    from_: str = Field(alias="from")
    to: str

    @model_validator(mode="after")
    def _validate(self) -> RenameResourceIdOp:
        RenameResourceIdArgs.model_validate({"from": self.from_, "to": self.to})
        return self


class MoveResourceOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["move.resource"]
    id: str
    new_parent: str = Field(
        alias="newParent",
        validation_alias=AliasChoices("newParent", "new_parent"),
    )
    inherit_style_from_parent: bool = Field(
        default=False,
        alias="inheritStyleFromParent",
        validation_alias=AliasChoices(
            "inheritStyleFromParent",
            "inherit_style_from_parent",
        ),
    )

    @model_validator(mode="after")
    def _validate(self) -> MoveResourceOp:
        MoveResourceArgs(
            id=self.id,
            new_parent=self.new_parent,
            inherit_style_from_parent=self.inherit_style_from_parent,
        )
        return self


class ResourceCreateOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["resource.create"]
    id: str
    name: str
    parent: str = "none"
    subtitle: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> ResourceCreateOp:
        ResourceCreateArgs(
            id=self.id,
            name=self.name,
            parent=self.parent,
            subtitle=self.subtitle,
        )
        return self


class ResourceDeleteOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["resource.delete"]
    id: str
    delete_subtree: bool = Field(
        default=False,
        alias="deleteSubtree",
        validation_alias=AliasChoices("deleteSubtree", "delete_subtree"),
    )

    @model_validator(mode="after")
    def _validate(self) -> ResourceDeleteOp:
        ResourceDeleteArgs(
            id=self.id,
            delete_subtree=self.delete_subtree,
        )
        return self


class ResourceCloneOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["resource.clone"]
    id: str
    new_id: str = Field(
        alias="newId",
        validation_alias=AliasChoices("newId", "new_id"),
    )
    new_parent: str | None = Field(
        default=None,
        alias="newParent",
        validation_alias=AliasChoices("newParent", "new_parent"),
    )
    new_name: str | None = Field(
        default=None,
        alias="newName",
        validation_alias=AliasChoices("newName", "new_name"),
    )
    with_children: bool = Field(
        default=False,
        alias="withChildren",
        validation_alias=AliasChoices("withChildren", "with_children"),
    )

    @model_validator(mode="after")
    def _validate(self) -> ResourceCloneOp:
        ResourceCloneArgs(
            id=self.id,
            new_id=self.new_id,
            new_parent=self.new_parent,
            new_name=self.new_name,
            with_children=self.with_children,
        )
        return self


class GroupCreateOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["group.create"]
    id: str
    name: str
    parent: str
    subtitle: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> GroupCreateOp:
        GroupCreateArgs(id=self.id, name=self.name, parent=self.parent, subtitle=self.subtitle)
        return self


class MoveManyOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["group.move-many"]
    ids: list[str]
    new_parent: str = Field(
        alias="newParent",
        validation_alias=AliasChoices("newParent", "new_parent"),
    )

    @model_validator(mode="after")
    def _validate(self) -> MoveManyOp:
        MoveManyArgs(ids=self.ids, new_parent=self.new_parent)
        return self


class RelationAddOp(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    op: Literal["relation.add"]
    perspective: str
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    via: str | None = None
    label: str | None = None
    description: str | None = None
    arrow_direction: RelationArrowDirection | None = Field(
        default=None,
        alias="arrowDirection",
        validation_alias=AliasChoices("arrowDirection", "arrow_direction"),
    )
    color: str | None = None
    secondary: bool | None = None

    @model_validator(mode="after")
    def _validate(self) -> RelationAddOp:
        RelationAddArgs.model_validate(
            {
                "perspective": self.perspective,
                "from": self.from_,
                "to": self.to,
                "via": self.via,
                "label": self.label,
                "description": self.description,
                "arrow_direction": self.arrow_direction,
                "color": self.color,
                "secondary": self.secondary,
            }
        )
        return self


class RelationAddManyOp(RelationPayloadBase):
    """Bulk add relation using target perspectives/contexts."""

    op: Literal["relation.add-many"]
    target: RelationTarget

    @model_validator(mode="after")
    def _validate_has_from_or_to(self) -> RelationAddManyOp:
        if self.from_ is None and self.to is None:
            raise ValueError("relation must define from or to (set from and/or to)")
        return self


class RelationRemoveOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["relation.remove"]
    perspective: str
    index: int

    @model_validator(mode="after")
    def _validate(self) -> RelationRemoveOp:
        RelationRemoveArgs(perspective=self.perspective, index=self.index)
        return self


class RelationRemoveMatchOp(BaseModel):
    """Bulk remove relations by matcher."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["relation.remove-match"]
    target: RelationTarget
    match: RelationMatchSpec
    require_match: bool = Field(
        default=True,
        alias="requireMatch",
        validation_alias=AliasChoices("requireMatch", "require_match"),
    )


class RelationEditOp(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    op: Literal["relation.edit"]
    perspective: str
    index: int
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    via: str | None = None
    label: str | None = None
    description: str | None = None
    arrow_direction: RelationArrowDirection | None = Field(
        default=None,
        alias="arrowDirection",
        validation_alias=AliasChoices("arrowDirection", "arrow_direction"),
    )
    color: str | None = None
    secondary: bool | None = None
    clear_from: bool = Field(
        default=False,
        alias="clearFrom",
        validation_alias=AliasChoices("clearFrom", "clear_from"),
    )
    clear_to: bool = Field(
        default=False,
        alias="clearTo",
        validation_alias=AliasChoices("clearTo", "clear_to"),
    )
    clear_via: bool = Field(
        default=False,
        alias="clearVia",
        validation_alias=AliasChoices("clearVia", "clear_via"),
    )
    clear_label: bool = Field(
        default=False,
        alias="clearLabel",
        validation_alias=AliasChoices("clearLabel", "clear_label"),
    )
    clear_description: bool = Field(
        default=False,
        alias="clearDescription",
        validation_alias=AliasChoices("clearDescription", "clear_description"),
    )

    @model_validator(mode="after")
    def _validate(self) -> RelationEditOp:
        RelationEditArgs.model_validate(
            {
                "perspective": self.perspective,
                "index": self.index,
                "from": self.from_,
                "to": self.to,
                "via": self.via,
                "label": self.label,
                "description": self.description,
                "arrow_direction": self.arrow_direction,
                "color": self.color,
                "secondary": self.secondary,
                "clear_from": self.clear_from,
                "clear_to": self.clear_to,
                "clear_via": self.clear_via,
                "clear_label": self.clear_label,
                "clear_description": self.clear_description,
            }
        )
        return self


class RelationEditMatchOp(BaseModel):
    """Bulk edit relations by matcher without index."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["relation.edit-match"]
    target: RelationTarget
    match: RelationMatchSpec
    set_: RelationSetSpec | None = Field(default=None, alias="set")
    clear: list[RelationClearField] = Field(default_factory=list)
    require_match: bool = Field(
        default=True,
        alias="requireMatch",
        validation_alias=AliasChoices("requireMatch", "require_match"),
    )

    @model_validator(mode="after")
    def _validate(self) -> RelationEditMatchOp:
        if self.set_ is None and not self.clear:
            raise ValueError(
                "edit-match requires `set` or non-empty `clear` "
                "(provide fields to update or clear)"
            )
        if len(set(self.clear)) != len(self.clear):
            raise ValueError("clear has duplicates (each field can appear once)")
        return self


class FmtStableOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["fmt.stable"]


Operation = Annotated[
    ResourceCreateOp
    | ResourceDeleteOp
    | ResourceCloneOp
    | RenameResourceOp
    | RenameResourceIdOp
    | MoveResourceOp
    | GroupCreateOp
    | MoveManyOp
    | RelationAddOp
    | RelationAddManyOp
    | RelationRemoveOp
    | RelationRemoveMatchOp
    | RelationEditOp
    | RelationEditMatchOp
    | FmtStableOp,
    Field(discriminator="op"),
]


class OpsFile(BaseModel):
    """Root ops.yaml model."""

    model_config = ConfigDict(extra="forbid")

    ops: list[Operation]

    @model_validator(mode="after")
    def _validate(self) -> OpsFile:
        if not self.ops:
            raise ValueError(
                "ops must contain at least one operation "
                "(example op: rename.resource)"
            )
        return self


def parse_ops_payload(payload: YamlNode) -> OpsFile:
    """Validate loaded ops payload."""

    try:
        return OpsFile.model_validate(payload)
    except PydanticValidationError as exc:
        raise ValidationError(_format_ops_validation_error(exc)) from exc


def _format_ops_validation_error(exc: PydanticValidationError) -> str:
    issues = exc.errors()
    if not issues:
        return "invalid ops file: no validation details available"

    preview_limit = 8
    lines = ["invalid ops file:"]
    for issue in issues[:preview_limit]:
        path = _format_error_path(issue.get("loc", ()))
        message = issue.get("msg", "validation error")
        lines.append(f"- {path}: {message}")
    if len(issues) > preview_limit:
        lines.append(f"- ... and {len(issues) - preview_limit} more")
    return "\n".join(lines)


def _format_error_path(loc: object) -> str:
    if not isinstance(loc, tuple):
        return "ops"

    path = ""
    for part in loc:
        if isinstance(part, int):
            path += f"[{part}]"
            continue
        if not isinstance(part, str):
            continue
        if not path:
            path = part
            continue
        path += f".{part}"
    return path or "ops"
