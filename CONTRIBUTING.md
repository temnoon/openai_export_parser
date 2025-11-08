# Contributing to openai-export-parser

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Be respectful, constructive, and helpful. We're all here to make this tool better.

## How to Contribute

### Reporting Bugs

1. Check existing [issues](https://github.com/yourusername/openai-export-parser/issues) to avoid duplicates
2. Use the bug report template
3. Include:
   - Your OS, Python version, and package version
   - Export format details (when downloaded, account type)
   - Full error output with `--verbose` flag
   - Steps to reproduce

### Suggesting Features

1. Check existing [issues](https://github.com/yourusername/openai-export-parser/issues) and [discussions](https://github.com/yourusername/openai-export-parser/discussions)
2. Use the feature request template
3. Explain the use case and expected behavior
4. Provide examples if possible

### Contributing Code

#### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/openai-export-parser.git
cd openai-export-parser

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

#### Development Workflow

1. **Fork and clone** the repository
2. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes** following our coding standards (see below)

4. **Run tests** to ensure everything works:
   ```bash
   pytest tests/ -v
   ```

5. **Check formatting**:
   ```bash
   black openai_export_parser/ tests/
   flake8 openai_export_parser/
   ```

6. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add feature: descriptive message"
   ```

7. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Open a Pull Request** using the PR template

## Coding Standards

### Style

- Use [Black](https://github.com/psf/black) for formatting (line length 88)
- Follow [PEP 8](https://pep8.org/) conventions
- Use type hints where helpful
- Write docstrings for public functions/classes

### Documentation

- Update README.md if adding user-facing features
- Add docstrings to new functions/classes
- Include inline comments for complex logic
- Update schema documentation if format changes

### Testing

- Write tests for new functionality
- Aim for high coverage on core parsing logic
- Test edge cases (empty exports, malformed data)
- Use descriptive test names

#### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=openai_export_parser --cov-report=term-missing

# Run specific test file
pytest tests/test_media_matcher.py -v

# Run specific test
pytest tests/test_basic_parse.py::test_parser_initialization -v
```

## Project Structure

```
openai-export-parser/
├── openai_export_parser/     # Main package
│   ├── __init__.py           # Package exports
│   ├── cli.py                # Command-line interface
│   ├── parser.py             # Main parsing logic
│   ├── media_matcher.py      # Media file matching
│   ├── schema_inference.py   # Schema detection
│   ├── threader.py           # Conversation threading
│   ├── utils.py              # Utility functions
│   └── version.py            # Version string
├── tests/                    # Test suite
│   ├── test_basic_parse.py
│   ├── test_media_matcher.py
│   ├── test_schema_inference.py
│   └── test_utils.py
├── .github/                  # GitHub configuration
│   ├── workflows/            # CI/CD workflows
│   └── ISSUE_TEMPLATE/       # Issue templates
├── README.md                 # User documentation
├── CONTRIBUTING.md           # This file
├── LICENSE                   # MIT License
├── setup.py                  # Package setup
└── pyproject.toml            # Modern packaging config
```

## Architecture Overview

### Core Components

1. **ExportParser** (`parser.py`)
   - Main orchestration class
   - Handles zip extraction, scanning, loading
   - Coordinates other components

2. **MediaMatcher** (`media_matcher.py`)
   - Links media files to messages
   - Uses regex patterns (file IDs, UUIDs)

3. **SchemaInference** (`schema_inference.py`)
   - Detects message/conversation structure
   - Future-proofs against format changes

4. **ConversationThreader** (`threader.py`)
   - Adds parent/child relationships
   - Enables tree visualization

### Data Flow

```
export.zip
    ↓ (unzip + scan)
conversation files + media files
    ↓ (load + normalize)
parsed conversations
    ↓ (media matching + threading)
enriched conversations
    ↓ (schema inference + output)
conversations/ + media/ + index.json
```

## Adding New Features

### Example: Adding a New Schema Detection

1. **Edit `schema_inference.py`**:
   ```python
   def infer_message_schema(self, msg):
       return {
           # ... existing fields ...
           "has_new_feature": self._detect_new_feature(msg),
       }

   def _detect_new_feature(self, msg):
       # Your detection logic
       return "new_field" in msg
   ```

2. **Add tests in `test_schema_inference.py`**:
   ```python
   def test_detect_new_feature():
       infer = SchemaInference()
       msg = {"new_field": "value"}
       schema = infer.infer_message_schema(msg)
       assert schema["has_new_feature"] is True
   ```

3. **Update README** with usage examples

4. **Submit PR** with description of the change

## OpenAI Export Format Changes

If OpenAI changes their export format:

1. **Document the change** - What's different? When did it start?
2. **Add detection logic** - Update `SchemaInference` to recognize it
3. **Handle both formats** - Maintain backward compatibility
4. **Add tests** - Create fixtures for the new format
5. **Update README** - Note the format variation

## Release Process

(For maintainers)

1. Update `version.py` and `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Create release on GitHub
5. Build and upload to PyPI:
   ```bash
   python -m build
   twine upload dist/*
   ```

## Questions?

- Open a [Discussion](https://github.com/yourusername/openai-export-parser/discussions)
- Ask in an issue
- Check existing documentation

Thank you for contributing!
