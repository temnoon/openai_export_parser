"""Tests for ConversationOrganizer folder naming (PR: parser correctness fixes)."""

from openai_export_parser.conversation_organizer import ConversationOrganizer


def _org():
    return ConversationOrganizer()


def test_folder_name_stable_across_position():
    """The same conversation must get the same folder name regardless of where
    it sits in the list — i.e. the name is keyed on the stable id, not index."""
    org = _org()
    conv = {
        "create_time": 1681491476.0,
        "title": "Hello World",
        "conversation_id": "a1153098-55b2-4c1b-81fa-cdf2825d1b5c",
    }
    name_at_5 = org.generate_folder_name(conv, 5)
    name_at_999 = org.generate_folder_name(conv, 999)

    assert name_at_5 == name_at_999, "folder name should not depend on list position"
    assert "a1153098" in name_at_5, "folder name should incorporate the conversation id"


def test_folder_name_falls_back_to_index_without_id():
    """When a conversation has no id, fall back to the positional index."""
    org = _org()
    conv = {"create_time": 1681491476.0, "title": "No ID"}
    name = org.generate_folder_name(conv, 7)

    assert name.endswith("00007"), "missing id should fall back to zero-padded index"
