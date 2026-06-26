"""Validate rendered data-layer OpenAPI documents before deployment."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

EXPECTED_INTEGRATION_TYPE = "aws_proxy"
EXPECTED_INTEGRATION_METHOD = "POST"
EXPECTED_PAYLOAD_FORMAT_VERSION = "2.0"
LAMBDA_INVOKE_URI_PREFIX = "arn:aws:apigateway:"
LAMBDA_INVOKE_URI_SUFFIX = "/invocations"
LAMBDA_PLACEHOLDER = "__LAMBDA_INVOKE_URI__"
HTTP_METHODS = {
    "delete",
    "get",
    "head",
    "options",
    "patch",
    "post",
    "put",
    "trace",
}


def main(argv: list[str] | None = None) -> int:
    """Validate a rendered OpenAPI document."""
    parser = argparse.ArgumentParser(
        description="Validate rendered data-layer OpenAPI YAML."
    )
    parser.add_argument("openapi_path", help="Path to rendered OpenAPI YAML.")
    args = parser.parse_args(argv)

    errors = validate_openapi(Path(args.openapi_path))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Validated OpenAPI document: {args.openapi_path}")
    return 0


def validate_openapi(openapi_path: Path) -> list[str]:
    """Return validation errors for the rendered OpenAPI document."""
    errors: list[str] = []
    document = _load_yaml(openapi_path, errors)
    if document is None:
        return errors

    _validate_top_level(document, errors)
    _validate_no_placeholder(document, errors)
    _validate_refs(document, errors)
    _validate_paths(document, errors)

    return errors


def _load_yaml(openapi_path: Path, errors: list[str]) -> dict[str, Any] | None:
    """Load an OpenAPI YAML document."""
    if not openapi_path.is_file():
        errors.append(f"OpenAPI document does not exist: {openapi_path}")
        return None

    try:
        document = yaml.safe_load(openapi_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(f"OpenAPI document is not valid YAML: {exc}")
        return None

    if not isinstance(document, dict):
        errors.append("OpenAPI document must be a mapping.")
        return None

    return document


def _validate_top_level(
    document: dict[str, Any],
    errors: list[str],
) -> None:
    """Validate required top-level OpenAPI fields."""
    openapi_version = document.get("openapi")
    if not isinstance(openapi_version, str) or not openapi_version:
        errors.append("Missing non-empty top-level 'openapi' version.")

    info = document.get("info")
    if not isinstance(info, dict):
        errors.append("Missing top-level 'info' object.")
    elif not info.get("title") or not info.get("version"):
        errors.append("OpenAPI 'info' must include title and version.")

    paths = document.get("paths")
    if not isinstance(paths, dict) or not paths:
        errors.append("Missing non-empty top-level 'paths' object.")


def _validate_no_placeholder(
    document: dict[str, Any],
    errors: list[str],
) -> None:
    """Validate rendered document no longer has deployment placeholders."""
    for location, value in _walk(document):
        if isinstance(value, str) and LAMBDA_PLACEHOLDER in value:
            errors.append(f"Unrendered Lambda placeholder at {location}.")


def _validate_refs(document: dict[str, Any], errors: list[str]) -> None:
    """Validate local OpenAPI references resolve."""
    for location, value in _walk(document):
        if not isinstance(value, dict):
            continue
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            if _resolve_ref(document, ref) is None:
                errors.append(
                    f"Unresolved local reference at {location}: {ref}"
                )


def _validate_paths(document: dict[str, Any], errors: list[str]) -> None:
    """Validate API Gateway integrations for every operation."""
    paths = document.get("paths")
    if not isinstance(paths, dict):
        return

    operation_count = 0
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            errors.append(f"Path item must be an object: {path}")
            continue

        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            operation_count += 1
            if not isinstance(operation, dict):
                errors.append(
                    f"Operation must be an object: {method.upper()} {path}"
                )
                continue
            _validate_integration(path, method, operation, errors)

    if operation_count == 0:
        errors.append("OpenAPI document must define at least one operation.")


def _validate_integration(
    path: str,
    method: str,
    operation: dict[str, Any],
    errors: list[str],
) -> None:
    """Validate one API Gateway integration block."""
    operation_label = f"{method.upper()} {path}"
    integration = operation.get("x-amazon-apigateway-integration")
    if not isinstance(integration, dict):
        errors.append(
            f"Missing API Gateway integration for {operation_label}."
        )
        return

    integration_type = integration.get("type")
    if integration_type != EXPECTED_INTEGRATION_TYPE:
        errors.append(
            f"{operation_label} integration type must be "
            f"{EXPECTED_INTEGRATION_TYPE!r}; got {integration_type!r}."
        )

    integration_method = integration.get("httpMethod")
    if integration_method != EXPECTED_INTEGRATION_METHOD:
        errors.append(
            f"{operation_label} integration httpMethod must be "
            f"{EXPECTED_INTEGRATION_METHOD!r}; got {integration_method!r}."
        )

    payload_format_version = str(integration.get("payloadFormatVersion", ""))
    if payload_format_version != EXPECTED_PAYLOAD_FORMAT_VERSION:
        errors.append(
            f"{operation_label} payloadFormatVersion must be "
            f"{EXPECTED_PAYLOAD_FORMAT_VERSION!r}; "
            f"got {payload_format_version!r}."
        )

    uri = integration.get("uri")
    if not isinstance(uri, str) or not uri:
        errors.append(f"{operation_label} integration uri must be non-empty.")
    elif not (
        uri.startswith(LAMBDA_INVOKE_URI_PREFIX)
        and uri.endswith(LAMBDA_INVOKE_URI_SUFFIX)
        and ":lambda:path/2015-03-31/functions/" in uri
    ):
        errors.append(
            f"{operation_label} integration uri is not a Lambda invoke URI."
        )


def _resolve_ref(document: dict[str, Any], ref: str) -> Any | None:
    """Resolve a local OpenAPI JSON pointer reference."""
    current: Any = document
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    """Yield all values in a nested mapping/list structure."""
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


if __name__ == "__main__":
    raise SystemExit(main())
