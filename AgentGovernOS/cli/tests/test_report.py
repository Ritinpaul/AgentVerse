import pytest
from pathlib import Path
from agentgovern.report.abom import build_abom
from agentgovern.report.sarif import build_sarif
from agentgovern.report.html import build_html_report, save_html_report
from agentgovern.scanner.manifest import ManifestParseResult, AgentDefinition
from agentgovern.scanner.dependency import DependencyScanResult
from agentgovern.scanner.codeprint import CodeprintScanResult
from agentgovern.scanner.authority import AuthorityAnalysisResult
from agentgovern.policy.engine import PolicyCheckResult, PolicyViolation

def test_build_abom:
    agent = AgentDefinition(code="A-001", name="Bot", framework="crewai", tier="T3", authority_limit=100)
    mr = ManifestParseResult(path=None, project="Test", version="1", agents=[agent])
    dr = DependencyScanResult
    cr = CodeprintScanResult
    ar = AuthorityAnalysisResult
    pr = PolicyCheckResult

    abom = build_abom("TestProj", [mr], dr, cr, ar, pr)
    assert abom["project"] == "TestProj"
    assert abom["summary"]["total_agents"] == 1
    assert abom["summary"]["overall_pass"] is True
    assert len(abom["agents"]) == 1
    assert abom["agents"][0]["code"] == "A-001"

def test_build_sarif:
    pr = PolicyCheckResult
    pr.add(PolicyViolation(
        rule_id="TEST-001",
        rule_name="Test Rule",
        severity="HIGH",
        agent_code="A-001",
        message="Violated stuff",
        suggestion="Fix it"
    ))
    cr = CodeprintScanResult
    sarif = build_sarif(pr, cr)
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"][0]["results"]) == 1
    assert sarif["runs"][0]["results"][0]["ruleId"] == "TEST-001"

def test_build_html_report:
    """Test HTML report generation."""
    # Create test data
    agent = AgentDefinition(code="A-001", name="Test Bot", framework="crewai", tier="T3", authority_limit=1000)
    mr = ManifestParseResult(path=None, project="TestProj", version="1", agents=[agent])
    dr = DependencyScanResult
    cr = CodeprintScanResult
    ar = AuthorityAnalysisResult
    pr = PolicyCheckResult

    # Build ABOM first
    abom = build_abom("TestProj", [mr], dr, cr, ar, pr)

    # Build HTML report
    html = build_html_report(abom, pr, cr)

    # Verify HTML structure
    assert "<!DOCTYPE html>" in html
    assert "<html lang=\"en\">" in html
    assert "AgentGovern OS" in html
    assert "TestProj" in html
    assert "A-001" in html
    assert "Test Bot" in html
    assert "Executive Summary" in html
    assert "Detected Agents" in html

def test_build_html_with_violations:
    """Test HTML report with policy violations."""
    agent = AgentDefinition(code="A-002", name="Risky Bot", framework="langchain", tier="T4", authority_limit=50000)
    mr = ManifestParseResult(path=None, project="TestProj", version="1", agents=[agent])
    dr = DependencyScanResult
    cr = CodeprintScanResult
    ar = AuthorityAnalysisResult

    # Add violations
    pr = PolicyCheckResult
    pr.add(PolicyViolation(
        rule_id="AUTH-001",
        rule_name="Authority Limit Exceeded",
        severity="CRITICAL",
        agent_code="A-002",
        message="Authority limit of 50000 exceeds tier maximum",
        suggestion="Reduce authority limit or upgrade tier"
    ))
    pr.add(PolicyViolation(
        rule_id="TIER-001",
        rule_name="Tier Validation",
        severity="HIGH",
        agent_code="A-002",
        message="T4 tier should not exceed 25000",
        suggestion="Review tier assignment"
    ))

    abom = build_abom("TestProj", [mr], dr, cr, ar, pr)
    abom["summary"]["overall_pass"] = False
    abom["summary"]["critical"] = 1
    abom["summary"]["high"] = 1

    html = build_html_report(abom, pr, cr)

    # Verify violations are shown
    assert "Policy Violations" in html
    assert "AUTH-001" in html
    assert "TIER-001" in html
    assert "CRITICAL" in html
    assert "HIGH" in html
    assert "FAILED" in html or "✗" in html

