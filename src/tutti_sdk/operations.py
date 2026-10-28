"""Verbatim GraphQL operations captured from the tutti Android app.

Generated from filippofinke/tutti-api src/operations/*.ts — do not edit by hand.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Operation:
    """A captured GraphQL operation. ``root_field`` is the top-level key in the
    response ``data`` object (often differs from ``name``)."""

    name: str
    id: str  # Apollo persisted-query id (sha256 of the document)
    root_field: str
    document: str


CATEGORIES = Operation(
    name="Categories",
    id="a2685d3153f06fcab78644435fa8f000baf37d3aea951848ef216be78e149ad1",
    root_field="categoriesRoot",
    document=(
        "query Categories { categoriesRoot { __typename ...categoryFragment children "
        "{ __typename ...categoryFragment children { __typename ...categoryFragment "
        "children { __typename ...categoryFragment } } } } }  fragment "
        "categoryFragment on Category { categoryID label parent { categoryID label } "
        "}"
    ),
)

GET_FEATURED_CATEGORIES = Operation(
    name="GetFeaturedCategories",
    id="f663bcce9541f1a9998bc3b9eaa5bf06f314fdbcb21865c0158258febc317ed5",
    root_field="categoriesFeatured",
    document=(
        "query GetFeaturedCategories($preferredImageSize: Int!) { categoriesFeatured "
        "{ __typename ...FeaturedCategoryFields } }  fragment FeaturedCategoryFields "
        "on Category { categoryID label searchToken mainImage { rendition(width: "
        "$preferredImageSize) { src } } }"
    ),
)

GET_LISTING_DETAILS = Operation(
    name="GetListingDetails",
    id="291bb5687dc211efa9f2f495c48596a8c885b35ecc14e84f7c052affebc1868e",
    root_field="listing",
    document=(
        "query GetListingDetails($itemId: ListingID!) { listing(listingID: $itemId) "
        "{ __typename ...listingDetailsFields } }  fragment quickReplyFields on "
        "ListingsQuickReplyOption { label messageBody shortLabel trackingId }  "
        "fragment externalPlatformFields on ListingExternalPlatform { externalURL "
        "label logoURL }  fragment similarListingFields on Listing { listingID title "
        "formattedPrice primaryCategory { categoryID label } thumbnail { rendition { "
        "src } } sellerInfo { publicAccountID } }  fragment listingDetailsFields on "
        "Listing { listingID body address formattedPrice formattedSource highlighted "
        "images(first: 50) { rendition { src } } language phoneInfo { isMobile "
        "phoneHash } postcodeInformation { canton { name shortName circularIcon { "
        "src(format: SVG) } } locationName postcode } primaryCategory { categoryID "
        "label parent { categoryID label } } properties { __typename ... on "
        "ListingPropertyText { listingPropertyID label text } } replyInfo { "
        "__typename ... on ListingTextReply { quickReplies { __typename "
        "...quickReplyFields } restrictedUntil } ... on ListingExternalTextReply { "
        "quickReplies { __typename ...quickReplyFields } externalPlatform { "
        "__typename ...externalPlatformFields } } ... on ListingExternalLinkReply { "
        "externalPlatform { __typename ...externalPlatformFields } } } sellerInfo { "
        "publicAccountID alias logo { rendition { src } } subscriptionInfo { "
        "subscriptionBadge { src } } } thumbnail { rendition { src } } timestamp "
        "title externalURL similarListings(first: 10) { edges { node { __typename "
        "...similarListingFields } } } }"
    ),
)

GET_PUBLIC_ACCOUNT_INFO = Operation(
    name="GetPublicAccountInfo",
    id="7dfaee0a6811ce250099d4c3321bb8ec41664d612be71c41134f1ed851f8dcb3",
    root_field="publicAccountInfo",
    document=(
        "query GetPublicAccountInfo($publicAccountID: PublicAccountID!) { "
        "publicAccountInfo(publicAccountID: $publicAccountID) { __typename "
        "...publicAccountInfoFields listings { totalCount totalApprovedCount } } }  "
        "fragment publicAccountInfoFields on PublicAccountInfo { publicAccountID "
        "accountName locationName memberSince logoURL url subscriptionInfo { "
        "subscriptionClass subscriptionBadge { src } } }"
    ),
)

GET_SEARCH_SUGGESTIONS = Operation(
    name="GetSearchSuggestionsQuery",
    id="c0145191dc1fdfef5f7552a6285a4b96dae6f8bd55fa6e16dfd841ca04e0076f",
    root_field="searchSuggestions",
    document=(
        "query GetSearchSuggestionsQuery($query: String!, $userIdentifier: "
        "SearchSuggestionsUserIdentifier!, $first: Int!) { searchSuggestions(query: "
        "$query, userIdentifier: $userIdentifier, first: $first) { suggestionGroups "
        "{ __typename ...searchSuggestionGroupFields } } }  fragment "
        "searchSuggestionFields on SearchSuggestion { searchSuggestionID "
        "labelTitleHighlighted labelDescription searchToken deletable }  fragment "
        "searchSuggestionGroupFields on SearchSuggestionGroup { suggestions { "
        "__typename ...searchSuggestionFields } }"
    ),
)

SEARCH_LISTINGS_BY_QUERY = Operation(
    name="SearchListingsByQuery",
    id="6a9d2981e8e49a73ba0fb631361bfaa4f1f4c2f9591661cbbcac1cc456fabecf",
    root_field="searchListingsByQuery",
    document=(
        "query SearchListingsByQuery($categoryId: ID, $query: String, $constraints: "
        "ListingSearchConstraints, $cursor: Cursor, $sort: ListingSortMode!, "
        "$direction: SortDirection!, $imageHeight: Int, $includePlacements: "
        "Boolean!, $includeExtraInfo: Boolean!, $placementsVariant: "
        "PlacementsAdVariant) { searchListingsByQuery(category: $categoryId, query: "
        "$query, constraints: $constraints) { __typename "
        "...ListingsSearchResultFields } }  fragment categoryFields on Category { "
        "categoryID label parent { categoryID label } }  fragment "
        "filterDescriptionFields on ListingsFilterDescription { disabled name label "
        "}  fragment intervalTypeTextFields on ListingIntervalTypeText { minLimit "
        "maxLimit }  fragment intervalTypeSliderFields on ListingIntervalTypeSlider "
        "{ sliderStart: minLimit sliderEnd: maxLimit }  fragment "
        "intervalFilterFields on ListingIntervalFilter { __typename "
        "...filterDescriptionFields intervalType { __typename ... on "
        "ListingIntervalTypeText { __typename ...intervalTypeTextFields } ... on "
        "ListingIntervalTypeSlider { __typename ...intervalTypeSliderFields } } "
        "intervalValue: value { min max } step unit minField { placeholder } "
        "maxField { placeholder } }  fragment selectOptionFields on "
        "ListingSelectOption { __typename value label }  fragment "
        "singleSelectFilterFields on ListingSingleSelectFilter { __typename "
        "...filterDescriptionFields placeholder inline selectedOption: value options "
        "{ __typename ...selectOptionFields } }  fragment multiSelectFilterFields on "
        "ListingMultiSelectFilter { __typename ...filterDescriptionFields "
        "placeholder inline selectedOptions: values options { __typename "
        "...selectOptionFields } }  fragment pricingFilterFields on "
        "ListingPricingFilter { __typename ...filterDescriptionFields pricingValue: "
        "value { min max freeOnly } minField { placeholder } maxField { placeholder "
        "} }  fragment localityFields on Locality { localityID name localityType }  "
        "fragment catalogLocationFilterFields on ListingLocationFilter { __typename "
        "...filterDescriptionFields placeholder locationValue: value { "
        "selectedLocalities { __typename ...localityFields } radius } }  fragment "
        "filterFields on ListingFilter { __typename ...filterDescriptionFields ... "
        "on ListingIntervalFilter { __typename ...intervalFilterFields } ... on "
        "ListingSingleSelectFilter { __typename ...singleSelectFilterFields } ... on "
        "ListingMultiSelectFilter { __typename ...multiSelectFilterFields } ... on "
        "ListingPricingFilter { __typename ...pricingFilterFields } ... on "
        "ListingLocationFilter { __typename ...catalogLocationFilterFields } }  "
        "fragment listingFields on Listing { listingID title address formattedPrice "
        "primaryCategory { categoryID label } images(first: 50) { rendition(height: "
        "$imageHeight) { src } } timestamp postcodeInformation { canton { name "
        "shortName circularIcon { src(format: SVG) } } locationName postcode } "
        "highlighted thumbnail { rendition { src } } sellerInfo { publicAccountID "
        "alias logo { rendition { src } } subscriptionInfo { subscriptionBadge { src "
        "} } } formattedSource }  fragment placementPositionFields on "
        "PlacementsPosition { adUnitID(variant: $placementsVariant) positionType }  "
        "fragment placementFields on PlacementsInformation { keyValues { key value } "
        "positions { __typename ...placementPositionFields } }  fragment "
        "ListingsSearchResultFields on ListingSearchResult { query @include(if: "
        "$includeExtraInfo) suggestedCategories(first: 2) @include(if: "
        "$includeExtraInfo) { __typename ...categoryFields } selectedCategory "
        "@include(if: $includeExtraInfo) { __typename ...categoryFields } filters "
        "@include(if: $includeExtraInfo) { __typename ...filterFields } "
        "galleryListings(first: 15) @include(if: $includeExtraInfo) { __typename "
        "...listingFields } listings(after: $cursor, sort: $sort, direction: "
        "$direction) { totalCount placements @include(if: $includePlacements) { "
        "__typename ...placementFields } edges { node { __typename ...listingFields "
        "} } pageInfo { hasNextPage endCursor } } searchToken @include(if: "
        "$includeExtraInfo) }"
    ),
)

SEARCH_LISTINGS_BY_TOKEN = Operation(
    name="SearchListingsByToken",
    id="9007a8005d55536a2f98b16447437ade17765368d9c86fa03940270e0c5ee3e5",
    root_field="searchListingsByToken",
    document=(
        "query SearchListingsByToken($token: SearchToken!, $cursor: Cursor, $sort: "
        "ListingSortMode!, $direction: SortDirection!, $imageHeight: Int, "
        "$includePlacements: Boolean!, $includeExtraInfo: Boolean!, "
        "$placementsVariant: PlacementsAdVariant) { searchListingsByToken(token: "
        "$token) { __typename ...ListingsSearchResultFields } }  fragment "
        "categoryFields on Category { categoryID label parent { categoryID label } } "
        " fragment filterDescriptionFields on ListingsFilterDescription { disabled "
        "name label }  fragment intervalTypeTextFields on ListingIntervalTypeText { "
        "minLimit maxLimit }  fragment intervalTypeSliderFields on "
        "ListingIntervalTypeSlider { sliderStart: minLimit sliderEnd: maxLimit }  "
        "fragment intervalFilterFields on ListingIntervalFilter { __typename "
        "...filterDescriptionFields intervalType { __typename ... on "
        "ListingIntervalTypeText { __typename ...intervalTypeTextFields } ... on "
        "ListingIntervalTypeSlider { __typename ...intervalTypeSliderFields } } "
        "intervalValue: value { min max } step unit minField { placeholder } "
        "maxField { placeholder } }  fragment selectOptionFields on "
        "ListingSelectOption { __typename value label }  fragment "
        "singleSelectFilterFields on ListingSingleSelectFilter { __typename "
        "...filterDescriptionFields placeholder inline selectedOption: value options "
        "{ __typename ...selectOptionFields } }  fragment multiSelectFilterFields on "
        "ListingMultiSelectFilter { __typename ...filterDescriptionFields "
        "placeholder inline selectedOptions: values options { __typename "
        "...selectOptionFields } }  fragment pricingFilterFields on "
        "ListingPricingFilter { __typename ...filterDescriptionFields pricingValue: "
        "value { min max freeOnly } minField { placeholder } maxField { placeholder "
        "} }  fragment localityFields on Locality { localityID name localityType }  "
        "fragment catalogLocationFilterFields on ListingLocationFilter { __typename "
        "...filterDescriptionFields placeholder locationValue: value { "
        "selectedLocalities { __typename ...localityFields } radius } }  fragment "
        "filterFields on ListingFilter { __typename ...filterDescriptionFields ... "
        "on ListingIntervalFilter { __typename ...intervalFilterFields } ... on "
        "ListingSingleSelectFilter { __typename ...singleSelectFilterFields } ... on "
        "ListingMultiSelectFilter { __typename ...multiSelectFilterFields } ... on "
        "ListingPricingFilter { __typename ...pricingFilterFields } ... on "
        "ListingLocationFilter { __typename ...catalogLocationFilterFields } }  "
        "fragment listingFields on Listing { listingID title address formattedPrice "
        "primaryCategory { categoryID label } images(first: 50) { rendition(height: "
        "$imageHeight) { src } } timestamp postcodeInformation { canton { name "
        "shortName circularIcon { src(format: SVG) } } locationName postcode } "
        "highlighted thumbnail { rendition { src } } sellerInfo { publicAccountID "
        "alias logo { rendition { src } } subscriptionInfo { subscriptionBadge { src "
        "} } } formattedSource }  fragment placementPositionFields on "
        "PlacementsPosition { adUnitID(variant: $placementsVariant) positionType }  "
        "fragment placementFields on PlacementsInformation { keyValues { key value } "
        "positions { __typename ...placementPositionFields } }  fragment "
        "ListingsSearchResultFields on ListingSearchResult { query @include(if: "
        "$includeExtraInfo) suggestedCategories(first: 2) @include(if: "
        "$includeExtraInfo) { __typename ...categoryFields } selectedCategory "
        "@include(if: $includeExtraInfo) { __typename ...categoryFields } filters "
        "@include(if: $includeExtraInfo) { __typename ...filterFields } "
        "galleryListings(first: 15) @include(if: $includeExtraInfo) { __typename "
        "...listingFields } listings(after: $cursor, sort: $sort, direction: "
        "$direction) { totalCount placements @include(if: $includePlacements) { "
        "__typename ...placementFields } edges { node { __typename ...listingFields "
        "} } pageInfo { hasNextPage endCursor } } searchToken @include(if: "
        "$includeExtraInfo) }"
    ),
)

SEARCH_LISTINGS_BY_USER = Operation(
    name="SearchListingsByUser",
    id="851d216fce882eec0c0de7daae432b4c12b977a5076c0cfd85320fcc9d2dadc5",
    root_field="publicAccountInfo",
    document=(
        "query SearchListingsByUser($publicAccountID: PublicAccountID!, $sort: "
        "ListingSortMode!, $direction: SortDirection!, $offset: Int = 0 , $size: Int "
        "= 30 , $imageHeight: Int) { publicAccountInfo(publicAccountID: "
        "$publicAccountID) { listings(sort: $sort, direction: $direction, offset: "
        "$offset, size: $size) { __typename ...PublicListingResultFields } } }  "
        "fragment listingFields on Listing { listingID title address formattedPrice "
        "primaryCategory { categoryID label } images(first: 50) { rendition(height: "
        "$imageHeight) { src } } timestamp postcodeInformation { canton { name "
        "shortName circularIcon { src(format: SVG) } } locationName postcode } "
        "highlighted thumbnail { rendition { src } } sellerInfo { publicAccountID "
        "alias logo { rendition { src } } subscriptionInfo { subscriptionBadge { src "
        "} } } formattedSource }  fragment PublicListingResultFields on "
        "PublicAccountListings { totalCount listings { __typename ...listingFields } "
        "}"
    ),
)

SEARCH_LOCALITIES = Operation(
    name="SearchLocalities",
    id="0bfe41259e77f875a21be04a97d2e7feb0c928b8687462eaaa96c8bd29561be7",
    root_field="searchLocalities",
    document=(
        "query SearchLocalities($search: String!, $excludeIds: [LocalityID!]) { "
        "searchLocalities(search: $search, exclude: $excludeIds) { __typename "
        "...localityFields } }  fragment localityFields on Locality { localityID "
        "name localityType }"
    ),
)

UPDATE_FILTERS = Operation(
    name="UpdateFilters",
    id="32544b66a5cc005ae1e853bb7896aa82b2bfce865f3e69cb64486ff92475a458",
    root_field="searchListingsByQuery",
    document=(
        "query UpdateFilters($categoryId: ID, $query: String, $constraints: "
        "ListingSearchConstraints) { searchListingsByQuery(category: $categoryId, "
        "query: $query, constraints: $constraints) { selectedCategory { __typename "
        "...categoryFields } suggestedCategories(first: 2) { __typename "
        "...categoryFields } filters { __typename ...filterFields } listings { "
        "totalCount } searchToken } }  fragment categoryFields on Category { "
        "categoryID label parent { categoryID label } }  fragment "
        "filterDescriptionFields on ListingsFilterDescription { disabled name label "
        "}  fragment intervalTypeTextFields on ListingIntervalTypeText { minLimit "
        "maxLimit }  fragment intervalTypeSliderFields on ListingIntervalTypeSlider "
        "{ sliderStart: minLimit sliderEnd: maxLimit }  fragment "
        "intervalFilterFields on ListingIntervalFilter { __typename "
        "...filterDescriptionFields intervalType { __typename ... on "
        "ListingIntervalTypeText { __typename ...intervalTypeTextFields } ... on "
        "ListingIntervalTypeSlider { __typename ...intervalTypeSliderFields } } "
        "intervalValue: value { min max } step unit minField { placeholder } "
        "maxField { placeholder } }  fragment selectOptionFields on "
        "ListingSelectOption { __typename value label }  fragment "
        "singleSelectFilterFields on ListingSingleSelectFilter { __typename "
        "...filterDescriptionFields placeholder inline selectedOption: value options "
        "{ __typename ...selectOptionFields } }  fragment multiSelectFilterFields on "
        "ListingMultiSelectFilter { __typename ...filterDescriptionFields "
        "placeholder inline selectedOptions: values options { __typename "
        "...selectOptionFields } }  fragment pricingFilterFields on "
        "ListingPricingFilter { __typename ...filterDescriptionFields pricingValue: "
        "value { min max freeOnly } minField { placeholder } maxField { placeholder "
        "} }  fragment localityFields on Locality { localityID name localityType }  "
        "fragment catalogLocationFilterFields on ListingLocationFilter { __typename "
        "...filterDescriptionFields placeholder locationValue: value { "
        "selectedLocalities { __typename ...localityFields } radius } }  fragment "
        "filterFields on ListingFilter { __typename ...filterDescriptionFields ... "
        "on ListingIntervalFilter { __typename ...intervalFilterFields } ... on "
        "ListingSingleSelectFilter { __typename ...singleSelectFilterFields } ... on "
        "ListingMultiSelectFilter { __typename ...multiSelectFilterFields } ... on "
        "ListingPricingFilter { __typename ...pricingFilterFields } ... on "
        "ListingLocationFilter { __typename ...catalogLocationFilterFields } }"
    ),
)
