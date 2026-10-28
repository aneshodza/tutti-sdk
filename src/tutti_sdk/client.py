from typing import Self

import httpx

from .account import AccountResource
from .graphql import GraphQLTransport
from .http import HttpClient
from .login import OAuthConfig
from .messaging import MessagingResource
from .resources import (
    CategoriesResource,
    ListingsResource,
    LocalitiesResource,
    ProfilesResource,
    SuggestionsResource,
)
from .search import SearchBuilder
from .session import Session


class TuttiClient:
    """Entry point. One instance = one session/account. Use several clients
    (optionally restored via ``Session.from_dict``) for several accounts.

    ``transport`` lets you inject an ``httpx`` transport (mocking, proxies); it is
    used for both the API and the login flow. Usable as a context manager.
    """

    def __init__(
        self,
        session: Session | None = None,
        *,
        base_url: str = "https://api.tutti.ch",
        api_version: str = "v10",
        oauth: OAuthConfig | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30,
    ) -> None:
        self.session = session or Session()
        # Streaming endpoints (messaging) are long-lived, so no read timeout.
        self._client = httpx.Client(transport=transport, timeout=httpx.Timeout(timeout, read=None))
        http = HttpClient(self._client, base_url, api_version, self.session)
        self._transport = GraphQLTransport(http)

        self.listings = ListingsResource(self._transport)
        self.localities = LocalitiesResource(self._transport)
        self.account = AccountResource(http, self.session, oauth or OAuthConfig(), transport)
        self.messaging = MessagingResource(http)
        self.categories = CategoriesResource(self._transport)
        self.profiles = ProfilesResource(self._transport)
        self.suggestions = SuggestionsResource(self._transport, self.session)

    def search(self, query: str | None = None) -> SearchBuilder:
        """Keyword/category/filter search: ``client.search("sofa").category("furniture")…``"""
        return SearchBuilder(self._transport, "query", query)

    def browse(self, token: str) -> SearchBuilder:
        """Browse a category by its opaque search token (from a prior result)."""
        return SearchBuilder(self._transport, "token", token)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
