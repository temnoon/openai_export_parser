class SchemaInference:
    """
    Examines message structures and conversation formats to infer:
    - Message field types
    - Timestamps and temporal data
    - Participant/role information
    - Multimodal content structures

    This enables future-proof parsing as OpenAI's export format evolves.
    """

    def infer_message_schema(self, msg):
        """
        Analyze a single message to determine its structure.

        Args:
            msg: A message dict

        Returns:
            Dict describing the message schema
        """
        return {
            "fields": list(msg.keys()),
            "has_content_list": isinstance(msg.get("content"), list),
            "has_text": isinstance(msg.get("content"), str),
            "has_files": any(k in msg for k in ["file_id", "asset_pointer", "attachments"]),
            "has_image_blocks": self._has_image_blocks(msg),
        }

    def _has_image_blocks(self, msg):
        """Check if message contains image content blocks."""
        c = msg.get("content")
        if not isinstance(c, list):
            return False
        return any(
            isinstance(i, dict) and i.get("type") in ("image", "input_image")
            for i in c
        )

    def infer_conversation_schema(self, conversation):
        """
        Analyze a conversation's structure.

        Args:
            conversation: A conversation dict

        Returns:
            Dict describing the conversation schema
        """
        out = {
            "root_fields": list(conversation.keys()),
            "message_count": len(conversation.get("messages", [])),
        }

        if conversation.get("messages"):
            msg = conversation["messages"][0]
            out["message_schema"] = self.infer_message_schema(msg)

        return out

    def infer_global_schema(self, conversations):
        """
        Analyze all conversations to understand overall export structure.

        Args:
            conversations: List of conversation dicts

        Returns:
            List of schema descriptions for each conversation
        """
        return [self.infer_conversation_schema(c) for c in conversations]
