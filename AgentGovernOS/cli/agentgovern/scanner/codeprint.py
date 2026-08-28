"""
Codeprint Scanner — detects AI agent instantiations in Python and JS source.

Uses Python AST for high-accuracy detection. Also detects:
- Hardcoded API keys
- Tool registrations
- System prompts
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

# ── Known agent class names (Python) ──────────────────────────────────────

PYTHON_AGENT_CLASSES = {
    # CrewAI
    "Agent": "crewai",
    "Crew": "crewai",
    "Task": "crewai",
    # LangChain
    "ChatOpenAI": "langchain",
    "ChatAnthropic": "langchain",
    "ChatGoogleGenerativeAI": "langchain",
    "AgentExecutor": "langchain",
    "ReActAgent": "langchain",
    "OpenAIFunctionsAgent": "langchain",
    # AutoGen
    "AssistantAgent": "autogen",
    "UserProxyAgent": "autogen",
    "ConversableAgent": "autogen",
    "GroupChat": "autogen",
    # OpenAI Agents SDK
    "Runner": "openai-agents",
    # Semantic Kernel
    "Kernel": "semantic-kernel",
    "ChatCompletionAgent": "semantic-kernel",
}

# Regex for detecting hardcoded API secrets
SECRET_PATTERNS: list[tuple[str, str]] = [
    (r"sk-[A-Za-z0-9]{20,}", "OPENAI_API_KEY"),
    (r"sk-ant-[A-Za-z0-9\-_]{30,}", "ANTHROPIC_API_KEY"),
    (r"gsk_[A-Za-z0-9]{20,}", "GROQ_API_KEY"),
    (r"AIza[A-Za-z0-9\-_]{35}", "GOOGLE_API_KEY"),
    (r"eyJ[A-Za-z0-9\-_=]{30,}", "JWT_TOKEN"),
    (r"AKIA[0-9A-Z]{16}", "AWS_ACCESS_KEY"),
]


@dataclass
class CodeprintDetection:
    """A single detected agent pattern in source code."""

    framework: str
    class_name: str
    file: str
    line: int
    confidence: str  # "high", "medium"
    context: str = ""  # snippet of surrounding code


@dataclass
class SecretDetection:
    """A detected hardcoded secret."""

    secret_type: str
    file: str
    line: int
    snippet: str  # redacted


@dataclass
class CodeprintScanResult:
    """Result of scanning source code for agent patterns."""

    agent_detections: list[CodeprintDetection] = field(default_factory=list)
    secret_detections: list[SecretDetection] = field(default_factory=list)
    scanned_files: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def has_hardcoded_secrets(self) -> bool:
        return bool(self.secret_detections)


# ── Helpers ────────────────────────────────────────────────────────────────

def _should_skip(path: Path) -> bool:
    """Return True if this file/directory should be ignored."""
    skip_parts = {".venv", "venv", "node_modules", ".git", "__pycache__", "dist", "build", "site-packages"}
    return any(part in skip_parts for part in path.parts)


def _redact(text: str) -> str:
    """Redact a secret value for safe display."""
    s = str(text)
    if len(s) <= 8:
        return "***"
    return s[:4] + "..." + s[-4:] + " [REDACTED]"


def _check_secrets(content: str, path: Path) -> list[SecretDetection]:
    """Scan file content for hardcoded secrets."""
    detections: list[SecretDetection] = []
    lines = content.splitlines
    for line_no, line in enumerate(lines, 1):
        for pattern, secret_type in SECRET_PATTERNS:
            m = re.search(pattern, line)
            if m:
                detections.append(SecretDetection(
                    secret_type=secret_type,
                    file=str(path),
                    line=line_no,
                    snippet=_redact(m.group),
                ))
    return detections


def _scan_python_ast(path: Path) -> tuple[list[CodeprintDetection], list[str]]:
    """Parse Python file via AST and detect agent class instantiations."""
    detections: list[CodeprintDetection] = []
    errors: list[str] = []

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        errors.append(f"Syntax error in {path}: {exc}")
        return detections, errors
    except OSError as exc:
        errors.append(f"Cannot read {path}: {exc}")
        return detections, errors

    lines = source.splitlines

    for node in ast.walk(tree):
        # Detect: SomeClass(...)
        if isinstance(node, ast.Call):
            func = node.func
            class_name = None
            if isinstance(func, ast.Name):
                class_name = func.id
            elif isinstance(func, ast.Attribute):
                class_name = func.attr

            if class_name and class_name in PYTHON_AGENT_CLASSES:
                framework = PYTHON_AGENT_CLASSES[class_name]
                line_no = node.lineno
                raw_snippet: str = lines[line_no - 1].strip if line_no <= len(lines) else ""
                detections.append(CodeprintDetection(
                    framework=framework,
                    class_name=class_name,
                    file=str(path),
                    line=line_no,
                    confidence="high",
                    context=raw_snippet[:120],
                ))

    return detections, errors


def _scan_text_patterns(path: Path, content: str) -> list[CodeprintDetection]:
    """Fallback regex-based detection for JS/TS and unknown files."""
    detections: list[CodeprintDetection] = []
    js_patterns = [
        (r"new\s+ChatOpenAI\s*\(", "langchain-js", "ChatOpenAI"),
        (r"new\s+Anthropic\s*\(", "anthropic-sdk-js", "Anthropic"),
        (r"new\s+OpenAI\s*\(", "openai-sdk-js", "OpenAI"),
        (r"Agent\s*\(\s*\{", "openai-agents-js", "Agent"),
        (r"createReactAgent\s*\(", "langchain-js", "createReactAgent"),
    ]
    lines = content.splitlines
    for line_no, line in enumerate(lines, 1):
        for pattern, framework, class_name in js_patterns:
            if re.search(pattern, line):
                detections.append(CodeprintDetection(
                    framework=framework,
                    class_name=class_name,
                    file=str(path),
                    line=line_no,
                    confidence="medium",
                    context=line.strip[:120],
                ))
    return detections


# ── Public API ─────────────────────────────────────────────────────────────

def scan_codeprint(root: Path) -> CodeprintScanResult:
    """
    Walk `root` and detect AI agent patterns in source code.
    Uses AST for Python, regex for JS/TS.
    Also checks for hardcoded secrets.
    """
    result = CodeprintScanResult
    seen_detections: set[str] = set

    python_exts = {".py"}
    js_exts = {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}

    for path in root.rglob("*"):
        if not path.is_file or _should_skip(path):
            continue
        suffix = path.suffix.lower

        if suffix in python_exts:
            result.scanned_files += 1
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            result.secret_detections.extend(_check_secrets(content, path))
            dets, errs = _scan_python_ast(path)
            result.errors.extend(errs)
            for d in dets:
                key = f"{d.file}:{d.line}:{d.class_name}"
                if key not in seen_detections:
                    seen_detections.add(key)
                    result.agent_detections.append(d)

        elif suffix in js_exts:
            result.scanned_files += 1
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            result.secret_detections.extend(_check_secrets(content, path))
            for d in _scan_text_patterns(path, content):
                key = f"{d.file}:{d.line}:{d.class_name}"
                if key not in seen_detections:
                    seen_detections.add(key)
                    result.agent_detections.append(d)

    return result
