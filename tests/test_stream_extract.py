"""Tests for the cross-platform pure-Python zip recovery extractor."""

import os
import zipfile

import pytest

from openai_export_parser.utils import _stream_extract


def _build_zip(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("hello.txt", "hello world" * 100, zipfile.ZIP_STORED)
        z.writestr("sub/dir/data.bin", bytes(range(256)) * 50, zipfile.ZIP_DEFLATED)
        z.writestr(
            "img/file-ABC123.dat",
            b"\x89PNG\r\n\x1a\n" + b"\x00" * 500,
            zipfile.ZIP_STORED,
        )


def test_stream_extract_recovers_all_members(tmp_path):
    zpath = tmp_path / "test.zip"
    _build_zip(zpath)
    out = tmp_path / "out"

    count = _stream_extract(str(zpath), str(out))
    assert count == 3

    for name in ["hello.txt", "sub/dir/data.bin", "img/file-ABC123.dat"]:
        with zipfile.ZipFile(zpath) as z:
            expected = z.read(name)
        assert (out / name).read_bytes() == expected


def test_stream_extract_handles_deflated_members(tmp_path):
    # A highly compressible payload exercises the inflate path.
    zpath = tmp_path / "deflate.zip"
    payload = b"A" * 100000
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("big.txt", payload, zipfile.ZIP_DEFLATED)

    out = tmp_path / "out"
    assert _stream_extract(str(zpath), str(out)) == 1
    assert (out / "big.txt").read_bytes() == payload


def test_stream_extract_creates_subdirectories(tmp_path):
    zpath = tmp_path / "nested.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("a/b/c/deep.txt", "deep", zipfile.ZIP_STORED)

    out = tmp_path / "out"
    _stream_extract(str(zpath), str(out))
    assert (out / "a" / "b" / "c" / "deep.txt").read_text() == "deep"
