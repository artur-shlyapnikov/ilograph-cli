"""`batch` command registration."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.cli_options import diff_mode_option, file_option
from ilograph_cli.cli_support import CliGuard, MutationRunner
from ilograph_cli.core.errors import ValidationError
from ilograph_cli.core.ops_models import parse_ops_payload
from ilograph_cli.ops.apply_ops import apply_ops

op_option = typer.Option(
    None,
    "--op",
    help=(
        "Single operation as JSON object; repeat --op for transaction "
        "(example: --op '{\"op\":\"rename.resource\",\"id\":\"api\",\"name\":\"API v2\"}')."
    ),
)


def register(app: typer.Typer, *, guard: CliGuard, runner: MutationRunner) -> None:
    """Register `batch` command."""

    @app.command("batch")
    def batch_cmd(
        file_path: Path = file_option,
        op: list[str] | None = op_option,
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Preview diff and validation results without writing.",
        ),
        diff_mode: str = diff_mode_option,
    ) -> None:
        """Apply multiple inline ops in one transaction."""

        with guard:
            raw_ops = op or []
            if not raw_ops:
                raise ValidationError("batch requires at least one --op JSON object")

            parsed_ops: list[dict[str, object]] = []
            for index, raw in enumerate(raw_ops, start=1):
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValidationError(
                        f"--op[{index}] invalid JSON: {exc.msg} (char {exc.pos})"
                    ) from exc
                if not isinstance(parsed, dict):
                    raise ValidationError(f"--op[{index}] must be a JSON object")
                parsed_ops.append(parsed)

            payload = CommentedMap(
                {
                    "ops": CommentedSeq([CommentedMap(item) for item in parsed_ops]),
                }
            )
            ops_file = parse_ops_payload(payload)

            def mutate(document: CommentedMap) -> bool:
                return apply_ops(document, ops_file)

            runner.run(
                file_path=file_path,
                dry_run=dry_run,
                diff_mode=diff_mode,
                mutator=mutate,
            )
