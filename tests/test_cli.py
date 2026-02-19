from __future__ import annotations

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from ilograph_cli.cli import app
from ilograph_cli.io.yaml_io import build_lock_path

runner = CliRunner()


def _copy_fixture(src: Path, dst_dir: Path, name: str = "diagram.yaml") -> Path:
    content = src.read_text(encoding="utf-8")
    dst = dst_dir / name
    dst.write_text(content, encoding="utf-8")
    return dst


def _write_yaml(dst_dir: Path, content: str, name: str = "diagram.yaml") -> Path:
    dst = dst_dir / name
    dst.write_text(content, encoding="utf-8")
    return dst


def test_rename_resource_id_golden(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)

    result = runner.invoke(
        app,
        [
            "rename",
            "resource-id",
            "--file",
            str(diagram),
            "--from",
            "db",
            "--to",
            "postgres",
        ],
    )

    assert result.exit_code == 0, result.output
    expected = (base / "expected.yaml").read_text(encoding="utf-8")
    actual = diagram.read_text(encoding="utf-8")
    assert actual == expected
    assert "&db_resource" in actual
    assert "*layout_defaults" in actual


def test_move_resource_golden(tmp_path: Path) -> None:
    base = Path("tests/golden/move_resource")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)

    result = runner.invoke(
        app,
        [
            "move",
            "resource",
            "--file",
            str(diagram),
            "--id",
            "api",
            "--new-parent",
            "shared",
        ],
    )

    assert result.exit_code == 0, result.output
    expected = (base / "expected.yaml").read_text(encoding="utf-8")
    actual = diagram.read_text(encoding="utf-8")
    assert actual == expected


def test_move_resource_anchor_safe_golden(tmp_path: Path) -> None:
    base = Path("tests/golden/move_resource_anchor_safe")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)

    result = runner.invoke(
        app,
        [
            "move",
            "resource",
            "--file",
            str(diagram),
            "--id",
            "acme",
            "--new-parent",
            "customers",
        ],
    )

    assert result.exit_code == 0, result.output
    expected = (base / "expected.yaml").read_text(encoding="utf-8")
    actual = diagram.read_text(encoding="utf-8")
    assert actual == expected
    assert "&external_integration_color" in actual


def test_noop_formatting_golden(tmp_path: Path) -> None:
    base = Path("tests/golden/noop_formatting")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)

    result = runner.invoke(
        app,
        [
            "rename",
            "resource",
            "--file",
            str(diagram),
            "--id",
            "app",
            "--name",
            "App v2",
        ],
    )

    assert result.exit_code == 0, result.output
    expected = (base / "expected.yaml").read_text(encoding="utf-8")
    actual = diagram.read_text(encoding="utf-8")
    assert actual == expected
    assert "{ resourceId: app, style: { color: red } }" in actual


def test_apply_ops_golden(tmp_path: Path) -> None:
    base = Path("tests/golden/apply_ops")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(base / "ops.yaml"),
        ],
    )

    assert result.exit_code == 0, result.output
    expected = (base / "expected.yaml").read_text(encoding="utf-8")
    actual = diagram.read_text(encoding="utf-8")
    assert actual == expected


def test_batch_inline_ops_runs_single_transaction(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "  - id: db\n"
            "    name: DB\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    name: Runtime\n"
        ),
    )

    result = runner.invoke(
        app,
        [
            "batch",
            "--file",
            str(diagram),
            "--op",
            '{"op":"rename.resource","id":"app","name":"Application"}',
            "--op",
            '{"op":"relation.add","perspective":"Runtime","from":"app","to":"db"}',
        ],
    )

    assert result.exit_code == 0, result.output
    after = diagram.read_text(encoding="utf-8")
    assert "name: Application" in after
    assert "from: app" in after
    assert "to: db" in after


def test_apply_ops_dry_run_does_not_write(tmp_path: Path) -> None:
    base = Path("tests/golden/apply_ops")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(base / "ops.yaml"),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    after = diagram.read_text(encoding="utf-8")
    assert after == before
    assert "dry-run" in result.output


def test_apply_ops_supports_resource_create_delete_clone(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
        ),
    )
    ops = _write_yaml(
        tmp_path,
        (
            "ops:\n"
            "  - op: resource.create\n"
            "    id: edge\n"
            "    name: Edge\n"
            "    parent: none\n"
            "  - op: resource.clone\n"
            "    id: edge\n"
            "    newId: edge_copy\n"
            "  - op: resource.delete\n"
            "    id: edge_copy\n"
        ),
        name="ops.yaml",
    )

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(ops),
        ],
    )

    assert result.exit_code == 0, result.output
    after = diagram.read_text(encoding="utf-8")
    assert "id: edge\n" in after
    assert "id: edge_copy\n" not in after


def test_apply_ops_relation_templates_golden(tmp_path: Path) -> None:
    base = Path("tests/golden/relation_templates")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(base / "ops.yaml"),
        ],
    )

    assert result.exit_code == 0, result.output
    expected = (base / "expected.yaml").read_text(encoding="utf-8")
    actual = diagram.read_text(encoding="utf-8")
    assert actual == expected


