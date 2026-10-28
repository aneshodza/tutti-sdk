"""Offline tests against a mocked transport — no network."""

import base64
import json
import struct
import zlib
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from tutti_sdk import (
    AuthState,
    FileSessionStore,
    InMemorySessionStore,
    LLMCaptchaProvider,
    Session,
    TuttiAuthError,
    TuttiGraphQLError,
    TuttiHttpError,
    TuttiNetworkError,
    TuttiValidationError,
    parse_data_uri,
    render_svg_to_png,
)
from tutti_sdk.login import pkce_challenge
from tutti_sdk.operations import SEARCH_LISTINGS_BY_QUERY, SEARCH_LISTINGS_BY_TOKEN, UPDATE_FILTERS


def gql(root_field: str, value) -> httpx.Response:
    return httpx.Response(200, json={"data": {root_field: value}})


def page(ids: list[str], next_cursor: str | None, total: int = 3) -> dict:
    return {
        "listings": {
            "totalCount": total,
            "edges": [{"node": {"listingID": i, "title": f"t{i}"}} for i in ids],
            "pageInfo": {"hasNextPage": next_cursor is not None, "endCursor": next_cursor},
        },
        "filters": [{"__typename": "ListingPricingFilter", "name": "price", "label": "Preis"}],
        "searchToken": "TOKEN",
    }


# ---- transport / headers / errors ----


def test_graphql_request_shape_and_session_headers(mock_client):
    client, rec = mock_client(lambda r: gql("searchLocalities", [{"localityID": "x", "name": "X"}]))
    client.session.language = "fr"

    assert client.localities.search("zür") == [{"localityID": "x", "name": "X"}]

    req = rec.requests[0]
    assert str(req.url) == "https://api.tutti.ch/v10/graphql"
    assert req.method == "POST"
    assert req.headers["X-APOLLO-OPERATION-NAME"] == "SearchLocalities"
    assert req.headers["X-Tutti-Hash"] == client.session.tutti_hash
    assert req.headers["User-Agent"] == "ch.tutti/android (Google Pixel 7a, OS 16)"
    assert req.headers["Accept-Language"] == "fr"
    assert req.headers["Content-Type"] == "application/json; charset=utf-8"
    assert "X-Tutti-Auth" not in req.headers
    body = rec.json()
    assert body["operationName"] == "SearchLocalities"
    assert body["query"].startswith("query SearchLocalities(")
    assert body["variables"] == {"search": "zür", "excludeIds": []}


def test_auth_header_applied_after_use_token(mock_client):
    client, rec = mock_client(lambda r: httpx.Response(200, json={"ok": True}))
    client.account.use_token("tok123", "acc1")
    assert client.account.profile() == {"ok": True}
    assert rec.requests[0].headers["X-Tutti-Auth"] == "tok123"
    assert str(rec.requests[0].url) == "https://api.tutti.ch/v10/account/profile.json"
    client.account.logout()
    client.account.profile()
    assert "X-Tutti-Auth" not in rec.requests[1].headers


def test_graphql_errors_raise(mock_client):
    client, _ = mock_client(
        lambda r: httpx.Response(200, json={"errors": [{"message": "boom"}], "data": None})
    )
    with pytest.raises(TuttiGraphQLError) as e:
        client.categories.tree()
    assert e.value.operation == "Categories"
    assert e.value.errors == [{"message": "boom"}]


def test_http_errors_raise(mock_client):
    client, _ = mock_client(lambda r: httpx.Response(422, text="nope"))
    with pytest.raises(TuttiHttpError) as e:
        client.categories.tree()
    assert e.value.status == 422
    assert e.value.body == "nope"


def test_network_errors_raise(mock_client):
    def boom(r):
        raise httpx.ConnectError("dns fail")

    client, _ = mock_client(boom)
    with pytest.raises(TuttiNetworkError):
        client.categories.tree()


# ---- search builder ----


