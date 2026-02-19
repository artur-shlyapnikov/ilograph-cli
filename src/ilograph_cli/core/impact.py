"""Impact analysis: where resource identifier is referenced."""

from __future__ import annotations

from dataclasses import dataclass

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.index import build_resource_locations, perspective_identifier
from ilograph_cli.core.reference_fields import ReferenceField, iter_reference_fields
from ilograph_cli.core.references import contains_identifier


@dataclass(slots=True)
class ImpactHit:
    """Single impact hit."""

    perspective: str | None
    section: str
    path: str
    field: str
    value: str


def impact_for_resource(
    document: CommentedMap,
    resource_id: str,
) -> list[ImpactHit]:
    """Find all references and ownership spots for resource."""

    hits: list[ImpactHit] = []

    for location in build_resource_locations(document):
        if location.identifier != resource_id:
            continue
        perspective = None
        hits.append(
            ImpactHit(
                perspective=perspective,
                section="resource",
                path=location.path,
                field="id/name",
                value=location.identifier,
            )
        )

    for field in iter_reference_fields(document):
        if not _field_matches(field, resource_id):
            continue
        hits.append(
            ImpactHit(
                perspective=field.perspective,
                section=field.section,
                path=field.path,
                field=field.key,
                value=field.value,
            )
        )

    hits.extend(_collect_context_hits(document, resource_id))
    return hits


def _field_matches(field: ReferenceField, resource_id: str) -> bool:
    return contains_identifier(field.value, resource_id)


def _collect_context_hits(
    document: CommentedMap,
    resource_id: str,
) -> list[ImpactHit]:
    hits: list[ImpactHit] = []
    contexts = document.get("contexts")
    if not isinstance(contexts, CommentedSeq):
        return hits

    for context_index, context in enumerate(contexts):
        if not isinstance(context, CommentedMap):
            continue
        context_id = context.get("id") or context.get("name")
        if not isinstance(context_id, str):
            context_id = f"context[{context_index}]"
        for key, value in context.items():
            if not isinstance(value, str):
                continue
            if not contains_identifier(value, resource_id):
                continue
            hits.append(
                ImpactHit(
                    perspective=None,
                    section=f"contexts:{context_id}",
                    path=f"contexts[{context_index}].{key}",
                    field=key,
                    value=value,
                )
            )

    perspectives = document.get("perspectives")
    if isinstance(perspectives, CommentedSeq):
        for perspective_index, perspective in enumerate(perspectives):
            if not isinstance(perspective, CommentedMap):
                continue
            perspective_id = perspective_identifier(perspective)
            if perspective_id != resource_id:
                continue
            hits.append(
                ImpactHit(
                    perspective=perspective_id,
                    section="perspective",
                    path=f"perspectives[{perspective_index}]",
                    field="id/name",
                    value=perspective_id,
                )
            )

    return hits
