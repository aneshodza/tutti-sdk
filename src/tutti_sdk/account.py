from dataclasses import dataclass
from typing import Any

import httpx

from .captcha import CaptchaProvider, ManualCaptchaProvider
from .errors import TuttiAuthError
from .http import HttpClient
from .login import _BROWSER_UA, OAuthConfig, OAuthTokens, run_login_flow
from .session import AuthState, Session


@dataclass
class AuthenticatedAccount:
    public_account_id: str
    token: str  # the tutti session token, sent as X-Tutti-Auth


class AccountResource:
    """Account auth + reads (REST on api.tutti.ch)."""

    def __init__(
        self,
        http: HttpClient,
        session: Session,
        oauth: OAuthConfig,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = http
        self._session = session
        self._oauth = oauth
        self._transport = transport

    def authenticate_jwt(self, access_token: str) -> AuthenticatedAccount:
        """Exchange an Auth0 access token (JWT) for a tutti session token and store
        it on the session. Subsequent requests are authenticated via X-Tutti-Auth."""
        res = self._http.request(
            "POST", "/account/authenticateJWT", headers={"Authorization": f"Bearer {access_token}"}
        )
        account = AuthenticatedAccount(
            public_account_id=res["public_account_id"], token=res["token"]
        )
        self._session.set_auth(AuthState(token=account.token, account_id=account.public_account_id))
        return account

    def login(
        self, username: str, password: str, captcha: CaptchaProvider | None = None
    ) -> AuthenticatedAccount:
        """Full login: run the Auth0 flow (solving the captcha via the provider,
        default :class:`ManualCaptchaProvider`), then exchange the resulting JWT
        for a tutti session."""
        tokens = self.run_oauth(username, password, captcha or ManualCaptchaProvider())
        return self.authenticate_jwt(tokens.access_token)

    def login_with_web_session(
        self, app_session: str, web_base_url: str = "https://www.tutti.ch"
    ) -> AuthenticatedAccount:
        """Mint a new tutti session from a logged-in tutti.ch browser session.

        ``app_session`` is the value of the website's ``__app_session`` cookie. The
        website (Auth0's Next.js SDK) hands out an Auth0 access token for it at
        ``/auth/access-token``, which is then exchanged like in :meth:`login`.

        The website keeps no refresh token, so this only works while the Auth0
        access token inside the cookie is fresh — i.e. shortly after logging in
        on tutti.ch."""
        with httpx.Client(
            transport=self._transport, timeout=30, cookies={"__app_session": app_session}
        ) as http:
            res = http.get(
                f"{web_base_url}/auth/access-token",
                headers={"Accept": "application/json", "User-Agent": _BROWSER_UA},
            )
        if res.is_error:
            hint = (
                " (log in again on tutti.ch and use the fresh __app_session cookie)"
                if "missing_refresh_token" in res.text
                else ""
            )
            raise TuttiAuthError(
                f"web session rejected: HTTP {res.status_code} {res.text[:200]}{hint}"
            )
        return self.authenticate_jwt(res.json()["token"])

    def run_oauth(self, username: str, password: str, captcha: CaptchaProvider) -> OAuthTokens:
        """Run only the Auth0 portion, returning raw tokens (no API exchange)."""
        return run_login_flow(username, password, captcha, self._oauth, self._transport)

    def use_token(self, token: str, account_id: str | None = None) -> None:
        """Authenticate with a tutti session token captured elsewhere (app/proxy)."""
        self._session.set_auth(AuthState(token=token, account_id=account_id))

    def profile(self) -> dict[str, Any]:
        """The signed-in account's profile (requires an authenticated session)."""
        return self._http.request("GET", "/account/profile.json")

    def logout(self) -> None:
        self._session.clear_auth()
