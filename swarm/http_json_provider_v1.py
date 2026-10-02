#!/usr/bin/env python3
"""Vendor-neutral HTTP JSON information provider adapter."""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


JsonTransport = Callable[[str, Mapping[str, str], int], Any]


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


class HttpJsonProvider:
    """Call a configurable GET endpoint returning JSON search results."""

    def __init__(
        self,
        endpoint: str,
        *,
        source_class: str,
        name: str = "http-json-v1",
        timeout_seconds: int = 20,
        api_key_env: str | None = None,
        transport: JsonTransport | None = None,
    ) -> None:
        endpoint = endpoint.strip()
        if not endpoint:
            raise ValueError("endpoint is required")
        if not source_class.strip():
            raise ValueError("source_class is required")
        self.endpoint = endpoint
        self.name = name.strip() or "http-json-v1"
        self.source_classes = (source_class.strip(),)
        self.timeout_seconds = int(timeout_seconds)
        self.api_key_env = api_key_env
        self._transport = transport

    def _default_transport(
        self,
        url: str,
        headers: Mapping[str, str],
        timeout: int,
    ) -> Any:
        request = Request(url, headers=dict(headers), method="GET")
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _extract_results(payload: Any) -> list[Mapping[str, Any]]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, Mapping)]
        if isinstance(payload, Mapping):
            results = payload.get("results")
            if isinstance(results, list):
                return [x for x in results if isinstance(x, Mapping)]
        raise ValueError("HTTP JSON provider expected a JSON array or {'results': [...]}")

    def search(
        self,
        request: Mapping[str, Any],
        *,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        params = {
            "q": _text(request.get("text")),
            "intent": _text(request.get("intent")).upper(),
            "question_id": _text(request.get("question_id")),
            "max_results": str(int(max_results)),
        }
        target_difference = _text(request.get("target_difference"))
        if target_difference:
            params["target_difference"] = target_difference

        query_url = f"{self.endpoint}{'&' if '?' in self.endpoint else '?'}{urlencode(params)}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "UFCPS-Information-Provider/1.0",
        }
        if self.api_key_env:
            api_key = os.environ.get(self.api_key_env, "").strip()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

        transport = self._transport or self._default_transport
        try:
            payload = transport(query_url, headers, self.timeout_seconds)
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"HTTP information provider failed: {exc}") from exc

        return [dict(item) for item in self._extract_results(payload)[:max_results]]
