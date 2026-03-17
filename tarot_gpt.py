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
    meanings: dict,
) -> str:
    """Build the GPT system+user prompt for a 3-card spread reading.

    Parameters
    ----------
    drawn_cards:
        List of exactly 3 card dicts, each containing at minimum
        ``id``, ``name_ko``, ``name_en``, and ``orientation``.
    category:
        Category key (e.g. ``"love"``).
    category_label:
        Human-readable Korean label for the category.
    question:
        The user's optional question string.
    meanings:
        Full ``meanings_ko.json`` parsed dict.
    """
    positions = ["과거", "현재", "미래"]

    card_lines: list[str] = []
    for card, pos in zip(drawn_cards, positions):
        card_meanings = meanings["cards"].get(card["id"], {})
        meaning_text = card_meanings.get("upright", "")
        hint = card_meanings.get("hints", {}).get(category, "")

        card_lines.append(
            f"- 위치: {pos}\n"
            f"  카드: {card['name_ko']} ({card['name_en']})\n"
            f"  기본 의미: {meaning_text}\n"
            f"  {category_label} 힌트: {hint}"
        )

    cards_section = "\n\n".join(card_lines)
    question_section = (
        f"질문: {question.strip()}" if question.strip() else "질문: (없음 – 일반 리딩)"
    )

    c0, c1, c2 = drawn_cards

    return f"""당신은 20년 이상의 경력을 가진 전문 타로 리더입니다. \
라이더-웨이트-스미스 덱의 상징과 의미를 깊이 이해하며, \
한국어로 따뜻하고 통찰력 있는 리딩을 제공합니다.

아래 정보를 바탕으로 매우 상세한 한국어 타로 리딩을 작성해주세요.

## 리딩 정보
카테고리: {category_label}
{question_section}

## 뽑힌 카드 (3장)
{cards_section}

---

다음 구조에 맞추어 **매우 상세하게** 작성해주세요. \
각 섹션은 마크다운 제목(##)을 사용하고, 풍부한 내용으로 채워주세요.

## 1. 종합 요약
3장 카드의 전체적인 흐름과 핵심 메시지를 2~3문단으로 요약합니다.

## 2. 과거 카드 — {c0['name_ko']} ({c0['name_en']})
이 카드가 과거·원인 포지션에서 갖는 의미를 최소 6~8문단으로 상세히 서술합니다.
{category_label} 맥락, 카드 상징, 현재와의 연결고리를 포함합니다.

## 3. 현재 카드 — {c1['name_ko']} ({c1['name_en']})
현재 상황에 대한 의미를 최소 6~8문단으로 서술합니다.
{category_label} 맥락에서의 핵심 메시지와 과거→미래 가교 역할을 설명합니다.

## 4. 미래 카드 — {c2['name_ko']} ({c2['name_en']})
앞으로의 전망과 가능성을 최소 6~8문단으로 서술합니다.
{category_label} 맥락에서의 방향 제시와 행동 지침을 포함합니다.

## 5. 카드 조합 해석
3장이 함께 만드는 시너지와 전체 스토리를 3~4문단으로 상세히 설명합니다.

## 6. 실행 조언
리딩을 바탕으로 구체적이고 실천 가능한 조언을 **5가지 이상** 번호 목록으로 제시합니다.

## 7. 주의점 및 리스크
이번 리딩에서 특히 주의해야 할 사항과 피해야 할 함정을 서술합니다.

모든 내용은 한국어로 작성하며, 전문적이고 따뜻한 어조를 유지합니다."""


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
            temperature=0.8,
            max_tokens=4000,
        )
        return response.choices[0].message.content, None
    except Exception as exc:  # noqa: BLE001
        return None, f"GPT API 호출 중 오류가 발생했습니다: {exc}"
