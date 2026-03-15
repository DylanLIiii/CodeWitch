from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

with open("README.md") as f:
    long_description = f.read()

setup(
    name="codewitch",
    version="0.1.0",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "cw=src.commands:app",
        ],
    },
    author="",
    description="Claude Code and Codex environment switcher CLI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
)