def test_apply_ops_relation_templates_unknown_context(tmp_path: Path) -> None:
    base = Path("tests/golden/relation_templates")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    ops = tmp_path / "ops.yaml"
    ops.write_text(
        (
            "ops:\n"
            "  - op: relation.add-many\n"
            "    target:\n"
            "      perspectives: [Runtime]\n"
            "      contexts: [missing]\n"
            "    from: app\n"
            "    to: db_{context}\n"
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(ops),
        ],
    )

    assert result.exit_code == 1
    assert "unknown context" in result.output


def test_check_reports_issues() -> None:
    result = runner.invoke(
        app,
        [
            "check",
            "--file",
            "tests/invalid_check.yaml",
        ],
    )

    assert result.exit_code == 1
    assert "duplicate-resource-id" in result.output
    assert "broken-reference" in result.output
    assert "restricted-resource-id" in result.output


def test_impact_output(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)

    result = runner.invoke(
        app,
        [
            "impact",
            "--file",
            str(diagram),
            "--resource-id",
            "db",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Impact for db" in result.output
    assert "relations" in result.output


def test_fmt_stable_is_safe(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)

    result = runner.invoke(
        app,
        [
            "fmt",
            "--file",
            str(diagram),
            "--stable",
        ],
    )

    assert result.exit_code == 0, result.output


def test_check_reports_duplicate_perspective_id(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    name: Runtime 1\n"
            "  - id: Runtime\n"
            "    name: Runtime 2\n"
        ),
    )

    result = runner.invoke(
        app,
        [
            "check",
            "--file",
            str(diagram),
        ],
    )

    assert result.exit_code == 1
    assert "duplicate-perspective-id" in result.output


def test_check_allows_duplicate_perspective_names_when_ids_differ(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "perspectives:\n"
            "  - id: RuntimeA\n"
            "    name: Runtime\n"
            "  - id: RuntimeB\n"
            "    name: Runtime\n"
        ),
    )

    result = runner.invoke(
        app,
        [
            "check",
            "--file",
            str(diagram),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "check ok" in result.output


def test_check_reports_name_needs_id_and_restricted_alias(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - name: Needs/Id\n"
            "  - id: app\n"
            "    name: App\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    aliases:\n"
            "      - alias: bad/alias\n"
            "        for: app\n"
        ),
    )

    result = runner.invoke(
        app,
        [
            "check",
            "--file",
            str(diagram),
        ],
    )

    assert result.exit_code == 1
    assert "name-needs-id" in result.output
    assert "restricted-alias-char" in result.output


def test_check_allows_alias_reference_tokens(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "  - id: api\n"
            "    name: API\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    aliases:\n"
            "      - alias: backend\n"
            "        for: api\n"
            "    relations:\n"
            "      - from: app\n"
            "        to: backend\n"
        ),
    )

    result = runner.invoke(
        app,
        [
            "check",
            "--file",
            str(diagram),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "check ok" in result.output


def test_relation_add_requires_from_or_to(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)

    result = runner.invoke(
        app,
        [
            "relation",
            "add",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--label",
            "invalid",
        ],
    )

    assert result.exit_code == 1
    assert "relation must define from or to" in result.output


def test_relation_edit_rejects_clearing_from_and_to(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)

    result = runner.invoke(
        app,
        [
            "relation",
            "edit",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--index",
            "1",
            "--clear-from",
            "--clear-to",
        ],
    )

    assert result.exit_code == 1
    assert "relation must define from or to" in result.output


def test_apply_ops_relation_template_requires_context_target(tmp_path: Path) -> None:
    base = Path("tests/golden/relation_templates")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    ops = _write_yaml(
        tmp_path,
        (
            "ops:\n"
            "  - op: relation.add-many\n"
            "    target:\n"
            "      perspectives: [Runtime]\n"
            "    from: app\n"
            "    to: db_{context}\n"
        ),
        name="ops.yaml",
    )

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(ops),
        ],
    )

    assert result.exit_code == 1
    assert "target.contexts is not set" in result.output


def test_rename_resource_id_rejects_existing_target_and_keeps_file(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "rename",
            "resource-id",
            "--file",
            str(diagram),
            "--from",
            "db",
            "--to",
            "app",
        ],
    )

    assert result.exit_code == 1
    assert "target id already exists: app" in result.output
    after = diagram.read_text(encoding="utf-8")
    assert after == before


def test_rename_resource_id_updates_exact_tokens_only(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "  - id: db\n"
            "    name: DB\n"
            "  - id: db_replica\n"
            "    name: DB Replica\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    relations:\n"
            "      - from: app\n"
            "        to: db\n"
            "      - from: app\n"
            "        to: db_replica\n"
        ),
    )

    result = runner.invoke(
        app,
        [
            "rename",
            "resource-id",
            "--file",
            str(diagram),
            "--from",
            "db",
            "--to",
            "postgres",
        ],
    )

    assert result.exit_code == 0, result.output
    after = diagram.read_text(encoding="utf-8")
    assert "to: postgres\n" in after
    assert "to: db_replica\n" in after
    assert "postgres_replica" not in after


def test_move_resource_rejects_move_under_descendant_and_keeps_file(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "move",
            "resource",
            "--file",
            str(diagram),
            "--id",
            "app",
            "--new-parent",
            "db",
        ],
    )

    assert result.exit_code == 1
    assert "own descendant" in result.output
    after = diagram.read_text(encoding="utf-8")
    assert after == before


