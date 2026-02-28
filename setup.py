from setuptools import setup, find_packages
from pathlib import Path

readme = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")

setup(
    name="claude-guard",
    version="0.1.0",
    description="Lightweight guardrails for Claude agents — rule checking, injection detection, SQLite audit log.",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Jamie Cole",
    author_email="clawgenesis@gmail.com",
    url="https://github.com/GenesisClawbot/claude-guard",
    license="MIT",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.10",
    install_requires=[],  # stdlib only: re, json, sqlite3, hashlib, pathlib, datetime
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Security",
    ],
    keywords=[
        "claude", "anthropic", "guardrails", "agents",
        "safety", "audit", "injection-detection", "llm"
    ],
    project_urls={
        "Bug Tracker": "https://github.com/GenesisClawbot/claude-guard/issues",
        "Source Code": "https://github.com/GenesisClawbot/claude-guard",
    },
)
