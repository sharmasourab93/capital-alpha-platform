"""Tests for SigV4 signing behavior."""

from __future__ import annotations

from datetime import datetime, timezone

from data_client.auth import AwsCredentials, SigV4Signer


def test_sigv4_signer_adds_api_gateway_auth_headers() -> None:
    """Verify signer produces the expected authorization header shape."""
    signer = SigV4Signer(
        AwsCredentials("AKID", "SECRET", "TOKEN"),
        region="ap-south-2",
    )

    headers = signer.sign(
        "GET",
        "https://abc.execute-api.ap-south-2.amazonaws.com/dev/health",
        headers={"Accept": "application/json"},
        now=datetime(2026, 6, 27, 5, 30, tzinfo=timezone.utc),
    )

    assert headers["Authorization"].startswith("AWS4-HMAC-SHA256 ")
    assert "Credential=AKID/20260627/ap-south-2/execute-api/aws4_request" in (
        headers["Authorization"]
    )
    assert "SignedHeaders=" in headers["Authorization"]
    assert headers["Host"] == "abc.execute-api.ap-south-2.amazonaws.com"
    assert headers["X-Amz-Date"] == "20260627T053000Z"
    assert headers["X-Amz-Security-Token"] == "TOKEN"


def test_sigv4_signature_is_stable_for_sorted_query_params() -> None:
    """Verify query canonicalization remains deterministic."""
    signer = SigV4Signer(
        AwsCredentials("AKID", "SECRET", "TOKEN"),
        region="ap-south-2",
    )

    headers = signer.sign(
        "GET",
        "https://abc.execute-api.ap-south-2.amazonaws.com/dev/health?b=two&a=one",
        headers={"Accept": "application/json"},
        now=datetime(2026, 6, 27, 5, 30, tzinfo=timezone.utc),
    )

    assert headers["Authorization"] == (
        "AWS4-HMAC-SHA256 "
        "Credential=AKID/20260627/ap-south-2/execute-api/aws4_request, "
        "SignedHeaders=accept;host;x-amz-content-sha256;x-amz-date;"
        "x-amz-security-token, "
        "Signature=ac1080ccce468e3923a687c9430bd0a194c3b7f5382c04980bf47ed858c02516"
    )
