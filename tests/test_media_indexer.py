"""Tests for the comprehensive media indexer, incl. the 2026 ".dat" naming."""

from openai_export_parser.comprehensive_media_indexer import (
    ComprehensiveMediaIndexer,
)


def test_dat_is_a_media_extension():
    # 2026 exports store assets as "file-<ID>.dat"; they must be indexed.
    assert ".dat" in ComprehensiveMediaIndexer.MEDIA_EXTENSIONS


class TestExtractFileId:
    def setup_method(self):
        self.idx = ComprehensiveMediaIndexer()

    def test_dat_stem_is_the_file_id(self):
        # New format: "file-<ID>.dat" with no name part.
        assert (
            self.idx._extract_file_id("file-aZlh7eXXkKmbAT3s8OUOyknk.dat")
            == "file-aZlh7eXXkKmbAT3s8OUOyknk"
        )

    def test_underscore_separated_name(self):
        assert (
            self.idx._extract_file_id("file-BTGHeayl9isKTp9kvyBzirg0_document.pdf")
            == "file-BTGHeayl9isKTp9kvyBzirg0"
        )

    def test_hyphen_separated_name(self):
        assert (
            self.idx._extract_file_id("file-MwiGI2eKYgkoMIPpOym4c7ex-photo.webp")
            == "file-MwiGI2eKYgkoMIPpOym4c7ex"
        )

    def test_bare_file_id(self):
        assert (
            self.idx._extract_file_id("file-CSDzgtOhPLr3NzxdVkRcDgEC")
            == "file-CSDzgtOhPLr3NzxdVkRcDgEC"
        )

    def test_non_file_id_names_return_none(self):
        assert self.idx._extract_file_id("photo-1234.jpeg") is None
        assert (
            self.idx._extract_file_id("12345678-1234-1234-1234-123456789abc.jpg")
            is None
        )


def test_build_index_finds_dat_assets_by_file_id(tmp_path):
    # A "file-<ID>.dat" asset should be indexed and resolvable by its file-ID.
    (tmp_path / "file-aZlh7eXXkKmbAT3s8OUOyknk.dat").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    )
    (tmp_path / "conversations-000.json").write_text("[]")  # ignored by indexer

    idx = ComprehensiveMediaIndexer()
    indices = idx.build_index(str(tmp_path))

    assert "file-aZlh7eXXkKmbAT3s8OUOyknk" in indices["file_id_to_path"]
    assert idx.get_stats()["total_files"] == 1
