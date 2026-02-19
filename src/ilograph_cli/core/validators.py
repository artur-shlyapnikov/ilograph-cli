"""Document validation for `check` command."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.constants import RESTRICTED_RESOURCE_ID_CHARS
from ilograph_cli.core.index import (
    build_resource_locations,
    perspective_identifier,
)
from ilograph_cli.core.reference_fields import iter_reference_fields
from ilograph_cli.core.references import parse_reference_components

ValidationMode = Literal["strict", "ilograph-native"]


@dataclass(slots=True)
class ValidationIssue:
    """Single validation issue."""

    code: str
    path: str
    message: str


class CheckResult:
    """Validation result payload."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues

    @property
    def ok(self) -> bool:
        return not self.issues


def validate_document(
    document: CommentedMap,
    *,
    mode: ValidationMode = "ilograph-native",
) -> CheckResult:
    """Run consistency checks required by CLI."""

    issues: list[ValidationIssue] = []

    issues.extend(_check_duplicate_resource_ids(document))
    issues.extend(_check_duplicate_perspective_ids(document))
    issues.extend(_check_restricted_chars(document))
    issues.extend(_check_broken_references(document, mode=mode))
    return CheckResult(issues)


def _check_duplicate_resource_ids(document: CommentedMap) -> list[ValidationIssue]:
    explicit_ids: list[tuple[str, str]] = []
    for location in build_resource_locations(document):
        raw_id = location.node.get("id")
        if not isinstance(raw_id, str):
            continue
        resource_id = raw_id.strip()
        if not resource_id:
            continue
        explicit_ids.append((resource_id, location.path))

    counter = Counter(item[0] for item in explicit_ids)
    issues: list[ValidationIssue] = []
    for identifier, path in explicit_ids:
        if counter[identifier] <= 1:
            continue
        issues.append(
            ValidationIssue(
                code="duplicate-resource-id",
                path=path,
                message=f"duplicate resource id: {identifier} (ids must be unique)",
            )
        )
    return issues


def _check_duplicate_perspective_ids(document: CommentedMap) -> list[ValidationIssue]:
    perspectives = document.get("perspectives")
    if not isinstance(perspectives, CommentedSeq):
        return []

    explicit_ids: list[tuple[str, int]] = []
    for index, perspective in enumerate(perspectives):
        if not isinstance(perspective, CommentedMap):
            continue
        raw_id = perspective.get("id")
        if not isinstance(raw_id, str):
            continue
        perspective_id = raw_id.strip()
        if not perspective_id:
            continue
        explicit_ids.append((perspective_id, index))

    counter = Counter(item[0] for item in explicit_ids)
    issues: list[ValidationIssue] = []
    for identifier, index in explicit_ids:
        if counter[identifier] <= 1:
            continue
        issues.append(
            ValidationIssue(
                code="duplicate-perspective-id",
                path=f"perspectives[{index}]",
                message=f"duplicate perspective id: {identifier} (ids must be unique)",
            )
        )
    return issues


