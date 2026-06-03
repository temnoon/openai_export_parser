"""Tests for ExportParser orchestration (PR: parser correctness fixes)."""

import os
import zipfile

import pytest

from openai_export_parser.parser import ExportParser


def _minimal_export(tmp_path):
    """A trivial but valid export zip: one conversations.json at the root."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "conversations.json").write_text("[]", encoding="utf-8")
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.write(src / "conversations.json", "conversations.json")
    return str(zip_path)


def test_temp_dir_removed_even_on_error(tmp_path, monkeypatch):
    """`_tmp` must be cleaned up even when parsing fails partway through."""
    zip_path = _minimal_export(tmp_path)
    out = tmp_path / "out"

    parser = ExportParser()

    def boom(*args, **kwargs):
        raise RuntimeError("forced failure after extraction")

    # scan() runs right after the archive is unzipped into _tmp.
    monkeypatch.setattr(parser, "scan", boom)

    with pytest.raises(RuntimeError):
        parser.parse_export(zip_path, str(out))

    assert not os.path.exists(os.path.join(str(out), "_tmp")), "_tmp was left behind"


def test_scan_only_extracts_zip_extension(tmp_path):
    """scan() should extract files named *.zip, but never probe/extract a
    non-.zip file just because its bytes happen to look like a zip."""
    root = tmp_path / "root"
    root.mkdir()

    # A genuine nested archive, correctly named .zip -> should be extracted.
    real = root / "real.zip"
    with zipfile.ZipFile(real, "w") as z:
        z.writestr("conversations.json", "[]")

    # A valid zip whose name does NOT end in .zip -> must be left untouched.
    decoy = root / "decoy.bin"
    with zipfile.ZipFile(decoy, "w") as z:
        z.writestr("inner.txt", "x")

    parser = ExportParser()
    parser.scan(str(root))

    assert os.path.isdir(str(real) + "_unzipped"), "real .zip should be extracted"
    assert not os.path.exists(str(decoy) + "_unzipped"), \
        "a non-.zip file must not be probed or extracted"
