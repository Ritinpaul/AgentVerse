"""
Dependency Scanner — detects AI agent frameworks from project dependency files.

Supports:
  - requirements.txt
  - pyproject.toml  (PEP 517/518)
  - package.json    (Node.js)
  - Pipfile
  - setup.py / setup.cfg (basic detection)
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# ── Known framework signatures ─────────────────────────────────────────────

# Maps package name pattern → normalized framework name
PYTHON_FRAMEWORK_PATTERNS: dict[str, str] = {
    r"crewai": "crewai",
    r"langchain[_\-]?core": "langchain",
    r"langchain[_\-]?community": "langchain",
    r"langchain[_\-]?openai": "langchain",
    r"langchain[_\-]?anthropic": "langchain",
    r"^langchain$": "langchain",
    r"pyautogen": "autogen",
    r"autogen[_\-]?agentchat": "autogen",
    r"openai[_\-]?agents": "openai-agents",
    r"llama[_\-]?index": "llamaindex",
    r"llama[_\-]?index[_\-]?core": "llamaindex",
    r"semantic[_\-]?kernel": "semantic-kernel",
    r"google[_\-]?adk": "google-adk",
    r"anthropic": "anthropic-sdk",
    r"openai": "openai-sdk",
    r"google[_\-]?generativeai": "google-ai-sdk",
    r"google[_\-]?genai": "google-ai-sdk",
    r"groq": "groq-sdk",
}

JS_FRAMEWORK_PATTERNS: dict[str, str] = {
    r"@langchain/core": "langchain-js",
    r"langchain": "langchain-js",
    r"@langchain/openai": "langchain-js",
    r"openai": "openai-sdk-js",
    r"anthropic": "anthropic-sdk-js",
    r"@anthropic-ai/sdk": "anthropic-sdk-js",
    r"@google/genai": "google-ai-sdk-js",
}

# Packages that are ONLY used in AI agent scenarios (high confidence)
HIGH_CONFIDENCE_AGENTS = {"crewai", "autogen", "openai-agents", "semantic-kernel", "google-adk"}


@dataclass
class DetectedDependency:
    """One detected AI framework dependency."""

    framework: str
    package: str
    version: str | None
    source_file: str
    high_confidence: bool = False


@dataclass
class DependencyScanResult:
    """Result of scanning all dependency files in a project."""

    detected: list[DetectedDependency] = field(default_factory=list)
    scanned_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def frameworks(self) -> set[str]:
        return {d.framework for d in self.detected}

    @property
    def has_agents(self) -> bool:
        return bool(self.detected)


# ── Helpers ────────────────────────────────────────────────────────────────

def _match_framework(package_name: str, patterns: dict[str, str]) -> str | None:
    pkg = package_name.lower.strip
    for pattern, framework in patterns.items:
        if re.search(pattern, pkg, re.IGNORECASE):
            return framework
    return None


def _parse_requirement_line(line: str) -> tuple[str, str | None] | None:
    """Parse a single requirements.txt line → (package, version) or None."""
    line = line.strip
    if not line or line.startswith("#") or line.startswith("-"):
        return None
    # Strip extras and markers: crewai[tools]>=0.100.0 ; python_requires>="3.11"
    m = re.match(r"^([A-Za-z0-9_\-\.]+)(\[.*?\])?([><=!~^]+.*?)?(?:\s*;.*)?$", line)
    if not m:
        return None
    pkg = m.group(1)
    ver = m.group(3).strip if m.group(3) else None
    return pkg, ver


# ── File-specific parsers ──────────────────────────────────────────────────

def _scan_requirements_txt(path: Path) -> tuple[list[DetectedDependency], list[str]]:
    detected: list[DetectedDependency] = []
    errors: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines:
            parsed = _parse_requirement_line(line)
            if not parsed:
                continue
            pkg, ver = parsed
            framework = _match_framework(pkg, PYTHON_FRAMEWORK_PATTERNS)
            if framework:
                detected.append(DetectedDependency(
                    framework=framework,
                    package=pkg,
                    version=ver,
                    source_file=str(path),
                    high_confidence=framework in HIGH_CONFIDENCE_AGENTS,
                ))
    except OSError as e:
        errors.append(f"Could not read {path}: {e}")
    return detected, errors


def _scan_pyproject_toml(path: Path) -> tuple[list[DetectedDependency], list[str]]:
    detected: list[DetectedDependency] = []
    errors: list[str] = []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        dep_lists: list[list[str]] = []

        # [project].dependencies
        proj_deps = data.get("project", {}).get("dependencies", [])
        dep_lists.append(proj_deps)

        # [tool.poetry.dependencies]
        poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        dep_lists.append(list(poetry_deps.keys))

        for dep_list in dep_lists:
            for dep in dep_list:
                parsed = _parse_requirement_line(dep)
                if not parsed:
                    continue
                pkg, ver = parsed
                framework = _match_framework(pkg, PYTHON_FRAMEWORK_PATTERNS)
                if framework:
                    detected.append(DetectedDependency(
                        framework=framework,
                        package=pkg,
                        version=ver,
                        source_file=str(path),
                        high_confidence=framework in HIGH_CONFIDENCE_AGENTS,
                    ))
    except (OSError, tomllib.TOMLDecodeError) as e:
        errors.append(f"Could not parse {path}: {e}")
    return detected, errors


def _scan_package_json(path: Path) -> tuple[list[DetectedDependency], list[str]]:
    import json
    detected: list[DetectedDependency] = []
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        all_deps = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }
        for pkg, ver in all_deps.items:
            framework = _match_framework(pkg, JS_FRAMEWORK_PATTERNS)
            if framework:
                detected.append(DetectedDependency(
                    framework=framework,
                    package=pkg,
                    version=ver,
                    source_file=str(path),
                    high_confidence=False,
                ))
    except (OSError, json.JSONDecodeError) as e:
        errors.append(f"Could not parse {path}: {e}")
    return detected, errors


def _scan_pipfile(path: Path) -> tuple[list[DetectedDependency], list[str]]:
    detected: list[DetectedDependency] = []
    errors: list[str] = []
    try:
        import tomllib
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        packages = {**data.get("packages", {}), **data.get("dev-packages", {})}
        for pkg, ver_spec in packages.items:
            ver = ver_spec if isinstance(ver_spec, str) else None
            framework = _match_framework(pkg, PYTHON_FRAMEWORK_PATTERNS)
            if framework:
                detected.append(DetectedDependency(
                    framework=framework,
                    package=pkg,
                    version=ver,
                    source_file=str(path),
                    high_confidence=framework in HIGH_CONFIDENCE_AGENTS,
                ))
    except Exception as e:
        errors.append(f"Could not parse Pipfile {path}: {e}")
    return detected, errors


# ── Public API ─────────────────────────────────────────────────────────────

def scan_dependencies(root: Path) -> DependencyScanResult:
    """Scan all dependency files under `root` for AI agent frameworks."""
    result = DependencyScanResult
    seen: set[str] = set  # deduplicate detections

    _scanners: list[tuple[str, Callable[[Path], tuple[list[DetectedDependency], list[str]]]]] = [
        ("requirements*.txt", _scan_requirements_txt),
        ("pyproject.toml", _scan_pyproject_toml),
        ("package.json", _scan_package_json),
        ("Pipfile", _scan_pipfile),
    ]

    for pattern, scanner_fn in _scanners:
        for path in root.rglob(pattern):
            # Skip venvs, node_modules etc.
            if any(part in {".venv", "venv", "node_modules", ".git", "__pycache__", "dist", "build"}
                   for part in path.parts):
                continue
            result.scanned_files.append(str(path))
            detections, errors = scanner_fn(path)
            result.errors.extend(errors)
            for det in detections:
                key = f"{det.framework}:{det.package}:{det.source_file}"
                if key not in seen:
                    seen.add(key)
                    result.detected.append(det)

    return result
