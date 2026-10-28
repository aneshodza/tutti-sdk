# tutti-sdk (Python)

Unofficial Python client for the reverse-engineered private API of [tutti.ch](https://www.tutti.ch). It covers search and filters, listings, seller profiles, categories, suggestions, live messaging, and Auth0 login.

> ⚠️ Not affiliated with tutti.ch. Respect tutti.ch's terms of service and rate limits.

## Install

```sh
pip install tutti-sdk    # or: uv add tutti-sdk
```

API reference: https://aneshodza.github.io/tutti-sdk/

## Development

```sh
uv sync
uv run pytest            # offline unit tests (mocked transport)
uv run pytest -m live    # + live tests against api.tutti.ch
uv run pdoc tutti_sdk    # browse the API docs locally (live-reloading server)
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/). [release-please](https://github.com/googleapis/release-please) keeps a release PR open on `main`, with the version bump and CHANGELOG. Merging it tags the release, publishes to PyPI, and deploys the API docs to GitHub Pages.

## Usage

```python
from tutti_sdk import TuttiClient

with TuttiClient() as client:  # anonymous; random device hash
    zurich = next(
        l for l in client.localities.search("zürich") if l["localityID"] == "geo-city-zurich"
    )

    result = (
        client.search("ledersofa")
        .category("furniture")
        .price(min=100, max=5000)  # or .free_only()
        .location(zurich)
        .radius(10)  # km
        .select("companyAd", "private")
        .multi_select("language", ["de"])
        .interval("carsAutoScoutRegYear", min=2015)
        .sort("timestamp", "desc")
        .fetch()
    )
    result.total_count, result.listings, result.available_filters
    result.next()  # next page or None
    for listing in result.paginate():  # every listing across pages
        ...

    client.listings.get("81078697")
    client.browse(search_token).fetch()
    client.search().category("cars").update_filters()  # filters + count, no listings
    client.categories.tree()
    client.categories.featured()
    client.profiles.get(public_account_id)
    client.profiles.listings(public_account_id, size=30)
    client.suggestions.search("sof")
```

Results are plain dicts straight from the API. `tutti_sdk.types` holds TypedDicts that document the known keys.

### Sessions

```python
from tutti_sdk import FileSessionStore, Session, TuttiClient

store = FileSessionStore(".tutti-sessions")
store.save("alice", client.session.to_dict())
client = TuttiClient(Session.from_dict(store.load("alice")))
```

Snapshots use the same camelCase JSON as the TS library's `Session.toJSON()`, so session files work with either library.

### Messaging (needs an authenticated session)

```python
for msg in client.messaging.stream_messages(conv_id):  # backlog, then live
    print(msg["content"].get("text"))  # break to close the stream
client.messaging.send(conv_id, "Hallo!")
client.messaging.mark_read(conv_id, offset)
client.messaging.reply(item_id, name, email, body)  # start a chat from a listing
```

### Authentication

tutti uses Auth0. The resulting JWT is exchanged for a tutti session token, which is sent as `X-Tutti-Auth` and is valid for about a year.

```python
client.account.use_token("mc1x…", account_id)  # session token, e.g. from your browser
client.account.authenticate_jwt(auth0_access_token)  # or an Auth0 access token
client.account.login(user, password, captcha=...)  # full headless flow, see caveat
```

**Getting a token from your browser.** The website uses the same session token as the app, stored in cookies. Log in on www.tutti.ch, then go to DevTools → Storage/Application → Cookies → `https://www.tutti.ch`:

- `mp_session_id` is the token (starts with `mc1x`).
- `mp_account_info` holds your account ID, the part before the first `%2C`.

`examples/login.py` checks the token and saves it as a session:

```sh
TUTTI_TOKEN=mc1x… TUTTI_ACCOUNT_ID=… uv run python examples/login.py
uv run pytest -m live   # now also runs the authenticated tests
```

**Minting a new session token.** `account.login_with_web_session(app_session)` takes the website's encrypted `__app_session` cookie. It gets an Auth0 access token from `www.tutti.ch/auth/access-token` and exchanges it at `/account/authenticateJWT` for a brand-new `mc1x…` token. That token is a separate session from your browser's. tutti's website stores no refresh token, so this only works shortly after you log in on tutti.ch. Once the access token in the cookie expires, the site answers `missing_refresh_token`. Run it with:

```sh
TUTTI_APP_SESSION=eyJ… uv run python examples/login.py
```

`__app_session` itself does not work as an API credential.

## Caveat: headless login is currently broken (as of 2026-10-28)

`account.login()` faithfully ports the TS flow: one `/u/login` form with username, password and an SVG text captcha, solved manually or by Gemini. tutti's Auth0 tenant has since moved to an identifier-first flow (`/u/login/identifier`) protected by Cloudflare Turnstile (`auth0_v2` captcha). The login page no longer has an image captcha, so the flow stops with `TuttiAuthError: no captcha image found`. Anonymous endpoints are unaffected, and so are `use_token()` and `authenticate_jwt()`. Use a browser token as described above.

Driving the login page with Playwright doesn't help either. Turnstile rejects the automated browser, even when a person types the credentials.
