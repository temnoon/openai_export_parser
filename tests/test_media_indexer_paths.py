"""Tests for ComprehensiveMediaIndexer path handling (PR: parser correctness fixes)."""

from openai_export_parser.comprehensive_media_indexer import ComprehensiveMediaIndexer

UUID = "a1153098-55b2-4c1b-81fa-cdf2825d1b5c"


def test_extract_conversation_id_posix_path():
    idx = ComprehensiveMediaIndexer()
    path = "/tmp/export/conversations/" + UUID + "/image.png"
    assert idx._extract_conversation_id(path) == UUID


def test_extract_conversation_id_windows_path():
    """os.walk yields backslash-separated paths on Windows; conversation-
    directory matching must still work there (regression guard)."""
    idx = ComprehensiveMediaIndexer()
    path = "C:\\export\\conversations\\" + UUID + "\\image.png"
    assert idx._extract_conversation_id(path) == UUID
