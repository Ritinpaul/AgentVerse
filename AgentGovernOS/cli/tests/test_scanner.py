import pytest
from pathlib import Path
from agentgovern.scanner.manifest import parse_manifest
from agentgovern.scanner.dependency import _scan_requirements_txt
from agentgovern.scanner.codeprint import _check_secrets

def test_manifest_parser(tmp_path: Path):
    manifest = tmp_path / "agentgovern.yaml"
    manifest.write_text("""
version: "1.0"
project: "Test"
agents:
  - code: "A-001"
    name: "Bot"
    framework: "crewai"
    tier: "T3"
    authority_limit: 500
    """)
    
    result = parse_manifest(manifest)
    assert result.is_valid
    assert len(result.agents) == 1
    assert result.agents[0].code == "A-001"
    assert result.agents[0].authority_limit == 500.0
    assert result.agents[0].tier == "T3"

def test_dependency_scanner(tmp_path: Path):
    req = tmp_path / "requirements.txt"
    req.write_text("crewai[tools]>=0.100.0\nlangchain==0.1.0\npandas")
    
    deps, errs = _scan_requirements_txt(req)
    assert len(errs) == 0
    frameworks = {d.framework for d in deps}
    assert "crewai" in frameworks
    assert "langchain" in frameworks

def test_codeprint_secret_detection(tmp_path: Path):
    content = 'api_key = "sk-ant-12345678901234567890123456789012345"\n'
    dets = _check_secrets(content, tmp_path / "main.py")
    assert len(dets) == 1
    assert dets[0].secret_type == "ANTHROPIC_API_KEY"
    assert "***" in dets[0].snippet or "REDACTED" in dets[0].snippet
