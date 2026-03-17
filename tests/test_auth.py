"""
Tests for the password authentication gate in app.py.

Run with:
    pytest tests/test_auth.py -v
"""
from __future__ import annotations

import sys
import unittest.mock as mock
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ── Module loader ─────────────────────────────────────────────────────────────

def _load_app_module():
    """Import app.py with an empty session_state and no secrets/env password."""
    import importlib.util

    def _cache_data_passthrough(func=None, **kwargs):
        if func is not None:
            return func  # @st.cache_data
        return lambda f: f  # @st.cache_data(show_spinner=False)

    mock_st = mock.MagicMock()
    mock_st.cache_data = _cache_data_passthrough
    mock_st.button.return_value = False
    mock_st.session_state = {}
    mock_st.secrets = {}  # no APP_PASSWORD in secrets

    with mock.patch.dict("sys.modules", {"streamlit": mock_st}):
        spec = importlib.util.spec_from_file_location("app", REPO_ROOT / "app.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


def _fresh_mock_st(session_state=None, secrets=None):
    """Return a fresh MagicMock that mimics the streamlit module."""
    st = mock.MagicMock()
    st.button.return_value = False
    st.text_input.return_value = ""
    st.session_state = session_state if session_state is not None else {}
    st.secrets = secrets if secrets is not None else {}
    return st


# ── Tests: _get_app_password ──────────────────────────────────────────────────

def test_get_app_password_from_env(monkeypatch):
    """_get_app_password falls back to the APP_PASSWORD env var."""
    monkeypatch.setenv("APP_PASSWORD", "env-secret")
    mod = _load_app_module()
    mock_st = _fresh_mock_st(secrets={})
    with mock.patch.object(mod, "st", mock_st):
        pw = mod._get_app_password()
    assert pw == "env-secret"


def test_get_app_password_prefers_secrets_over_env(monkeypatch):
    """st.secrets['APP_PASSWORD'] takes priority over the env var."""
    monkeypatch.setenv("APP_PASSWORD", "env-secret")
    mod = _load_app_module()
    mock_st = _fresh_mock_st(secrets={"APP_PASSWORD": "secrets-secret"})
    with mock.patch.object(mod, "st", mock_st):
        pw = mod._get_app_password()
    assert pw == "secrets-secret"


def test_get_app_password_strips_whitespace(monkeypatch):
    """_get_app_password strips leading/trailing whitespace."""
    monkeypatch.setenv("APP_PASSWORD", "  my-pw  ")
    mod = _load_app_module()
    mock_st = _fresh_mock_st(secrets={})
    with mock.patch.object(mod, "st", mock_st):
        pw = mod._get_app_password()
    assert pw == "my-pw"


def test_get_app_password_returns_empty_when_not_set(monkeypatch):
    """_get_app_password returns an empty string when APP_PASSWORD is absent."""
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    mod = _load_app_module()
    mock_st = _fresh_mock_st(secrets={})
    with mock.patch.object(mod, "st", mock_st):
        pw = mod._get_app_password()
    assert pw == ""


# ── Tests: _require_auth ──────────────────────────────────────────────────────

def test_require_auth_passes_when_authed(monkeypatch):
    """_require_auth returns without calling st.stop() when authed=True."""
    monkeypatch.setenv("APP_PASSWORD", "correct-pw")
    mod = _load_app_module()
    mock_st = _fresh_mock_st(
        session_state={"authed": True},
        secrets={},
    )
    with mock.patch.object(mod, "st", mock_st):
        mod._require_auth()
    mock_st.stop.assert_not_called()


def test_require_auth_stops_when_not_authed(monkeypatch):
    """_require_auth calls st.stop() when the user has not authenticated."""
    monkeypatch.setenv("APP_PASSWORD", "correct-pw")
    mod = _load_app_module()
    mock_st = _fresh_mock_st(session_state={}, secrets={})
    with mock.patch.object(mod, "st", mock_st):
        mod._require_auth()
    mock_st.stop.assert_called_once()


def test_require_auth_stops_when_password_not_configured(monkeypatch):
    """_require_auth calls st.stop() and shows an error when APP_PASSWORD is not set."""
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    mod = _load_app_module()
    mock_st = _fresh_mock_st(session_state={}, secrets={})
    with mock.patch.object(mod, "st", mock_st):
        mod._require_auth()
    mock_st.stop.assert_called_once()


def test_require_auth_sets_authed_on_correct_password(monkeypatch):
    """Correct password click sets session_state['authed'] = True and calls st.rerun()."""
    monkeypatch.setenv("APP_PASSWORD", "correct-pw")
    mod = _load_app_module()
    session = {}
    mock_st = _fresh_mock_st(session_state=session, secrets={})
    # Simulate user typing correct password and clicking login
    mock_st.text_input.return_value = "correct-pw"
    mock_st.button.return_value = True  # login button clicked

    with mock.patch.object(mod, "st", mock_st):
        mod._require_auth()

    assert session.get("authed") is True
    mock_st.rerun.assert_called_once()


def test_require_auth_shows_error_on_wrong_password(monkeypatch):
    """Wrong password click shows an error and does NOT set authed."""
    monkeypatch.setenv("APP_PASSWORD", "correct-pw")
    mod = _load_app_module()
    session = {}
    mock_st = _fresh_mock_st(session_state=session, secrets={})
    mock_st.text_input.return_value = "wrong-pw"
    mock_st.button.return_value = True  # login button clicked

    with mock.patch.object(mod, "st", mock_st):
        mod._require_auth()

    assert session.get("authed") is not True
    mock_st.rerun.assert_not_called()
    # st.error should have been called (inside the sidebar context block)
    mock_st.error.assert_called_once()
