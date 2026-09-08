"""Fixture-based tests for collectors/steam_catalog_common.py's
classify_app() — no network calls. This is the crux of correctness for
the whole Steam-catalog build (PRD §9.12a), since both Track A and Track
B route every app through it."""

from collectors.steam_catalog_common import classify_app


def _base_app(**overrides) -> dict:
    app = {
        "type": "game",
        "name": "Example Game",
        "release_date": {"coming_soon": False, "date": "25 Mar, 2020"},
        "genres": [{"id": "1", "description": "Action"}, {"id": "25", "description": "Adventure"}],
        "categories": [{"id": 2, "description": "Single-player"}],
        "developers": ["Example Studio"],
        "publishers": ["Example Publisher"],
        "recommendations": {"total": 5000},
    }
    app.update(overrides)
    return app


def test_normal_well_formed_app():
    result = classify_app(_base_app())
    assert result["name"] == "Example Game"
    assert result["app_type"] == "game"
    assert result["release_date_raw"] == "25 Mar, 2020"
    assert result["release_date"] == "2020-03-25"
    assert result["is_released"] == 1
    assert result["genres"] == "Action,Adventure"
    assert result["is_indie"] == 0
    assert result["categories"] == "Single-player"
    assert result["has_vr_support"] == 0
    assert result["vr_only"] == 0
    assert result["developers"] == "Example Studio"
    assert result["publishers"] == "Example Publisher"
    assert result["recommendations_total"] == 5000
    assert result["low_relevance_flag"] == 0


def test_recommendations_entirely_absent_is_none_not_zero():
    app = _base_app()
    del app["recommendations"]
    result = classify_app(app)
    assert result["recommendations_total"] is None
    assert result["low_relevance_flag"] == 1  # NULL counts as low-relevance


def test_recommendations_present_but_below_threshold():
    result = classify_app(_base_app(recommendations={"total": 3}))
    assert result["recommendations_total"] == 3
    assert result["low_relevance_flag"] == 1


def test_recommendations_at_threshold_boundary_not_flagged():
    # LOW_RELEVANCE_THRESHOLD = 10; a value strictly less than it is
    # flagged, a value at or above it is not.
    result = classify_app(_base_app(recommendations={"total": 10}))
    assert result["recommendations_total"] == 10
    assert result["low_relevance_flag"] == 0

    result_below = classify_app(_base_app(recommendations={"total": 9}))
    assert result_below["low_relevance_flag"] == 1


def test_release_date_coming_soon_is_unparseable_not_a_crash():
    result = classify_app(_base_app(release_date={"coming_soon": True, "date": "Coming soon"}))
    assert result["release_date_raw"] == "Coming soon"
    assert result["release_date"] is None
    assert result["is_released"] == 0


def test_release_date_empty_string():
    result = classify_app(_base_app(release_date={"coming_soon": False, "date": ""}))
    assert result["release_date_raw"] == ""
    assert result["release_date"] is None


def test_release_date_missing_entirely():
    app = _base_app()
    del app["release_date"]
    result = classify_app(app)
    assert result["release_date_raw"] is None
    assert result["release_date"] is None
    assert result["is_released"] == 1  # no coming_soon flag present -> default released


def test_vr_only_app_has_both_flags_set():
    # Confirmed live against Half-Life: Alyx: VR-only titles carry BOTH
    # category 31 ("VR Support") and 54 ("VR Only") simultaneously.
    result = classify_app(_base_app(categories=[
        {"id": 2, "description": "Single-player"},
        {"id": 31, "description": "VR Support"},
        {"id": 54, "description": "VR Only"},
    ]))
    assert result["has_vr_support"] == 1
    assert result["vr_only"] == 1


def test_vr_support_without_vr_only():
    # A flat-screen-playable-with-optional-VR title: 31 present, 54 absent.
    result = classify_app(_base_app(categories=[
        {"id": 2, "description": "Single-player"},
        {"id": 31, "description": "VR Support"},
    ]))
    assert result["has_vr_support"] == 1
    assert result["vr_only"] == 0


def test_no_vr_categories_at_all():
    result = classify_app(_base_app(categories=[{"id": 2, "description": "Single-player"}]))
    assert result["has_vr_support"] == 0
    assert result["vr_only"] == 0


def test_indie_genre_present():
    result = classify_app(_base_app(genres=[
        {"id": "492", "description": "Indie"}, {"id": "1", "description": "Action"},
    ]))
    assert result["is_indie"] == 1
    assert result["genres"] == "Indie,Action"


def test_non_indie_app():
    result = classify_app(_base_app(genres=[{"id": "1", "description": "Action"}]))
    assert result["is_indie"] == 0


def test_empty_genres_and_categories_produce_none_not_empty_string():
    result = classify_app(_base_app(genres=[], categories=[]))
    assert result["genres"] is None
    assert result["categories"] is None
    assert result["is_indie"] == 0


def test_category_id_as_int_vs_genre_id_as_string_both_handled():
    # Confirmed live: categories[].id is a JSON int, genres[].id is a JSON
    # string, inconsistently, in the same real appdetails response.
    result = classify_app(_base_app(
        genres=[{"id": "492", "description": "Indie"}],
        categories=[{"id": 31, "description": "VR Support"}],
    ))
    assert result["is_indie"] == 1
    assert result["has_vr_support"] == 1
