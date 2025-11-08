class ConversationThreader:
    """
    Adds threading metadata to conversations.

    Assigns sequential IDs and resolves parent/child relationships,
    enabling conversation tree visualization and analysis.
    """

    def thread(self, conversation):
        """
        Add threading information to a conversation.

        Args:
            conversation: A conversation dict with messages

        Returns:
            Updated conversation with message IDs and parent references
        """
        for i, msg in enumerate(conversation.get("messages", [])):
            msg.setdefault("id", f"msg_{i+1:05d}")

            # Basic linear threading - each message references previous
            if i > 0:
                msg["parent"] = conversation["messages"][i - 1]["id"]

        return conversation
