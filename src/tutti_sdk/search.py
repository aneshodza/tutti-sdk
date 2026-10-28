from collections.abc import Iterator
from typing import Any, Literal

from .errors import TuttiValidationError
from .graphql import GraphQLTransport
from .operations import SEARCH_LISTINGS_BY_QUERY, SEARCH_LISTINGS_BY_TOKEN, UPDATE_FILTERS
from .types import (
    Constraints,
    Filter,
    IntervalConstraint,
    Listing,
    ListingSearchResult,
    Locality,
    PageInfo,
    PriceConstraint,
    SortDirection,
    SortField,
    StringConstraint,
)

SearchMode = Literal["query", "token"]


class SearchBuilder:
    """Chainable search query builder. Each call mutates the draft and returns
    ``self``; ``.fetch()`` runs the search and returns a :class:`SearchResult`."""

    def __init__(self, transport: GraphQLTransport, mode: SearchMode, seed: str | None = None):
        self._transport = transport
        self._mode = mode
        self._query = seed if mode == "query" else None
        self._token = seed if mode == "token" else None
        self._category_id: str | None = None
        self._cursor: str | None = None
        self._sort = "TIMESTAMP"
        self._direction = "DESCENDING"
        self._image_height = 630

        self._prices: list[PriceConstraint] = []
        self._localities: list[Locality] = []
        self._radius: float | None = None
        self._intervals: list[IntervalConstraint] = []
        self._strings: list[StringConstraint] = []

    def category(self, category_id: str) -> "SearchBuilder":
        """Restrict to a category id (e.g. "furniture", "cars")."""
        self._category_id = category_id
        return self

    def price(
        self, min: float | None = None, max: float | None = None, free_only: bool = False
    ) -> "SearchBuilder":
        """Price bounds in CHF. Omit min or max for open-ended."""
        if min is not None and max is not None and min > max:
            raise TuttiValidationError(f"price min ({min}) > max ({max})")
        p: PriceConstraint = {"key": "price", "freeOnly": free_only}
        if min is not None:
            p["min"] = min
        if max is not None:
            p["max"] = max
        self._prices = [p]
        return self

    def free_only(self) -> "SearchBuilder":
        """Only free items."""
        self._prices = [{"key": "price", "freeOnly": True}]
        return self

    def location(self, locality: Locality) -> "SearchBuilder":
        """Add a locality (from ``client.localities.search()``). Repeatable."""
        self._localities.append(locality)
        return self

    def radius(self, km: float) -> "SearchBuilder":
        """Search radius around the selected localities (as the app sends it, in km)."""
        self._radius = km
        return self

    def interval(
        self, name: str, min: float | None = None, max: float | None = None
    ) -> "SearchBuilder":
        """Numeric range filter (e.g. "year", "mileage")."""
        if min is not None and max is not None and min > max:
            raise TuttiValidationError(f"interval {name}: min > max")
        c: IntervalConstraint = {"key": name}
        if min is not None:
            c["min"] = min
        if max is not None:
            c["max"] = max
        self._intervals.append(c)
        return self

    def select(self, name: str, value: str) -> "SearchBuilder":
        """Single-select filter (e.g. ``select("companyAd", "private")``)."""
        self._strings.append({"key": name, "value": [value]})
        return self

    def multi_select(self, name: str, values: list[str]) -> "SearchBuilder":
        """Multi-select filter (e.g. ``multi_select("language", ["de", "fr"])``)."""
        self._strings.append({"key": name, "value": list(values)})
        return self

    def sort(
        self, field: SortField = "timestamp", direction: SortDirection = "desc"
    ) -> "SearchBuilder":
        """Sort field + direction (default: timestamp desc — newest first).
        ``timestamp`` is the only sort mode the API exposes."""
        self._sort = "TIMESTAMP"
        self._direction = "ASCENDING" if direction == "asc" else "DESCENDING"
        return self

    def image_height(self, px: int) -> "SearchBuilder":
        """Thumbnail height requested from the API."""
        self._image_height = px
        return self

    def cursor(self, cursor: str | None) -> "SearchBuilder":
        """Set the pagination cursor (used by ``SearchResult.next()``)."""
        self._cursor = cursor
        return self

    def _constraints(self) -> Constraints:
        locations = []
        if self._localities:
            loc: dict[str, Any] = {
                "key": "location",
                "localities": [l["localityID"] for l in self._localities],
            }
            if self._radius is not None:
                loc["radius"] = self._radius
            locations.append(loc)
        return {
            "intervals": self._intervals,
            "locations": locations,  # type: ignore[typeddict-item]
            "prices": self._prices,
            "strings": self._strings,
        }

    def _variables(self) -> dict[str, Any]:
        common = {
            "cursor": self._cursor,
            "sort": self._sort,
            "direction": self._direction,
            "imageHeight": self._image_height,
            "includePlacements": False,
            "includeExtraInfo": True,
            "placementsVariant": None,
        }
        if self._mode == "token":
            return {**common, "token": self._token, "placementsVariant": "SMG"}
        return {
            **common,
            "categoryId": self._category_id,
            "query": self._query,
            "constraints": self._constraints(),
        }

    def fetch(self) -> "SearchResult":
        """Execute the search and return the first page of results."""
        op = SEARCH_LISTINGS_BY_TOKEN if self._mode == "token" else SEARCH_LISTINGS_BY_QUERY
        root = self._transport.request(op, self._variables())
        return SearchResult(self, root)

    def update_filters(self) -> ListingSearchResult:
        """Fetch the available filters + result count for the current
        category/query/constraints WITHOUT fetching a listings page."""
        return self._transport.request(
            UPDATE_FILTERS,
            {
                "categoryId": self._category_id,
                "query": self._query,
                "constraints": self._constraints(),
            },
        )


class SearchResult:
    """One page of search results, plus helpers to paginate and to discover the
    filters available for the current query/category."""

    def __init__(self, builder: SearchBuilder, root: ListingSearchResult) -> None:
        self._builder = builder
        self._root = root

    @property
    def total_count(self) -> int:
        """Total matching listings server-side (across all pages)."""
        return (self._root.get("listings") or {}).get("totalCount") or 0

    @property
    def listings(self) -> list[Listing]:
        """Listings on this page."""
        return [e["node"] for e in (self._root.get("listings") or {}).get("edges") or []]

    @property
    def gallery_listings(self) -> list[Listing]:
        """Featured/hero listings returned alongside the result set."""
        return self._root.get("galleryListings") or []

    @property
    def available_filters(self) -> list[Filter]:
        """Filters available for this query/category (names, labels, options)."""
        return self._root.get("filters") or []

    @property
    def search_token(self) -> str | None:
        """Opaque token to browse this category via ``client.browse(token)``."""
        return self._root.get("searchToken")

    @property
    def page_info(self) -> PageInfo:
        return (self._root.get("listings") or {}).get("pageInfo") or {
            "hasNextPage": False,
            "endCursor": None,
        }

    @property
    def has_next_page(self) -> bool:
        return self.page_info["hasNextPage"]

    def next(self) -> "SearchResult | None":
        """Fetch the next page, or ``None`` if there is none."""
        info = self.page_info
        if not info["hasNextPage"] or not info["endCursor"]:
            return None
        return self._builder.cursor(info["endCursor"]).fetch()

    def paginate(self) -> Iterator[Listing]:
        """Iterate every listing across all pages (fetching lazily)."""
        page: SearchResult | None = self
        while page:
            yield from page.listings
            page = page.next()

    def raw(self) -> ListingSearchResult:
        """The raw, unmodeled response root (escape hatch)."""
        return self._root
