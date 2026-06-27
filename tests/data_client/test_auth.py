"""Tests for AWS credential loading."""

from __future__ import annotations

import pytest

from data_client.auth import AwsCredentials
from data_client.exceptions import DataLayerClientConfigError


def test_credentials_from_env_loads_required_and_session_values() -> None:
    """Verify static and temporary AWS credentials are read consistently."""
    credentials = AwsCredentials.from_env(
        {
            "AWS_ACCESS_KEY_ID": " access ",
            "AWS_SECRET_ACCESS_KEY": " secret ",
            "AWS_SESSION_TOKEN": " token ",
        }
    )

    assert credentials.access_key_id == "access"
    assert credentials.secret_access_key == "secret"
    assert credentials.session_token == "token"


def test_credentials_from_env_allows_missing_session_token() -> None:
    """Verify long-lived credentials do not require AWS_SESSION_TOKEN."""
    credentials = AwsCredentials.from_env(
        {
            "AWS_ACCESS_KEY_ID": "access",
            "AWS_SECRET_ACCESS_KEY": "secret",
        }
    )

    assert credentials.session_token is None


def test_credentials_from_env_rejects_missing_required_value() -> None:
    """Verify credential misconfiguration fails before a signed request."""
    with pytest.raises(
        DataLayerClientConfigError, match="AWS_SECRET_ACCESS_KEY"
    ):
        AwsCredentials.from_env({"AWS_ACCESS_KEY_ID": "access"})
