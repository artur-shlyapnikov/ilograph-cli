from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ilograph_cli.core.errors import ValidationError
from ilograph_cli.ops.relation_ops import add_relation_many, remove_relations_match_many

_PERSPECTIVE_ID = st.from_regex(r"[A-Z][A-Za-z0-9]{0,4}", fullmatch=True)
_CONTEXT_NAME = st.from_regex(r"[a-z][a-z0-9]{0,6}", fullmatch=True)


def _build_document(
    perspective_ids: list[str],
    context_names: list[str],
) -> CommentedMap:
    resources = CommentedSeq(
        [
            CommentedMap({"id": "app", "name": "App"}),
            CommentedMap({"id": "db", "name": "DB"}),
        ]
    )
    perspectives = CommentedSeq([CommentedMap({"id": item}) for item in perspective_ids])
    contexts = CommentedSeq([CommentedMap({"name": item}) for item in context_names])
    return CommentedMap(
        {
            "resources": resources,
            "perspectives": perspectives,
            "contexts": contexts,
        }
    )


@st.composite
def _relation_case(draw: st.DrawFn) -> tuple[list[str], list[str], list[str], bool]:
    perspective_ids = draw(st.lists(_PERSPECTIVE_ID, min_size=1, max_size=3, unique=True))
    available_contexts = draw(st.lists(_CONTEXT_NAME, min_size=1, max_size=4, unique=True))
    target_contexts = draw(
        st.lists(st.sampled_from(available_contexts), min_size=1, max_size=6)
    )
    use_context_token = draw(st.booleans())
    return perspective_ids, available_contexts, target_contexts, use_context_token


@settings(max_examples=80)
@given(case=_relation_case())
def test_add_many_and_remove_match_many_are_symmetric(
    case: tuple[list[str], list[str], list[str], bool],
) -> None:
    perspective_ids, available_contexts, target_contexts, use_context_token = case
    document = _build_document(perspective_ids, available_contexts)

    template: dict[str, str | bool] = {
        "from": "app",
        "to": "db_{context}" if use_context_token else "db",
    }

    added = add_relation_many(
        document,
        perspectives=perspective_ids,
        contexts=target_contexts,
        template=template,
    )
    expected_per_perspective = len(set(target_contexts)) if use_context_token else 1
    assert added == len(perspective_ids) * expected_per_perspective

    removed = remove_relations_match_many(
        document,
        perspectives=perspective_ids,
        contexts=target_contexts,
        match_template=template,
        require_match=True,
    )
    assert removed == added

    raw_perspectives = document["perspectives"]
    assert isinstance(raw_perspectives, CommentedSeq)
    for perspective in raw_perspectives:
        assert isinstance(perspective, CommentedMap)
        relations = perspective.get("relations")
        assert isinstance(relations, CommentedSeq)
        assert len(relations) == 0


@settings(max_examples=50)
@given(
    perspective_ids=st.lists(_PERSPECTIVE_ID, min_size=1, max_size=3, unique=True),
    context_names=st.lists(_CONTEXT_NAME, min_size=1, max_size=4, unique=True),
)
def test_add_many_rejects_context_template_without_context_target(
    perspective_ids: list[str],
    context_names: list[str],
) -> None:
    document = _build_document(perspective_ids, context_names)
    template: dict[str, str | bool] = {"from": "app", "to": "db_{context}"}

    with pytest.raises(ValidationError, match=r"target\.contexts is not set"):
        add_relation_many(
            document,
            perspectives=perspective_ids,
            contexts=None,
            template=template,
        )
