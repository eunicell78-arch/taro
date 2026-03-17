"""
타로카드 리딩 앱 – Streamlit
categories: 오늘의운세 / 연애운 / 직업운 / 학업및시험운 / 건강운 / 애정운 / 인간관계
"""
import json
import random
from pathlib import Path

import streamlit as st

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CARDS_PATH = BASE_DIR / "data" / "cards.json"
MEANINGS_PATH = BASE_DIR / "data" / "meanings_ko.json"
IMAGES_DIR = BASE_DIR / "assets" / "rws"


# ── 데이터 로드 ────────────────────────────────────────────────────────────────
@st.cache_data
def load_cards():
    with open(CARDS_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_meanings():
    with open(MEANINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


CARDS = load_cards()
MEANINGS = load_meanings()
CATEGORY_MAP = MEANINGS["_categories"]  # key → Korean label


# ── 핵심 로직 ─────────────────────────────────────────────────────────────────
def draw_cards(include_reversed: bool = True) -> list:
    """78장에서 중복 없이 3장을 뽑고 방향을 결정합니다."""
    selected = random.sample(CARDS, 3)
    result = []
    for card in selected:
        orientation = (
            random.choice(["upright", "reversed"]) if include_reversed else "upright"
        )
        result.append({**card, "orientation": orientation})
    return result


def get_interpretation(card_id: str, orientation: str, category: str) -> str:
    """카드 ID + 방향 + 카테고리로 최종 해석 텍스트를 생성합니다."""
    card_data = MEANINGS["cards"].get(card_id, {})
    base = card_data.get(orientation, "")
    hint = card_data.get("hints", {}).get(category, "")
    if hint:
        return f"{base}\n\n**[{CATEGORY_MAP[category]}]** {hint}"
    return base


def generate_summary(drawn: list, category: str) -> str:
    """3장 카드를 종합한 요약 텍스트를 생성합니다."""
    cat_label = CATEGORY_MAP[category]
    card_names = [
        f"{c['name_ko']}({'정방향' if c['orientation'] == 'upright' else '역방향'})"
        for c in drawn
    ]
    upright_count = sum(1 for c in drawn if c["orientation"] == "upright")
    if upright_count == 3:
        tone = "세 장 모두 정방향으로 매우 긍정적인 흐름이 이어집니다."
    elif upright_count == 2:
        tone = "전반적으로 긍정적인 흐름이지만 한 가지 주의할 점이 있습니다."
    elif upright_count == 1:
        tone = "도전적인 상황이지만 하나의 긍정적 돌파구가 존재합니다."
    else:
        tone = "세 장 모두 역방향으로 어려움이 있지만, 내면의 변화를 통해 반전이 가능합니다."

    return (
        f"**{cat_label} 종합 해석**\n\n"
        f"{card_names[0]}, {card_names[1]}, {card_names[2]} 세 장의 카드가 이야기하는 "
        f"{cat_label}의 흐름: {tone} "
        f"첫 번째 카드({card_names[0]})는 현재 상황의 핵심을, "
        f"두 번째 카드({card_names[1]})는 그 안의 도전과 기회를, "
        f"세 번째 카드({card_names[2]})는 앞으로의 방향과 조언을 전달합니다. "
        f"세 카드의 에너지를 종합하면, {cat_label} 면에서 "
        f"의식적인 선택과 내면의 성찰이 가장 중요한 열쇠임을 알 수 있습니다."
    )


# ── UI ────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="타로카드 리딩",
    page_icon="🔮",
    layout="wide",
)

st.title("🔮 타로카드 리딩")
st.caption("카테고리를 선택하고 카드 3장을 뽑아보세요.")

# ── 사이드바: 설정 ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("설정")
    category_label = st.selectbox(
        "카테고리 선택",
        options=list(CATEGORY_MAP.values()),
        index=0,
    )
    # label → key 변환
    category_key = next(k for k, v in CATEGORY_MAP.items() if v == category_label)

    include_reversed = st.toggle(
        "역방향 포함",
        value=True,
        help="비활성화하면 모든 카드가 정방향으로만 나옵니다.",
    )

    st.markdown("---")
    draw_btn = st.button("🃏 3장 뽑기", use_container_width=True, type="primary")
    if draw_btn:
        st.session_state["drawn"] = draw_cards(include_reversed)
        st.session_state["category"] = category_key

    if "drawn" in st.session_state:
        if st.button("🔄 다시 섞기", use_container_width=True):
            st.session_state["drawn"] = draw_cards(include_reversed)
            st.session_state["category"] = category_key

    st.markdown("---")
    st.caption(
        "이미지: Rider–Waite Tarot (공개 도메인, Wikimedia Commons)\n\n"
        "이미지가 없으면 `scripts/download_rws_images.py`를 실행하세요."
    )

# ── 결과 표시 ─────────────────────────────────────────────────────────────────
if "drawn" in st.session_state:
    drawn = st.session_state["drawn"]
    saved_category = st.session_state.get("category", "today")

    current_cat_label = CATEGORY_MAP.get(saved_category, saved_category)
    st.subheader(f"📖 {current_cat_label} 리딩 결과")

    images_available = IMAGES_DIR.is_dir() and any(IMAGES_DIR.iterdir())

    cols = st.columns(3)
    positions = ["첫 번째 카드", "두 번째 카드", "세 번째 카드"]

    for i, (col, card) in enumerate(zip(cols, drawn)):
        with col:
            orientation_ko = "정방향 ↑" if card["orientation"] == "upright" else "역방향 ↓"
            st.markdown(f"### {positions[i]}")
            st.markdown(f"**{card['name_ko']}** *({card['name_en']})*")

            # 방향 배지
            if card["orientation"] == "upright":
                st.success(orientation_ko)
            else:
                st.warning(orientation_ko)

            # 카드 이미지
            img_path = IMAGES_DIR / card["image_file"]
            if img_path.exists():
                st.image(str(img_path), use_container_width=True)
            else:
                st.markdown(
                    """
                    <div style='
                        background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
                        border: 2px solid #e2b96b;
                        border-radius: 12px;
                        height: 200px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: #e2b96b;
                        font-size: 3rem;
                        text-align: center;
                        margin-bottom: 8px;
                    '>🃏</div>
                    """,
                    unsafe_allow_html=True,
                )
                if not images_available:
                    st.caption("이미지 다운로드: `python scripts/download_rws_images.py`")

            # 해석 텍스트
            interpretation = get_interpretation(
                card["id"], card["orientation"], saved_category
            )
            with st.expander("📜 해석 보기", expanded=True):
                st.markdown(interpretation)

    st.markdown("---")
    # 종합 요약
    st.markdown(generate_summary(drawn, saved_category))

else:
    # 초기 안내
    st.info(
        "👈 왼쪽 사이드바에서 카테고리를 선택하고 **3장 뽑기** 버튼을 클릭하세요.",
        icon="🔮",
    )

    if not (IMAGES_DIR.is_dir() and any(IMAGES_DIR.iterdir())):
        st.warning(
            "**카드 이미지가 없습니다.** 이미지를 표시하려면 먼저 다음 명령어를 실행하세요:\n\n"
            "```bash\npython scripts/download_rws_images.py\n```\n\n"
            "이미지 없이도 텍스트 해석은 정상적으로 동작합니다.",
            icon="🖼️",
        )
