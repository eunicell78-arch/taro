"""
🔮 타로카드 리딩 앱

Streamlit 기반 78장 라이더-웨이트-스미스 타로 리딩 웹앱.
카드 이미지는 로컬 assets/rws/ 에서 우선 로딩하며,
파일이 없거나 손상된 경우에만 Wikimedia Commons에서 다운로드합니다.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st

import tarot_gpt

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

_MIN_IMAGE_BYTES = 5 * 1024  # cached files smaller than this are treated as corrupt
_MAX_DOWNLOAD_ATTEMPTS = 3
_RETRYABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})


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


def _is_image_bytes(data: bytes) -> bool:
    """Return True if *data* starts with a recognised image magic-byte sequence."""
    if data[:3] == b"\xff\xd8\xff":                      # JPEG
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":                # PNG
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):               # GIF
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":   # WebP
        return True
    return False


def fetch_card_image(image_file: str) -> tuple[Optional[Path], Optional[str]]:
    """Return *(path, None)* when the image is available locally, or *(None, reason)*
    when it cannot be obtained.

    Validates any cached file (size ≥ 5 KB and valid magic bytes); corrupt or partial
    files are deleted and re-downloaded.  Uses up to 3 attempts with exponential
    back-off and jitter for transient HTTP 429/5xx errors and URLErrors.
    """
    dest = ASSETS_DIR / image_file

    # Validate any existing cached file.
    if dest.exists():
        data = dest.read_bytes()
        if len(data) >= _MIN_IMAGE_BYTES and _is_image_bytes(data):
            return dest, None
        # Corrupt or partial – evict and re-download.
        dest.unlink(missing_ok=True)
        print(f"WARN: evicted corrupt/partial cache file {dest.name}", file=sys.stderr)

    wiki_name = WIKIMEDIA_FILES.get(image_file)
    if not wiki_name:
        return None, f"no Wikimedia mapping for {image_file!r}"

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    url = _wikimedia_url(wiki_name)
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept-Language": "en",
    }

    last_reason = "unknown error"
    for attempt in range(_MAX_DOWNLOAD_ATTEMPTS):
        if attempt:
            delay = (2 ** attempt) + random.uniform(0.0, 1.0)
            time.sleep(delay)
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=30) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    last_reason = f"non-image Content-Type: {content_type!r}"
                    print(f"WARN: {image_file}: {last_reason}", file=sys.stderr)
                    return None, last_reason  # not retryable
                data = resp.read()
            if not _is_image_bytes(data):
                last_reason = (
                    f"invalid magic bytes (Content-Type was {content_type!r})"
                )
                print(f"WARN: {image_file}: {last_reason}", file=sys.stderr)
                return None, last_reason  # not retryable
            dest.write_bytes(data)
            return dest, None
        except HTTPError as exc:
            last_reason = f"HTTP {exc.code}"
            if exc.code not in _RETRYABLE_HTTP_CODES:
                break
        except URLError as exc:
            last_reason = str(exc.reason)
        print(
            f"WARN: {image_file}: attempt {attempt + 1} failed: {last_reason}",
            file=sys.stderr,
        )
    return None, last_reason


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

def draw_cards(cards: list, n: int = 3) -> list:
    """Return *n* randomly sampled cards, each with an 'orientation' key set to 'upright'."""
    selected = random.sample(cards, n)
    return [
        {
            **card,
            "orientation": "upright",
        }
        for card in selected
    ]


# ── GPT reading (cached) ──────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _cached_gpt_reading(
    drawn_key: tuple,
    question: str,
    category: str,
) -> tuple[Optional[str], Optional[str]]:
    """Cached wrapper around tarot_gpt.generate_reading.

    The cache key is (drawn_key, question, category) so the
    GPT API is only called when the draw or user inputs actually change.
    """
    drawn_cards = [
        {"id": cid, "name_ko": nko, "name_en": nen, "orientation": ori}
        for cid, nko, nen, ori in drawn_key
    ]
    cat_label = _CATEGORY_LABELS[category]
    return tarot_gpt.generate_reading(
        drawn_cards, category, cat_label, question, load_meanings()
    )


# ── Access gate ───────────────────────────────────────────────────────────────

def _get_app_password() -> str:
    """Return the shared app password from Streamlit secrets or APP_PASSWORD env var."""
    try:
        if "APP_PASSWORD" in st.secrets:
            return str(st.secrets["APP_PASSWORD"]).strip()
    except Exception:  # noqa: BLE001
        pass
    return os.getenv("APP_PASSWORD", "").strip()


def _require_auth() -> None:
    """Render a full-page login gate and stop the app if the session is not authenticated.

    The app is halted via ``st.stop()`` so that no main-area content (card images,
    GPT calls, etc.) is rendered or executed before the user authenticates.
    """
    pw = _get_app_password()

    if not pw:
        st.error(
            "APP_PASSWORD가 설정되지 않았습니다.\n"
            "Streamlit Cloud → Settings → Secrets 에 `APP_PASSWORD`를 추가하세요."
        )
        st.stop()
        return  # unreachable in production; keeps linters/type checkers happy

    if st.session_state.get("authed") is True:
        return

   
    st.divider()
    st.info("💡 이 서비스는 인증된 사용자만 이용 가능합니다.")
    st.markdown("비밀번호를 입력하세요")
    entered = st.text_input(
        "", placeholder="패스워드 입력", type="password", key="pw_input"
    )
    login_clicked = st.button("🔓 로그인", use_container_width=True)

    if login_clicked:
        if entered == pw:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")

    st.divider()
    st.caption("🔒 문의: 관리자에게 연락하세요")
    st.stop()


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
st.caption(
    "78장 라이더-웨이트-스미스 타로 • "
    "이미지는 로컬 에셋을 우선 사용하며, 없을 경우 Wikimedia Commons에서 다운로드됩니다."
)

# ── Authentication guard ──────────────────────────────────────────────────────
# Halts the app (st.stop) before any data loading or network/GPT calls when the
# visitor has not yet entered the shared access password.
_require_auth()

cards = load_cards()
meanings = load_meanings()

# Initialise category default before the widget is rendered.
st.session_state.setdefault("category", "today")

# Category selection in main area, above the draw button.
category = st.selectbox(
    "리딩 카테고리",
    options=list(_CATEGORY_LABELS.keys()),
    format_func=lambda k: _CATEGORY_LABELS[k],
    key="category",
)

# Process the draw button BEFORE rendering the sidebar so that
# st.session_state['drawn'] is set during this same script run.
if st.button("카드 뽑기 🃏", type="primary"):
    st.session_state["drawn"] = draw_cards(cards, n=3)

with st.sidebar:
    st.header("설정")
    if st.button("로그아웃", use_container_width=True, key="logout_btn"):
        st.session_state["authed"] = False
        st.rerun()

if "drawn" in st.session_state:
    drawn = st.session_state["drawn"]
    positions = ["과거", "현재", "미래"]
    cols = st.columns(3)

    for col, card, pos in zip(cols, drawn, positions):
        with col:
            st.subheader(f"{pos}")
            st.markdown(f"**{card['name_ko']}** ({card['name_en']})")

            # Per-card on-demand image download
            with st.spinner(f"{card['name_ko']} 이미지 로딩 중…"):
                img_path, img_error = fetch_card_image(card["image_file"])

            if img_path:
                img_bytes = img_path.read_bytes()
                st.image(img_bytes, use_container_width=True)
            else:
                st.info("🃏 이미지를 불러올 수 없습니다.")
                if img_error:
                    with st.expander("오류 상세"):
                        st.caption(img_error)

            # Meaning and category hint
            card_meanings = meanings["cards"].get(card["id"], {})
            meaning_text = card_meanings.get("upright", "")
            if meaning_text:
                st.markdown(f"> {meaning_text}")

            hint = card_meanings.get("hints", {}).get(category, "")
            if hint:
                cat_label = _CATEGORY_LABELS[category]
                st.markdown(f"*{cat_label}: {hint}*")

    # ── GPT 상세풀이 ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("🤖 GPT 상세풀이")
    gpt_question = st.text_area(
        "질문 (선택)",
        placeholder="예) 이번 달 연애운은 어떤가요?",
        help="질문이 없으면 일반 리딩을 생성합니다.",
        key="gpt_question",
    )
    gpt_button = st.button("상세풀이 생성 ✨", type="primary", key="gpt_btn")

    if gpt_button:
        drawn_key = tuple(
            (c["id"], c["name_ko"], c["name_en"], c["orientation"]) for c in drawn
        )
        with st.spinner("GPT가 상세풀이를 생성 중입니다…"):
            reading_text, reading_error = _cached_gpt_reading(
                drawn_key,
                gpt_question,
                category,
            )

        if reading_error:
            st.error(reading_error)
        elif reading_text:
            st.divider()
            st.subheader("🤖 GPT 상세풀이")
            st.markdown(reading_text)