def test_build_html_with_secrets:
    """Test HTML report with detected secrets."""
    from agentgovern.scanner.codeprint import SecretDetection

    agent = AgentDefinition(code="A-003", name="Bot", framework="crewai", tier="T2", authority_limit=100)
    mr = ManifestParseResult(path=None, project="TestProj", version="1", agents=[agent])
    dr = DependencyScanResult
    ar = AuthorityAnalysisResult
    pr = PolicyCheckResult

    # Add secret detections
    cr = CodeprintScanResult
    cr.secret_detections.append(SecretDetection(
        secret_type="ANTHROPIC_API_KEY",
        file="src/config.py",
        line=42,
        snippet="api_key = 'sk-ant-***'"
    ))
    cr.secret_detections.append(SecretDetection(
        secret_type="OPENAI_API_KEY",
        file="src/main.py",
        line=15,
        snippet="OPENAI_KEY = 'sk-***'"
    ))

    abom = build_abom("TestProj", [mr], dr, cr, ar, pr)
    abom["summary"]["hardcoded_secrets"] = 2

    html = build_html_report(abom, pr, cr)

    # Verify secrets section
    assert "Hardcoded Secrets" in html
    assert "ANTHROPIC_API_KEY" in html
    assert "OPENAI_API_KEY" in html
    assert "src/config.py" in html
    assert "src/main.py" in html

def test_build_html_with_frameworks:
    """Test HTML report with detected frameworks."""
    from agentgovern.scanner.dependency import FrameworkDetection

    agent = AgentDefinition(code="A-004", name="Bot", framework="crewai", tier="T3", authority_limit=1000)
    mr = ManifestParseResult(path=None, project="TestProj", version="1", agents=[agent])
    ar = AuthorityAnalysisResult
    pr = PolicyCheckResult
    cr = CodeprintScanResult

    # Add framework detections
    dr = DependencyScanResult
    dr.detected.append(FrameworkDetection(
        framework="crewai",
        package="crewai[tools]",
        source_file="requirements.txt",
        high_confidence=True
    ))
    dr.detected.append(FrameworkDetection(
        framework="langchain",
        package="langchain-core",
        source_file="pyproject.toml",
        high_confidence=True
    ))
    dr.frameworks.add("crewai")
    dr.frameworks.add("langchain")

    abom = build_abom("TestProj", [mr], dr, cr, ar, pr)
    abom["frameworks_detected"] = [
        {
            "framework": "crewai",
            "package": "crewai[tools]",
            "source_file": "requirements.txt",
            "high_confidence": True
        },
        {
            "framework": "langchain",
            "package": "langchain-core",
            "source_file": "pyproject.toml",
            "high_confidence": True
        }
    ]

    html = build_html_report(abom, pr, cr)

    # Verify frameworks section
    assert "AI Frameworks Detected" in html
    assert "crewai" in html
    assert "langchain" in html
    assert "HIGH CONFIDENCE" in html

def test_save_html_report(tmp_path: Path):
    """Test saving HTML report to file."""
    html_content = "<!DOCTYPE html><html><body>Test</body></html>"
    output_file = tmp_path / "report.html"

    save_html_report(html_content, output_file)

    assert output_file.exists
    assert output_file.read_text(encoding="utf-8") == html_content

def test_html_css_embedded:
    """Test that HTML report includes embedded CSS."""
    agent = AgentDefinition(code="A-001", name="Bot", framework="crewai", tier="T3", authority_limit=100)
    mr = ManifestParseResult(path=None, project="Test", version="1", agents=[agent])
    dr = DependencyScanResult
    cr = CodeprintScanResult
    ar = AuthorityAnalysisResult
    pr = PolicyCheckResult

    abom = build_abom("TestProj", [mr], dr, cr, ar, pr)
    html = build_html_report(abom, pr, cr)

    # Verify CSS is embedded
    assert "<style>" in html
    assert "</style>" in html
    assert "font-family" in html
    assert "background" in html
    assert "color" in html

def test_html_metadata_section:
    """Test that HTML report includes metadata section."""
    agent = AgentDefinition(code="A-001", name="Bot", framework="crewai", tier="T3", authority_limit=100)
    mr = ManifestParseResult(path=None, project="TestProj", version="1", agents=[agent])
    dr = DependencyScanResult
    cr = CodeprintScanResult
    ar = AuthorityAnalysisResult
    pr = PolicyCheckResult

    abom = build_abom("TestProj", [mr], dr, cr, ar, pr)
    html = build_html_report(abom, pr, cr)

    # Verify metadata
    assert "Scan Metadata" in html
    assert "Project:" in html
    assert "Scan Time:" in html
    assert "Duration:" in html

