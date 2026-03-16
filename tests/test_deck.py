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


def draw_cards(cards, include_reversed=True):
    """Minimal draw function mirroring app.py logic."""
    selected = random.sample(cards, 3)
    return [
        {
            **card,
            "orientation": (
                random.choice(["upright", "reversed"]) if include_reversed else "upright"
            ),
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


def test_draw_orientations_when_reversed_included():
    cards = load_cards()
    seen = set()
    for _ in range(200):
        drawn = draw_cards(cards, include_reversed=True)
        seen.update(c["orientation"] for c in drawn)
    assert "upright" in seen and "reversed" in seen, (
        "Expected both orientations when include_reversed=True"
    )


def test_draw_all_upright_when_reversed_excluded():
    cards = load_cards()
    for _ in range(20):
        drawn = draw_cards(cards, include_reversed=False)
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
