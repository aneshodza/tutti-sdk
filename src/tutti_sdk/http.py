import json
from collections.abc import Iterator, Mapping
from typing import Any

import httpx

from .errors import TuttiHttpError, TuttiNetworkError
from .session import Session

Query = Mapping[str, str | int | float | bool | None]


class HttpClient:
    """Protocol-agnostic HTTP layer: applies session headers (per request, so
    auth set mid-life takes effect immediately), JSON-encodes bodies, and maps
    failures to typed errors. Shared by GraphQL, REST, and streaming."""

    def __init__(self, client: httpx.Client, base_url: str, api_version: str, session: Session):
        self._client = client
        self._prefix = f"{base_url.rstrip('/')}/{api_version}"
        self._session = session

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        query: Query | None = None,
    ) -> Any:
        """Send a request and parse the JSON body (``None`` if empty)."""
        try:
            res = self._client.send(self._build(method, path, body, headers, query))
        except httpx.HTTPError as e:
            raise TuttiNetworkError(e) from e
        text = res.text
        if res.is_error:
            raise TuttiHttpError(res.status_code, res.reason_phrase, text)
        return json.loads(text) if text else None

    def stream_ndjson(
        self, method: str, path: str, *, query: Query | None = None
    ) -> Iterator[dict[str, Any]]:
        """Open a long-lived response and yield one parsed JSON object per line.
        Closing the generator (e.g. ``break`` out of the loop) closes the connection."""
        req = self._build(method, path, None, None, query)
        try:
            res = self._client.send(req, stream=True)
        except httpx.HTTPError as e:
            raise TuttiNetworkError(e) from e
        try:
            if res.is_error:
                res.read()
                raise TuttiHttpError(res.status_code, res.reason_phrase, res.text)
            try:
                for line in res.iter_lines():
                    line = line.strip()
                    if line:
                        yield json.loads(line)
            except httpx.HTTPError as e:
                raise TuttiNetworkError(e) from e
        finally:
            res.close()

    def _build(
        self,
        method: str,
        path: str,
        body: Any,
        headers: Mapping[str, str] | None,
        query: Query | None,
    ) -> httpx.Request:
        all_headers = {**self._session.build_headers(), **(headers or {})}
        content: str | None = None
        if isinstance(body, str):
            # Pre-encoded body (e.g. form-urlencoded); caller sets Content-Type.
            content = body
        elif body is not None:
            all_headers["Content-Type"] = "application/json; charset=utf-8"
            content = json.dumps(body)
        params = {k: _qs(v) for k, v in (query or {}).items() if v is not None}
        return self._client.build_request(
            method, self._prefix + path, headers=all_headers, content=content, params=params
        )


def _qs(v: str | float | bool) -> str:
    # Match JS String(v) for booleans.
    return ("true" if v else "false") if isinstance(v, bool) else str(v)