def test_move_resource_inherit_style_from_parent_drops_style_block(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: source_group\n"
            "    name: Source\n"
            "    children:\n"
            "      - id: acme\n"
            "        name: Acme\n"
            "        style:\n"
            "          color: '#ff0000'\n"
            "  - id: destination_group\n"
            "    name: Destination\n"
        ),
    )

    result = runner.invoke(
        app,
        [
            "move",
            "resource",
            "--file",
            str(diagram),
            "--id",
            "acme",
            "--new-parent",
            "destination_group",
            "--inherit-style-from-parent",
        ],
    )

    assert result.exit_code == 0, result.output
    after = diagram.read_text(encoding="utf-8")
    assert "destination_group" in after
    assert "children:\n      - id: acme" in after
    assert "color: '#ff0000'" not in after


def test_relation_remove_rejects_out_of_range_index_and_keeps_file(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "relation",
            "remove",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--index",
            "99",
        ],
    )

    assert result.exit_code == 1
    assert "relation index out of range" in result.output
    after = diagram.read_text(encoding="utf-8")
    assert after == before


def test_group_move_many_rejects_duplicate_ids_and_keeps_file(tmp_path: Path) -> None:
    base = Path("tests/golden/apply_ops")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "group",
            "move-many",
            "--file",
            str(diagram),
            "--ids",
            "svc_a,svc_a",
            "--new-parent",
            "platform",
        ],
    )

    assert result.exit_code == 1
    assert "duplicate id in --ids: svc_a" in result.output
    after = diagram.read_text(encoding="utf-8")
    assert after == before


def test_apply_is_transactional_on_failure(tmp_path: Path) -> None:
    base = Path("tests/golden/apply_ops")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    before = diagram.read_text(encoding="utf-8")
    ops = _write_yaml(
        tmp_path,
        (
            "ops:\n"
            "  - op: rename.resource\n"
            "    id: svc_a\n"
            "    name: Service A Updated\n"
            "  - op: move.resource\n"
            "    id: missing\n"
            "    newParent: platform\n"
        ),
        name="ops.yaml",
    )

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(ops),
        ],
    )

    assert result.exit_code == 1
    assert "resource id not found: missing" in result.output
    after = diagram.read_text(encoding="utf-8")
    assert after == before


def test_mutation_fails_fast_when_diagram_is_locked(tmp_path: Path) -> None:
    base = Path("tests/golden/apply_ops")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    lock_path = build_lock_path(diagram)
    lock_path.write_text(f"pid={os.getpid()}\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "rename",
            "resource",
            "--file",
            str(diagram),
            "--id",
            "platform",
            "--name",
            "Platform v2",
        ],
    )

    assert result.exit_code == 1
    assert "file is locked by another command" in result.output
    assert diagram.read_text(encoding="utf-8") == (base / "input.yaml").read_text(encoding="utf-8")


def test_apply_relation_remove_match_require_match_false_is_safe_noop(tmp_path: Path) -> None:
    base = Path("tests/golden/relation_templates")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    before = diagram.read_text(encoding="utf-8")
    ops = _write_yaml(
        tmp_path,
        (
            "ops:\n"
            "  - op: relation.remove-match\n"
            "    target:\n"
            "      perspectives: [Runtime]\n"
            "    match:\n"
            "      from: ghost\n"
            "    requireMatch: false\n"
        ),
        name="ops.yaml",
    )

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(ops),
        ],
    )

    assert result.exit_code == 0, result.output
    after = diagram.read_text(encoding="utf-8")
    assert after == before
    assert "no changes" in result.output


def test_apply_move_resource_inherit_style_from_parent(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: source\n"
            "    name: Source\n"
            "    children:\n"
            "      - id: acme\n"
            "        name: Acme\n"
            "        style:\n"
            "          color: '#f00'\n"
            "  - id: destination\n"
            "    name: Destination\n"
        ),
    )
    ops = _write_yaml(
        tmp_path,
        (
            "ops:\n"
            "  - op: move.resource\n"
            "    id: acme\n"
            "    newParent: destination\n"
            "    inheritStyleFromParent: true\n"
        ),
        name="ops.yaml",
    )

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(ops),
        ],
    )

    assert result.exit_code == 0, result.output
    after = diagram.read_text(encoding="utf-8")
    assert "destination" in after
    assert "children:\n      - id: acme" in after
    assert "color: '#f00'" not in after


def test_apply_relation_remove_match_require_match_true_errors_on_noop(tmp_path: Path) -> None:
    base = Path("tests/golden/relation_templates")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    before = diagram.read_text(encoding="utf-8")
    ops = _write_yaml(
        tmp_path,
        (
            "ops:\n"
            "  - op: relation.remove-match\n"
            "    target:\n"
            "      perspectives: [Runtime]\n"
            "    match:\n"
            "      from: ghost\n"
            "    requireMatch: true\n"
        ),
        name="ops.yaml",
    )

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(ops),
        ],
    )

    assert result.exit_code == 1
    assert "no relations matched for relation.remove-match" in result.output
    after = diagram.read_text(encoding="utf-8")
    assert after == before


def test_apply_rejects_empty_ops_list(tmp_path: Path) -> None:
    base = Path("tests/golden/apply_ops")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    ops = _write_yaml(
        tmp_path,
        "ops: []\n",
        name="ops.yaml",
    )

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(ops),
        ],
    )

    assert result.exit_code == 1
    assert "ops must contain at least one operation" in result.output


