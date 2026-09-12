---
name: verify-ilograph
description: "Drive and prove the ilograph CLI (Ilograph YAML validate/edit terminal tool). Use whenever changing CLI behavior, ops, validation, or docs, or when asked to verify the app end to end."
---

# Verify ilograph CLI

`ilograph` is a short-lived terminal CLI (Typer app at
`ilograph_cli.cli:main`). It validates and edits Ilograph YAML diagrams.
There is no server, no port, no browser, no auth. Verification means: build
once, then run real subcommands against isolated copies of fixture YAML and
capture the command, the exit code, the output, and the resulting file
state.

Read `.pi/skills/verify-ilograph/features/README.md` before any proof run,
then follow the matching feature file. A proof that drives one convenient
entry point is incomplete when the map lists others.

## Launch

There is no daemon to start. Launch means: install deps once, confirm the
binary answers, then start each drive in its own isolated work directory.

```bash
uv sync
uv run ilograph --help
RUN_ID=run1
WORK=/tmp/ilograph-verify-$RUN_ID/work
EVIDENCE=/tmp/ilograph-verify-$RUN_ID/evidence
mkdir -p "$WORK" "$EVIDENCE"
helpers/control-ilograph fixture tests/golden/rename_id/input.yaml "$WORK" diagram.yaml
```

Ready means: `uv run ilograph --help` exits 0 and prints the command list
(`check`, `apply`, `batch`, `impact`, `resolve`, `fmt`, `rename`, `move`,
`group`, `relation`, `resource`, `perspective`, `context`, `alias`,
`override`, `sequence`, `walkthrough`).

There is nothing to keep alive. Teardown is file cleanup only (see
Cleanup). Never run verification against the only copy of a diagram: always
drive a copy under `/tmp/ilograph-verify-$RUN_ID/work/`.

## Doctor

Run this read-only check first whenever anything looks off. It answers "is
this instance worth driving?"

```bash
.pi/skills/verify-ilograph/helpers/control-ilograph doctor --file "$WORK/diagram.yaml"
```

Doctor asserts:

- `uv run ilograph --help` exits 0.
- `ilograph check --file tests/golden/rename_id/input.yaml` reports
  `check ok` (the repo's known-good fixture validates clean).
- The target `--file` exists and has no sibling `<file>.lock` (a stale lock
  means a previous run died mid-mutation; remove the work dir and
  re-create it from the fixture, never hand-delete a lock next to a real
  user file).
- The `ilograph` entry point resolves to this checkout (`uv run` from the
  repo root), not some other installed copy.

Do not drive a checkout that fails doctor. Fix the base first.

## Drive

The harness is the shell plus disposable YAML files, via the
`control-ilograph` helper. Stable handles, in preference order:

- Resource identifiers: exact `id` first (`--id api`), `name` fallback only
  where the command documents it. `rename resource --id` matches explicit
  `id` only; passing a display name fails with `resource id not found`.
- Rule codes for `check --ignore-rule/--only-rule`
  (`broken-reference`, `duplicate-resource-id`, ...).
- Perspective/context identifiers (`--perspective Runtime`), relation
  one-based `--index` (`--index 1` is the first relation).
- Ops payload `op` names in `apply`/`batch` (`rename.resource`,
  `relation.add`, `move.resource`, ... see `docs/ops.md`).
- `--ref`/`--reference` token strings for `resolve`/`find`, resource ids
  for `impact --resource-id`.

Recipe shape for every drive:

```bash
# 1. Isolate: fresh work dir + fixture copy per drive.
D=$WORK/<feature>; mkdir -p "$D"
helpers/control-ilograph fixture <fixture-src> "$D" diagram.yaml
cp "$D/diagram.yaml" "$D/before.yaml"
# 2. Run the real user command (transcript everything).
helpers/control-ilograph cli -- check --file "$D/diagram.yaml" | tee "$EVIDENCE/<feature>.transcript.txt"
# 3. Prove side effects: diff the file, re-read with a second command.
diff -u "$D/before.yaml" "$D/diagram.yaml" | tee "$EVIDENCE/<feature>.diff.txt"
helpers/control-ilograph cli -- check --file "$D/diagram.yaml" --mode strict | tee -a "$EVIDENCE/<feature>.transcript.txt"
```

Prefer `helpers/control-ilograph cli -- <args>` over bare `uv run
ilograph`: it pins the repo root and fails loudly outside the checkout.
Every flag spelling in the feature map is literal: `--file`, `--mode
strict|ilograph-native`, `--json`, `--dry-run`, `--diff full|summary|none`,
`--ignore-rule`/`--only-rule`, `--no-truncate`, `--resource-id`,
`--perspective`, `--ref`/`--reference`.

Concurrency: drives are isolated by file. Two drives may run side by side
only with different `--file` paths in different work dirs. Never point two
concurrent mutations at the same file: the `<file>.lock` guard will fail
one of them with `file is locked by another command`.

## Evidence

Proof artifacts live under `/tmp/ilograph-verify-$RUN_ID/evidence/` and
survive cleanup. One feature proof contains:

- `<feature>.transcript.txt`: the exact command lines, full stdout, full
  stderr, and exit code for every command in the recipe.
- `<feature>.diff.txt`: unified diff of the diagram before vs after (or an
  explicit `no changes` note for read-only proofs).
- `<feature>.json` (when the recipe uses `--json`): the machine-readable
  payload used for assertions.
- The feature ID and entry point used, recorded as the first lines of the
  transcript.

Proof standards (non-negotiable):

- Exercise the real user path: actual `ilograph <subcommand>` processes
  against a real YAML file. Not `CliRunner` snippets, not internal Python
  setters, not test-only endpoints.
- Capture the action and the resulting state, not just the final screen:
  the command plus the diff plus a read-only second view (`check`,
  `impact`, `relation list`, re-`cat` of the file).
- Verify side effects alongside visible output: files written (diff),
  validation status (`check --mode strict` after a mutation), rows
  inserted/removed (`relation list --json` count before/after).
- Mocks only where a production boundary already isolates the external
  system. This CLI has no network calls; do not mock the filesystem or the
  YAML layer.
- Trust, but verify, `--dry-run`: after any dry-run proof, `diff` the file
  against `before.yaml` and assert byte-identical. A dry-run that writes
  is a bug, regardless of its output saying `dry-run`.

## Cleanup

Remove instances and scratch state, never the evidence.

```bash
# Remove the work dirs this run created. Never kill by process name:
# there is no ilograph daemon, so there is nothing to kill.
rm -rf /tmp/ilograph-verify-$RUN_ID/work
# Confirm the proof survived.
ls -la /tmp/ilograph-verify-$RUN_ID/evidence/
```

Rules:

- Delete only work dirs under `/tmp/ilograph-verify-$RUN_ID/` that this
  run created. Never `rm` a diagram outside the work dir.
- Never `pkill/killall ilograph` or kill by process name. If a runaway
  process holds a work-file lock, kill that PID (captured at spawn time),
  not the name.
- Fixture copies and `<file>.lock` files die with the work dir. Proof
  artifacts under `evidence/` are never deleted by cleanup.
- Run cleanup after every failed iteration too, so broken attempts do not
  strand work dirs.

## Helpers

One executable ships with this skill. Its invocation is shown in every
recipe that needs it; nothing here requires reading the script source.

- `helpers/control-ilograph doctor --file <diagram>` — the Doctor check.
- `helpers/control-ilograph fixture <src> <destdir> [name]` — copy a
  fixture into an isolated dir; prints the new path.
- `helpers/control-ilograph cli -- <ilograph args...>` — run the repo's
  `ilograph` with the repo root pinned; transparent passthrough of args,
  stdout, stderr, and exit code.

```bash
.pi/skills/verify-ilograph/helpers/control-ilograph doctor --file "$WORK/diagram.yaml"
.pi/skills/verify-ilograph/helpers/control-ilograph fixture tests/golden/apply_ops/input.yaml "$WORK/apply"
.pi/skills/verify-ilograph/helpers/control-ilograph cli -- impact --file "$WORK/diagram.yaml" --resource-id db
```