def test_search_variables_and_constraints(mock_client):
    client, rec = mock_client(lambda r: gql("searchListingsByQuery", page(["1"], None)))
    zurich = {"localityID": "geo-city-zurich", "name": "Zürich"}

    (
        client.search("sofa")
        .category("furniture")
        .price(min=100, max=500)
        .location(zurich)
        .radius(10)
        .interval("year", min=2015)
        .select("companyAd", "private")
        .multi_select("language", ["de", "fr"])
        .sort("timestamp", "asc")
        .image_height(300)
        .fetch()
    )

    body = rec.json()
    assert body["operationName"] == SEARCH_LISTINGS_BY_QUERY.name
    assert body["variables"] == {
        "cursor": None,
        "sort": "TIMESTAMP",
        "direction": "ASCENDING",
        "imageHeight": 300,
        "includePlacements": False,
        "includeExtraInfo": True,
        "placementsVariant": None,
        "categoryId": "furniture",
        "query": "sofa",
        "constraints": {
            "intervals": [{"key": "year", "min": 2015}],
            "locations": [{"key": "location", "localities": ["geo-city-zurich"], "radius": 10}],
            "prices": [{"key": "price", "freeOnly": False, "min": 100, "max": 500}],
            "strings": [
                {"key": "companyAd", "value": ["private"]},
                {"key": "language", "value": ["de", "fr"]},
            ],
        },
    }


def test_free_only_and_defaults(mock_client):
    client, rec = mock_client(lambda r: gql("searchListingsByQuery", page([], None, 0)))
    client.search().free_only().fetch()
    v = rec.json()["variables"]
    assert v["query"] is None and v["categoryId"] is None
    assert v["direction"] == "DESCENDING" and v["imageHeight"] == 630
    assert v["constraints"]["prices"] == [{"key": "price", "freeOnly": True}]


def test_browse_by_token(mock_client):
    client, rec = mock_client(lambda r: gql("searchListingsByToken", page(["9"], None, 1)))
    result = client.browse("Ak8CkY2Fyc5TAwMDA").fetch()
    body = rec.json()
    assert body["operationName"] == SEARCH_LISTINGS_BY_TOKEN.name
    assert body["variables"]["token"] == "Ak8CkY2Fyc5TAwMDA"
    assert body["variables"]["placementsVariant"] == "SMG"
    assert "constraints" not in body["variables"]
    assert [listing["listingID"] for listing in result.listings] == ["9"]


def test_update_filters(mock_client):
    client, rec = mock_client(lambda r: gql("searchListingsByQuery", {"filters": []}))
    client.search().category("cars").update_filters()
    body = rec.json()
    assert body["operationName"] == UPDATE_FILTERS.name
    assert set(body["variables"]) == {"categoryId", "query", "constraints"}


@pytest.mark.parametrize(
    "build",
    [
        lambda b: b.price(min=10, max=5),
        lambda b: b.interval("year", min=2020, max=2010),
    ],
)
def test_validation(mock_client, build):
    client, _ = mock_client(lambda r: httpx.Response(500))
    with pytest.raises(TuttiValidationError):
        build(client.search("x"))


def test_pagination(mock_client):
    pages = {None: page(["1", "2"], "c1"), "c1": page(["3"], None)}

    def handler(r):
        return gql("searchListingsByQuery", pages[json.loads(r.content)["variables"]["cursor"]])

    client, rec = mock_client(handler)
    first = client.search("x").fetch()
    assert first.total_count == 3
    assert first.has_next_page
    assert first.search_token == "TOKEN"
    assert [f["name"] for f in first.available_filters] == ["price"]
    assert [listing["listingID"] for listing in first.paginate()] == ["1", "2", "3"]
    assert len(rec.requests) == 2
    last = first.next()
    assert last is not None and last.next() is None


# ---- sessions ----


def test_session_roundtrip_is_ts_compatible():
    s = Session(language="it", auth=AuthState(token="t", account_id="a"))
    snap = s.to_dict()
    assert snap["tuttiHash"] == s.tutti_hash
    assert snap["app"]["clientId"] == "android/11.0.0+env-live.git-a9330101d"
    assert snap["auth"] == {"token": "t", "accountId": "a"}
    restored = Session.from_dict(json.loads(json.dumps(snap)))
    assert restored == s
    assert restored.build_headers() == s.build_headers()


def test_session_from_ts_snapshot():
    # Exactly what the TS FileSessionStore writes.
    ts = {
        "tuttiHash": "h",
        "app": {"version": "v", "source": "s", "clientId": "c", "appId": "", "userAgent": "ua"},
        "language": "de",
        "auth": {"token": "tok", "accountId": "42"},
    }
    s = Session.from_dict(ts)
    assert s.is_authenticated and s.auth.account_id == "42"
    assert s.build_headers()["User-Agent"] == "ua"
    assert s.to_dict() == ts


