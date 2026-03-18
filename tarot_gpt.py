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
    question_section = (
        f"질문: {question.strip()}" if question.strip() else "질문: (없음)"
    )

    if category == "today":
        card = drawn_cards[0]
        cards_section = (
            f"- 위치: 오늘\n"
            f"  카드: {card['name_ko']} ({card['name_en']})"
        )
        return f"""너는 타로 해설자가 아니라 '상황을 읽어주는 상담자'다.

리딩 조건:
- 카드 의미/상징/전통적 해석 설명 금지.
- 카드 이름을 근거로 사용자의 현재 상태를 읽어라.
- 반복 금지, 추상적 문장("좋은 기운" 등) 금지.
- 현실적이고 즉시 실행 가능한 행동 조언 포함.
- 사용자에게 직접 말하는 형태 ("너는 지금 ~ 상태야").

출력 규격(매우 중요):
- 아래 3개 섹션을 정확히 이 제목으로 출력한다.
- 전체 분량은 공백 포함 300자 내외(±30자)로 맞춘다.
- JSON, 마크다운, 코드펜스, 서론, 인사 등 다른 형식 금지.

오늘의 핵심 상태: ...
주의할 점: ...
활용 방법: ...

리딩 정보
- 카테고리: {category_label}
- {question_section}

뽑힌 카드
{cards_section}
"""

    # 3-card spread (과거 / 현재 / 미래)
    positions = ["과거", "현재", "미래"]
    card_lines: list[str] = []
    for card, pos in zip(drawn_cards, positions):
        card_lines.append(
            f"- 위치: {pos}\n"
            f"  카드: {card['name_ko']} ({card['name_en']})"
        )
    cards_section = "\n\n".join(card_lines)

    return f"""너는 타로 해설자가 아니라 '상황을 읽어주는 상담자'다.

타로 리딩 규칙:
1. 카드 하나씩 설명하지 말고 서로 연결해서 해석할 것.
2. 과거 카드는 원인, 현재 카드는 핵심 상태, 미래 카드는 가능성으로 해석할 것.
3. 미래를 단정하지 말고 조건 기반으로 설명할 것.
4. 카드 의미를 그대로 설명하지 말고 상황으로 번역할 것.
5. 반복되는 표현 금지.

문체:
- 자연스럽고 직설적인 한국어
- 사용자에게 직접 말하는 형태

출력 규격(매우 중요):
- 아래 4개 섹션을 정확히 이 제목으로 출력한다.
- 줄바꿈을 유지한다.
- 한줄요약은 1~2문장으로 작성한다.
- 과거/현재/미래는 각각 약 300자로 작성한다.
- JSON, 마크다운, 코드펜스, 서론, 인사 등 다른 형식 금지.

한줄요약: (1~2문장)
과거: (약 300자)
현재: (약 300자)
미래: (약 300자)

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
