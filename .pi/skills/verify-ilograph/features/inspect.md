# Inspection and formatting

Inspection commands explain where a resource is used and how reference tokens resolve, list collection contents, and check formatting without changing the diagram.

## Sub-features

- `inspect-impact` shows every section where a resource id is referenced.
- `inspect-resolve` explains per-token resolution (`resolved`, `alias`, `unresolved`, `wildcard`) for a perspective.
- `inspect-lists` enumerates perspectives, contexts, aliases, overrides, sequences, and walkthroughs (`* list`, alias `* ls`).
- `inspect-fmt` checks stable formatting (`fmt --stable`, `--dry-run`) and reports `no changes` when clean.

## How to get to it (user POV)

- Run `ilograph impact --file diagram.yaml --resource-id api` to see where a resource is used.
- Run `ilograph resolve --file diagram.yaml --ref "app,db" --perspective Runtime` (or `find`, which is the same inspection under a second name) to explain token resolution.
- Run `ilograph relation list --file diagram.yaml --perspective Runtime --json` and the sibling `perspective list`, `context list`, `alias list`, `override list`, `sequence list`, `walkthrough list` commands.
- Run `ilograph fmt --file diagram.yaml --stable` to check formatting.

## Driving it with control-ilograph

Preconditions:

- `helpers/control-ilograph doctor --file "$D/diagram.yaml"` reports all checks passed.
- Work dir holds a copy of `tests/golden/rename_id/input.yaml` as `diagram.yaml`.

- **Impact.** Run `helpers/control-ilograph cli -- impact --file "$D/diagram.yaml" --resource-id db`. Exit code `0`, stdout contains `Impact for db` and `relations`. Re-run with `--json`, parse stdout, and assert `resourceId` is `db`, `count` is `> 0`, and at least one hit has `section` `relations`.
- **Resolve tokens.** Run `helpers/control-ilograph cli -- resolve --file "$D/diagram.yaml" --reference "backend,missing" --perspective Runtime --json`. Exit code `0`; parse stdout and assert `rows` contains an `alias` status (for `backend`, which aliases `app,db`) and an `unresolved` status (for `missing`).
- **Find parity.** Run `helpers/control-ilograph cli -- find --file "$D/diagram.yaml" --perspective Runtime --reference "backend"`. Exit code `0` and stdout mentions `alias`.
- **Unknown perspective.** Run `helpers/control-ilograph cli -- resolve --file "$D/diagram.yaml" --reference "app" --perspective MissingPerspective`. Exit code `1` with `perspective not found: MissingPerspective`.
- **Collection lists.** Run `helpers/control-ilograph cli -- perspective list --file "$D/diagram.yaml" --json` and `helpers/control-ilograph cli -- alias list --file "$D/diagram.yaml" --perspective Runtime --json`. Both exit `0` with `count >= 1`; every collection also answers to `ls` (e.g. `relation ls`).
- **Stable format noop.** Run `helpers/control-ilograph cli -- fmt --file "$D/diagram.yaml" --stable --dry-run`. Exit code `0` with `no changes`; `diff -u` against `before.yaml` is empty. (The stable formatter currently only reports; a `no changes` result on an unmodified fixture is the correct end state.)
- **Proof.** Save transcripts to `$EVIDENCE/inspect.transcript.txt`, JSON payloads to `$EVIDENCE/inspect.json`, and note the `diff`-empty formatting assertion in the transcript.

## Gotchas

- `resolve` needs `--perspective` for alias-aware statuses; without it, alias tokens report differently. Always pass the perspective in proofs.
- `--ref` and `--reference` are the same flag; `--resource-id` (impact) is not interchangeable with `--id` (mutation commands).
- Long outputs truncate. Add `--no-truncate` when asserting on full token lists, and `--json` when asserting on structure.
- Inspection commands never write, but assert it anyway: a stray `diff` after the recipe costs nothing and catches regressions.
- `fmt --stable` without `--dry-run` rewrites the file through the round-trip emitter even when content is unchanged in meaning; drive formatting proofs with `--dry-run` unless the recipe explicitly targets the write path.
