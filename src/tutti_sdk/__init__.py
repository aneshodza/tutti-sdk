"""Unofficial Python client for the (reverse-engineered) tutti.ch API.

Port of the TypeScript `tutti-api` by Filippo Finke (MIT):
https://github.com/filippofinke/tutti-api

Entry point: :class:`TuttiClient`.
"""

__docformat__ = "restructuredtext"

from .account import AccountResource, AuthenticatedAccount
from .captcha import (
    CaptchaChallenge,
    CaptchaProvider,
    LLMCaptchaProvider,
    ManualCaptchaProvider,
    parse_data_uri,
)
from .client import TuttiClient
from .errors import (
    TuttiAuthError,
    TuttiError,
    TuttiGraphQLError,
    TuttiHttpError,
    TuttiNetworkError,
    TuttiValidationError,
)
from .graphql import GraphQLTransport
from .http import HttpClient
from .login import OAuthConfig, OAuthTokens, run_login_flow
from .messaging import MessagingResource
from .operations import Operation
from .resources import (
    CategoriesResource,
    ListingsResource,
    LocalitiesResource,
    ProfilesResource,
    SuggestionsResource,
)
from .search import SearchBuilder, SearchResult
from .session import (
    AppConfig,
    AuthState,
    FileSessionStore,
    InMemorySessionStore,
    Session,
    SessionSnapshot,
    SessionStore,
)
from .svg import render_svg_to_png

__all__ = [
    "AccountResource",
    "AppConfig",
    "AuthState",
    "AuthenticatedAccount",
    "CaptchaChallenge",
    "CaptchaProvider",
    "CategoriesResource",
    "FileSessionStore",
    "GraphQLTransport",
    "HttpClient",
    "InMemorySessionStore",
    "LLMCaptchaProvider",
    "ListingsResource",
    "LocalitiesResource",
    "ManualCaptchaProvider",
    "MessagingResource",
    "OAuthConfig",
    "OAuthTokens",
    "Operation",
    "ProfilesResource",
    "SearchBuilder",
    "SearchResult",
    "Session",
    "SessionSnapshot",
    "SessionStore",
    "SuggestionsResource",
    "TuttiAuthError",
    "TuttiClient",
    "TuttiError",
    "TuttiGraphQLError",
    "TuttiHttpError",
    "TuttiNetworkError",
    "TuttiValidationError",
    "parse_data_uri",
    "render_svg_to_png",
    "run_login_flow",
]