def test_apply_edit_match_requires_set_or_clear(tmp_path: Path) -> None:
    base = Path("tests/golden/relation_templates")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    ops = _write_yaml(
        tmp_path,
        (
            "ops:\n"
            "  - op: relation.edit-match\n"
            "    target:\n"
            "      perspectives: [Runtime]\n"
            "    match:\n"
            "      from: app\n"
        ),
        name="ops.yaml",
    )

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(ops),
        ],
    )

    assert result.exit_code == 1
    assert "edit-match requires `set` or" in result.output
    assert "non-empty `clear`" in result.output


def test_load_document_accepts_unquoted_wildcard_reference_for_check_fmt_and_impact(
    tmp_path: Path,
) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: cert\n"
            "    name: Certificate\n"
            "perspectives:\n"
            "  - id: DNS\n"
            "    name: DNS\n"
            "    relations:\n"
            "      - from: [*.cloudfront.net]\n"
            "        to: cert\n"
        ),
    )

    check_result = runner.invoke(app, ["check", "--file", str(diagram)])
    assert check_result.exit_code == 0, check_result.output

    fmt_result = runner.invoke(
        app,
        ["fmt", "--file", str(diagram), "--stable", "--dry-run"],
    )
    assert fmt_result.exit_code == 0, fmt_result.output
    assert "no changes" in fmt_result.output

    impact_result = runner.invoke(
        app,
        ["impact", "--file", str(diagram), "--resource-id", "cert"],
    )
    assert impact_result.exit_code == 0, impact_result.output
    assert "Impact for cert" in impact_result.output


def test_check_allows_duplicate_resource_names_but_not_duplicate_ids(tmp_path: Path) -> None:
    duplicate_names = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - name: Service\n"
            "  - name: Service\n"
        ),
        name="duplicate_names.yaml",
    )
    duplicate_ids = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: svc\n"
            "    name: Service A\n"
            "  - id: svc\n"
            "    name: Service B\n"
        ),
        name="duplicate_ids.yaml",
    )

    names_result = runner.invoke(app, ["check", "--file", str(duplicate_names)])
    assert names_result.exit_code == 0, names_result.output

    ids_result = runner.invoke(app, ["check", "--file", str(duplicate_ids)])
    assert ids_result.exit_code == 1, ids_result.output
    assert "duplicate-resource-id" in ids_result.output


def test_check_parses_reference_expressions_without_word_tokenization_noise(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - name: API Gateway\n"
            "    children:\n"
            "      - name: api.ilograph.com\n"
            "  - name: handleDiagram()\n"
            "  - name: getDiagram()\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    name: Runtime\n"
            "    relations:\n"
            "      - from: API Gateway/api.ilograph.com\n"
            "        to: handleDiagram()\n"
            "      - from: handleDiagram()\n"
            "        to: getDiagram()\n"
        ),
    )

    result = runner.invoke(app, ["check", "--file", str(diagram)])
    assert result.exit_code == 0, result.output
    assert "check ok" in result.output


def test_check_does_not_validate_instanceof_as_resource_reference(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "  - id: derived\n"
            "    name: Derived\n"
            "    instanceOf: AWS::S3::Bucket\n"
        ),
    )

    result = runner.invoke(app, ["check", "--file", str(diagram)])
    assert result.exit_code == 0, result.output


def test_check_mode_strict_vs_ilograph_native_and_rule_filters(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    name: Runtime\n"
            "    relations:\n"
            "      - from: app\n"
            "        to: Ext::ImportedResource\n"
        ),
    )

    native_result = runner.invoke(
        app,
        ["check", "--file", str(diagram), "--mode", "ilograph-native"],
    )
    assert native_result.exit_code == 0, native_result.output

    strict_result = runner.invoke(
        app,
        ["check", "--file", str(diagram), "--mode", "strict"],
    )
    assert strict_result.exit_code == 1, strict_result.output
    assert "broken-reference" in strict_result.output
    assert "Ext::ImportedResource" in strict_result.output

    ignored_result = runner.invoke(
        app,
        [
            "check",
            "--file",
            str(diagram),
            "--mode",
            "strict",
            "--ignore-rule",
            "broken-reference",
        ],
    )
    assert ignored_result.exit_code == 0, ignored_result.output

    only_result = runner.invoke(
        app,
        [
            "check",
            "--file",
            str(diagram),
            "--mode",
            "strict",
            "--only-rule",
            "broken-reference",
        ],
    )
    assert only_result.exit_code == 1, only_result.output
    assert "broken-reference" in only_result.output


def test_fmt_stable_is_noop_roundtrip(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path, name="fmt_noop.yaml")
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "fmt",
            "--file",
            str(diagram),
            "--stable",
        ],
    )

    assert result.exit_code == 0, result.output
    after = diagram.read_text(encoding="utf-8")
    assert after == before
    assert "no changes" in result.output


