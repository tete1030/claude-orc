"""Setup script for Claude Multi-Agent Orchestrator"""

from setuptools import setup, find_packages

setup(
    name="claude-orchestrator",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "watchdog>=2.1.0",
    ],
    python_requires=">=3.8",
    author="Claude Orchestrator Team",
    description="Multi-agent orchestration system for Claude",
    entry_points={
        "console_scripts": [
            "claude-orchestrator=orchestrator.main:main",
        ],
    },
)