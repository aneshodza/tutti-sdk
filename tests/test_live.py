"""Live tests against the real api.tutti.ch (anonymous). Run with ``pytest -m live``.

Kept deliberately small (~20 requests) to stay polite to tutti.ch.
"""

import pytest

from tutti_sdk import TuttiClient

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def client():
    with TuttiClient() as c:
        yield c


@pytest.fixture(scope="module")
def zurich(client):
    locs = client.localities.search("zürich")
    assert any(loc["localityType"] == "Kanton" for loc in locs)
    return next(loc for loc in locs if loc["localityID"] == "geo-city-zurich")


@pytest.fixture(scope="module")
def first_page(client):
    return client.search("velo").fetch()


def echo(filters, name):
    f = next(f for f in filters if f["name"] == name)
    return (
        f.get("pricingValue")
        or f.get("locationValue")
        or f.get("intervalValue")
        or f.get("selectedOption")
        or f.get("selectedOptions")
    )


def test_search_and_paginate(first_page):
    assert first_page.total_count > 1000
    assert len(first_page.listings) == 30
    assert first_page.has_next_page
    assert first_page.search_token
    assert {"location", "price"} <= {f["name"] for f in first_page.available_filters}
    listing = first_page.listings[0]
    assert listing["listingID"] and listing["title"]

    second = first_page.next()
    assert second is not None and len(second.listings) > 0
    ids1 = {item["listingID"] for item in first_page.listings}
    ids2 = {item["listingID"] for item in second.listings}
    assert not ids1 & ids2


def test_sort_direction(client):
    desc = [x["timestamp"] for x in client.search("velo").fetch().listings if x.get("timestamp")]
    asc = [
        x["timestamp"]
        for x in client.search("velo").sort("timestamp", "asc").fetch().listings
        if x.get("timestamp")
    ]
    assert desc == sorted(desc, reverse=True)
    assert asc == sorted(asc)
    assert asc[0] < desc[0]


def test_listing_details_and_seller_profile(client, first_page):
    listing_id = first_page.listings[0]["listingID"]
    detail = client.listings.get(listing_id)
    assert detail["listingID"] == listing_id
    assert "body" in detail and "images" in detail

    seller = detail["sellerInfo"]["publicAccountID"]
    profile = client.profiles.get(seller)
    assert profile["listings"]["totalCount"] >= 1
    listings = client.profiles.listings(seller, size=5)
    assert listings  # raw GraphQL data


def test_unknown_listing_is_none(client):
    assert client.listings.get("0") is None


def test_filters_change_counts_and_are_echoed(client, zurich):
    base = client.search().category("cars").update_filters()
    total = base["listings"]["totalCount"]
    assert total > 1000

    def check(builder, name, expected):
        res = builder.update_filters()
        assert 0 < res["listings"]["totalCount"] < total, name
        got = echo(res["filters"], name)
        assert got == expected, (name, got)

    cars = lambda: client.search().category("cars")
    check(cars().price(min=1000, max=5000), "price", {"min": 1000, "max": 5000, "freeOnly": False})
    check(
        cars().location(zurich).radius(10),
        "location",
        {"selectedLocalities": [{"__typename": "Locality", **zurich}], "radius": 10},
    )
    check(
        cars().interval("carsAutoScoutRegYear", min=2020),
        "carsAutoScoutRegYear",
        {"min": 2020, "max": None},
    )
    check(cars().select("companyAd", "private"), "companyAd", "private")
    check(
        cars().multi_select("carsAutoScoutFuelType", ["diesel"]),
        "carsAutoScoutFuelType",
        ["diesel"],
    )


def test_free_only(client):
    res = client.search("sofa").free_only().fetch()
    assert res.total_count > 0
    assert all(item["formattedPrice"] == "Gratis" for item in res.listings)


def test_categories_featured_and_browse(client):
    tree = client.categories.tree()
    assert len(tree) > 10
    assert all("categoryID" in c and "label" in c for c in tree)

    featured = client.categories.featured()
    cars = next(c for c in featured if c["categoryID"] == "cars")
    browsed = client.browse(cars["searchToken"]).fetch()
    assert browsed.total_count > 1000
    assert len(browsed.listings) > 0


def test_suggestions(client):
    sug = client.suggestions.search("sof")
    flat = [s for g in sug["suggestionGroups"] for s in g.get("suggestions") or []]
    assert flat
