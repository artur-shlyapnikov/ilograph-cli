"""Apply ops.yaml operations transactionally."""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap

from ilograph_cli.core.ops_models import OpsFile
from ilograph_cli.ops.dispatch import apply_ops_batch


def apply_ops(document: CommentedMap, ops_file: OpsFile) -> bool:
    """Apply validated ops sequentially, return True when doc mutated."""

    return apply_ops_batch(document, ops_file.ops)
