"""Live tests that need a logged-in session. Run with ``pytest -m live``.

The session comes from TUTTI_TOKEN, or from ./.tutti-sessions/<TUTTI_SESSION or
"default">.json (written by ``examples/login.py``). Skipped when neither exists.

Read-only on purpose: sending messages, read receipts and listing replies are
visible to other tutti users, so those are only covered by the mocked tests.
"""

import os
import threading
from pathlib import Path

import pytest

from tutti_sdk import AuthState, FileSessionStore, Session, TuttiClient

pytestmark = [pytest.mark.live, pytest.mark.auth]

SESSIONS = Path(__file__).resolve().parents[1] / ".tutti-sessions"


def load_session() -> Session | None:
    if token := os.environ.get("TUTTI_TOKEN"):
        s = Session()
        s.set_auth(AuthState(token=token, account_id=os.environ.get("TUTTI_ACCOUNT_ID")))
        return s
    snap = FileSessionStore(SESSIONS).load(os.environ.get("TUTTI_SESSION", "default"))
    return Session.from_dict(snap) if snap else None


@pytest.fixture
def client():
    session = load_session()
    if not session or not session.is_authenticated:
        pytest.skip("no authenticated session (run examples/login.py or set TUTTI_TOKEN)")
    with TuttiClient(session) as c:
        yield c


def take(client: TuttiClient, gen, n: int, timeout: float = 10.0) -> list:
    """Collect up to ``n`` items from a live stream, giving up after ``timeout``
    (the stream stays open forever once the backlog is sent)."""
    items, errors = [], []

    def run():
        try:
            for item in gen:
                items.append(item)
                if len(items) >= n:
                    break
        except Exception as e:  # noqa: BLE001 — surfaced below unless we aborted it
            errors.append(e)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    aborted = t.is_alive()
    if aborted:
        client.close()  # unblocks the reader thread
        t.join(5)
    if errors and not aborted:
        raise errors[0]
    return items


def test_profile(client):
    profile = client.account.profile()
    assert isinstance(profile, dict) and profile


def test_stream_conversations(client):
    convs = take(client, client.messaging.stream_conversations(), n=1)
    for conv in convs:
        assert conv["id"]


def test_stream_messages_backlog(client):
    convs = take(client, client.messaging.stream_conversations(), n=1)
    if not convs:
        pytest.skip("account has no conversations")
    with TuttiClient(client.session) as c2:
        msgs = take(c2, c2.messaging.stream_messages(convs[0]["id"]), n=3)
    assert msgs, "expected at least one message in an existing conversation"
    offsets = [m["offset"] for m in msgs]
    assert offsets == sorted(offsets)
    assert all(m["senderPublicAccountId"] for m in msgs)
