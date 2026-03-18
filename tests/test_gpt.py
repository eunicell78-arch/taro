"""
Tests for the tarot_gpt module.

Run with:
    pytest tests/test_gpt.py -v
"""
from __future__ import annotations

import json
import sys
import unittest.mock as mock
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import tarot_gpt  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_drawn_cards():
    return [
        {"id": "major_00", "name_ko": "바보", "name_en": "The Fool", "orientation": "upright"},
        {"id": "major_01", "name_ko": "마법사", "name_en": "The Magician", "orientation": "reversed"},
        {"id": "major_02", "name_ko": "여사제", "name_en": "The High Priestess", "orientation": "upright"},
    ]


@pytest.fixture()
def sample_meanings():
    with open(REPO_ROOT / "data" / "meanings_ko.json", encoding="utf-8") as f:
        return json.load(f)


# ── Tests: _get_api_key ───────────────────────────────────────────────────────

def test_get_api_key_from_env(monkeypatch):
    monkeypatch.setenv(tarot_gpt.OPENAI_API_KEY_ENV, "sk-test-env-key")
    key = tarot_gpt._get_api_key()
    assert key == "sk-test-env-key"


def test_get_api_key_returns_none_when_missing(monkeypatch):
    monkeypatch.delenv(tarot_gpt.OPENAI_API_KEY_ENV, raising=False)
    # Also ensure streamlit is not importable or returns empty
    with mock.patch.dict("sys.modules", {"streamlit": None}):
        key = tarot_gpt._get_api_key()
    assert key is None


def test_get_api_key_falls_back_to_streamlit_secrets(monkeypatch):
    monkeypatch.delenv(tarot_gpt.OPENAI_API_KEY_ENV, raising=False)
    mock_st = mock.MagicMock()
    mock_st.secrets.get.return_value = "sk-test-secret-key"
    with mock.patch.dict("sys.modules", {"streamlit": mock_st}):
        key = tarot_gpt._get_api_key()
    assert key == "sk-test-secret-key"


# ── Tests: build_prompt ───────────────────────────────────────────────────────

def test_build_prompt_contains_card_names(sample_drawn_cards, sample_meanings):
    prompt = tarot_gpt.build_prompt(
        sample_drawn_cards, "love", "연애운", "테스트 질문입니다.", sample_meanings
    )
    assert "바보" in prompt
    assert "The Fool" in prompt
    assert "마법사" in prompt
    assert "여사제" in prompt


def test_build_prompt_contains_positions(sample_drawn_cards, sample_meanings):
    prompt = tarot_gpt.build_prompt(
        sample_drawn_cards, "love", "연애운", "", sample_meanings
    )
    # Verify position labels appear in the card section in the correct order
    idx_past = prompt.index("위치: 과거")
    idx_present = prompt.index("위치: 현재")
    idx_future = prompt.index("위치: 미래")
    assert idx_past < idx_present < idx_future


def test_build_prompt_today_contains_single_position(sample_drawn_cards, sample_meanings):
    one = sample_drawn_cards[:1]
    prompt = tarot_gpt.build_prompt(one, "today", "오늘의 운세", "", sample_meanings)
    assert "위치: 오늘" in prompt
    assert "위치: 과거" not in prompt
    assert "위치: 현재" not in prompt
    assert "위치: 미래" not in prompt


def test_build_prompt_contains_category_label(sample_drawn_cards, sample_meanings):
    prompt = tarot_gpt.build_prompt(
        sample_drawn_cards, "career", "직업운", "", sample_meanings
    )
    assert "직업운" in prompt


def test_build_prompt_includes_question(sample_drawn_cards, sample_meanings):
    question = "이번 달 연애운은 어떤가요?"
    prompt = tarot_gpt.build_prompt(
        sample_drawn_cards, "love", "연애운", question, sample_meanings
    )
    assert question in prompt


def test_build_prompt_no_question_placeholder(sample_drawn_cards, sample_meanings):
    prompt = tarot_gpt.build_prompt(
        sample_drawn_cards, "love", "연애운", "", sample_meanings
    )
    assert "없음" in prompt


def test_build_prompt_does_not_contain_orientation_labels(sample_drawn_cards, sample_meanings):
    prompt = tarot_gpt.build_prompt(
        sample_drawn_cards, "today", "오늘의 운세", "", sample_meanings
    )
    assert "정방향" not in prompt
    assert "역방향" not in prompt


