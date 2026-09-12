"""`relation` mutate command registration."""

from __future__ import annotations

from pathlib import Path

import typer
from ruamel.yaml.comments import CommentedMap

from ilograph_cli.cli_options import diff_mode_option, file_option
from ilograph_cli.cli_support import CliGuard, MutationRunner, validate_payload
from ilograph_cli.commands.relation_shared import (
    _build_relation_template,
    _parse_multi_values,
    context_filter_option,
    perspective_filter_option,
)
from ilograph_cli.core.arg_models import RelationAddArgs, RelationEditArgs, RelationRemoveArgs
from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.relation_types import RelationClearField
from ilograph_cli.ops.relation_ops import (
    add_relation,
    edit_relation,
    edit_relations_match_many,
    remove_relation,
    remove_relations_match_many,
)


def register(
    app: typer.Typer,
    *,
    guard: CliGuard,
    runner: MutationRunner,
) -> None:
    """Register relation mutate subcommands."""

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
