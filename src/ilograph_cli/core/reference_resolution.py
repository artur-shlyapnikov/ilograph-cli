"""Reference-resolution helpers shared by CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.index import build_resource_locations, perspective_identifier
from ilograph_cli.core.references import parse_reference_components, split_reference_list

ResolveStatus = Literal[
    "resolved",
    "special",
    "wildcard",
    "alias",
    "imported-namespace",
    "unresolved-namespace",
    "ambiguous",
    "unresolved",
    "empty",
]


@dataclass(slots=True)
class ResolveRow:
    part: str
    token: str
    status: ResolveStatus
    details: str


def resolve_reference(
    document: CommentedMap,
    *,
    reference: str,
    perspective: str | None,
) -> tuple[str | None, list[ResolveRow]]:
    """Resolve reference expression into per-token status rows."""

    resource_index = _collect_resource_reference_index(document)
    aliases = _resolve_aliases_for_perspective(document, perspective)
    import_namespaces = _collect_import_namespaces(document)

    rows: list[ResolveRow] = []
    parts = split_reference_list(reference)
    if not parts:
        rows.append(ResolveRow(part=reference, token="-", status="empty", details="-"))
        return perspective, rows

    for part in parts:
        components = parse_reference_components(part)
        if not components:
            rows.append(ResolveRow(part=part, token="-", status="empty", details="-"))
            continue

        for component in components:
            token = component.token
            status: ResolveStatus = "resolved"
            details = "-"

            if component.special:
                status = "special"
            elif component.wildcard:
                status = "wildcard"
            elif token in aliases:
                status = "alias"
                details = aliases[token]
            elif component.namespaced:
                namespace = token.split("::", 1)[0]
                if namespace in import_namespaces:
                    status = "imported-namespace"
                else:
                    status = "unresolved-namespace"
            else:
                paths = resource_index.get(token, [])
                if not paths:
                    status = "unresolved"
                elif len(paths) > 1:
                    status = "ambiguous"
                    details = ", ".join(paths)
                else:
                    details = paths[0]

            rows.append(
                ResolveRow(
                    part=part,
                    token=token,
                    status=status,
                    details=details,
                )
            )

    return perspective, rows


def _collect_resource_reference_index(document: CommentedMap) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for location in build_resource_locations(document):
        resource_id = location.node.get("id")
        if isinstance(resource_id, str) and resource_id.strip():
            index.setdefault(resource_id.strip(), []).append(location.path)
        resource_name = location.node.get("name")
        if isinstance(resource_name, str) and resource_name.strip():
            index.setdefault(resource_name.strip(), []).append(location.path)
    return index


def _resolve_aliases_for_perspective(
    document: CommentedMap,
    perspective: str | None,
) -> dict[str, str]:
    if perspective is None:
        return {}

    perspectives = document.get("perspectives")
    if not isinstance(perspectives, CommentedSeq):
        return {}

    for node in perspectives:
        if not isinstance(node, CommentedMap):
            continue
        perspective_id = perspective_identifier(node)
        if perspective_id != perspective:
            continue
        aliases = node.get("aliases")
        if not isinstance(aliases, CommentedSeq):
            return {}

        result: dict[str, str] = {}
        for alias in aliases:
            if not isinstance(alias, CommentedMap):
                continue
            alias_name = alias.get("alias")
            alias_for = alias.get("for")
            if isinstance(alias_name, str) and isinstance(alias_for, str):
                result[alias_name] = alias_for
        return result

    return {}


def _collect_import_namespaces(document: CommentedMap) -> set[str]:
    namespaces: set[str] = set()
    imports = document.get("imports")
    if not isinstance(imports, CommentedSeq):
        return namespaces

    for item in imports:
        if not isinstance(item, CommentedMap):
            continue
        namespace = item.get("namespace")
        if isinstance(namespace, str) and namespace.strip():
            namespaces.add(namespace.strip())
    return namespaces