def test_check_json_output_has_summary_by_code() -> None:
    result = runner.invoke(
        app,
        [
            "check",
            "--file",
            "tests/invalid_check.yaml",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["summary"]["total"] > 0
    assert payload["summary"]["by_code"]["duplicate-resource-id"] >= 1
    assert payload["summary"]["by_code"]["broken-reference"] >= 1


def test_resolve_and_find_commands_explain_reference_resolution(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "  - name: API Gateway\n"
            "    children:\n"
            "      - name: api.ilograph.com\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    name: Runtime\n"
            "    aliases:\n"
            "      - alias: API_ALIAS\n"
            "        for: API Gateway/api.ilograph.com\n"
        ),
    )

    resolve_result = runner.invoke(
        app,
        [
            "resolve",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--reference",
            "API Gateway/api.ilograph.com, API_ALIAS, Missing Thing, [Port *]",
        ],
    )
    assert resolve_result.exit_code == 0, resolve_result.output
    assert "resolved" in resolve_result.output
    assert "alias" in resolve_result.output
    assert "unresolved" in resolve_result.output
    assert "wildcard" in resolve_result.output

    find_result = runner.invoke(
        app,
        [
            "find",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--reference",
            "API_ALIAS",
        ],
    )
    assert find_result.exit_code == 0, find_result.output
    assert "alias" in find_result.output


def test_apply_fmt_stable_only_is_noop(tmp_path: Path) -> None:
    base = Path("tests/golden/apply_ops")
    diagram = _copy_fixture(base / "input.yaml", tmp_path, name="fmt_ops_input.yaml")
    before = diagram.read_text(encoding="utf-8")
    ops = _write_yaml(
        tmp_path,
        (
            "ops:\n"
            "  - op: fmt.stable\n"
        ),
        name="fmt_ops.yaml",
    )

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(ops),
        ],
    )

    assert result.exit_code == 0, result.output
    after = diagram.read_text(encoding="utf-8")
    assert after == before
    assert "no changes" in result.output


def test_resolve_unknown_perspective_fails(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    name: Runtime\n"
        ),
    )

    result = runner.invoke(
        app,
        [
            "resolve",
            "--file",
            str(diagram),
            "--reference",
            "app",
            "--perspective",
            "MissingPerspective",
        ],
    )

    assert result.exit_code == 1
    assert "perspective not found: MissingPerspective" in result.output


