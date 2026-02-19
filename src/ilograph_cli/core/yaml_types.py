"""Core YAML node typing helpers."""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap, CommentedSeq

type YamlScalar = str | int | float | bool | None
type YamlNode = CommentedMap | CommentedSeq | YamlScalar
