# Safe refactors

Safe refactors rename and relocate resources (and manage groups and resource lifecycles) while preserving YAML comments and formatting, validating the result in strict mode, and leaving the input file untouched when validation fails.

## Sub-features

- `refactor-rename` renames a resource display name (`rename resource`) or its identifier (`rename resource-id`, updating every exact reference token).
- `refactor-move` relocates a resource subtree (`move resource`, `group move-many`).
- `refactor-group-resource` creates groups and resources, clones, and deletes (`group create`, `resource create|clone|delete`).
- `refactor-dry-run` previews validation plus diff (`--dry-run --diff full|summary|none`) without writing.
- `refactor-atomic` keeps the file byte-identical when the mutation is rejected.

## How to get to it (user POV)

- Run `ilograph rename resource --file diagram.yaml --id api --name "API Gateway"` to rename a display name.
- Run `ilograph rename resource-id --file diagram.yaml --from api --to edge_api` to rename an identifier everywhere it is referenced.
- Run `ilograph move resource --file diagram.yaml --id service --new-parent platform` to relocate a subtree.
- Run `ilograph group create --file diagram.yaml --id domain --name Domain --parent platform` or `ilograph resource create --file diagram.yaml --id edge --name Edge --parent platform` to add nodes.
- Run any write command with `--dry-run --diff full` to preview without writing.

## Driving it with control-ilograph

Preconditions:

- `helpers/control-ilograph doctor --file "$D/diagram.yaml"` reports all checks passed.
- Work dir holds a copy of `tests/golden/rename_id/input.yaml` as `diagram.yaml` plus `before.yaml`.

- **Rename display name.** Run `helpers/control-ilograph cli -- rename resource --file "$D/diagram.yaml" --id app --name "App v2"`. Exit code `0`. `diff -u before.yaml diagram.yaml` shows the `name: App` to `name: App v2` hunk and nothing else; `check --file "$D/diagram.yaml" --mode strict` exits `0`.
- **Rename identifier.** Run `helpers/control-ilograph cli -- rename resource-id --file "$D/diagram.yaml" --from db --to postgres`. Exit code `0`. The file contains `to: postgres` and still contains `&db_resource` anchor and `*layout_defaults` alias; a sibling id such as `db_replica` is untouched (exact-token update only).
- **Move subtree.** Run `helpers/control-ilograph cli -- move resource --file "$D/diagram.yaml" --id cache --new-parent worker`. Exit code `0`. The `cache` node now nests under `worker`; `check --mode strict` exits `0`.
- **Dry-run writes nothing.** Run `helpers/control-ilograph cli -- rename resource --file "$D/diagram.yaml" --id app --name "Preview" --dry-run --diff full`. Exit code `0`, stdout contains a unified diff and `dry-run`; `diff -u before.yaml diagram.yaml` against the pre-command copy is empty.
- **Rejected mutation keeps file.** Run `helpers/control-ilograph cli -- rename resource-id --file "$D/diagram.yaml" --from db --to app` (target exists). Exit code `1`, stdout contains `target id already exists: app`; the file is byte-identical to `before.yaml`.
- **Proof.** Save transcripts to `$EVIDENCE/safe-refactor.transcript.txt`, diffs to `$EVIDENCE/safe-refactor.diff.txt`, and the post-mutation `check --mode strict` output appended to the transcript.

## Gotchas

- `rename resource --id` matches the explicit `id` only. Passing a display name fails with `resource id not found`, which is correct behavior, not a bug.
- `resource delete` refuses a node with children unless `--delete-subtree` is passed; the failure leaves the file unchanged.
- Moving a resource under its own descendant fails with `own descendant`; assert the file is unchanged, not just the error text.
- Relation indices are one-based. `--index 1` is the first relation.
- A concurrent mutation on the same `--file` fails with `file is locked by another command`. Give every parallel drive its own file.