def test_resolve_json_output_contains_rows(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    name: Runtime\n"
            "    aliases:\n"
            "      - alias: APP_ALIAS\n"
            "        for: app\n"
        ),
    )

    result = runner.invoke(
        app,
        [
            "resolve",
            "--file",
            str(diagram),
            "--reference",
            "APP_ALIAS,missing",
            "--perspective",
            "Runtime",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["reference"] == "APP_ALIAS,missing"
    assert payload["perspective"] == "Runtime"
    assert len(payload["rows"]) >= 2
    statuses = {row["status"] for row in payload["rows"]}
    assert "alias" in statuses
    assert "unresolved" in statuses


def test_impact_json_output_contains_hits(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path, name="impact_json.yaml")

    result = runner.invoke(
        app,
        [
            "impact",
            "--file",
            str(diagram),
            "--resource-id",
            "db",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["resourceId"] == "db"
    assert payload["count"] > 0
    assert any(hit["section"] == "relations" for hit in payload["hits"])


def test_mutation_diff_none_hides_patch_lines(tmp_path: Path) -> None:
    base = Path("tests/golden/apply_ops")
    diagram = _copy_fixture(base / "input.yaml", tmp_path, name="diff_none.yaml")

    result = runner.invoke(
        app,
        [
            "rename",
            "resource",
            "--file",
            str(diagram),
            "--id",
            "platform",
            "--name",
            "Platform v2",
            "--dry-run",
            "--diff",
            "none",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "diff hidden" in result.output
    assert "touched sections: resources" in result.output
    assert "--- a/" not in result.output


def test_diff_headers_do_not_render_double_slash_for_absolute_paths(tmp_path: Path) -> None:
    base = Path("tests/golden/apply_ops")
    diagram = _copy_fixture(base / "input.yaml", tmp_path, name="abs_path.yaml")

    result = runner.invoke(
        app,
        [
            "rename",
            "resource",
            "--file",
            str(diagram),
            "--id",
            "platform",
            "--name",
            "Platform v2",
            "--dry-run",
            "--diff",
            "full",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "a/private/" in result.output
    assert "b/private/" in result.output
    assert "a//" not in result.output
    assert "b//" not in result.output


def test_rename_resource_noop_skips_round_trip_churn(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "- id: app\n"
            "  name: App\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    walkthrough:\n"
            "    - text:  |-\n"
            "        Some walkthrough text\n"
        ),
    )
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "rename",
            "resource",
            "--file",
            str(diagram),
            "--id",
            "app",
            "--name",
            "App",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "no changes" in result.output
    assert "--- a/" not in result.output
    assert diagram.read_text(encoding="utf-8") == before


def test_relation_edit_noop_skips_round_trip_churn(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "- id: app\n"
            "  name: App\n"
            "- id: db\n"
            "  name: DB\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    relations:\n"
            "    - from: app\n"
            "      to: db\n"
            "      label: reads\n"
            "    walkthrough:\n"
            "    - text:  |-\n"
            "        Some walkthrough text\n"
        ),
    )
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "relation",
            "edit",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--index",
            "1",
            "--label",
            "reads",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "no changes" in result.output
    assert "--- a/" not in result.output
    assert diagram.read_text(encoding="utf-8") == before


def test_mutation_rejects_invalid_result_and_keeps_file(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "relation",
            "add",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--from",
            "unknown_from",
            "--to",
            "unknown_to",
        ],
    )

    assert result.exit_code == 1
    assert "mutation would produce invalid document" in result.output
    assert "broken-reference" in result.output
    assert diagram.read_text(encoding="utf-8") == before


def test_rename_resource_matches_explicit_id_only(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App Name\n"
        ),
    )

    result = runner.invoke(
        app,
        [
            "rename",
            "resource",
            "--file",
            str(diagram),
            "--id",
            "App Name",
            "--name",
            "Renamed",
        ],
    )

    assert result.exit_code == 1
    assert "resource id not found: App Name" in result.output


def test_apply_ops_schema_error_is_humanized(tmp_path: Path) -> None:
    base = Path("tests/golden/rename_id")
    diagram = _copy_fixture(base / "input.yaml", tmp_path)
    ops = _write_yaml(
        tmp_path,
        (
            "ops:\n"
            "  - op: relation.add\n"
            "    perspective: Runtime\n"
            "    from: app\n"
            "    to: db\n"
            "    labels: typo\n"
        ),
        name="ops.yaml",
    )

    result = runner.invoke(
        app,
        [
            "apply",
            "--file",
            str(diagram),
            "--ops",
            str(ops),
        ],
    )

    assert result.exit_code == 1
    assert "invalid ops file:" in result.output
    assert "ops[0].relation.add.labels" in result.output
    assert "Extra inputs are not permitted" in result.output
    assert "pydantic.dev" not in result.output


def test_mutation_diff_omits_unrelated_style_only_block_scalar_changes(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "- id: app\n"
            "  name: App\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    walkthrough:\n"
            "    - text:  |-\n"
            "        Some walkthrough text\n"
        ),
    )

    result = runner.invoke(
        app,
        [
            "rename",
            "resource",
            "--file",
            str(diagram),
            "--id",
            "app",
            "--name",
            "App v2",
            "--dry-run",
            "--diff",
            "full",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "-  name: App" in result.output
    assert "+  name: App v2" in result.output
    assert "text:  |-" not in result.output
    assert "text: |-" not in result.output


def test_relation_list_and_match_commands(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "  - id: db\n"
            "    name: DB\n"
            "  - id: cache\n"
            "    name: Cache\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    name: Runtime\n"
            "    relations:\n"
            "      - from: app\n"
            "        to: db\n"
            "        label: call\n"
            "      - from: app\n"
            "        to: cache\n"
            "        label: read\n"
        ),
    )

    list_result = runner.invoke(
        app,
        [
            "relation",
            "ls",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--json",
        ],
    )
    assert list_result.exit_code == 0, list_result.output
    payload = json.loads(list_result.output)
    assert payload["count"] == 2

    edit_result = runner.invoke(
        app,
        [
            "relation",
            "edit-match",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--match-from",
            "app",
            "--set-label",
            "updated",
        ],
    )
    assert edit_result.exit_code == 0, edit_result.output

    remove_result = runner.invoke(
        app,
        [
            "relation",
            "remove-match",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--from",
            "app",
            "--to",
            "db",
        ],
    )
    assert remove_result.exit_code == 0, remove_result.output
    after = diagram.read_text(encoding="utf-8")
    assert "to: db\n" not in after
    assert "label: updated\n" in after


def test_resource_create_clone_delete_lifecycle(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "    children:\n"
            "      - id: db\n"
            "        name: DB\n"
        ),
    )

    create_result = runner.invoke(
        app,
        [
            "resource",
            "create",
            "--file",
            str(diagram),
            "--id",
            "cache",
            "--name",
            "Cache",
            "--parent",
            "app",
        ],
    )
    assert create_result.exit_code == 0, create_result.output

    clone_result = runner.invoke(
        app,
        [
            "resource",
            "clone",
            "--file",
            str(diagram),
            "--id",
            "app",
            "--new-id",
            "app_copy",
            "--shallow",
        ],
    )
    assert clone_result.exit_code == 0, clone_result.output

    delete_fail = runner.invoke(
        app,
        [
            "resource",
            "delete",
            "--file",
            str(diagram),
            "--id",
            "app",
        ],
    )
    assert delete_fail.exit_code == 1
    assert "resource has children" in delete_fail.output

    delete_ok = runner.invoke(
        app,
        [
            "resource",
            "delete",
            "--file",
            str(diagram),
            "--id",
            "app_copy",
        ],
    )
    assert delete_ok.exit_code == 0, delete_ok.output

    delete_subtree = runner.invoke(
        app,
        [
            "resource",
            "delete",
            "--file",
            str(diagram),
            "--id",
            "app",
            "--delete-subtree",
        ],
    )
    assert delete_subtree.exit_code == 0, delete_subtree.output
    after = diagram.read_text(encoding="utf-8")
    assert "id: app\n" not in after
    assert "id: cache\n" not in after


def test_perspective_and_context_crud_commands(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    name: Runtime\n"
            "contexts:\n"
            "  - name: prod\n"
        ),
    )

    assert (
        runner.invoke(
            app,
            [
                "perspective",
                "create",
                "--file",
                str(diagram),
                "--id",
                "Batch",
                "--name",
                "Batch",
                "--extends",
                "Runtime",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "perspective",
                "copy",
                "--file",
                str(diagram),
                "--id",
                "Runtime",
                "--new-id",
                "RuntimeCopy",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "perspective",
                "rename",
                "--file",
                str(diagram),
                "--id",
                "RuntimeCopy",
                "--new-id",
                "RuntimeShadow",
                "--new-name",
                "Runtime Shadow",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "perspective",
                "reorder",
                "--file",
                str(diagram),
                "--id",
                "Batch",
                "--index",
                "1",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "perspective",
                "delete",
                "--file",
                str(diagram),
                "--id",
                "RuntimeShadow",
            ],
        ).exit_code
        == 0
    )

    assert (
        runner.invoke(
            app,
            [
                "context",
                "create",
                "--file",
                str(diagram),
                "--name",
                "stage",
                "--extends",
                "prod",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "context",
                "copy",
                "--file",
                str(diagram),
                "--name",
                "prod",
                "--new-name",
                "prod_copy",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "context",
                "rename",
                "--file",
                str(diagram),
                "--name",
                "prod_copy",
                "--new-name",
                "prod_shadow",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "context",
                "delete",
                "--file",
                str(diagram),
                "--name",
                "prod_shadow",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "context",
                "reorder",
                "--file",
                str(diagram),
                "--name",
                "stage",
                "--index",
                "1",
            ],
        ).exit_code
        == 0
    )

    perspective_list = runner.invoke(
        app,
        [
            "perspective",
            "ls",
            "--file",
            str(diagram),
            "--json",
        ],
    )
    assert perspective_list.exit_code == 0, perspective_list.output
    perspectives_payload = json.loads(perspective_list.output)
    assert perspectives_payload["count"] == 2
    assert perspectives_payload["rows"][0]["identifier"] == "Batch"

    context_list = runner.invoke(
        app,
        [
            "context",
            "ls",
            "--file",
            str(diagram),
            "--json",
        ],
    )
    assert context_list.exit_code == 0, context_list.output
    contexts_payload = json.loads(context_list.output)
    assert contexts_payload["count"] == 2
    assert contexts_payload["rows"][0]["name"] == "stage"


def test_alias_and_override_crud_commands(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "  - id: db\n"
            "    name: DB\n"
            "perspectives:\n"
            "  - id: Runtime\n"
            "    name: Runtime\n"
        ),
    )

    assert (
        runner.invoke(
            app,
            [
                "alias",
                "add",
                "--file",
                str(diagram),
                "--perspective",
                "Runtime",
                "--alias",
                "backend",
                "--for",
                "db",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "alias",
                "edit",
                "--file",
                str(diagram),
                "--perspective",
                "Runtime",
                "--alias",
                "backend",
                "--new-alias",
                "storage",
                "--new-for",
                "db",
            ],
        ).exit_code
        == 0
    )
    alias_list = runner.invoke(
        app,
        [
            "alias",
            "ls",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--json",
        ],
    )
    assert alias_list.exit_code == 0, alias_list.output
    alias_payload = json.loads(alias_list.output)
    assert alias_payload["count"] == 1
    assert alias_payload["rows"][0]["alias"] == "storage"

    assert (
        runner.invoke(
            app,
            [
                "override",
                "add",
                "--file",
                str(diagram),
                "--perspective",
                "Runtime",
                "--resource-id",
                "db",
                "--parent-id",
                "app",
                "--scale",
                "0.8",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "override",
                "edit",
                "--file",
                str(diagram),
                "--perspective",
                "Runtime",
                "--resource-id",
                "db",
                "--new-resource-id",
                "storage",
                "--clear-parent-id",
                "--scale",
                "0.6",
            ],
        ).exit_code
        == 0
    )

    override_list = runner.invoke(
        app,
        [
            "override",
            "ls",
            "--file",
            str(diagram),
            "--perspective",
            "Runtime",
            "--json",
        ],
    )
    assert override_list.exit_code == 0, override_list.output
    override_payload = json.loads(override_list.output)
    assert override_payload["count"] == 1
    assert override_payload["rows"][0]["resourceId"] == "storage"
    assert override_payload["rows"][0]["parentId"] is None

    assert (
        runner.invoke(
            app,
            [
                "override",
                "remove",
                "--file",
                str(diagram),
                "--perspective",
                "Runtime",
                "--resource-id",
                "storage",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "alias",
                "remove",
                "--file",
                str(diagram),
                "--perspective",
                "Runtime",
                "--alias",
                "storage",
            ],
        ).exit_code
        == 0
    )


def test_sequence_and_walkthrough_step_slide_commands(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "  - id: api\n"
            "    name: API\n"
            "perspectives:\n"
            "  - id: Flow\n"
            "    name: Flow\n"
        ),
    )

    assert (
        runner.invoke(
            app,
            [
                "sequence",
                "add",
                "--file",
                str(diagram),
                "--perspective",
                "Flow",
                "--start",
                "app",
                "--to",
                "api",
                "--label",
                "first",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "sequence",
                "edit",
                "--file",
                str(diagram),
                "--perspective",
                "Flow",
                "--index",
                "1",
                "--to-and-back",
                "app",
                "--clear-label",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "sequence",
                "remove",
                "--file",
                str(diagram),
                "--perspective",
                "Flow",
                "--index",
                "1",
            ],
        ).exit_code
        == 0
    )

    assert (
        runner.invoke(
            app,
            [
                "walkthrough",
                "add",
                "--file",
                str(diagram),
                "--perspective",
                "Flow",
                "--text",
                "Step 1",
                "--select",
                "app",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "walkthrough",
                "edit",
                "--file",
                str(diagram),
                "--perspective",
                "Flow",
                "--index",
                "1",
                "--highlight",
                "api",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "walkthrough",
                "remove",
                "--file",
                str(diagram),
                "--perspective",
                "Flow",
                "--index",
                "1",
            ],
        ).exit_code
        == 0
    )

    sequence_list = runner.invoke(
        app,
        [
            "sequence",
            "ls",
            "--file",
            str(diagram),
            "--perspective",
            "Flow",
            "--json",
        ],
    )
    assert sequence_list.exit_code == 0, sequence_list.output
    assert json.loads(sequence_list.output)["count"] == 0

    walkthrough_list = runner.invoke(
        app,
        [
            "walkthrough",
            "ls",
            "--file",
            str(diagram),
            "--perspective",
            "Flow",
            "--json",
        ],
    )
    assert walkthrough_list.exit_code == 0, walkthrough_list.output
    assert json.loads(walkthrough_list.output)["count"] == 0


