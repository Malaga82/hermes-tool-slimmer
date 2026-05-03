from __future__ import annotations

from typing import Iterable

from .bm25 import BM25
from .config import ToolSlimmerConfig
from .corpus import build_corpus, tool_name, tool_toolset
from .tokenizer import tokenize
from .toolsets import is_mcp_schema
from .types import Schema, SelectionResult, ToolDocument


class ToolSelector:
    def __init__(self, config: ToolSlimmerConfig | None = None) -> None:
        self.config = config or ToolSlimmerConfig()

    def select(self, user_message: str, schemas: list[Schema], **_: object) -> SelectionResult:
        if not self.config.enabled or self.config.mode == "eager":
            return SelectionResult(self.config.mode, schemas, [tool_name(s) for s in schemas], {}, len(schemas), [])
        try:
            return self._select_keyword(user_message, schemas)
        except Exception as exc:
            if self.config.fail_open:
                return SelectionResult(self.config.mode, schemas, [tool_name(s) for s in schemas], {}, len(schemas), [], fail_open=True, reason=str(exc))
            raise

    def _eligible(self, schemas: Iterable[Schema]) -> list[Schema]:
        disabled = set(self.config.disabled_tools)
        disabled_toolsets = set(self.config.disabled_toolsets)
        out = []
        for schema in schemas:
            name = tool_name(schema)
            toolset = tool_toolset(schema)
            if name in disabled or (toolset and toolset in disabled_toolsets):
                continue
            is_mcp = is_mcp_schema(schema)
            if is_mcp and not self.config.include_mcp_tools:
                continue
            if not is_mcp and not self.config.include_native_tools:
                continue
            out.append(schema)
        return out

    def _select_keyword(self, user_message: str, schemas: list[Schema]) -> SelectionResult:
        eligible = self._eligible(schemas)
        docs = build_corpus(eligible)
        query_tokens = tokenize(user_message)
        bm25 = BM25([doc.tokens for doc in docs])
        raw_scores = bm25.scores(query_tokens)
        scores = {doc.name: score + self._boost(query_tokens, doc) for doc, score in zip(docs, raw_scores, strict=True)}

        by_name = {tool_name(schema): schema for schema in eligible}
        selected: list[Schema] = []
        selected_names: set[str] = set()
        always_present: list[str] = []
        for name in self.config.always_include:
            if name in by_name and name not in selected_names:
                selected.append(by_name[name])
                selected_names.add(name)
                always_present.append(name)

        remaining_slots = self.config.top_k
        ranked = sorted(docs, key=lambda doc: (scores.get(doc.name, 0.0), doc.name), reverse=True)
        for doc in ranked:
            if remaining_slots <= 0:
                break
            if doc.name in selected_names:
                continue
            if scores.get(doc.name, 0.0) <= 0 and selected:
                continue
            selected.append(by_name[doc.name])
            selected_names.add(doc.name)
            remaining_slots -= 1

        if not selected and eligible and self.config.fail_open:
            return SelectionResult(self.config.mode, schemas, [tool_name(s) for s in schemas], scores, len(schemas), always_present, fail_open=True, reason="selector produced empty set")
        return SelectionResult(self.config.mode, selected, [tool_name(s) for s in selected], scores, len(schemas), always_present)

    @staticmethod
    def _boost(query_tokens: list[str], doc: ToolDocument) -> float:
        query = set(query_tokens)
        boost = 0.0
        normalized_name = doc.name.lower()
        if normalized_name in " ".join(query_tokens) or normalized_name.replace("_", " ") in " ".join(query_tokens):
            boost += 10.0
        if doc.toolset and set(tokenize(doc.toolset)) & query:
            boost += 2.5
        boost += 1.25 * len(doc.parameter_tokens & query)
        return boost


def select_schemas(user_message: str, schemas: list[Schema], config: ToolSlimmerConfig | None = None, **kwargs: object) -> list[Schema]:
    return ToolSelector(config).select(user_message, schemas, **kwargs).selected
