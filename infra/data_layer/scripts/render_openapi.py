"""Render data-layer OpenAPI documents for deployment."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

LAMBDA_PLACEHOLDER = "__LAMBDA_INVOKE_URI__"
PATH_ENABLED_KEY = "x-capital-alpha-enabled"
PATH_GROUP_KEY = "x-capital-alpha-group"


def main() -> int:
    """Render an OpenAPI source document."""
    parser = argparse.ArgumentParser(
        description="Render data-layer OpenAPI YAML for deployment."
    )
    parser.add_argument("--source", required=True, help="Source OpenAPI YAML.")
    parser.add_argument(
        "--output", required=True, help="Rendered OpenAPI YAML output path."
    )
    parser.add_argument(
        "--lambda-invoke-uri",
        required=True,
        help="Resolved API Gateway Lambda invoke URI.",
    )
    parser.add_argument(
        "--enable-account",
        action="store_true",
        help="Include account API paths in the rendered document.",
    )
    parser.add_argument(
        "--enable-fundamentals",
        action="store_true",
        help="Include fundamentals API paths in the rendered document.",
    )
    args = parser.parse_args()

    render_openapi(
        source_path=Path(args.source),
        output_path=Path(args.output),
        lambda_invoke_uri=args.lambda_invoke_uri,
        enable_account=args.enable_account,
        enable_fundamentals=args.enable_fundamentals,
    )
    return 0


def render_openapi(
    *,
    source_path: Path,
    output_path: Path,
    lambda_invoke_uri: str,
    enable_account: bool = False,
    enable_fundamentals: bool = False,
) -> None:
    """Render an OpenAPI source document for API Gateway import."""
    document = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("OpenAPI source document must be a mapping.")

    enabled_groups = {
        "account": enable_account,
        "fundamentals": enable_fundamentals,
    }
    _filter_paths(document, enabled_groups)
    _replace_placeholder(document, lambda_invoke_uri)

    output_path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )


def _filter_paths(
    document: dict[str, Any],
    enabled_groups: dict[str, bool],
) -> None:
    """Remove disabled paths from the rendered document."""
    paths = document.get("paths")
    if not isinstance(paths, dict):
        return

    for path, path_item in list(paths.items()):
        if not isinstance(path_item, dict):
            continue
        group = path_item.get(PATH_GROUP_KEY)
        enabled = path_item.get(PATH_ENABLED_KEY, True)
        group_enabled = enabled_groups.get(group, True)
        if enabled is False and not group_enabled:
            del paths[path]
            continue
        path_item.pop(PATH_ENABLED_KEY, None)
        path_item.pop(PATH_GROUP_KEY, None)


def _replace_placeholder(value: Any, lambda_invoke_uri: str) -> None:
    """Replace Lambda invoke placeholders in a nested document."""
    if isinstance(value, dict):
        for key, child in list(value.items()):
            if isinstance(child, str):
                value[key] = child.replace(
                    LAMBDA_PLACEHOLDER,
                    lambda_invoke_uri,
                )
            else:
                _replace_placeholder(child, lambda_invoke_uri)
    elif isinstance(value, list):
        for child in value:
            _replace_placeholder(child, lambda_invoke_uri)


if __name__ == "__main__":
    raise SystemExit(main())