def test_resource_clone_with_children_rejects_duplicate_descendant_ids(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "    children:\n"
            "      - id: db\n"
            "        name: DB\n"
        ),
    )
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "resource",
            "clone",
            "--file",
            str(diagram),
            "--id",
            "app",
            "--new-id",
            "app_copy",
            "--with-children",
        ],
    )

    assert result.exit_code == 1
    assert "cannot clone subtree with explicit child ids" in result.output
    assert "conflicting id: db" in result.output
    assert diagram.read_text(encoding="utf-8") == before


def test_sequence_add_requires_start_when_sequence_missing(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "  - id: api\n"
            "    name: API\n"
            "perspectives:\n"
            "  - id: Flow\n"
            "    name: Flow\n"
        ),
    )
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "sequence",
            "add",
            "--file",
            str(diagram),
            "--perspective",
            "Flow",
            "--to",
            "api",
        ],
    )

    assert result.exit_code == 1
    assert "perspective has no sequence; pass --start to initialize sequence" in result.output
    assert diagram.read_text(encoding="utf-8") == before


def test_sequence_add_rejects_ambiguous_action_flags(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "  - id: api\n"
            "    name: API\n"
            "perspectives:\n"
            "  - id: Flow\n"
            "    name: Flow\n"
            "    sequence:\n"
            "      start: app\n"
            "      steps: []\n"
        ),
    )
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "sequence",
            "add",
            "--file",
            str(diagram),
            "--perspective",
            "Flow",
            "--to",
            "api",
            "--to-async",
            "api",
        ],
    )

    assert result.exit_code == 1
    assert "step requires exactly one action" in result.output
    assert diagram.read_text(encoding="utf-8") == before


