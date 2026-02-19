"""Iterators over reference-bearing fields in document."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.constants import WALKTHROUGH_REFERENCE_KEYS
from ilograph_cli.core.index import perspective_identifier


@dataclass(slots=True)
class ReferenceField:
    """Mutable reference-bearing field."""

    container: CommentedMap
    key: str
    path: str
    perspective: str | None
    section: str

    @property
    def value(self) -> str:
        raw = self.container.get(self.key)
        if isinstance(raw, str):
            return raw
        return ""


def iter_reference_fields(
    document: CommentedMap,
    *,
    include_instance_of: bool = True,
) -> Iterator[ReferenceField]:
    """Yield reference-like string fields from document."""

    resources = document.get("resources")
    if isinstance(resources, CommentedSeq):
        yield from _iter_resource_reference_fields(
            resources,
            "resources",
            include_instance_of=include_instance_of,
        )

    perspectives = document.get("perspectives")
    if isinstance(perspectives, CommentedSeq):
        for index, raw in enumerate(perspectives):
            if not isinstance(raw, CommentedMap):
                continue
            perspective = perspective_identifier(raw)
            base = f"perspectives[{index}]"
            yield from _iter_perspective_reference_fields(raw, perspective, base)


def _iter_resource_reference_fields(
    resources: CommentedSeq,
    base_path: str,
    *,
    include_instance_of: bool,
) -> Iterator[ReferenceField]:
    for index, raw in enumerate(resources):
        if not isinstance(raw, CommentedMap):
            continue
        path = f"{base_path}[{index}]"
        instance_of = raw.get("instanceOf")
        if include_instance_of and isinstance(instance_of, str):
            yield ReferenceField(
                container=raw,
                key="instanceOf",
                path=f"{path}.instanceOf",
                perspective=None,
                section="resource.instanceOf",
            )
        children = raw.get("children")
        if isinstance(children, CommentedSeq):
            yield from _iter_resource_reference_fields(
                children,
                f"{path}.children",
                include_instance_of=include_instance_of,
            )


def _iter_perspective_reference_fields(
    perspective_node: CommentedMap,
    perspective: str | None,
    base_path: str,
) -> Iterator[ReferenceField]:
    relations = perspective_node.get("relations")
    if isinstance(relations, CommentedSeq):
        for index, relation in enumerate(relations):
            if not isinstance(relation, CommentedMap):
                continue
            relation_path = f"{base_path}.relations[{index}]"
            for key in ("from", "to", "via"):
                value = relation.get(key)
                if isinstance(value, str):
                    yield ReferenceField(
                        container=relation,
                        key=key,
                        path=f"{relation_path}.{key}",
                        perspective=perspective,
                        section="relations",
                    )

    overrides = perspective_node.get("overrides")
    if isinstance(overrides, CommentedSeq):
        for index, override in enumerate(overrides):
            if not isinstance(override, CommentedMap):
                continue
            override_path = f"{base_path}.overrides[{index}]"
            for key in ("resourceId", "parentId"):
                value = override.get(key)
                if isinstance(value, str):
                    yield ReferenceField(
                        container=override,
                        key=key,
                        path=f"{override_path}.{key}",
                        perspective=perspective,
                        section="overrides",
                    )

    aliases = perspective_node.get("aliases")
    if isinstance(aliases, CommentedSeq):
        for index, alias in enumerate(aliases):
            if not isinstance(alias, CommentedMap):
                continue
            alias_for = alias.get("for")
            if isinstance(alias_for, str):
                yield ReferenceField(
                    container=alias,
                    key="for",
                    path=f"{base_path}.aliases[{index}].for",
                    perspective=perspective,
                    section="aliases",
                )

    walkthrough = perspective_node.get("walkthrough")
    if isinstance(walkthrough, CommentedSeq):
        for slide_index, slide in enumerate(walkthrough):
            if not isinstance(slide, CommentedMap):
                continue
            slide_path = f"{base_path}.walkthrough[{slide_index}]"
            for key, value in slide.items():
                if key not in WALKTHROUGH_REFERENCE_KEYS:
                    continue
                if isinstance(value, str):
                    yield ReferenceField(
                        container=slide,
                        key=key,
                        path=f"{slide_path}.{key}",
                        perspective=perspective,
                        section="walkthrough",
                    )

    sequence = perspective_node.get("sequence")
    if isinstance(sequence, CommentedMap):
        start = sequence.get("start")
        if isinstance(start, str):
            yield ReferenceField(
                container=sequence,
                key="start",
                path=f"{base_path}.sequence.start",
                perspective=perspective,
                section="sequence",
            )
        steps = sequence.get("steps")
        if isinstance(steps, CommentedSeq):
            yield from _iter_steps_reference_fields(
                steps,
                perspective,
                f"{base_path}.sequence.steps",
            )


def _iter_steps_reference_fields(
    steps: CommentedSeq,
    perspective: str | None,
    base_path: str,
) -> Iterator[ReferenceField]:
    for index, step in enumerate(steps):
        if not isinstance(step, CommentedMap):
            continue
        step_path = f"{base_path}[{index}]"
        for key in ("to", "toAndBack", "toAsync", "restartAt"):
            value = step.get(key)
            if isinstance(value, str):
                yield ReferenceField(
                    container=step,
                    key=key,
                    path=f"{step_path}.{key}",
                    perspective=perspective,
                    section="sequence",
                )

        sub_sequence = step.get("subSequence")
        if isinstance(sub_sequence, CommentedMap):
            sub_steps = sub_sequence.get("steps")
            if isinstance(sub_steps, CommentedSeq):
                yield from _iter_steps_reference_fields(
                    sub_steps,
                    perspective,
                    f"{step_path}.subSequence.steps",
                )
