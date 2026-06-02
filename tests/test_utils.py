"""Tests for openai_export_parser.utils."""

from openai_export_parser.utils import (
    sniff_extension,
    sanitize_filename,
    timestamp_to_iso,
)

# --- sniff_extension: recover real type for ".dat" / extension-less assets ----

# (magic-byte prefix, expected extension)
MAGIC_CASES = [
    (b"\x89PNG\r\n\x1a\n" + b"\x00" * 8, ".png"),
    (b"\xff\xd8\xff\xe0" + b"\x00" * 8, ".jpg"),
    (b"GIF89a" + b"\x00" * 8, ".gif"),
    (b"%PDF-1.7" + b"\x00" * 8, ".pdf"),
    (b"RIFF\x00\x00\x00\x00WAVEfmt ", ".wav"),
    (b"RIFF\x00\x00\x00\x00WEBPVP8 ", ".webp"),
    (b"OggS" + b"\x00" * 8, ".ogg"),
    (b"\x00\x00\x00\x18ftypmp42", ".mp4"),
]


def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


def test_sniff_extension_detects_real_type(tmp_path):
    for i, (data, expected) in enumerate(MAGIC_CASES):
        path = _write(tmp_path, f"file-ID{i}.dat", data)
        assert sniff_extension(path) == expected, f"failed for {expected}"


def test_sniff_extension_falls_back_to_current_extension(tmp_path):
    # Unrecognized content keeps the file's existing extension by default.
    path = _write(tmp_path, "mystery.bin", b"not a known magic header")
    assert sniff_extension(path) == ".bin"


def test_sniff_extension_falls_back_to_dat_when_no_extension(tmp_path):
    path = _write(tmp_path, "noext", b"still unknown")
    assert sniff_extension(path) == ".dat"


def test_sniff_extension_explicit_default(tmp_path):
    path = _write(tmp_path, "noext", b"unknown")
    assert sniff_extension(path, default=".png") == ".png"


def test_sniff_extension_missing_file_returns_default():
    assert sniff_extension("/nonexistent/file.dat") == ".dat"


# --- sanitize_filename --------------------------------------------------------


def test_sanitize_filename_replaces_unsafe_characters():
    assert "/" not in sanitize_filename("a/b:c?d")
    assert sanitize_filename("hello world") == "hello_world"


def test_sanitize_filename_handles_empty():
    assert sanitize_filename("") == "untitled"


def test_sanitize_filename_truncates():
    out = sanitize_filename("x" * 200, max_length=50)
    assert len(out) <= 50


# --- timestamp_to_iso ---------------------------------------------------------


def test_timestamp_to_iso_formats_date():
    # timestamp_to_iso uses local time, so derive the expected value the same
    # way (keeps the test stable across CI timezones).
    from datetime import datetime

    ts = 1704067200
    expected = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    assert timestamp_to_iso(ts) == expected
    assert len(timestamp_to_iso(ts)) == 10  # YYYY-MM-DD shape


def test_timestamp_to_iso_handles_missing():
    assert timestamp_to_iso(None) == "0000-00-00"
    assert timestamp_to_iso(0) == "0000-00-00"