def test_sequence_remove_rejects_out_of_range_index_and_keeps_file(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "  - id: api\n"
            "    name: API\n"
            "perspectives:\n"
            "  - id: Flow\n"
            "    name: Flow\n"
            "    sequence:\n"
            "      start: app\n"
            "      steps:\n"
            "        - to: api\n"
        ),
    )
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "sequence",
            "remove",
            "--file",
            str(diagram),
            "--perspective",
            "Flow",
            "--index",
            "2",
        ],
    )

    assert result.exit_code == 1
    assert "sequence step index out of range: 2" in result.output
    assert diagram.read_text(encoding="utf-8") == before


def test_walkthrough_add_requires_at_least_one_field(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "perspectives:\n"
            "  - id: Flow\n"
            "    name: Flow\n"
        ),
    )
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "walkthrough",
            "add",
            "--file",
            str(diagram),
            "--perspective",
            "Flow",
        ],
    )

    assert result.exit_code == 1
    assert "slide requires at least one field" in result.output
    assert diagram.read_text(encoding="utf-8") == before


def test_walkthrough_edit_requires_update_fields(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "perspectives:\n"
            "  - id: Flow\n"
            "    name: Flow\n"
            "    walkthrough:\n"
            "      - text: Step 1\n"
        ),
    )
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "walkthrough",
            "edit",
            "--file",
            str(diagram),
            "--perspective",
            "Flow",
            "--index",
            "1",
        ],
    )

    assert result.exit_code == 1
    assert "set at least one update field" in result.output
    assert diagram.read_text(encoding="utf-8") == before


def test_walkthrough_remove_rejects_out_of_range_index_and_keeps_file(tmp_path: Path) -> None:
    diagram = _write_yaml(
        tmp_path,
        (
            "resources:\n"
            "  - id: app\n"
            "    name: App\n"
            "perspectives:\n"
            "  - id: Flow\n"
            "    name: Flow\n"
            "    walkthrough:\n"
            "      - text: Step 1\n"
        ),
    )
    before = diagram.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "walkthrough",
            "remove",
            "--file",
            str(diagram),
            "--perspective",
            "Flow",
            "--index",
            "2",
        ],
    )

    assert result.exit_code == 1
    assert "walkthrough slide index out of range: 2" in result.output
    assert diagram.read_text(encoding="utf-8") == before
