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


def test_sigv4_signature_handles_encoded_query_and_body() -> None:
    """Verify signed requests are stable for encoded queries and JSON bodies."""
    signer = SigV4Signer(
        AwsCredentials(
            "AKIDEXAMPLE",
            "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY",
        ),
        region="us-east-1",
    )

    headers = signer.sign(
        "POST",
        "https://abc.execute-api.us-east-1.amazonaws.com/prod/"
        "market/angelone/NSE/quotes?symbol=SBIN%2CRELIANCE&space=a+b",
        body=b'{"mode":"LTP","symbols":["SBIN"]}',
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        now=datetime(2015, 8, 30, 12, 36, tzinfo=timezone.utc),
    )

    assert headers["X-Amz-Content-Sha256"] == (
        "a65bb7bd8ea70643f4a69b7e7ebf5a3b4d84fac9515b77b6c87d79bf2011427d"
    )
    assert headers["Authorization"] == (
        "AWS4-HMAC-SHA256 "
        "Credential=AKIDEXAMPLE/20150830/us-east-1/execute-api/aws4_request, "
        "SignedHeaders=accept;content-type;host;x-amz-content-sha256;"
        "x-amz-date, "
        "Signature=dce9e09b42451e7a864b72bd1e8d919f737f5d4144150170bc4a7be3730360fe"
    )
