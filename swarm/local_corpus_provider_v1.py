#!/usr/bin/env python3
"""Deterministic local-corpus information provider for UFCPS."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".rst", ".py", ".json", ".yaml", ".yml", ".toml",
}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _terms(value: str) -> list[str]:
    return list(dict.fromkeys(
        token.lower()
        for token in re.findall(r"[A-Za-z0-9_]{3,}", value)
        if token.lower() not in {
            "the", "and", "for", "with", "from", "that", "this",
            "what", "how", "which", "into", "are", "was", "not",
        }
    ))


class LocalCorpusProvider:
    """Search a local text corpus using deterministic term scoring."""

    name = "local-corpus-v1"
    source_classes = ("internal_corpus",)

    def __init__(
        self,
        root: str | Path,
        *,
        suffixes: Sequence[str] = tuple(sorted(DEFAULT_SUFFIXES)),
        max_file_bytes: int = 2_000_000,
    ) -> None:
        self.root = Path(root)
        self.suffixes = {str(x).lower() for x in suffixes}
        self.max_file_bytes = int(max_file_bytes)

    def _files(self) -> list[Path]:
        if self.root.is_file():
            return [self.root]
        if not self.root.exists():
            return []
        return sorted(
            path for path in self.root.rglob("*")
            if path.is_file() and (
                not self.suffixes or path.suffix.lower() in self.suffixes
            )
        )

    @staticmethod
    def _snippet(content: str, terms: Sequence[str], width: int = 280) -> str:
        lowered = content.lower()
        positions = [lowered.find(term.lower()) for term in terms]
        positions = [p for p in positions if p >= 0]
        start = max(0, min(positions) - 90) if positions else 0
        snippet = content[start:start + width].replace("\x00", " ")
        return " ".join(snippet.split())

    @staticmethod
    def _relevance(score: int) -> str:
        if score >= 5:
            return "HIGH"
        if score >= 3:
            return "MEDIUM"
        if score >= 1:
            return "LOW"
        return "UNKNOWN"

    def search(
        self,
        request: Mapping[str, Any],
        *,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        query = " ".join([
            _text(request.get("text")),
            _text(request.get("target_difference")),
        ])
        terms = _terms(query)
        if not terms:
            return []

        scored: list[tuple[int, Path, str]] = []
        for path in self._files():
            try:
                if path.stat().st_size > self.max_file_bytes:
                    continue
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lowered = content.lower()
            score = sum(lowered.count(term) for term in terms)
            filename = path.name.lower()
            score += sum(1 for term in terms if term in filename)
            if score > 0:
                scored.append((score, path, content))

        scored.sort(key=lambda item: (-item[0], str(item[1])))
        results: list[dict[str, Any]] = []
        for score, path, content in scored[:max_results]:
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            results.append({
                "locator": path.resolve().as_uri(),
                "content_reference": f"sha256:{digest}",
                "title": path.name,
                "snippet": self._snippet(content, terms),
                "relevance": self._relevance(score),
                "source": {
                    "name": self.name,
                    "type": "internal_corpus",
                    "path": str(path.resolve()),
                },
                "metadata": {
                    "score": score,
                    "term_count": len(terms),
                },
            })
        return results
