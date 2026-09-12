# Apply and batch transactions

Apply and batch run many operations as one atomic transaction from an ops file or inline JSON, either writing the result or previewing it with `--dry-run`.

## Sub-features

- `txn-apply` reads `ops.yaml` (`ops:` list of `{op, ...}` objects, see `docs/ops.md`) and applies every op atomically.
- `txn-batch` takes repeated `--op '<json>'` flags and runs them as one transaction.
- `txn-dry-run` previews validation plus diff without writing; the file must stay byte-identical.
- `txn-atomic-failure` leaves the file unchanged when any op fails or the result is invalid.
- `txn-schema-error` reports malformed ops payloads as human-readable errors without pydantic URLs.

## How to get to it (user POV)

- Run `ilograph apply --file diagram.yaml --ops ops.yaml --dry-run --diff full` to preview a file of ops.
- Run `ilograph apply --file diagram.yaml --ops ops.yaml` to commit it.
- Run `ilograph batch --file diagram.yaml --op '{"op":"rename.resource","id":"api","name":"API v2"}' --op '{"op":"relation.add","perspective":"Runtime","from":"web","to":"api"}'` for inline ops.

## Driving it with control-ilograph

Preconditions:

- `helpers/control-ilograph doctor --file "$D/diagram.yaml"` reports all checks passed.
- Work dir holds a copy of `tests/golden/apply_ops/input.yaml` as `diagram.yaml`, a copy of `tests/golden/apply_ops/ops.yaml` as `ops.yaml`, and `before.yaml`.

- **Dry-run preview.** Run `helpers/control-ilograph cli -- apply --file "$D/diagram.yaml" --ops "$D/ops.yaml" --dry-run --diff full`. Exit code `0`, stdout contains a unified diff and `dry-run`; `diff -u` the diagram against `before.yaml` is empty (nothing written).
- **Commit.** Run `helpers/control-ilograph cli -- apply --file "$D/diagram.yaml" --ops "$D/ops.yaml"`. Exit code `0`. `diff -u` against `before.yaml` is non-empty and equals the committed change; `check --file "$D/diagram.yaml" --mode strict` exits `0`.
- **Batch inline.** On a fresh fixture copy, run `helpers/control-ilograph cli -- batch --file "$D/diagram.yaml" --op '{"op":"rename.resource","id":"svc_a","name":"Service A Updated"}' --op '{"op":"relation.add","perspective":"Runtime","from":"svc_a","to":"ext"}' --dry-run --diff full`. Exit code `0` and the file is unchanged (dry-run); drop `--dry-run` to commit and re-verify with `check --mode strict`.
- **Atomic failure.** Write `bad-ops.yaml` with one valid `rename.resource` plus one `move.resource` of id `missing`, then run `helpers/control-ilograph cli -- apply --file "$D/diagram.yaml" --ops "$D/bad-ops.yaml"`. Exit code `1`, stdout contains `resource id not found: missing`; the diagram is byte-identical to its pre-command state (the valid op did not partially apply).
- **Schema error.** Write an ops file with a misspelled field (e.g. `labels: typo` on `relation.add`) and run `apply`. Exit code `1`; stdout contains `invalid ops file:` and the offending path (`ops[0].relation.add.labels`) and `Extra inputs are not permitted`, with no `pydantic.dev` URL.
- **Empty ops rejected.** Write `ops: []` and run `apply`. Exit code `1` with `ops must contain at least one operation`.
- **Proof.** Save transcripts to `$EVIDENCE/apply-batch.transcript.txt`, diffs to `$EVIDENCE/apply-batch.diff.txt`, and keep the exact ops files used beside them.

## Gotchas

- `apply` and `batch` validate the resulting document in strict mode before writing. An op that is individually plausible can still fail the transaction if the final document is invalid; the whole file is then unchanged.
- `--diff summary` is the default and hides patch text; use `--diff full` in proofs so the transcript shows what changed, and `--diff none` only when asserting the `diff hidden` path.
- Ops YAML uses camelCase keys (`newParent`, `newId`) while CLI flags use kebab-case (`--new-parent`, `--new-id`). Copy the spelling from `docs/ops.md`, not from `--help`.
- `batch --op` values must be single JSON objects. Quote them with single quotes so the shell does not eat the double quotes.
