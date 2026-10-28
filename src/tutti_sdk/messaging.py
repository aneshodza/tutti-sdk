import uuid
from collections.abc import Iterator
from typing import Any, cast
from urllib.parse import urlencode

from .http import HttpClient
from .types import Conversation, Message


class MessagingResource:
    """Messaging / chat. Live feeds are NDJSON-over-HTTP streams exposed as
    generators (backlog first, then live updates); sends are plain POSTs.
    Requires an authenticated session."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def stream_conversations(self) -> Iterator[Conversation]:
        """Live stream of conversations. Yields a full conversation on every change
        (initial backlog, then updates) — keep your own dict keyed by ``id``.
        Runs until you stop iterating or the server closes."""
        for frame in self._http.stream_ndjson("GET", "/messaging/stream/conversations"):
            for conv in (frame.get("data") or {}).values():
                yield cast(Conversation, conv)

    def stream_messages(self, conversation_id: str, offset: int = 0) -> Iterator[Message]:
        """Live stream of messages in a conversation. Yields backlog (from
        ``offset``, ordered by offset) then new messages as they arrive."""
        frames = self._http.stream_ndjson(
            "GET",
            f"/messaging/stream/conversations/{conversation_id}/messages",
            query={"offset": offset},
        )
        for frame in frames:
            batch = list((frame.get("data") or {}).values())
            batch.sort(key=lambda m: m.get("offset") or 0)
            yield from batch

    def send(self, conversation_id: str, text: str) -> Message:
        """Send a text message. Returns the created message (with server offset)."""
        return self._http.request(
            "POST",
            f"/messaging/conversations/{conversation_id}/messages",
            body={"id": str(uuid.uuid4()), "type": "text", "payload": text},
        )

    def mark_read(self, conversation_id: str, offset: int) -> None:
        """Mark the conversation read up to (and including) ``offset``."""
        self._http.request(
            "POST",
            f"/messaging/conversations/{conversation_id}/receipt",
            body={"offset": offset},
        )

    def reply(
        self, item_id: str, name: str, email: str, body: str, cc: bool = False
    ) -> dict[str, Any]:
        """Start a conversation by replying to a listing. Does NOT return a
        conversation id — discover it via ``stream_conversations``.
        Returns ``{"message": ..., "publicAccountId": ...}``."""
        form = urlencode(
            {
                "item_id": item_id,
                "cc": "true" if cc else "false",
                "name": name,
                "email": email,
                "body": body,
            }
        )
        return self._http.request(
            "POST",
            "/item/reply.json",
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
            body=form,
        )
