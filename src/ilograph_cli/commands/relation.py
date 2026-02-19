"""`relation` command registration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, TypedDict

import typer
from rich.console import Console
from rich.table import Table
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.cli_options import diff_mode_option, file_option
from ilograph_cli.cli_support import CliGuard, MutationRunner, validate_payload
from ilograph_cli.core.arg_models import RelationAddArgs, RelationEditArgs, RelationRemoveArgs
from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.index import build_perspective_locations, get_single_perspective
from ilograph_cli.core.normalize import normalize_optional_str
from ilograph_cli.core.relation_types import (
    RelationArrowDirection,
    RelationClearField,
    RelationTemplate,
)
from ilograph_cli.io.yaml_io import load_document
from ilograph_cli.ops.relation_ops import (
    add_relation,
    edit_relation,
    edit_relations_match_many,
    remove_relation,
    remove_relations_match_many,
)

_ALLOWED_DIRECTIONS: set[str] = {"forward", "backward", "bidirectional"}

perspective_filter_option = typer.Option(
    None,
    "--perspective",
    help="Perspective id/name filter. Repeat or pass comma-separated values.",
)
context_filter_option = typer.Option(
    None,
    "--context",
    help="Context for {context} template expansion. Repeat/comma-separated.",
)


class RelationRow(TypedDict):
    perspective: str
    index: int
    from_: str | None
    to: str | None
    via: str | None
    label: str | None
    description: str | None
    arrow_direction: str | None
    color: str | None
    secondary: bool


def register(
    app: typer.Typer,
    *,
    console: Console,
    guard: CliGuard,
    runner: MutationRunner,
) -> None:
    """Register relation subcommands."""

    @app.command("ls")
    @app.command("list")
    def relation_list_cmd(
        file_path: Path = file_option,
        perspective: list[str] | None = perspective_filter_option,
        from_ref: str | None = typer.Option(None, "--from"),
        to_ref: str | None = typer.Option(None, "--to"),
        via: str | None = typer.Option(None, "--via"),
        label: str | None = typer.Option(None, "--label"),
        description: str | None = typer.Option(None, "--description"),
        arrow_direction: str | None = typer.Option(None, "--arrow-direction"),
        color: str | None = typer.Option(None, "--color"),
        secondary: bool | None = typer.Option(
            None,
            "--secondary/--no-secondary",
            help="Filter by relation.secondary",
        ),
        json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
        no_truncate: bool = typer.Option(
            False,
            "--no-truncate",
            help="Do not wrap/truncate table columns",
        ),
    ) -> None:
        """List perspective relations with filters."""

        with guard:
            document = load_document(file_path)
            selected_perspectives = _resolve_perspectives(
                document,
                _parse_multi_values(perspective),
            )
            filters = _build_relation_template(
                from_ref=from_ref,
                to_ref=to_ref,
                via=via,
                label=label,
                description=description,
                arrow_direction=arrow_direction,
                color=color,
                secondary=secondary,
            )
            rows = _list_relations(document, selected_perspectives, filters=filters)

            if json_output:
                payload = {
                    "count": len(rows),
                    "filters": filters,
                    "rows": rows,
                }
                typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
                return

            if not rows:
                console.print("no relations found")
                return

            overflow_mode: Literal["ignore", "fold"] = "ignore" if no_truncate else "fold"
            table = Table(title="Relations")
            table.add_column("Perspective", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Index", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("From", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("To", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Via", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Label", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Direction", overflow=overflow_mode, no_wrap=no_truncate)
            table.add_column("Secondary", overflow=overflow_mode, no_wrap=no_truncate)

            for row in rows:
                from_value = row["from_"] or "-"
                to_value = row["to"] or "-"
                via_value = row["via"] or "-"
                label_value = row["label"] or "-"
                direction_value = row["arrow_direction"] or "-"
                table.add_row(
                    row["perspective"],
                    str(row["index"]),
                    from_value,
                    to_value,
                    via_value,
                    label_value,
                    direction_value,
                    str(row["secondary"]),
                )
            console.print(table)
            console.print(f"total: {len(rows)}")

    @app.command("add")
    def relation_add_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        from_ref: str | None = typer.Option(None, "--from"),
        to_ref: str | None = typer.Option(None, "--to"),
        via: str | None = typer.Option(None, "--via"),
        label: str | None = typer.Option(None, "--label"),
        description: str | None = typer.Option(None, "--description"),
        arrow_direction: str | None = typer.Option(None, "--arrow-direction"),
        color: str | None = typer.Option(None, "--color"),
        secondary: bool | None = typer.Option(None, "--secondary/--no-secondary"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Add relation."""

        with guard:
            args = validate_payload(
                RelationAddArgs,
                {
                    "perspective": perspective,
                    "from": from_ref,
                    "to": to_ref,
                    "via": via,
                    "label": label,
                    "description": description,
                    "arrow_direction": arrow_direction,
                    "color": color,
                    "secondary": secondary,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return add_relation(
                    document,
                    perspective_id=args.perspective,
                    from_ref=args.from_,
                    to_ref=args.to,
                    via=args.via,
                    label=args.label,
                    description=args.description,
                    arrow_direction=args.arrow_direction,
                    color=args.color,
                    secondary=args.secondary,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("remove")
    def relation_remove_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        index: int = typer.Option(..., "--index", help="1-based relation index"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Remove relation."""

        with guard:
            args = validate_payload(
                RelationRemoveArgs,
                {"perspective": perspective, "index": index},
            )

            def mutate(document: CommentedMap) -> bool:
                return remove_relation(
                    document,
                    perspective_id=args.perspective,
                    index_1_based=args.index,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("remove-match")
    def relation_remove_match_cmd(
        file_path: Path = file_option,
        perspective: list[str] | None = perspective_filter_option,
        context: list[str] | None = context_filter_option,
        from_ref: str | None = typer.Option(None, "--from"),
        to_ref: str | None = typer.Option(None, "--to"),
        via: str | None = typer.Option(None, "--via"),
        label: str | None = typer.Option(None, "--label"),
        description: str | None = typer.Option(None, "--description"),
        arrow_direction: str | None = typer.Option(None, "--arrow-direction"),
        color: str | None = typer.Option(None, "--color"),
        secondary: bool | None = typer.Option(
            None,
            "--secondary/--no-secondary",
            help="Match relation.secondary",
        ),
        require_match: bool = typer.Option(
            True,
            "--require-match/--allow-noop",
            help="Fail when nothing matches (default: require match).",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Remove all relations matching filters."""

        with guard:
            selected_perspectives = _parse_multi_values(perspective)
            selected_contexts = _parse_multi_values(context)
            match = _build_relation_template(
                from_ref=from_ref,
                to_ref=to_ref,
                via=via,
                label=label,
                description=description,
                arrow_direction=arrow_direction,
                color=color,
                secondary=secondary,
            )
            if not match:
                raise ValidationError("match must define at least one field")

            def mutate(document: CommentedMap) -> bool:
                removed = remove_relations_match_many(
                    document,
                    perspectives=selected_perspectives or "*",
                    contexts=selected_contexts or None,
                    match_template=match,
                    require_match=require_match,
                )
                return removed > 0

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("edit")
    def relation_edit_cmd(
        file_path: Path = file_option,
        perspective: str = typer.Option(..., "--perspective"),
        index: int = typer.Option(..., "--index", help="1-based relation index"),
        from_ref: str | None = typer.Option(None, "--from"),
        to_ref: str | None = typer.Option(None, "--to"),
        via: str | None = typer.Option(None, "--via"),
        label: str | None = typer.Option(None, "--label"),
        description: str | None = typer.Option(None, "--description"),
        arrow_direction: str | None = typer.Option(None, "--arrow-direction"),
        color: str | None = typer.Option(None, "--color"),
        secondary: bool | None = typer.Option(None, "--secondary/--no-secondary"),
        clear_from: bool = typer.Option(False, "--clear-from"),
        clear_to: bool = typer.Option(False, "--clear-to"),
        clear_via: bool = typer.Option(False, "--clear-via"),
        clear_label: bool = typer.Option(False, "--clear-label"),
        clear_description: bool = typer.Option(False, "--clear-description"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Edit relation."""

        with guard:
            args = validate_payload(
                RelationEditArgs,
                {
                    "perspective": perspective,
                    "index": index,
                    "from": from_ref,
                    "to": to_ref,
                    "via": via,
                    "label": label,
                    "description": description,
                    "arrow_direction": arrow_direction,
                    "color": color,
                    "secondary": secondary,
                    "clear_from": clear_from,
                    "clear_to": clear_to,
                    "clear_via": clear_via,
                    "clear_label": clear_label,
                    "clear_description": clear_description,
                },
            )

            def mutate(document: CommentedMap) -> bool:
                return edit_relation(
                    document,
                    perspective_id=args.perspective,
                    index_1_based=args.index,
                    from_ref=args.from_,
                    to_ref=args.to,
                    via=args.via,
                    label=args.label,
                    description=args.description,
                    arrow_direction=args.arrow_direction,
                    color=args.color,
                    secondary=args.secondary,
                    clear_from=args.clear_from,
                    clear_to=args.clear_to,
                    clear_via=args.clear_via,
                    clear_label=args.clear_label,
                    clear_description=args.clear_description,
                )

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )

    @app.command("edit-match")
    def relation_edit_match_cmd(
        file_path: Path = file_option,
        perspective: list[str] | None = perspective_filter_option,
        context: list[str] | None = context_filter_option,
        match_from: str | None = typer.Option(None, "--match-from"),
        match_to: str | None = typer.Option(None, "--match-to"),
        match_via: str | None = typer.Option(None, "--match-via"),
        match_label: str | None = typer.Option(None, "--match-label"),
        match_description: str | None = typer.Option(None, "--match-description"),
        match_arrow_direction: str | None = typer.Option(None, "--match-arrow-direction"),
        match_color: str | None = typer.Option(None, "--match-color"),
        match_secondary: bool | None = typer.Option(
            None,
            "--match-secondary/--match-no-secondary",
            help="Match relation.secondary",
        ),
        set_from: str | None = typer.Option(None, "--set-from"),
        set_to: str | None = typer.Option(None, "--set-to"),
        set_via: str | None = typer.Option(None, "--set-via"),
        set_label: str | None = typer.Option(None, "--set-label"),
        set_description: str | None = typer.Option(None, "--set-description"),
        set_arrow_direction: str | None = typer.Option(None, "--set-arrow-direction"),
        set_color: str | None = typer.Option(None, "--set-color"),
        set_secondary: bool | None = typer.Option(
            None,
            "--set-secondary/--set-no-secondary",
            help="Set relation.secondary",
        ),
        clear_from: bool = typer.Option(False, "--clear-from"),
        clear_to: bool = typer.Option(False, "--clear-to"),
        clear_via: bool = typer.Option(False, "--clear-via"),
        clear_label: bool = typer.Option(False, "--clear-label"),
        clear_description: bool = typer.Option(False, "--clear-description"),
        clear_arrow_direction: bool = typer.Option(False, "--clear-arrow-direction"),
        clear_color: bool = typer.Option(False, "--clear-color"),
        clear_secondary: bool = typer.Option(False, "--clear-secondary"),
        require_match: bool = typer.Option(
            True,
            "--require-match/--allow-noop",
            help="Fail when nothing matches (default: require match).",
        ),
        dry_run: bool = typer.Option(False, "--dry-run"),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Edit all relations matching filters."""

        with guard:
            selected_perspectives = _parse_multi_values(perspective)
            selected_contexts = _parse_multi_values(context)
            match = _build_relation_template(
                from_ref=match_from,
                to_ref=match_to,
                via=match_via,
                label=match_label,
                description=match_description,
                arrow_direction=match_arrow_direction,
                color=match_color,
                secondary=match_secondary,
            )
            if not match:
                raise ValidationError("match must define at least one field")

            set_template = _build_relation_template(
                from_ref=set_from,
                to_ref=set_to,
                via=set_via,
                label=set_label,
                description=set_description,
                arrow_direction=set_arrow_direction,
                color=set_color,
                secondary=set_secondary,
            )

            clear_fields: list[RelationClearField] = []
            if clear_from:
                clear_fields.append("from")
            if clear_to:
                clear_fields.append("to")
            if clear_via:
                clear_fields.append("via")
            if clear_label:
                clear_fields.append("label")
            if clear_description:
                clear_fields.append("description")
            if clear_arrow_direction:
                clear_fields.append("arrowDirection")
            if clear_color:
                clear_fields.append("color")
            if clear_secondary:
                clear_fields.append("secondary")

            if not set_template and not clear_fields:
                raise ValidationError("edit-match requires set values or clear flags")

            def mutate(document: CommentedMap) -> bool:
                edited = edit_relations_match_many(
                    document,
                    perspectives=selected_perspectives or "*",
                    contexts=selected_contexts or None,
                    match_template=match,
                    set_template=set_template or None,
                    clear_fields=clear_fields,
                    require_match=require_match,
                )
                return edited > 0

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )


def _list_relations(
    document: CommentedMap,
    selected_perspectives: list[str],
    *,
    filters: RelationTemplate,
) -> list[RelationRow]:
    rows: list[RelationRow] = []
    for perspective_id in selected_perspectives:
        perspective = get_single_perspective(document, perspective_id)
        relations = perspective.node.get("relations")
        if not isinstance(relations, CommentedSeq):
            continue

        for index, relation in enumerate(relations, start=1):
            if not isinstance(relation, CommentedMap):
                continue
            if not _relation_matches_filters(relation, filters):
                continue

            secondary = relation.get("secondary")
            rows.append(
                {
                    "perspective": perspective.identifier,
                    "index": index,
                    "from_": _as_optional_str(relation.get("from")),
                    "to": _as_optional_str(relation.get("to")),
                    "via": _as_optional_str(relation.get("via")),
                    "label": _as_optional_str(relation.get("label")),
                    "description": _as_optional_str(relation.get("description")),
                    "arrow_direction": _as_optional_str(relation.get("arrowDirection")),
                    "color": _as_optional_str(relation.get("color")),
                    "secondary": bool(secondary) if isinstance(secondary, bool) else False,
                }
            )
    return rows


def _relation_matches_filters(relation: CommentedMap, filters: RelationTemplate) -> bool:
    for key, expected in filters.items():
        if key == "secondary":
            actual = relation.get("secondary")
            actual_bool = actual if isinstance(actual, bool) else False
            if actual_bool != expected:
                return False
            continue
        if relation.get(key) != expected:
            return False
    return True


def _resolve_perspectives(document: CommentedMap, selected: list[str]) -> list[str]:
    if selected:
        return [get_single_perspective(document, item).identifier for item in selected]
    return [item.identifier for item in build_perspective_locations(document)]


def _parse_multi_values(values: list[str] | None) -> list[str]:
    if not values:
        return []
    parsed: list[str] = []
    for raw in values:
        for token in raw.split(","):
            candidate = token.strip()
            if candidate:
                parsed.append(candidate)
    return parsed


def _build_relation_template(
    *,
    from_ref: str | None,
    to_ref: str | None,
    via: str | None,
    label: str | None,
    description: str | None,
    arrow_direction: str | None,
    color: str | None,
    secondary: bool | None,
) -> RelationTemplate:
    payload: RelationTemplate = {}

    normalized_from = _normalize_relation_value(from_ref, field_name="from")
    normalized_to = _normalize_relation_value(to_ref, field_name="to")
    normalized_via = _normalize_relation_value(via, field_name="via")
    normalized_label = _normalize_relation_value(label, field_name="label")
    normalized_description = _normalize_relation_value(description, field_name="description")
    normalized_color = _normalize_relation_value(color, field_name="color")

    normalized_direction: RelationArrowDirection | None = None
    if arrow_direction is not None:
        cleaned_direction = _normalize_relation_value(
            arrow_direction,
            field_name="arrow_direction",
        )
        if cleaned_direction is None:
            raise ValidationError("arrow-direction must not be empty")
        lowered = cleaned_direction.lower()
        if lowered not in _ALLOWED_DIRECTIONS:
            raise ValidationError(
                "arrow-direction must be one of: forward, backward, bidirectional"
            )
        normalized_direction = lowered  # type: ignore[assignment]

    if normalized_from is not None:
        payload["from"] = normalized_from
    if normalized_to is not None:
        payload["to"] = normalized_to
    if normalized_via is not None:
        payload["via"] = normalized_via
    if normalized_label is not None:
        payload["label"] = normalized_label
    if normalized_description is not None:
        payload["description"] = normalized_description
    if normalized_direction is not None:
        payload["arrowDirection"] = normalized_direction
    if normalized_color is not None:
        payload["color"] = normalized_color
    if secondary is not None:
        payload["secondary"] = secondary

    return payload


def _normalize_relation_value(value: str | None, *, field_name: str) -> str | None:
    try:
        return normalize_optional_str(value, field_name=field_name)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


def _as_optional_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None
