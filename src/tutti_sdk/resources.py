"""Read-only GraphQL resources. Most return raw GraphQL data (shape unmodeled)."""

from typing import Any

from .graphql import GraphQLTransport
from .operations import (
    CATEGORIES,
    GET_FEATURED_CATEGORIES,
    GET_LISTING_DETAILS,
    GET_PUBLIC_ACCOUNT_INFO,
    GET_SEARCH_SUGGESTIONS,
    SEARCH_LISTINGS_BY_USER,
    SEARCH_LOCALITIES,
)
from .session import Session
from .types import Listing, Locality, SortDirection


class CategoriesResource:
    """Category taxonomy reads."""

    def __init__(self, transport: GraphQLTransport) -> None:
        self._transport = transport

    def tree(self) -> list[dict[str, Any]]:
        """The full category tree."""
        return self._transport.request(CATEGORIES, {})

    def featured(self, preferred_image_size: int = 200) -> list[dict[str, Any]]:
        """Featured categories for the home screen."""
        return self._transport.request(
            GET_FEATURED_CATEGORIES, {"preferredImageSize": preferred_image_size}
        )


class ListingsResource:
    """Listing reads."""

    def __init__(self, transport: GraphQLTransport) -> None:
        self._transport = transport

    def get(self, listing_id: str) -> Listing:
        """Full detail for a single listing by id."""
        return self._transport.request(GET_LISTING_DETAILS, {"itemId": listing_id})


class LocalitiesResource:
    """Locality lookup — feed results into ``SearchBuilder.location()``."""

    def __init__(self, transport: GraphQLTransport) -> None:
        self._transport = transport

    def search(self, text: str, exclude_ids: list[str] | None = None) -> list[Locality]:
        """Autocomplete localities by free text (e.g. "zür")."""
        result = self._transport.request(
            SEARCH_LOCALITIES, {"search": text, "excludeIds": exclude_ids or []}
        )
        return result or []


class ProfilesResource:
    """Public seller profiles + their listings."""

    def __init__(self, transport: GraphQLTransport) -> None:
        self._transport = transport

    def get(self, public_account_id: str) -> dict[str, Any]:
        """A seller's public account info."""
        return self._transport.request(
            GET_PUBLIC_ACCOUNT_INFO, {"publicAccountID": public_account_id}
        )

    def listings(
        self,
        public_account_id: str,
        *,
        direction: SortDirection = "desc",
        offset: int = 0,
        size: int = 30,
        image_height: int = 630,
    ) -> dict[str, Any]:
        """A seller's listings, paged by offset/size."""
        return self._transport.request(
            SEARCH_LISTINGS_BY_USER,
            {
                "publicAccountID": public_account_id,
                "sort": "TIMESTAMP",
                "direction": "ASCENDING" if direction == "asc" else "DESCENDING",
                "offset": offset,
                "size": size,
                "imageHeight": image_height,
            },
        )


class SuggestionsResource:
    """Search-box autocomplete suggestions."""

    def __init__(self, transport: GraphQLTransport, session: Session) -> None:
        self._transport = transport
        self._session = session

    def search(
        self, query: str, *, user_identifier: str | None = None, first: int = 6
    ) -> dict[str, Any]:
        """Suggestions for a partial query. ``user_identifier`` defaults to the
        session's device hash."""
        return self._transport.request(
            GET_SEARCH_SUGGESTIONS,
            {
                "query": query,
                "userIdentifier": user_identifier or self._session.tutti_hash,
                "first": first,
            },
        )
