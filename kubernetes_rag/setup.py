from setuptools import setup, find_packages

setup(
    name="kubernetes-rag",
    version="0.1.0",
    description="Comprehensive RAG System for Kubernetes Learning and Testing",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        line.strip()
        for line in open("requirements.txt").readlines()
        if line.strip() and not line.startswith("#")
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "k8s-rag=src.cli:main",
        ],
    },
)
