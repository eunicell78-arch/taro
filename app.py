"""
🔮 타로카드 리딩 앱

Streamlit 기반 78장 라이더-웨이트-스미스 타로 리딩 웹앱.
카드 이미지는 필요한 시점에 Wikimedia Commons에서 한 장씩 자동으로 내려받습니다.
"""
import base64
import hashlib
import importlib.util
import json
import random
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st

# ── Paths ──────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent
ASSETS_DIR = REPO_ROOT / "assets" / "rws"
CARDS_PATH = REPO_ROOT / "data" / "cards.json"
MEANINGS_PATH = REPO_ROOT / "data" / "meanings_ko.json"
SCRIPTS_PATH = REPO_ROOT / "scripts"

WIKIMEDIA_FILE_BASE = "https://upload.wikimedia.org/wikipedia/commons"
_USER_AGENT = (
    "TarotAppImageDownloader/1.0 "
    "(https://github.com/eunicell78-arch/tarot; tarot card reading app)"
)


# ── Wikimedia filename mapping (loaded from the download script) ───────────────

def _load_wikimedia_files() -> dict:
    """Import WIKIMEDIA_FILES from scripts/download_rws_images.py."""
    spec = importlib.util.spec_from_file_location(
        "download_rws_images", SCRIPTS_PATH / "download_rws_images.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.WIKIMEDIA_FILES


WIKIMEDIA_FILES: dict = _load_wikimedia_files()


# ── Per-card on-demand image fetcher ──────────────────────────────────────────

def _wikimedia_url(wiki_name: str) -> str:
    """Compute the direct download URL for a Wikimedia Commons file."""
    name = wiki_name.replace(" ", "_")
    md5 = hashlib.md5(name.encode("utf-8")).hexdigest()
    return f"{WIKIMEDIA_FILE_BASE}/{md5[0]}/{md5[:2]}/{name}"


def fetch_card_image(image_file: str) -> Optional[Path]:
    """Return the local path for *image_file*, downloading it on demand from
    Wikimedia Commons if it is not already present in assets/rws/.

    Downloads only the single requested image (per-card, on-demand).
    Returns ``None`` when the filename is not in the mapping or the download fails.
    """
    dest = ASSETS_DIR / image_file
    if dest.exists():
        return dest

    wiki_name = WIKIMEDIA_FILES.get(image_file)
    if not wiki_name:
        return None

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    url = _wikimedia_url(wiki_name)
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(req, timeout=30) as resp:
            data = resp.read()
        dest.write_bytes(data)
        return dest
    except (HTTPError, URLError):
        return None


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data
def load_cards() -> list:
    with open(CARDS_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_meanings() -> dict:
    with open(MEANINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── Draw logic ────────────────────────────────────────────────────────────────

def draw_cards(cards: list, n: int = 3, include_reversed: bool = True) -> list:
    """Return *n* randomly sampled cards, each with an 'orientation' key."""
    selected = random.sample(cards, n)
    return [
        {
            **card,
            "orientation": (
                random.choice(["upright", "reversed"]) if include_reversed else "upright"
            ),
        }
        for card in selected
    ]


# ── Streamlit UI ──────────────────────────────────────────────────────────────

_CATEGORY_LABELS = {
    "today": "오늘의 운세",
    "love": "연애운",
    "career": "직업운",
    "study": "학업·시험운",
    "health": "건강운",
    "romance": "애정운",
    "relationship": "인간관계",
}

st.set_page_config(page_title="🔮 타로카드 리딩", layout="wide")
st.title("🔮 타로카드 리딩")
st.caption("78장 라이더-웨이트-스미스 타로 • 이미지는 Wikimedia Commons에서 자동 다운로드됩니다.")

with st.sidebar:
    st.header("설정")
    include_reversed = st.checkbox("역방향 카드 포함", value=True)
    category = st.selectbox(
        "리딩 카테고리",
        options=list(_CATEGORY_LABELS.keys()),
        format_func=lambda k: _CATEGORY_LABELS[k],
    )

cards = load_cards()
meanings = load_meanings()

if st.button("카드 뽑기 🃏", type="primary"):
    st.session_state["drawn"] = draw_cards(cards, n=3, include_reversed=include_reversed)

if "drawn" in st.session_state:
    drawn = st.session_state["drawn"]
    positions = ["과거", "현재", "미래"]
    cols = st.columns(3)

    for col, card, pos in zip(cols, drawn, positions):
        with col:
            orientation = card["orientation"]
            label = "정방향 ↑" if orientation == "upright" else "역방향 ↓"
            st.subheader(f"{pos}")
            st.markdown(f"**{card['name_ko']}** ({card['name_en']})  \n{label}")

            # Per-card on-demand image download
            with st.spinner(f"{card['name_ko']} 이미지 로딩 중…"):
                img_path = fetch_card_image(card["image_file"])

            if img_path:
                img_bytes = img_path.read_bytes()
                if orientation == "reversed":
                    b64 = base64.b64encode(img_bytes).decode()
                    st.markdown(
                        f'<img src="data:image/jpeg;base64,{b64}" '
                        f'style="width:100%;transform:rotate(180deg);">',
                        unsafe_allow_html=True,
                    )
                else:
                    st.image(img_bytes, use_container_width=True)
            else:
                st.info("🃏 이미지를 불러올 수 없습니다.")

            # Meaning and category hint
            card_meanings = meanings["cards"].get(card["id"], {})
            meaning_text = card_meanings.get(orientation, "")
            if meaning_text:
                st.markdown(f"> {meaning_text}")

            hint = card_meanings.get("hints", {}).get(category, "")
            if hint:
                cat_label = _CATEGORY_LABELS[category]
                st.markdown(f"*{cat_label}: {hint}*")