def _check_restricted_chars(document: CommentedMap) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for location in build_resource_locations(document):
        raw_id = location.node.get("id")
        if isinstance(raw_id, str):
            bad = _first_restricted_char(raw_id)
            if bad is not None:
                issues.append(
                    ValidationIssue(
                        code="restricted-resource-id-char",
                        path=f"{location.path}.id",
                        message=(
                            f"resource id contains restricted char '{bad}' "
                            "(use letters, digits, ., -, _)"
                        ),
                    )
                )

        raw_name = location.node.get("name")
        if isinstance(raw_name, str) and "id" not in location.node:
            bad = _first_restricted_char(raw_name)
            if bad is not None:
                issues.append(
                    ValidationIssue(
                        code="name-needs-id",
                        path=f"{location.path}.name",
                        message=(
                            "resource name has restricted char and requires explicit id "
                            f"('{bad}'; add a clean `id` field)"
                        ),
                    )
                )

    perspectives = document.get("perspectives")
    if isinstance(perspectives, CommentedSeq):
        for perspective_index, perspective in enumerate(perspectives):
            if not isinstance(perspective, CommentedMap):
                continue
            aliases = perspective.get("aliases")
            if not isinstance(aliases, CommentedSeq):
                continue
            for alias_index, alias in enumerate(aliases):
                if not isinstance(alias, CommentedMap):
                    continue
                alias_value = alias.get("alias")
                if not isinstance(alias_value, str):
                    continue
                bad = _first_restricted_char(alias_value)
                if bad is None:
                    continue
                issues.append(
                    ValidationIssue(
                        code="restricted-alias-char",
                        path=f"perspectives[{perspective_index}].aliases[{alias_index}].alias",
                        message=(
                            f"alias contains restricted char '{bad}' "
                            "(use letters, digits, ., -, _)"
                        ),
                    )
                )
    return issues


def _first_restricted_char(value: str) -> str | None:
    for char in value:
        if char in RESTRICTED_RESOURCE_ID_CHARS:
            return char
    return None


def _check_broken_references(
    document: CommentedMap,
    *,
    mode: ValidationMode,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    perspective_aliases = _build_perspective_aliases(document)
    import_namespaces = _build_import_namespaces(document)
    known_identifiers = _collect_known_identifiers(document)
    emitted: set[tuple[str, str]] = set()

    # `instanceOf` frequently points to imported type paths and cannot be checked
    # as regular resource references without import/type resolution.
    for field in iter_reference_fields(document, include_instance_of=False):
        aliases = perspective_aliases.get(field.perspective, set())
        for component in parse_reference_components(field.value):
            token = component.token
            if component.special or component.wildcard:
                continue
            if token in known_identifiers or token in aliases:
                continue
            if component.namespaced:
                namespace = token.split("::", 1)[0]
                if namespace in import_namespaces:
                    continue
                if mode == "ilograph-native":
                    continue
            if (field.path, token) in emitted:
                continue
            emitted.add((field.path, token))
            issues.append(
                ValidationIssue(
                    code="broken-reference",
                    path=field.path,
                    message=(
                        f"unknown reference '{token}' "
                        "(not found in resources, aliases, or imports)"
                    ),
                )
            )
    return issues


def _collect_known_identifiers(document: CommentedMap) -> set[str]:
    known: set[str] = set()
    for location in build_resource_locations(document):
        resource_id = location.node.get("id")
        if isinstance(resource_id, str) and resource_id.strip():
            known.add(resource_id.strip())
        resource_name = location.node.get("name")
        if isinstance(resource_name, str) and resource_name.strip():
            known.add(resource_name.strip())

    perspectives = document.get("perspectives")
    if isinstance(perspectives, CommentedSeq):
        for perspective in perspectives:
            if not isinstance(perspective, CommentedMap):
                continue
            perspective_id = perspective_identifier(perspective)
            if perspective_id is not None:
                known.add(perspective_id)
    return known


def _build_perspective_aliases(document: CommentedMap) -> dict[str | None, set[str]]:
    result: dict[str | None, set[str]] = {}
    perspectives = document.get("perspectives")
    if not isinstance(perspectives, CommentedSeq):
        return result

    for perspective in perspectives:
        if not isinstance(perspective, CommentedMap):
            continue
        perspective_id = perspective_identifier(perspective)
        aliases_set: set[str] = set()
        aliases = perspective.get("aliases")
        if isinstance(aliases, CommentedSeq):
            for alias in aliases:
                if not isinstance(alias, CommentedMap):
                    continue
                alias_name = alias.get("alias")
                if isinstance(alias_name, str):
                    aliases_set.add(alias_name)
        result[perspective_id] = aliases_set
    return result


def _build_import_namespaces(document: CommentedMap) -> set[str]:
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
