"""
Claude conversation export parser.

Converts Claude's export format to the unified conversation format
used by this tool for HTML generation.
"""

import json
from pathlib import Path
from datetime import datetime


class ClaudeParser:
    """Parse Claude conversation exports and convert to unified format."""

    def __init__(self, verbose=False):
        self.verbose = verbose

    def parse_export(self, export_path):
        """
        Parse a Claude export zip file.

        Args:
            export_path: Path to claude export zip or directory

        Returns:
            List of conversations in unified format
        """
        export_path = Path(export_path)

        # Handle zip file
        if export_path.suffix == '.zip':
            import zipfile
            import tempfile

            temp_dir = Path(tempfile.mkdtemp(prefix='claude_export_'))
            if self.verbose:
                print(f"Extracting Claude export to {temp_dir}")

            with zipfile.ZipFile(export_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            return self._parse_directory(temp_dir)
        else:
            return self._parse_directory(export_path)

    def _parse_directory(self, directory):
        """Parse extracted Claude export directory."""
        directory = Path(directory)

        # Load conversations.json
        conversations_file = directory / 'conversations.json'
        if not conversations_file.exists():
            raise ValueError(f"No conversations.json found in {directory}")

        with open(conversations_file, encoding='utf-8') as f:
            claude_conversations = json.load(f)

        if self.verbose:
            print(f"Found {len(claude_conversations)} Claude conversations")

        # Load projects.json (optional)
        projects = []
        projects_file = directory / 'projects.json'
        if projects_file.exists():
            with open(projects_file, encoding='utf-8') as f:
                projects = json.load(f)
            if self.verbose:
                print(f"Found {len(projects)} Claude projects")

        # Convert to unified format
        unified_conversations = []
        for claude_conv in claude_conversations:
            unified = self._convert_conversation(claude_conv)
            if unified:
                unified_conversations.append(unified)

        return unified_conversations

    def _convert_conversation(self, claude_conv):
        """
        Convert a Claude conversation to unified format.

        Claude format:
        {
            "uuid": "...",
            "name": "...",
            "created_at": "2024-07-14T03:26:07.804181Z",
            "updated_at": "...",
            "account": {...},
            "chat_messages": [...]
        }

        Unified format (OpenAI-like):
        {
            "conversation_id": "...",
            "title": "...",
            "create_time": 1234567890.0,
            "update_time": 1234567890.0,
            "mapping": {...}
        }
        """
        conversation_id = claude_conv.get('uuid', 'unknown')
        title = claude_conv.get('name', 'Untitled Conversation')

        # Convert ISO timestamps to Unix timestamps
        created_at = claude_conv.get('created_at')
        updated_at = claude_conv.get('updated_at')

        create_time = self._iso_to_timestamp(created_at) if created_at else None
        update_time = self._iso_to_timestamp(updated_at) if updated_at else None

        # Build message mapping (OpenAI uses a tree structure, Claude is flat)
        mapping = {}
        chat_messages = claude_conv.get('chat_messages', [])

        # Create root node
        root_id = 'root'
        mapping[root_id] = {
            'id': root_id,
            'message': None,
            'parent': None,
            'children': []
        }

        # Convert messages to nodes
        prev_id = root_id
        for idx, claude_msg in enumerate(chat_messages):
            node_id = claude_msg.get('uuid', f'msg_{idx}')

            # Convert message
            message = self._convert_message(claude_msg)

            # Create node
            mapping[node_id] = {
                'id': node_id,
                'message': message,
                'parent': prev_id,
                'children': []
            }

            # Link to parent
            if prev_id in mapping:
                mapping[prev_id]['children'].append(node_id)

            prev_id = node_id

        return {
            'conversation_id': conversation_id,
            'title': title,
            'create_time': create_time,
            'update_time': update_time,
            'mapping': mapping,
            '_source': 'claude'
        }

    def _convert_message(self, claude_msg):
        """
        Convert a Claude message to unified format.

        Claude message:
        {
            "uuid": "...",
            "text": "...",
            "content": [{
                "type": "text",
                "text": "...",
                "citations": []
            }],
            "sender": "human" or "assistant",
            "created_at": "...",
            "updated_at": "...",
            "attachments": [],
            "files": [{"file_name": "..."}]
        }

        Unified message (OpenAI-like):
        {
            "id": "...",
            "author": {"role": "user" or "assistant"},
            "create_time": 1234567890.0,
            "content": {
                "content_type": "text",
                "parts": ["..."]
            }
        }
        """
        msg_id = claude_msg.get('uuid', 'unknown')
        sender = claude_msg.get('sender', 'human')

        # Map sender to role
        role = 'user' if sender == 'human' else 'assistant'

        # Get timestamp
        created_at = claude_msg.get('created_at')
        create_time = self._iso_to_timestamp(created_at) if created_at else None

        # Extract text content
        text = claude_msg.get('text', '')

        # Check for files/attachments
        files = claude_msg.get('files', [])
        attachments = claude_msg.get('attachments', [])

        # Build content
        content = {
            'content_type': 'text',
            'parts': [text] if text else []
        }

        # Store file references
        message = {
            'id': msg_id,
            'author': {'role': role},
            'create_time': create_time,
            'content': content
        }

        # Add file metadata if present
        if files or attachments:
            message['_files'] = files
            message['_attachments'] = attachments

        return message

    def _iso_to_timestamp(self, iso_string):
        """Convert ISO 8601 timestamp to Unix timestamp."""
        try:
            # Handle timezone-aware strings
            if '+' in iso_string or iso_string.endswith('Z'):
                iso_string = iso_string.replace('Z', '+00:00')
                dt = datetime.fromisoformat(iso_string)
            else:
                dt = datetime.fromisoformat(iso_string)

            return dt.timestamp()
        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not parse timestamp '{iso_string}': {e}")
            return None
