"""Response/input shapes modeled from captured tutti.ch API traffic.

Everything the client returns is a plain ``dict`` straight from the JSON; these
TypedDicts only document the known keys. Fields seen rarely or nullable in
captures are optional, and unknown fields are never stripped.
"""

from typing import Any, Literal, NotRequired, TypedDict

SortField = Literal["timestamp"]
SortDirection = Literal["asc", "desc"]


class Locality(TypedDict):
    localityID: str
    name: str
    localityType: NotRequired[str]


# ---- Search filter constraints (GraphQL input: ListingSearchConstraints) ----


class PriceConstraint(TypedDict):
    key: Literal["price"]
    # Required non-null on the wire; omitting it fails GRAPHQL_VALIDATION_FAILED.
    freeOnly: bool
    min: NotRequired[float]
    max: NotRequired[float]


class LocationConstraint(TypedDict):
    key: Literal["location"]
    localities: list[str]  # LocalityID strings, not Locality objects
    radius: NotRequired[float]


class IntervalConstraint(TypedDict):
    key: str
    min: NotRequired[float]
    max: NotRequired[float]


class StringConstraint(TypedDict):
    key: str
    value: list[str]


class Constraints(TypedDict):
    intervals: list[IntervalConstraint]
    locations: list[LocationConstraint]
    prices: list[PriceConstraint]
    strings: list[StringConstraint]


# ---- Listing model ----


class ImageRendition(TypedDict):
    src: str


class ListingImage(TypedDict, total=False):
    rendition: ImageRendition


class Canton(TypedDict, total=False):
    name: str
    shortName: str
    circularIcon: ImageRendition


class PostcodeInformation(TypedDict, total=False):
    canton: Canton
    locationName: str
    postcode: str


class SellerInfo(TypedDict, total=False):
    publicAccountID: str
    alias: str
    logo: ImageRendition | None
    subscriptionInfo: Any


class CategoryRef(TypedDict):
    categoryID: str
    label: str


class Listing(TypedDict, total=False):
    __typename: str
    listingID: str
    title: str
    address: str | None
    formattedPrice: str
    primaryCategory: CategoryRef
    images: list[ListingImage]
    timestamp: str
    postcodeInformation: PostcodeInformation
    highlighted: bool
    thumbnail: ListingImage
    sellerInfo: SellerInfo
    formattedSource: str | None


class Filter(TypedDict, total=False):
    """A filter offered for the current query/category. Selected fields depend on
    the captured query document, so this is deliberately permissive."""

    __typename: str
    name: str
    label: str


# ---- Connection / response envelope ----


class PageInfo(TypedDict):
    hasNextPage: bool
    endCursor: str | None


class ListingEdge(TypedDict):
    node: Listing


class ListingConnection(TypedDict, total=False):
    totalCount: int
    edges: list[ListingEdge]
    pageInfo: PageInfo
    placements: list[Any]


class ListingSearchResult(TypedDict, total=False):
    __typename: str
    selectedCategory: CategoryRef | None
    suggestedCategories: list[CategoryRef]
    filters: list[Filter]
    galleryListings: list[Listing]
    listings: ListingConnection
    searchToken: str | None
    query: str | None


# ---- Messaging ----


class MessageContent(TypedDict, total=False):
    text: str


class Message(TypedDict, total=False):
    id: str
    offset: int  # sequence number within the conversation; drives read receipts
    type: str  # "text"
    content: MessageContent
    senderPublicAccountId: str
    timestamp: str


class Participant(TypedDict, total=False):
    publicAccountId: str
    name: str
    role: str  # "seller" | "buyer"
    active: bool


class ConversationItem(TypedDict, total=False):
    id: str  # listing id
    subject: str
    active: bool
    price: Any
    language: str | None
    thumbnailName: str | None


class LatestMessage(TypedDict, total=False):
    content: MessageContent
    senderPublicAccountId: str
    timestamp: str
    type: str
    offset: int


class BlockList(TypedDict):
    blocked: bool
    blockedBy: bool


class Conversation(TypedDict, total=False):
    id: str
    item: ConversationItem
    participants: list[Participant]
    latestMessage: LatestMessage
    unreadMessages: int
    unreadMessageOffset: int
    archivedAt: str | None
    blockList: BlockList
