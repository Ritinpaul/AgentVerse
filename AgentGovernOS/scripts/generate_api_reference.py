from __future__ import annotations

import json
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve.parents[1]
MAIN_PATH = ROOT / "services" / "governance-api" / "main.py"
OUTPUT_PATH = ROOT / "docs" / "API_REFERENCE.md"


def load_app:
    service_dir = str(MAIN_PATH.parent)
    if service_dir not in sys.path:
        sys.path.insert(0, service_dir)

    spec = importlib.util.spec_from_file_location("governance_api_main", MAIN_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load app from {MAIN_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def generate_markdown(openapi: dict) -> str:
    lines: list[str] = []
    lines.append("# API Reference")
    lines.append("")
    lines.append("Auto-generated from FastAPI OpenAPI schema.")
    lines.append("")

    paths = openapi.get("paths", {})
    for route in sorted(paths.keys):
        lines.append(f"## `{route}`")
        for method, operation in sorted(paths[route].items):
            summary = operation.get("summary") or operation.get("operationId", "")
            tags = ", ".join(operation.get("tags", []))
            lines.append(f"- **{method.upper}**: {summary}")
            if tags:
                lines.append(f"  - Tags: {tags}")
            if operation.get("requestBody"):
                lines.append("  - Request body: yes")
            responses = operation.get("responses", {})
            status_codes = ", ".join(sorted(responses.keys))
            lines.append(f"  - Responses: {status_codes}")
        lines.append("")

    return "\n".join(lines)


def main -> None:
    app = load_app
    openapi = app.openapi
    markdown = generate_markdown(openapi)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(markdown, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main
