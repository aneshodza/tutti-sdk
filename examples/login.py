"""Store a logged-in session; the authenticated tests (and your own scripts) load
it from ./.tutti-sessions/<key>.json — the same format the TS tutti-api writes,
so sessions are interchangeable.

Get the token from a browser where you're logged in to www.tutti.ch:
DevTools → Storage/Application → Cookies → https://www.tutti.ch
  mp_session_id    the session token (starts with "mc1x")  → TUTTI_TOKEN
  mp_account_info  your account id is the part before the first "%2C" → TUTTI_ACCOUNT_ID

    TUTTI_TOKEN=mc1x… TUTTI_ACCOUNT_ID=… uv run python examples/login.py

Or mint a NEW session token from the website's __app_session cookie (same place):

    TUTTI_APP_SESSION=eyJ… uv run python examples/login.py

Or the headless flow (currently blocked by tutti's Turnstile check):

    TUTTI_USER=… TUTTI_PASS=… uv run python examples/login.py

The key defaults to "default" (override with TUTTI_SESSION).
"""

import os
import sys

from tutti_sdk import FileSessionStore, LLMCaptchaProvider, ManualCaptchaProvider, TuttiClient

store = FileSessionStore(".tutti-sessions")
key = os.environ.get("TUTTI_SESSION", "default")

with TuttiClient() as client:
    if token := os.environ.get("TUTTI_TOKEN"):
        client.account.use_token(token, os.environ.get("TUTTI_ACCOUNT_ID"))
        client.account.profile()  # fail fast on a dead token
        print("Token works ✓")
    elif app_session := os.environ.get("TUTTI_APP_SESSION"):
        account = client.account.login_with_web_session(app_session)
        print(f"Minted a new session ✓ account {account.public_account_id}")
    elif os.environ.get("TUTTI_USER") and os.environ.get("TUTTI_PASS"):
        captcha = (
            LLMCaptchaProvider() if os.environ.get("GEMINI_API_KEY") else ManualCaptchaProvider()
        )
        account = client.account.login(
            os.environ["TUTTI_USER"], os.environ["TUTTI_PASS"], captcha=captcha
        )
        print(f"Logged in ✓ account {account.public_account_id}")
    else:
        sys.exit(
            "Provide TUTTI_TOKEN or TUTTI_APP_SESSION (see docstring), or TUTTI_USER + TUTTI_PASS."
        )

    store.save(key, client.session.to_dict())
    print(f'Saved session "{key}". Stored keys: {store.keys()}')