def test_in_memory_store_copies():
    store = InMemorySessionStore()
    snap = Session().to_dict()
    store.save("a", snap)
    snap["language"] = "xx"
    assert store.load("a")["language"] == "de"
    assert store.keys() == ["a"]
    store.delete("a")
    assert store.load("a") is None


def test_file_store(tmp_path):
    store = FileSessionStore(tmp_path / "sessions")
    assert store.keys() == []
    assert store.load("missing") is None
    store.save("alice@x.ch/1", Session().to_dict())
    assert (tmp_path / "sessions" / "alice%40x.ch%2F1.json").exists()
    assert store.keys() == ["alice@x.ch/1"]
    assert Session.from_dict(store.load("alice@x.ch/1"))
    store.delete("alice@x.ch/1")
    store.delete("alice@x.ch/1")  # no-op
    assert store.keys() == []


# ---- messaging ----


def test_stream_messages_parses_ndjson_and_sorts(mock_client):
    frames = [
        {
            "event": "messages",
            "data": {"b": {"id": "b", "offset": 2}, "a": {"id": "a", "offset": 1}},
        },
        {"event": "messages", "data": {"c": {"id": "c", "offset": 3}}},
    ]
    raw = "".join(json.dumps(f) + "\n\n" for f in frames).encode()
    # Split mid-line to exercise buffering across chunk boundaries.
    chunks = [raw[:17], raw[17:60], raw[60:]]

    def handler(r):
        return httpx.Response(200, stream=httpx.ByteStream(b"".join(chunks)))

    client, rec = mock_client(handler)
    msgs = list(client.messaging.stream_messages("conv1", offset=5))
    assert [m["id"] for m in msgs] == ["a", "b", "c"]
    assert str(rec.requests[0].url).endswith(
        "/v10/messaging/stream/conversations/conv1/messages?offset=5"
    )


def test_stream_conversations(mock_client):
    frame = {"data": {"x": {"id": "x"}, "y": {"id": "y"}}}
    client, _ = mock_client(lambda r: httpx.Response(200, content=json.dumps(frame).encode()))
    assert [c["id"] for c in client.messaging.stream_conversations()] == ["x", "y"]


def test_stream_http_error(mock_client):
    client, _ = mock_client(lambda r: httpx.Response(401, text="unauthorized"))
    with pytest.raises(TuttiHttpError) as e:
        list(client.messaging.stream_conversations())
    assert e.value.status == 401


def test_send_mark_read_reply(mock_client):
    client, rec = mock_client(lambda r: httpx.Response(200, json={"ok": 1}))
    client.messaging.send("c1", "Hallo")
    body = rec.json()
    assert body["type"] == "text" and body["payload"] == "Hallo" and len(body["id"]) == 36
    assert rec.requests[0].url.path == "/v10/messaging/conversations/c1/messages"

    client.messaging.mark_read("c1", 7)
    assert rec.json() == {"offset": 7}
    assert rec.requests[1].url.path == "/v10/messaging/conversations/c1/receipt"

    client.messaging.reply("123", "Anes", "a@b.ch", "Noch da?")
    req = rec.requests[2]
    assert req.headers["Content-Type"].startswith("application/x-www-form-urlencoded")
    assert parse_qs(req.content.decode()) == {
        "item_id": ["123"],
        "cc": ["false"],
        "name": ["Anes"],
        "email": ["a@b.ch"],
        "body": ["Noch da?"],
    }


# ---- captcha / svg ----


def test_parse_data_uri():
    c = parse_data_uri("data:image/svg+xml;base64," + base64.b64encode(b"<svg/>").decode())
    assert c.data == b"<svg/>" and c.content_type == "image/svg+xml"
    c = parse_data_uri("data:image/svg+xml,%3Csvg%2F%3E")
    assert c.data == b"<svg/>"
    with pytest.raises(ValueError):
        parse_data_uri("not-a-data-uri")


