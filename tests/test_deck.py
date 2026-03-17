"""
Minimal sanity tests for the tarot deck data and draw logic.

Run with:
    pytest tests/test_deck.py -v
"""
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CARDS_PATH = REPO_ROOT / "data" / "cards.json"
MEANINGS_PATH = REPO_ROOT / "data" / "meanings_ko.json"
SCRIPTS_PATH = REPO_ROOT / "scripts"

sys.path.insert(0, str(REPO_ROOT))


# ── Fixtures / helpers ────────────────────────────────────────────────────────

def load_cards():
    with open(CARDS_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_meanings():
    with open(MEANINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def draw_cards(cards):
    """Minimal draw function mirroring app.py logic (always upright)."""
    selected = random.sample(cards, 3)
    return [
        {
            **card,
            "orientation": "upright",
        }
        for card in selected
    ]


# ── Tests: deck structure ─────────────────────────────────────────────────────

def test_deck_has_78_cards():
    cards = load_cards()
    assert len(cards) == 78, f"Expected 78 cards, got {len(cards)}"


def test_deck_unique_ids():
    cards = load_cards()
    ids = [c["id"] for c in cards]
    assert len(ids) == len(set(ids)), "Duplicate card IDs found"


def test_deck_major_arcana_count():
    cards = load_cards()
    major = [c for c in cards if c["arcana"] == "major"]
    assert len(major) == 22, f"Expected 22 major arcana, got {len(major)}"


def test_deck_minor_arcana_count():
    cards = load_cards()
    minor = [c for c in cards if c["arcana"] == "minor"]
    assert len(minor) == 56, f"Expected 56 minor arcana, got {len(minor)}"


def test_minor_arcana_suits():
    cards = load_cards()
    for suit in ("wands", "cups", "swords", "pentacles"):
        suit_cards = [c for c in cards if c.get("suit") == suit]
        assert len(suit_cards) == 14, f"Expected 14 {suit} cards, got {len(suit_cards)}"


def test_all_cards_have_image_file():
    cards = load_cards()
    for card in cards:
        assert "image_file" in card and card["image_file"], (
            f"Card {card['id']} missing image_file"
        )


def test_image_filename_format():
    """Each image_file must be a non-empty string ending in .jpg."""
    cards = load_cards()
    for card in cards:
        fname = card["image_file"]
        assert isinstance(fname, str) and fname.endswith(".jpg"), (
            f"Card {card['id']} has invalid image_file: {fname!r}"
        )


def test_cards_json_trailing_newline():
    """cards.json should end with a newline character."""
    raw = CARDS_PATH.read_bytes()
    assert raw.endswith(b"\n"), "data/cards.json is missing a trailing newline"


# ── Tests: draw logic ─────────────────────────────────────────────────────────

def test_draw_returns_three_cards():
    cards = load_cards()
    drawn = draw_cards(cards)
    assert len(drawn) == 3


def test_draw_unique_cards():
    cards = load_cards()
    for _ in range(20):
        drawn = draw_cards(cards)
        ids = [c["id"] for c in drawn]
        assert len(ids) == len(set(ids)), "Draw returned duplicate cards"


def test_draw_all_upright():
    cards = load_cards()
    for _ in range(20):
        drawn = draw_cards(cards)
        for card in drawn:
            assert card["orientation"] == "upright"


# ── Tests: meanings data ──────────────────────────────────────────────────────

def test_meanings_has_all_78_cards():
    meanings = load_meanings()
    cards = load_cards()
    missing = [c["id"] for c in cards if c["id"] not in meanings["cards"]]
    assert not missing, f"Missing meanings for: {missing}"


def test_meanings_upright_reversed_present():
    meanings = load_meanings()
    for card_id, data in meanings["cards"].items():
        assert "upright" in data and data["upright"], (
            f"Card {card_id} missing upright meaning"
        )
        assert "reversed" in data and data["reversed"], (
            f"Card {card_id} missing reversed meaning"
        )


def test_meanings_category_hints_present():
    meanings = load_meanings()
    categories = list(meanings["_categories"].keys())
    for card_id, data in meanings["cards"].items():
        hints = data.get("hints", {})
        for cat in categories:
            assert cat in hints and hints[cat], (
                f"Card {card_id} missing hint for category '{cat}'"
            )


# ── Tests: download script ────────────────────────────────────────────────────

def test_download_script_exists():
    script = SCRIPTS_PATH / "download_rws_images.py"
    assert script.exists(), "scripts/download_rws_images.py not found"


def test_download_script_covers_all_cards():
    """WIKIMEDIA_FILES in download script must map all 78 image filenames."""
    import importlib.util

    script = SCRIPTS_PATH / "download_rws_images.py"
    spec = importlib.util.spec_from_file_location("download_rws_images", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    cards = load_cards()
    expected_files = {c["image_file"] for c in cards}
    mapped_files = set(mod.WIKIMEDIA_FILES.keys())

    missing = expected_files - mapped_files
    assert not missing, f"Download script missing mappings for: {missing}"


# ── Tests: fetch_card_image (per-card on-demand download) ────────────────────

def _load_app_module():
    """Import app.py without executing the Streamlit UI code."""
    import importlib.util
    import unittest.mock as mock

    # Stub out streamlit so module-level UI calls don't raise errors.
    # cache_data must be a passthrough so decorated functions work normally.
    # It can be called as @st.cache_data or @st.cache_data(show_spinner=False).
    def _cache_data_passthrough(func=None, **kwargs):
        if func is not None:
            return func  # used as plain @st.cache_data
        return lambda f: f  # used as @st.cache_data(show_spinner=False)

    mock_st = mock.MagicMock()
    mock_st.cache_data = _cache_data_passthrough
    mock_st.button.return_value = False       # don't trigger draw on import
    mock_st.session_state = {}                # no prior draw state

    with mock.patch.dict("sys.modules", {"streamlit": mock_st}):
        spec = importlib.util.spec_from_file_location("app", REPO_ROOT / "app.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


def test_fetch_card_image_returns_path_when_image_exists(tmp_path):
    """fetch_card_image returns the Path when the image file is already on disk."""
    import unittest.mock as mock

    app = _load_app_module()

    fake_img = tmp_path / "00_fool.jpg"
    # Write a valid JPEG (correct magic bytes, size >= _MIN_IMAGE_BYTES).
    fake_img.write_bytes(b"\xff\xd8\xff" + b"\x00" * app._MIN_IMAGE_BYTES)

    with mock.patch.object(app, "ASSETS_DIR", tmp_path):
        result, error = app.fetch_card_image("00_fool.jpg")

    assert result == fake_img
    assert error is None


def test_fetch_card_image_returns_none_for_unknown_file(tmp_path):
    """fetch_card_image returns None for a filename not in WIKIMEDIA_FILES."""
    import unittest.mock as mock

    app = _load_app_module()

    with mock.patch.object(app, "ASSETS_DIR", tmp_path):
        result, error = app.fetch_card_image("nonexistent_card.jpg")

    assert result is None
    assert error is not None


def test_fetch_card_image_downloads_missing_image(tmp_path):
    """fetch_card_image downloads from Wikimedia when the local file is absent."""
    import unittest.mock as mock

    app = _load_app_module()

    fake_bytes = b"\xff\xd8\xff" + b"\x00" * 16  # minimal JPEG-like bytes

    def fake_urlopen(req, timeout=None):  # noqa: ARG001
        mock_resp = mock.MagicMock()
        mock_resp.headers.get.side_effect = (
            lambda k, d="": {"Content-Type": "image/jpeg"}.get(k, d)
        )
        mock_resp.read.return_value = fake_bytes
        cm = mock.MagicMock()
        cm.__enter__ = lambda s: mock_resp
        cm.__exit__ = mock.MagicMock(return_value=False)
        return cm

    with (
        mock.patch.object(app, "ASSETS_DIR", tmp_path),
        mock.patch.object(app, "urlopen", fake_urlopen),
    ):
        result, error = app.fetch_card_image("00_fool.jpg")

    assert result is not None
    assert error is None
    assert result.read_bytes() == fake_bytes


def test_fetch_card_image_returns_none_on_network_error(tmp_path):
    """fetch_card_image returns None when the network request fails."""
    import unittest.mock as mock
    from urllib.error import URLError

    app = _load_app_module()

    with (
        mock.patch.object(app, "ASSETS_DIR", tmp_path),
        mock.patch.object(app, "urlopen", side_effect=URLError("timeout")),
        mock.patch("time.sleep"),
    ):
        result, error = app.fetch_card_image("00_fool.jpg")

    assert result is None
    assert error is not None


def test_fetch_card_image_invalid_cached_file_triggers_redownload(tmp_path):
    """A cached file that is too small is deleted and re-downloaded."""
    import unittest.mock as mock

    app = _load_app_module()

    # Write a tiny (< 5 KB), corrupt cached file.
    bad_cache = tmp_path / "00_fool.jpg"
    bad_cache.write_bytes(b"not an image")

    fake_bytes = b"\xff\xd8\xff" + b"\x00" * 16  # JPEG magic bytes

    def fake_urlopen(req, timeout=None):  # noqa: ARG001
        mock_resp = mock.MagicMock()
        mock_resp.headers.get.side_effect = (
            lambda k, d="": {"Content-Type": "image/jpeg"}.get(k, d)
        )
        mock_resp.read.return_value = fake_bytes
        cm = mock.MagicMock()
        cm.__enter__ = lambda s: mock_resp
        cm.__exit__ = mock.MagicMock(return_value=False)
        return cm

    with (
        mock.patch.object(app, "ASSETS_DIR", tmp_path),
        mock.patch.object(app, "urlopen", fake_urlopen),
    ):
        result, error = app.fetch_card_image("00_fool.jpg")

    assert result is not None
    assert error is None
    assert result.read_bytes() == fake_bytes


def test_fetch_card_image_non_image_response_rejected(tmp_path):
    """A non-image Content-Type response is rejected and not written to disk."""
    import unittest.mock as mock

    app = _load_app_module()

    def fake_urlopen(req, timeout=None):  # noqa: ARG001
        mock_resp = mock.MagicMock()
        mock_resp.headers.get.side_effect = (
            lambda k, d="": {"Content-Type": "text/html"}.get(k, d)
        )
        mock_resp.read.return_value = b"<html>error page</html>"
        cm = mock.MagicMock()
        cm.__enter__ = lambda s: mock_resp
        cm.__exit__ = mock.MagicMock(return_value=False)
        return cm

    with (
        mock.patch.object(app, "ASSETS_DIR", tmp_path),
        mock.patch.object(app, "urlopen", fake_urlopen),
    ):
        result, error = app.fetch_card_image("00_fool.jpg")

    assert result is None
    assert error is not None and "non-image" in error
    assert not (tmp_path / "00_fool.jpg").exists()


def test_fetch_card_image_retries_then_succeeds(tmp_path):
    """A transient HTTP 503 error causes a retry; the second attempt succeeds."""
    import unittest.mock as mock
    from urllib.error import HTTPError

    app = _load_app_module()

    fake_bytes = b"\xff\xd8\xff" + b"\x00" * 16  # JPEG magic bytes
    calls = [0]

    def fake_urlopen(req, timeout=None):  # noqa: ARG001
        calls[0] += 1
        if calls[0] == 1:
            raise HTTPError(req.full_url, 503, "Service Unavailable", {}, None)
        mock_resp = mock.MagicMock()
        mock_resp.headers.get.side_effect = (
            lambda k, d="": {"Content-Type": "image/jpeg"}.get(k, d)
        )
        mock_resp.read.return_value = fake_bytes
        cm = mock.MagicMock()
        cm.__enter__ = lambda s: mock_resp
        cm.__exit__ = mock.MagicMock(return_value=False)
        return cm

    with (
        mock.patch.object(app, "ASSETS_DIR", tmp_path),
        mock.patch.object(app, "urlopen", fake_urlopen),
        mock.patch("time.sleep"),
    ):
        result, error = app.fetch_card_image("00_fool.jpg")

    assert result is not None
    assert error is None
    assert calls[0] == 2  # first call failed (503), second succeeded
    assert result.read_bytes() == fake_bytes
