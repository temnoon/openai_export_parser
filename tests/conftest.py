"""
pytest configuration and fixtures for openai-export-parser tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test output."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir)


@pytest.fixture
def sample_conversation():
    """Sample conversation structure for testing."""
    return {
        "id": "conv-test-123",
        "title": "Test Conversation",
        "create_time": 1704067200,
        "update_time": 1704067800,
        "messages": [
            {
                "role": "user",
                "content": "Hello, how are you?",
                "create_time": 1704067200,
            },
            {
                "role": "assistant",
                "content": "I'm doing well, thank you!",
                "create_time": 1704067300,
            },
            {
                "role": "user",
                "content": "Can you help me with Python?",
                "create_time": 1704067400,
            },
            {
                "role": "assistant",
                "content": "Of course! What would you like to know?",
                "create_time": 1704067500,
            },
        ],
    }


@pytest.fixture
def sample_multimodal_conversation():
    """Sample conversation with multimodal content."""
    return {
        "id": "conv-multimodal-456",
        "title": "Image Analysis",
        "create_time": 1704067200,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image", "image_url": "file-abc123.png"},
                ],
                "create_time": 1704067200,
            },
            {
                "role": "assistant",
                "content": "I see a beautiful landscape with mountains.",
                "create_time": 1704067300,
            },
        ],
    }


@pytest.fixture
def sample_media_files(temp_dir):
    """Create sample media files for testing."""
    media_dir = temp_dir / "media"
    media_dir.mkdir()

    # Create dummy media files
    files = [
        "image_abc123.png",
        "file-xyz789.pdf",
        "12345678-1234-1234-1234-123456789abc.jpg",
        "document.pdf",
    ]

    created_files = []
    for filename in files:
        filepath = media_dir / filename
        filepath.write_text("dummy content")
        created_files.append(str(filepath))

    return created_files
