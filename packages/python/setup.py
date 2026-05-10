"""Setup configuration for ZPL Engine SDK."""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_file(filename):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

setup(
    name="zeropointlogic",
    version="1.0.0",
    description="Professional Python SDK for Zero Point Logic Engine API",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    author="Alex Cicic",
    author_email="cicicalex20@gmail.com",
    url="https://github.com/zeropointlogic/zpl-python-sdk",
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
        "Documentation": "https://github.com/zeropointlogic/zpl-python-sdk",
        "Source Code": "https://github.com/zeropointlogic/zpl-python-sdk",
        "Issue Tracker": "https://github.com/zeropointlogic/zpl-python-sdk/issues",
        "Changelog": "https://github.com/zeropointlogic/zpl-python-sdk/releases",
    },
)
