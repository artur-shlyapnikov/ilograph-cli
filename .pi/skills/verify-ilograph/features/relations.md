# Relation editing

Relation editing adds, edits, and removes entries in a perspective's relation list, including bulk match-based variants, and lists relations for inspection.

## Sub-features

- `relation-add` appends a relation requiring at least one of `from`/`to`.
- `relation-edit` changes a one-based-indexed relation, with `--clear-from`/`--clear-to` unless both sides would be emptied.
- `relation-remove` deletes a one-based-indexed relation and rejects out-of-range indices.
- `relation-match` bulk-edits or removes by field match (`edit-match`, `remove-match`, `remove-match --require-match`).
- `relation-list` shows a perspective's relations (`relation list`, alias `relation ls`) with `--json` counts.

## How to get to it (user POV)

- Run `ilograph relation add --file diagram.yaml --perspective Runtime --from web --to api --label calls` to add a relation.
- Run `ilograph relation edit --file diagram.yaml --perspective Runtime --index 1 --label "calls v2"` to edit one.
- Run `ilograph relation remove --file diagram.yaml --perspective Runtime --index 1` to delete one.
- Run `ilograph relation list --file diagram.yaml --perspective Runtime --json` (or `relation ls`) to inspect.
- Run `ilograph relation edit-match --file diagram.yaml --perspective Runtime --match-from app --set-label updated` for bulk edits.

## Driving it with control-ilograph

Preconditions:

- `helpers/control-ilograph doctor --file "$D/diagram.yaml"` reports all checks passed.
- Work dir holds a copy of `tests/golden/rename_id/input.yaml` as `diagram.yaml` (its `Runtime` perspective starts with relations `app -> db` and `worker via db`) plus `before.yaml`.

- **List baseline.** Run `helpers/control-ilograph cli -- relation list --file "$D/diagram.yaml" --perspective Runtime --json`. Exit code `0`; parse stdout as JSON and record `count` (2 on the golden fixture).
- **Add.** Run `helpers/control-ilograph cli -- relation add --file "$D/diagram.yaml" --perspective Runtime --from app --to cache --label calls`. Exit code `0`. Re-run `relation list --json` and assert `count` grew by one and one row has `label: calls`.
- **Edit by index.** Run `helpers/control-ilograph cli -- relation edit --file "$D/diagram.yaml" --perspective Runtime --index 1 --label "calls v2"`. Exit code `0`. `relation list --json` shows the first row with the new label; `check --mode strict` exits `0`.
- **Remove by index.** Run `helpers/control-ilograph cli -- relation remove --file "$D/diagram.yaml" --perspective Runtime --index 1`. Exit code `0`. `relation list --json` count drops by one.
- **Reject empty relation.** Run `helpers/control-ilograph cli -- relation add --file "$D/diagram.yaml" --perspective Runtime --label invalid` (no `--from`/`--to`). Exit code `1`, stdout contains `relation must define from or to`; the file is byte-identical to its pre-command state.
- **Reject bad index.** Run `helpers/control-ilograph cli -- relation remove --file "$D/diagram.yaml" --perspective Runtime --index 99`. Exit code `1`, stdout contains `relation index out of range`; the file is unchanged.
- **Proof.** Save transcripts to `$EVIDENCE/relations.transcript.txt`, the `--json` list payloads to `$EVIDENCE/relations.json`, and diffs to `$EVIDENCE/relations.diff.txt`.

## Gotchas

- Indices are one-based and positional: adding or removing shifts later indices. Re-list before every indexed edit in a sequence.
- `--clear-from --clear-to` together is rejected (`relation must define from or to`); that is validation working, not a failure to report.
- `remove-match` with no match is a silent no-op (`no changes`) unless `--require-match` is set, which turns it into an error. Assert the mode you asked for.
- An `add` referencing unknown resources fails closed with `mutation would produce invalid document` plus `broken-reference`, and the file is unchanged. This is the correct end state.