def decode_png(png: bytes) -> tuple[int, int, list[bytes]]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos : pos + 4])
        kind = png[pos + 4 : pos + 8]
        data = png[pos + 8 : pos + 8 + length]
        (crc,) = struct.unpack(">I", png[pos + 8 + length : pos + 12 + length])
        assert crc == zlib.crc32(kind + data)
        if kind == b"IHDR":
            w, h = struct.unpack(">II", data[:8])
            assert data[8:10] == b"\x08\x00"  # 8-bit grayscale
        elif kind == b"IDAT":
            idat += data
        pos += 12 + length
    raw = zlib.decompress(idat)
    rows = [raw[y * (w + 1) + 1 : (y + 1) * (w + 1)] for y in range(h)]
    return w, h, rows


SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="150" height="50" viewBox="0,0,150,50">'
    '<path d="M10 10 L60 10 L60 40 L10 40 Z" fill="#333"/>'
    '<path d="M70 45 Q 100 0 140 45" stroke="#111" stroke-width="2" fill="none"/>'
    '<path d="M80 5 h10 v10 h-10 z" fill="none"/>'
    "</svg>"
)


def test_render_svg_to_png():
    w, h, rows = decode_png(render_svg_to_png(SVG))
    assert (w, h) == (450, 150)
    px = lambda x, y: rows[int(y * 3)][int(x * 3)]
    assert px(35, 25) == 0  # inside the filled rectangle
    assert px(5, 5) == 255  # background
    assert px(85, 10) == 255  # fill="none" path isn't painted
    assert px(70.2, 44.8) < 128  # stroke start of the quadratic curve
    assert px(105, 30) == 255  # under the curve, not filled


