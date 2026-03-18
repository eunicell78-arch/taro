"""
GPT-powered tarot reading generator.

Uses the OpenAI Chat Completions API to produce a very detailed, Korean-language
3-card spread reading.  The API key is read from (in order of precedence):

1. The ``OPENAI_API_KEY`` environment variable.
2. Streamlit secrets (``st.secrets["OPENAI_API_KEY"]``), when running inside
   a Streamlit app.

Never hard-code the key in source code.
"""
from __future__ import annotations

import os
from typing import Optional

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
_GPT_MODEL = "gpt-4o"


def _get_api_key() -> Optional[str]:
    """Return the OpenAI API key from the environment or Streamlit secrets."""
    key = os.environ.get(OPENAI_API_KEY_ENV, "").strip()
    if not key:
        try:
            import streamlit as st  # optional – only present inside the app

            key = str(st.secrets.get(OPENAI_API_KEY_ENV, "")).strip()
        except (ImportError, AttributeError, KeyError, TypeError):
            pass
    return key or None


def build_prompt(
    drawn_cards: list[dict],
    category: str,
    category_label: str,
    question: str,
    meanings: dict,  # kept for signature compatibility – not used
) -> str:
    """Build the GPT prompt for a tarot reading.

    Parameters
    ----------
    drawn_cards:
        List of card dicts (1 card for ``category == "today"``, 3 otherwise),
        each containing at minimum ``name_ko`` and ``name_en``.
    category:
        Category key (e.g. ``"love"``).
    category_label:
        Human-readable Korean label for the category.
    question:
        The user's optional question string.
    meanings:
        Full ``meanings_ko.json`` parsed dict (not used in prompt; kept for
        backwards-compatible call sites).
    """
    if category == "today":
        positions = ["오늘"]
    else:
        positions = ["과거", "현재", "미래"]

    # Only card names and positions are passed — no meanings or hints.
    card_lines: list[str] = []
    for card, pos in zip(drawn_cards, positions):
        card_lines.append(
            f"- 위치: {pos}\n"
            f"  카드: {card['name_ko']} ({card['name_en']})"
        )

    cards_section = "\n\n".join(card_lines)
    question_section = (
        f"질문: {question.strip()}" if question.strip() else "질문: (없음)"
    )

    return f"""너는 타로 해설자가 아니라 '상황을 읽어주는 상담자'다.

규칙:
- 카드 의미/상징/전통적 해석을 직접 설명하지 마라.
- 카드 이름을 근거로 사용자의 '현재 상태'를 읽어라.
- 반복하지 마라.
- 추상적인 문장(예: '좋은 기운', '우주가 돕는다') 쓰지 마라.
- 과장 없이 현실적으로 말해라.
- 조언은 반드시 실제 행동으로 이어져야 한다.

문체:
- 자연스럽고 직설적인 한국어
- 사용자에게 직접 말하는 형태 ("너는 지금 ~ 상태야")

출력 규격(매우 중요):
- 아래 4개 섹션을 정확히 이 제목으로 출력한다.
- 각 섹션은 2~4문장으로 작성한다.
- 전체 분량은 공백 포함 500~700자 정도로 맞춘다.
- JSON, 마크다운, 코드펜스, 서론, 인사 등 다른 형식 금지.

한줄요약: ...
지금상태: ...
흐름: ...
지금 해야할것: ...

리딩 정보
- 카테고리: {category_label}
- {question_section}

뽑힌 카드
{cards_section}
"""


def generate_reading(
    drawn_cards: list[dict],
    category: str,
    category_label: str,
    question: str,
    meanings: dict,
) -> tuple[Optional[str], Optional[str]]:
    """Generate a detailed GPT tarot reading.

    Returns
    -------
    (reading_text, None)
        On success.
    (None, error_message)
        On failure (missing key, import error, API error, etc.).
    """
    api_key = _get_api_key()
    if not api_key:
        return None, (
            "**OpenAI API 키가 설정되지 않았습니다.**\n\n"
            "- **로컬 실행**: `.env` 파일에 `OPENAI_API_KEY=sk-...` 를 추가하거나, "
            "터미널에서 `export OPENAI_API_KEY=sk-...` 를 실행하세요.\n"
            "- **Streamlit Cloud**: 앱 대시보드 → Settings → Secrets 에서 "
            "`OPENAI_API_KEY = \"sk-...\"` 를 추가하세요."
        )

    try:
        from openai import OpenAI
    except ImportError:
        return None, (
            "`openai` 패키지가 설치되지 않았습니다. "
            "`pip install openai` 를 실행하세요."
        )

    prompt = build_prompt(drawn_cards, category, category_label, question, meanings)

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=_GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=900,
        )
        return response.choices[0].message.content, None
    except Exception as exc:  # noqa: BLE001
        return None, f"GPT API 호출 중 오류가 발생했습니다: {exc}"
