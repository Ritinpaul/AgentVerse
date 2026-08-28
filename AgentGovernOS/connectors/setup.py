"""
Setup script for agentgovern-sdk.

This is provided for backwards compatibility with tools that don't support pyproject.toml.
For modern installations, use: pip install -e .
"""

from setuptools import find_packages, setup

setup(
    name="agentgovern-sdk",
    packages=find_packages(where="."),
    package_dir={"": "."},
)
