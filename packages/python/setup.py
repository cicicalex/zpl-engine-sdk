"""Setup configuration for ZPL Engine SDK.

NOTE: pyproject.toml is the source of truth for modern installs.
This setup.py exists for legacy tooling (e.g. `python setup.py install`,
some CI/Conda flows). Read the version from `zeropointlogic/version.py`
so we never re-diverge — pre-fix this file said 1.0.4 while pyproject
already shipped 2.0.3, and any tool reading setup.py would install a
broken pre-wire-shape-fix version that 400's every compute call.
"""

from setuptools import setup, find_packages
import os

def read_file(filename):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

def read_version():
    version_file = os.path.join(
        os.path.dirname(__file__), "zeropointlogic", "version.py"
    )
    with open(version_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"').strip("'")
    raise RuntimeError("__version__ not found in zeropointlogic/version.py")

setup(
    name="zeropointlogic",
    version=read_version(),
    description="Professional Python SDK for Zero Point Logic Engine API",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    author="Alex Cicic",
    author_email="cicicalex20@gmail.com",
    url="https://github.com/cicicalex/zpl-engine-sdk",
    license="MIT",
    packages=find_packages(exclude=["tests", "examples"]),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "async": ["httpx>=0.24.0"],
        "pandas": ["pandas>=1.5.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    keywords=[
        "zpl",
        "zeropointlogic",
        "api",
        "neutrality",
        "bias",
        "stability",
        "crypto",
        "finance",
        "sdk",
    ],
    project_urls={
        "Documentation": "https://github.com/cicicalex/zpl-engine-sdk",
        "Source Code": "https://github.com/cicicalex/zpl-engine-sdk",
        "Issue Tracker": "https://github.com/cicicalex/zpl-engine-sdk/issues",
        "Changelog": "https://github.com/cicicalex/zpl-engine-sdk/releases",
    },
)
