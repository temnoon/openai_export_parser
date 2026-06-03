"""Tests for HTML viewer generation, focused on XSS-safe embedding.

These tests guard the fixes in PR 1:
  * conversation data is embedded so that a literal "</script>" cannot
    break out of its <script> block,
  * the conversation_id shown in the footer is HTML-escaped,
  * the viewer loads DOMPurify and uses it to sanitize rendered Markdown,
  * the footer links to the real upstream repository.
"""

import json

import pytest

from openai_export_parser.html_generator import HTMLGenerator


@pytest.fixture
def generator():
    return HTMLGenerator()


def _minimal_conversation(**overrides):
    """A small but structurally valid conversation for the generator."""
    conv = {
        "title": "Test conversation",
        "create_time": 1700000000,
        "update_time": 1700000100,
        "conversation_id": "11111111-1111-1111-1111-111111111111",
        "mapping": {
            "node1": {
                "id": "node1",
                "message": {
                    "author": {"role": "user"},
                    "create_time": 1700000000,
                    "content": {"content_type": "text", "parts": ["hello"]},
                },
            }
        },
    }
    conv.update(overrides)
    return conv


def test_embed_json_escapes_angle_brackets_and_amp(generator):
    payload = {"text": "</script><img src=x onerror=alert(1)>", "amp": "a & b"}
    embedded = generator._embed_json(payload)

    # The raw tag-breakout sequence must not survive verbatim...
    assert "</script>" not in embedded
    # ...it must appear only in escaped form.
    assert "\\u003c/script\\u003e" in embedded
    assert "\\u0026" in embedded  # the & is escaped too

    # And it must still be valid JSON that round-trips to the original value.
    assert json.loads(embedded) == payload


def test_script_payload_in_title_is_neutralized(generator):
    conv = _minimal_conversation(title="x</script><img src=x onerror=alert(1)>")
    html = generator.generate_conversation_html(conversation=conv)

    # The exact malicious payload must never appear unescaped anywhere.
    assert "</script><img src=x onerror=alert(1)>" not in html


def test_conversation_id_is_escaped_in_footer(generator):
    conv = _minimal_conversation(conversation_id="<svg/onload=alert(1)>")
    html = generator.generate_conversation_html(conversation=conv)

    assert "<svg/onload=alert(1)>" not in html


def test_viewer_loads_sanitizer(generator):
    html = generator.generate_conversation_html(conversation=_minimal_conversation())

    # DOMPurify must be loaded and used to sanitize rendered Markdown.
    assert "dompurify" in html.lower()
    assert "DOMPurify.sanitize(" in html


def test_footer_attribution_points_to_real_repo(generator):
    html = generator.generate_conversation_html(conversation=_minimal_conversation())

    assert "github.com/temnoon/openai_export_parser" in html
    assert "anthropics/openai-export-parser" not in html

def test_viewer_backfills_children_from_parent(generator):
    html = generator.generate_conversation_html(conversation=_minimal_conversation())
    assert "backfill-children" in html  # parent-only exports must still render
