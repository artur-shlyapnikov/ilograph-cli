"""Resource/perspective index helpers."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.errors import ValidationError


@dataclass(slots=True)
class ResourceLocation:
    """Resource node location inside tree."""

    identifier: str
    node: CommentedMap
    parent: CommentedMap | None
    container: CommentedSeq
    index: int
    path: str


@dataclass(slots=True)
class PerspectiveLocation:
    """Perspective location."""

    identifier: str
    node: CommentedMap
    index: int


def resource_identifier(resource: CommentedMap) -> str | None:
    """Resource identifier: id or fallback name."""

    resource_id = resource.get("id")
    if isinstance(resource_id, str) and resource_id.strip():
        return resource_id.strip()
    resource_name = resource.get("name")
    if isinstance(resource_name, str) and resource_name.strip():
        return resource_name.strip()
    return None


def perspective_identifier(perspective: CommentedMap) -> str | None:
    """Perspective identifier: id or fallback name."""

    perspective_id = perspective.get("id")
    if isinstance(perspective_id, str) and perspective_id.strip():
        return perspective_id.strip()
    perspective_name = perspective.get("name")
    if isinstance(perspective_name, str) and perspective_name.strip():
        return perspective_name.strip()
    return None


def iter_resources(
    resources: CommentedSeq,
    *,
    parent: CommentedMap | None = None,
    path_prefix: str = "resources",
) -> Iterator[ResourceLocation]:
    """Depth-first resource iterator with structural metadata."""

    for index, raw in enumerate(resources):
        if not isinstance(raw, CommentedMap):
            continue
        identifier = resource_identifier(raw)
        if identifier is None:
            continue
        location = ResourceLocation(
            identifier=identifier,
            node=raw,
            parent=parent,
            container=resources,
            index=index,
            path=f"{path_prefix}[{index}]",
        )
        yield location
        children = raw.get("children")
        if isinstance(children, CommentedSeq):
            child_prefix = f"{location.path}.children"
            yield from iter_resources(children, parent=raw, path_prefix=child_prefix)


def build_resource_locations(document: CommentedMap) -> list[ResourceLocation]:
    """Collect all resource locations."""

    resources = document.get("resources")
    if not isinstance(resources, CommentedSeq):
        return []
    return list(iter_resources(resources))


def build_resource_index(document: CommentedMap) -> dict[str, list[ResourceLocation]]:
    """Map resource identifier to all locations."""

    index: dict[str, list[ResourceLocation]] = {}
    for location in build_resource_locations(document):
        index.setdefault(location.identifier, []).append(location)
    return index


def build_resource_id_index(document: CommentedMap) -> dict[str, list[ResourceLocation]]:
    """Map explicit resource ids to all locations."""

    index: dict[str, list[ResourceLocation]] = {}
    for location in build_resource_locations(document):
        raw_id = location.node.get("id")
        if not isinstance(raw_id, str):
            continue
        resource_id = raw_id.strip()
        if not resource_id:
            continue
        index.setdefault(resource_id, []).append(location)
    return index


def get_single_resource(document: CommentedMap, identifier: str) -> ResourceLocation:
    """Return single resource by identifier or raise."""

    index = build_resource_index(document)
    found = index.get(identifier, [])
    if not found:
        raise ValidationError(
            f"resource not found: {identifier} "
            "(lookup checks id first, then name)"
        )
    if len(found) > 1:
        paths = ", ".join(item.path for item in found)
        raise ValidationError(
            f"resource id not unique: {identifier} ({paths}) "
            "(set explicit unique ids)"
        )
    return found[0]


def get_single_resource_by_id(document: CommentedMap, resource_id: str) -> ResourceLocation:
    """Return single resource by explicit id or raise."""

    index = build_resource_id_index(document)
    found = index.get(resource_id, [])
    if not found:
        raise ValidationError(
            f"resource id not found: {resource_id} "
            "(expected exact match in resources[].id)"
        )
    if len(found) > 1:
        paths = ", ".join(item.path for item in found)
        raise ValidationError(
            f"resource id not unique: {resource_id} ({paths}) "
            "(set explicit unique ids)"
        )
    return found[0]


def ensure_children(resource: CommentedMap) -> CommentedSeq:
    """Ensure `children` list exists and return it."""

    children = resource.get("children")
    if isinstance(children, CommentedSeq):
        return children
    new_children = CommentedSeq()
    resource["children"] = new_children
    return new_children


def build_perspective_locations(document: CommentedMap) -> list[PerspectiveLocation]:
    """Collect perspectives."""

    perspectives = document.get("perspectives")
    if not isinstance(perspectives, CommentedSeq):
        return []
    locations: list[PerspectiveLocation] = []
    for index, raw in enumerate(perspectives):
        if not isinstance(raw, CommentedMap):
            continue
        identifier = perspective_identifier(raw)
        if identifier is None:
            continue
        locations.append(PerspectiveLocation(identifier=identifier, node=raw, index=index))
    return locations


def get_single_perspective(
    document: CommentedMap,
    identifier: str,
) -> PerspectiveLocation:
    """Return unique perspective by id/name."""

    candidates = [
        item
        for item in build_perspective_locations(document)
        if item.identifier == identifier
    ]
    if not candidates:
        raise ValidationError(
            f"perspective not found: {identifier} "
            "(lookup checks id first, then name)"
        )
    if len(candidates) > 1:
        indices = ", ".join(str(item.index) for item in candidates)
        raise ValidationError(
            f"perspective id not unique: {identifier} ({indices}) "
            "(set explicit unique ids)"
        )
    return candidates[0]
