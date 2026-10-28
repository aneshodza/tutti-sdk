import json
from collections.abc import Callable

import httpx
import pytest

from tutti_sdk import TuttiClient

Handler = Callable[[httpx.Request], httpx.Response]


class Recorder:
    """MockTransport wrapper that records every request it sees."""

    def __init__(self, handler: Handler) -> None:
        self.requests: list[httpx.Request] = []
        self._handler = handler
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        request.read()
        self.requests.append(request)
        return self._handler(request)

    def json(self, i: int = -1) -> dict:
        return json.loads(self.requests[i].content)


@pytest.fixture
def mock_client() -> Callable[[Handler], tuple[TuttiClient, Recorder]]:
    def make(handler: Handler, **kwargs) -> tuple[TuttiClient, Recorder]:
        rec = Recorder(handler)
        return TuttiClient(transport=rec.transport, **kwargs), rec

    return make
