"""Headless Auth0 authorization-code + PKCE login, as performed by the tutti
Android app."""

import base64
import hashlib
import re
import secrets
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import httpx

from .captcha import CaptchaProvider, parse_data_uri
from .errors import TuttiAuthError


@dataclass
class OAuthConfig:
    """Auth0 / OAuth parameters. Defaults mirror the captured tutti Android client."""

    auth_base_url: str = "https://auth.tutti.ch"
    client_id: str = "lykoMeGKh14siOyOVev0QBAB8vsSKV7b"
    redirect_uri: str = "ch.tutti://auth.tutti.ch/android/ch.tutti/callback"
    audience: str = "https://api.tutti.ch"
    scope: str = "openid profile email"
    ui_locales: str | None = "en"


@dataclass
class OAuthTokens:
    access_token: str
    token_type: str
    expires_in: int
    id_token: str | None = None
    scope: str | None = None


_AUTH0_CLIENT = (
    "eyJuYW1lIjoiQXV0aDAuQW5kcm9pZCIsImVudiI6eyJhbmRyb2lkIjoiMzYifSwidmVyc2lvbiI6IjMuMTAuMCJ9"
)
_BROWSER_UA = (
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/149.0.0.0 Mobile Safari/537.36"
)
_HTML_ACCEPT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
    "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def random_string(nbytes: int = 32) -> str:
    """Cryptographically random base64url string (32 bytes → 43 chars)."""
    return _b64url(secrets.token_bytes(nbytes))


def pkce_challenge(verifier: str) -> str:
    """S256 PKCE challenge for a code verifier."""
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


def _location(res: httpx.Response) -> str:
    loc = res.headers.get("location")
    if not loc:
        raise TuttiAuthError(f"expected a redirect but got HTTP {res.status_code} with no Location")
    return loc


def _authorize_url(config: OAuthConfig, verifier: str, state: str) -> str:
    params = {
        "audience": config.audience,
        "scope": config.scope,
        "response_type": "code",
        "code_challenge": pkce_challenge(verifier),
        "code_challenge_method": "S256",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "state": state,
        "nonce": random_string(32),
        "auth0Client": _AUTH0_CLIENT,
    }
    if config.ui_locales:
        params["ui_locales"] = config.ui_locales
    return f"{config.auth_base_url}/authorize?{urlencode(params)}"


def _code_from_callback(location: str, state: str) -> str:
    """Pull the authorization code out of the ``ch.tutti://…callback`` redirect."""
    qs = parse_qs(urlparse(location).query)
    code = qs.get("code", [None])[0]
    if not code:
        raise TuttiAuthError("authorization code missing from callback redirect")
    if qs.get("state", [None])[0] != state:
        raise TuttiAuthError("OAuth state mismatch (possible CSRF)")
    return code


def _exchange_code(
    http: httpx.Client, config: OAuthConfig, code: str, verifier: str
) -> OAuthTokens:
    res = http.post(
        f"{config.auth_base_url}/oauth/token",
        headers={
            "User-Agent": "okhttp/5.1.0",
            "Auth0-Client": _AUTH0_CLIENT,
            "Accept": "application/json",
        },
        json={
            "client_id": config.client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
            "code_verifier": verifier,
        },
    )
    if res.is_error:
        raise TuttiAuthError(f"token exchange failed: HTTP {res.status_code} {res.text}")
    token = res.json()
    return OAuthTokens(
        access_token=token["access_token"],
        token_type=token["token_type"],
        expires_in=token["expires_in"],
        id_token=token.get("id_token"),
        scope=token.get("scope"),
    )


def run_login_flow(
    username: str,
    password: str,
    captcha: CaptchaProvider,
    config: OAuthConfig | None = None,
    transport: httpx.BaseTransport | None = None,
) -> OAuthTokens:
    """Drive the Auth0 login headlessly: start the flow, fetch the hosted login
    page, solve its captcha via the provider, submit credentials, follow the
    redirects to the authorization code, and exchange it for tokens. The
    returned access token is then traded for a tutti session via
    ``/account/authenticateJWT``.

    Note: as of 2026-10 tutti's login page uses Cloudflare Turnstile instead of
    an image captcha, so this fails; use ``AccountResource.use_token`` instead."""
    config = config or OAuthConfig()
    base = config.auth_base_url
    verifier = random_string(32)
    state = random_string(32)

    html_headers = {
        "User-Agent": _BROWSER_UA,
        "Accept": _HTML_ACCEPT,
        "Accept-Language": "en-US,en;q=0.9",
    }
    # The client's cookie jar carries the Auth0 session + Cloudflare cookies
    # across the redirect steps; redirects are followed by hand.
    with httpx.Client(transport=transport, follow_redirects=False, timeout=30) as http:
        res = http.get(
            _authorize_url(config, verifier, state),
            headers={**html_headers, "Referer": "android-app://ch.tutti/"},
        )
        login_url = urljoin(base, _location(res))  # /u/login?state=<blob>

        res = http.get(login_url, headers={**html_headers, "Referer": "android-app://ch.tutti/"})
        html = res.text

        img = re.search(r'<img[^>]*alt="captcha"[^>]*src="(data:[^"]+)"', html, re.IGNORECASE)
        if not img:
            raise TuttiAuthError(
                "no captcha image found on the login page (layout may have changed)"
            )
        form_state = _form_state(html) or parse_qs(urlparse(login_url).query).get("state", [""])[0]

        solution = captcha.solve(parse_data_uri(img.group(1)))

        res = http.post(
            login_url,
            headers={
                **html_headers,
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": base,
                "Referer": login_url,
            },
            content=urlencode(
                {
                    "state": form_state,
                    "username": username,
                    "password": password,
                    "captcha": solution,
                }
            ),
        )
        after_login = urljoin(base, _location(res))
        if "/authorize/resume" not in urlparse(after_login).path:
            raise TuttiAuthError(
                "login rejected (wrong credentials or captcha). "
                f"Redirected to {urlparse(after_login).path}"
            )

        res = http.get(after_login, headers={**html_headers, "Referer": login_url})
        code = _code_from_callback(_location(res), state)  # ch.tutti://...callback?code=...
        return _exchange_code(http, config, code, verifier)


def _form_state(html: str) -> str | None:
    m = re.search(r'name="state"[^>]*value="([^"]*)"', html, re.IGNORECASE) or re.search(
        r'value="([^"]*)"[^>]*name="state"', html, re.IGNORECASE
    )
    return m.group(1) if m else None
