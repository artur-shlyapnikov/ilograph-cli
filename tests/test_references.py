from __future__ import annotations

from ilograph_cli.core.references import extract_reference_tokens, split_reference_list


def test_split_reference_list_does_not_split_commas_inside_fn_calls() -> None:
    parts = split_reference_list("fn(a,b), Resource A, ../fn2(x,y)")
    assert parts == ["fn(a,b)", "Resource A", "../fn2(x,y)"]


def test_extract_reference_tokens_keeps_spaces_paths_and_parentheses() -> None:
    tokens = extract_reference_tokens("API Gateway/api.ilograph.com, handleDiagram()")
    assert "API Gateway" in tokens
    assert "api.ilograph.com" in tokens
    assert "handleDiagram()" in tokens


def test_extract_reference_tokens_strips_clone_suffix_and_skips_wildcards() -> None:
    tokens = extract_reference_tokens("Resource A *2, [Port *], ../Load Balancer")
    assert "Resource A" in tokens
    assert "Load Balancer" in tokens
    assert "Port *" not in tokens
