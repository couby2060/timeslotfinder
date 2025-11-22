"""
Setup script for timeslotfinder package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="timeslotfinder",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Find available meeting slots using Microsoft Graph API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/timeslotfinder",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "timeslotfinder=src.cli.app:app",
        ],
    },
    include_package_data=True,
)