def test_llm_captcha_provider_rasterizes_and_retries(monkeypatch):
    monkeypatch.setattr("tutti_sdk.captcha.time.sleep", lambda s: None)
    calls = []

    def handler(r: httpx.Request) -> httpx.Response:
        calls.append(json.loads(r.content))
        assert r.headers["x-goog-api-key"] == "k"
        assert r.url.path == "/v1beta/models/gemini-3.1-flash-lite:generateContent"
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": " The text is: aB3xY9\n"}]}}]}
        )

    provider = LLMCaptchaProvider(
        api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    challenge = parse_data_uri(
        "data:image/svg+xml;base64," + base64.b64encode(SVG.encode()).decode()
    )
    assert provider.solve(challenge) == "aB3xY9"
    assert len(calls) == 2
    inline = calls[1]["contents"][0]["parts"][0]["inline_data"]
    assert inline["mime_type"] == "image/png"
    assert base64.b64decode(inline["data"])[:4] == b"\x89PNG"


def test_llm_captcha_provider_needs_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(TuttiAuthError):
        LLMCaptchaProvider().solve(parse_data_uri("data:image/png;base64,AAAA"))


# ---- login flow ----


def test_pkce_rfc7636_vector():
    assert (
        pkce_challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")
        == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    )


class FakeAuth0:
    """Simulates auth.tutti.ch's redirect chain plus api.tutti.ch's JWT exchange."""

    def __init__(self, accept_captcha: str = "SOLVED") -> None:
        self.accept_captcha = accept_captcha
        self.authorize_params: dict[str, str] = {}
        self.posted_form: dict[str, list[str]] = {}
        self.token_body: dict = {}
        self.jwt_auth: str | None = None

    def __call__(self, r: httpx.Request) -> httpx.Response:
        host, path = r.url.host, r.url.path
        if host == "auth.tutti.ch" and path == "/authorize":
            self.authorize_params = dict(r.url.params)
            return httpx.Response(
                302,
                headers={"Location": "/u/login?state=LOGIN", "Set-Cookie": "auth0=sess; Path=/"},
            )
        if host == "auth.tutti.ch" and path == "/u/login" and r.method == "GET":
            assert "auth0=sess" in r.headers.get("cookie", "")
            svg = base64.b64encode(SVG.encode()).decode()
            html = (
                '<form><input type="hidden" name="state" value="FORM">'
                f'<img alt="captcha" class="c" src="data:image/svg+xml;base64,{svg}"></form>'
            )
            return httpx.Response(200, text=html)
        if host == "auth.tutti.ch" and path == "/u/login" and r.method == "POST":
            assert "auth0=sess" in r.headers.get("cookie", "")
            self.posted_form = parse_qs(r.content.decode())
            if self.posted_form["captcha"] != [self.accept_captcha]:
                return httpx.Response(302, headers={"Location": "/u/login?state=LOGIN&error=1"})
            return httpx.Response(302, headers={"Location": "/authorize/resume?state=FORM"})
        if host == "auth.tutti.ch" and path == "/authorize/resume":
            cb = (
                "ch.tutti://auth.tutti.ch/android/ch.tutti/callback?code=THECODE"
                f"&state={self.authorize_params['state']}"
            )
            return httpx.Response(302, headers={"Location": cb})
        if host == "auth.tutti.ch" and path == "/oauth/token":
            self.token_body = json.loads(r.content)
            return httpx.Response(
                200,
                json={"access_token": "JWT", "token_type": "Bearer", "expires_in": 86400},
            )
        if host == "api.tutti.ch" and path == "/v10/account/authenticateJWT":
            self.jwt_auth = r.headers.get("authorization")
            return httpx.Response(
                200, json={"message": "ok", "public_account_id": "777", "token": "SESSION"}
            )
        raise AssertionError(f"unexpected request {r.method} {r.url}")


class FixedCaptcha:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.seen = None

    def solve(self, challenge):
        self.seen = challenge
        return self.answer


def test_login_flow(mock_client):
    fake = FakeAuth0()
    client, _ = mock_client(fake)
    captcha = FixedCaptcha("SOLVED")

    account = client.account.login("user@x.ch", "pw", captcha=captcha)

    assert captcha.seen.content_type == "image/svg+xml"
    assert fake.authorize_params["client_id"] == "lykoMeGKh14siOyOVev0QBAB8vsSKV7b"
    assert fake.authorize_params["code_challenge_method"] == "S256"
    assert fake.posted_form == {
        "state": ["FORM"],
        "username": ["user@x.ch"],
        "password": ["pw"],
        "captcha": ["SOLVED"],
    }
    assert fake.token_body["code"] == "THECODE"
    assert (
        pkce_challenge(fake.token_body["code_verifier"]) == fake.authorize_params["code_challenge"]
    )
    assert fake.jwt_auth == "Bearer JWT"
    assert account.public_account_id == "777" and account.token == "SESSION"
    assert client.session.auth == AuthState(token="SESSION", account_id="777")


def test_login_rejected(mock_client):
    client, _ = mock_client(FakeAuth0())
    with pytest.raises(TuttiAuthError, match="login rejected"):
        client.account.login("user@x.ch", "pw", captcha=FixedCaptcha("WRONG"))
    assert client.session.auth is None


def test_login_state_mismatch(mock_client):
    fake = FakeAuth0()
    orig = fake.__call__

    def tamper(r):
        res = orig(r)
        if r.url.path == "/authorize/resume":
            loc = res.headers["Location"]
            q = parse_qs(urlparse(loc).query)
            return httpx.Response(302, headers={"Location": loc.replace(q["state"][0], "evil")})
        return res

    client, _ = mock_client(tamper)
    with pytest.raises(TuttiAuthError, match="state mismatch"):
        client.account.login("u", "p", captcha=FixedCaptcha("SOLVED"))


def test_login_with_web_session(mock_client):
    seen = {}

    def handler(r: httpx.Request) -> httpx.Response:
        if r.url.host == "www.tutti.ch" and r.url.path == "/auth/access-token":
            seen["cookie"] = r.headers.get("cookie")
            return httpx.Response(200, json={"token": "WEBJWT", "expires_at": 1793200000})
        if r.url.path == "/v10/account/authenticateJWT":
            seen["auth"] = r.headers.get("authorization")
            return httpx.Response(
                200, json={"message": "ok", "public_account_id": "42", "token": "mc1xNEW"}
            )
        raise AssertionError(f"unexpected request {r.method} {r.url}")

    client, _ = mock_client(handler)
    account = client.account.login_with_web_session("JWE.COOKIE")
    assert seen == {"cookie": "__app_session=JWE.COOKIE", "auth": "Bearer WEBJWT"}
    assert account.token == "mc1xNEW"
    assert client.session.auth == AuthState(token="mc1xNEW", account_id="42")


def test_login_with_web_session_rejected(mock_client):
    client, _ = mock_client(
        lambda r: httpx.Response(401, json={"error": {"code": "missing_refresh_token"}})
    )
    with pytest.raises(TuttiAuthError, match="log in again on tutti.ch"):
        client.account.login_with_web_session("expired")
    assert client.session.auth is None
