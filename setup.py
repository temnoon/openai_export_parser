from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="openai-export-parser",
    version="0.2.0",
    author="OpenAI Export Parser Contributors",
    description="Parse and normalize OpenAI ChatGPT export archives",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/openai-export-parser",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "tqdm>=4.65.0",
        "python-dateutil>=2.8.0",
    ],
    entry_points={
        "console_scripts": [
            "openai-export-parser=openai_export_parser.cli:main",
            "openai-render-html=openai_export_parser.render_html:main",
        ]
    },
)