def test_build_prompt_requests_four_sections(sample_drawn_cards, sample_meanings):
    """Prompt must include all four required section headers and length guidance."""
    prompt = tarot_gpt.build_prompt(
        sample_drawn_cards[:1], "today", "오늘의 운세", "", sample_meanings
    )
    assert "한줄요약" in prompt
    assert "지금상태" in prompt
    assert "흐름" in prompt
    assert "지금 해야할것" in prompt
    assert "500~700자" in prompt
    # The new format must NOT ask for JSON output
    assert '"summary"' not in prompt
    assert '"insight"' not in prompt



def test_generate_reading_returns_error_when_api_key_missing(
    monkeypatch, sample_drawn_cards, sample_meanings
):
    monkeypatch.delenv(tarot_gpt.OPENAI_API_KEY_ENV, raising=False)
    with mock.patch.dict("sys.modules", {"streamlit": None}):
        reading, error = tarot_gpt.generate_reading(
            sample_drawn_cards, "love", "연애운", "", sample_meanings
        )
    assert reading is None
    assert error is not None
    assert "OpenAI API 키가 설정되지" in error


def test_generate_reading_returns_error_when_openai_missing(
    monkeypatch, sample_drawn_cards, sample_meanings
):
    monkeypatch.setenv(tarot_gpt.OPENAI_API_KEY_ENV, "sk-fake-key")
    with mock.patch.dict("sys.modules", {"openai": None}):
        reading, error = tarot_gpt.generate_reading(
            sample_drawn_cards, "love", "연애운", "", sample_meanings
        )
    assert reading is None
    assert error is not None


def test_generate_reading_calls_openai_and_returns_text(
    monkeypatch, sample_drawn_cards, sample_meanings
):
    monkeypatch.setenv(tarot_gpt.OPENAI_API_KEY_ENV, "sk-fake-key")

    fake_text = "## 1. 종합 요약\n이것은 테스트 리딩입니다."

    mock_response = mock.MagicMock()
    mock_response.choices[0].message.content = fake_text

    mock_client_instance = mock.MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_response

    mock_openai_module = mock.MagicMock()
    mock_openai_module.OpenAI.return_value = mock_client_instance

    with mock.patch.dict("sys.modules", {"openai": mock_openai_module}):
        reading, error = tarot_gpt.generate_reading(
            sample_drawn_cards, "love", "연애운", "테스트 질문", sample_meanings
        )

    assert error is None
    assert reading == fake_text
    mock_client_instance.chat.completions.create.assert_called_once()


def test_generate_reading_returns_error_on_api_exception(
    monkeypatch, sample_drawn_cards, sample_meanings
):
    monkeypatch.setenv(tarot_gpt.OPENAI_API_KEY_ENV, "sk-fake-key")

    mock_client_instance = mock.MagicMock()
    mock_client_instance.chat.completions.create.side_effect = RuntimeError("timeout")

    mock_openai_module = mock.MagicMock()
    mock_openai_module.OpenAI.return_value = mock_client_instance

    with mock.patch.dict("sys.modules", {"openai": mock_openai_module}):
        reading, error = tarot_gpt.generate_reading(
            sample_drawn_cards, "love", "연애운", "", sample_meanings
        )

    assert reading is None
    assert error is not None
    assert "오류" in error


def test_generate_reading_passes_correct_model(
    monkeypatch, sample_drawn_cards, sample_meanings
):
    monkeypatch.setenv(tarot_gpt.OPENAI_API_KEY_ENV, "sk-fake-key")

    mock_response = mock.MagicMock()
    mock_response.choices[0].message.content = "리딩 텍스트"

    mock_client_instance = mock.MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_response

    mock_openai_module = mock.MagicMock()
    mock_openai_module.OpenAI.return_value = mock_client_instance

    with mock.patch.dict("sys.modules", {"openai": mock_openai_module}):
        tarot_gpt.generate_reading(
            sample_drawn_cards, "today", "오늘의 운세", "", sample_meanings
        )

    call_kwargs = mock_client_instance.chat.completions.create.call_args
    assert call_kwargs.kwargs.get("model") == tarot_gpt._GPT_MODEL
