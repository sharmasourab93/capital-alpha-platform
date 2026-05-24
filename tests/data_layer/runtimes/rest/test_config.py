"""Tests for REST runtime configuration."""

from data_layer.runtimes.rest.config import RestRuntimeSettings


def test_rest_runtime_settings_load_from_env(monkeypatch) -> None:
    """Verify REST runtime settings load from environment variables."""
    monkeypatch.setenv("REST_HOST", "0.0.0.0")
    monkeypatch.setenv("REST_PORT", "9000")
    monkeypatch.setenv("REST_RELOAD", "true")
    monkeypatch.setenv("REST_LOG_LEVEL", "info")

    settings = RestRuntimeSettings.from_env()

    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.reload is True
    assert settings.log_level == "info"
