"""
Setup script for AgentGovern CLI package.

This setup.py provides backwards compatibility with older build tools.
The canonical build configuration is in pyproject.toml (PEP 517/518).
"""

from pathlib import Path
from setuptools import setup, find_packages

# Read the README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists else ""

setup(
    name="agentgovern",
    use_scm_version=False,  # Version is specified in pyproject.toml
    description="The open-source AI Agent Governance scanner — Black Duck for AI Agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Ritin Paul",
    author_email="ritinpaul@example.com",
    url="https://github.com/Ritinpaul/AgentGovern-OS",
    license="Apache-2.0",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=[
        "typer>=0.12.0",
        "rich>=13.7.0",
        "pyyaml>=6.0.1",
        "httpx>=0.28.0",
        "jsonschema>=4.23.0",
        "pathspec>=0.12.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.0",
            "pytest-cov>=6.0.0",
            "ruff>=0.8.0",
        ],
        "watch": [
            "watchdog>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "agentgovern=agentgovern.cli:app",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security",
        "Topic :: Software Development :: Quality Assurance",
    ],
    keywords="ai agents governance security compliance llm crewai langchain",
)
