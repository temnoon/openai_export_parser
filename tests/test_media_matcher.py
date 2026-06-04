"""Tests for ComprehensiveMediaMatcher precision (PR: matcher precision)."""

from openai_export_parser.comprehensive_media_matcher import ComprehensiveMediaMatcher


class FakeExtractor:
    """Minimal stand-in for MediaReferenceExtractor."""

    def __init__(self, references, hashes=None, ids=None, filenames=None):
        self._refs = references
        self._hashes = hashes or []
        self._ids = ids or []
        self._filenames = filenames or []

    def extract_all_references(self, conv):
        return self._refs

    def get_all_file_hashes(self, refs):
        return self._hashes

    def get_all_file_ids(self, refs):
        return self._ids

    def get_all_filenames(self, refs):
        return self._filenames


def _empty_indices():
    return {
        "file_hash_to_path": {},
        "file_id_to_path": {},
        "basename_size_to_path": {},
        "conversation_to_paths": {},
        "size_to_paths": {},
        "path_to_metadata": {},
    }


def _refs(**kw):
    base = {"attachments": [], "dalle_generations": [], "asset_pointers": []}
    base.update(kw)
    return base


def test_match_records_hash_provenance():
    matcher = ComprehensiveMediaMatcher()
    conv = {"conversation_id": "c1"}
    ext = FakeExtractor(_refs(), hashes=["file_abc"])
    indices = _empty_indices()
    indices["file_hash_to_path"]["file_abc"] = "/m/img.png"

    matcher.match([conv], indices, ext)

    assert conv["_media_files"] == ["/m/img.png"]
    assert conv["_media_matches"]["/m/img.png"] == "by_file_hash"


def test_match_unique_size_is_confident():
    """A size shared by exactly one file in the archive is a confident match."""
    matcher = ComprehensiveMediaMatcher()
    conv = {"conversation_id": "c1"}
    ext = FakeExtractor(_refs(dalle_generations=[{"size_bytes": 2000, "gen_id": None}]))
    indices = _empty_indices()
    indices["size_to_paths"][2000] = ["/m/only.png"]

    matcher.match([conv], indices, ext)

    assert conv["_media_matches"]["/m/only.png"] == "by_size_metadata"


def test_match_gen_id_disambiguates_same_size():
    matcher = ComprehensiveMediaMatcher()
    conv = {"conversation_id": "c1"}
    ext = FakeExtractor(_refs(dalle_generations=[{"size_bytes": 1000, "gen_id": "genXYZ"}]))
    indices = _empty_indices()
    indices["size_to_paths"][1000] = ["/m/aaa.png", "/m/genXYZ-img.png"]

    matcher.match([conv], indices, ext)

    assert conv["_media_files"] == ["/m/genXYZ-img.png"]
    assert conv["_media_matches"]["/m/genXYZ-img.png"] == "by_size_metadata"


def test_match_ambiguous_size_tagged_low_confidence():
    matcher = ComprehensiveMediaMatcher()
    conv = {"conversation_id": "c1"}
    ext = FakeExtractor(_refs(dalle_generations=[{"size_bytes": 1000, "gen_id": None}]))
    indices = _empty_indices()
    indices["size_to_paths"][1000] = ["/m/aaa.png", "/m/bbb.png"]

    matcher.match([conv], indices, ext)

    assert len(conv["_media_files"]) == 1
    taken = conv["_media_files"][0]
    assert conv["_media_matches"][taken] == "by_size_ambiguous"


def test_match_multiple_same_size_refs_all_ambiguous():
    """Two references sharing a non-unique size must BOTH stay low-confidence —
    consuming the first candidate must not make the second look 'unique'."""
    matcher = ComprehensiveMediaMatcher()
    conv = {"conversation_id": "c1"}
    ext = FakeExtractor(_refs(dalle_generations=[
        {"size_bytes": 1000, "gen_id": None},
        {"size_bytes": 1000, "gen_id": None},
    ]))
    indices = _empty_indices()
    indices["size_to_paths"][1000] = ["/m/aaa.png", "/m/bbb.png"]

    matcher.match([conv], indices, ext)

    assert len(conv["_media_files"]) == 2
    assert set(conv["_media_matches"].values()) == {"by_size_ambiguous"}
