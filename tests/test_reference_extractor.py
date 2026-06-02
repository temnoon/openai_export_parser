"""Tests for media reference extraction from the OpenAI mapping tree."""

from openai_export_parser.media_reference_extractor import (
    MediaReferenceExtractor,
)


def _conversation_with_image_and_attachment():
    """A minimal mapping-tree conversation exercising both reference styles."""
    return {
        "conversation_id": "conv-1",
        "mapping": {
            "node-1": {
                "message": {
                    "author": {"role": "user"},
                    "content": {
                        "content_type": "multimodal_text",
                        "parts": [
                            "here is a picture",
                            {
                                "content_type": "image_asset_pointer",
                                "asset_pointer": "file-service://file-FVJSQmYWxZwxkqvQbDudDl8H",
                                "width": 1080,
                                "height": 1440,
                            },
                        ],
                    },
                    "metadata": {
                        "attachments": [
                            {
                                "id": "file-CKBHwnGQ5wfuNwJt39Yv7SfZ",
                                "name": "Tem@UnderStarks.jpg",
                                "size": 55182,
                                "mimeType": "image/jpeg",
                            }
                        ]
                    },
                }
            }
        },
    }


def test_extracts_asset_pointer_and_attachment():
    extractor = MediaReferenceExtractor()
    refs = extractor.extract_all_references(
        _conversation_with_image_and_attachment()
    )

    assert len(refs["asset_pointers"]) == 1
    assert refs["asset_pointers"][0]["type"] == "file-service"
    assert len(refs["attachments"]) == 1
    assert refs["attachments"][0]["name"] == "Tem@UnderStarks.jpg"


def test_get_all_file_ids_includes_pointer_and_attachment_ids():
    extractor = MediaReferenceExtractor()
    refs = extractor.extract_all_references(
        _conversation_with_image_and_attachment()
    )
    file_ids = extractor.get_all_file_ids(refs)

    assert "file-FVJSQmYWxZwxkqvQbDudDl8H" in file_ids  # from asset_pointer
    assert "file-CKBHwnGQ5wfuNwJt39Yv7SfZ" in file_ids  # from attachment


def test_empty_conversation_yields_no_references():
    extractor = MediaReferenceExtractor()
    refs = extractor.extract_all_references({"mapping": {}})
    assert extractor.count_references(refs) == {
        "asset_pointers": 0,
        "attachments": 0,
        "dalle_generations": 0,
        "text_references": 0,
    }
