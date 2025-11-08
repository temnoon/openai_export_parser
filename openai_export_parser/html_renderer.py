"""
HTML renderer for OpenAI conversation exports.

Generates human-readable HTML from conversation JSON with:
- Message threading (parent/child relationships)
- Inline images
- File attachments
- Metadata panel
"""

import os
import json
from datetime import datetime
from html import escape


class HTMLRenderer:
    """
    Renders OpenAI conversation exports as HTML.

    Handles the complex 'mapping' structure and generates
    readable HTML with media embedded.
    """

    def __init__(self):
        self.conversation = None
        self.media_manifest = None
        self.media_dir = "media"

    def render_conversation(self, conversation_folder):
        """
        Render a conversation folder to HTML.

        Args:
            conversation_folder: Path to conversation folder containing:
                - conversation.json
                - media/ (optional)
                - media_manifest.json (optional)

        Returns:
            HTML string
        """
        # Load conversation
        conv_path = os.path.join(conversation_folder, "conversation.json")
        with open(conv_path, "r", encoding="utf-8") as f:
            self.conversation = json.load(f)

        # Load media manifest if exists
        manifest_path = os.path.join(conversation_folder, "media_manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                self.media_manifest = json.load(f)
        else:
            self.media_manifest = {}

        # Generate HTML
        html = self._generate_html()

        return html

    def _generate_html(self):
        """Generate complete HTML document."""
        # Extract messages from conversation
        messages = self._extract_messages()

        # Build HTML
        html_parts = []

        # Header
        html_parts.append(self._html_header())

        # Metadata panel
        html_parts.append(self._html_metadata())

        # Messages
        html_parts.append('<div class="messages">')
        for msg in messages:
            html_parts.append(self._html_message(msg))
        html_parts.append('</div>')

        # Footer
        html_parts.append(self._html_footer())

        return "\n".join(html_parts)

    def _extract_messages(self):
        """
        Extract messages from conversation structure.

        Handles both simple messages array and complex mapping structure.

        Returns:
            List of message dicts in display order
        """
        messages = []

        # Try simple messages array first
        if "messages" in self.conversation and isinstance(
            self.conversation["messages"], list
        ):
            return self.conversation["messages"]

        # Handle complex mapping structure
        if "mapping" in self.conversation:
            messages = self._extract_from_mapping()

        return messages

    def _extract_from_mapping(self):
        """
        Extract messages from OpenAI's complex mapping structure.

        The mapping is a graph of message nodes with parent/child relationships.
        We need to traverse it to get messages in conversation order.
        """
        mapping = self.conversation.get("mapping", {})
        current_node = self.conversation.get("current_node")

        # Build parent->children index
        children_map = {}
        for node_id, node_data in mapping.items():
            parent = node_data.get("parent")
            if parent:
                children_map.setdefault(parent, []).append(node_id)

        # Find root node (no parent)
        root_nodes = [
            node_id for node_id, node_data in mapping.items() if not node_data.get("parent")
        ]

        if not root_nodes:
            return []

        # Traverse from root
        messages = []
        self._traverse_mapping(root_nodes[0], mapping, children_map, messages)

        return messages

    def _traverse_mapping(self, node_id, mapping, children_map, messages):
        """Recursively traverse mapping to extract messages."""
        node = mapping.get(node_id)
        if not node:
            return

        # Add message if it exists and has content
        if "message" in node and node["message"]:
            msg = node["message"]
            # Skip hidden system messages
            if not msg.get("metadata", {}).get("is_visually_hidden_from_conversation"):
                messages.append(msg)

        # Traverse children
        for child_id in children_map.get(node_id, []):
            self._traverse_mapping(child_id, mapping, children_map, messages)

    def _html_header(self):
        """Generate HTML header with CSS."""
        title = escape(self.conversation.get("title", "Conversation"))

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 30px;
        }}
        .metadata h1 {{
            margin-bottom: 15px;
            color: #2c3e50;
        }}
        .metadata .info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            font-size: 0.9em;
            color: #666;
        }}
        .metadata .info-item {{
            padding: 8px;
            background: white;
            border-radius: 4px;
        }}
        .metadata .info-item strong {{
            display: block;
            color: #333;
            margin-bottom: 4px;
        }}
        .messages {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .message {{
            padding: 15px 20px;
            border-radius: 8px;
            border-left: 4px solid #e0e0e0;
        }}
        .message.user {{
            background: #e3f2fd;
            border-left-color: #2196f3;
        }}
        .message.assistant {{
            background: #f3e5f5;
            border-left-color: #9c27b0;
        }}
        .message.system {{
            background: #fff3e0;
            border-left-color: #ff9800;
            font-size: 0.9em;
        }}
        .message-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            font-size: 0.9em;
            color: #666;
        }}
        .message-role {{
            font-weight: bold;
            text-transform: capitalize;
        }}
        .message-time {{
            font-size: 0.85em;
        }}
        .message-content {{
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .message-content img {{
            max-width: 100%;
            height: auto;
            margin: 15px 0;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .file-attachment {{
            display: inline-block;
            padding: 8px 12px;
            background: #eceff1;
            border-radius: 4px;
            margin: 5px 5px 5px 0;
            text-decoration: none;
            color: #1976d2;
            font-size: 0.9em;
        }}
        .file-attachment:hover {{
            background: #cfd8dc;
        }}
        .file-attachment::before {{
            content: "📎 ";
        }}
    </style>
</head>
<body>
    <div class="container">'''

    def _html_metadata(self):
        """Generate metadata panel HTML."""
        title = escape(self.conversation.get("title", "Untitled"))
        create_time = self._format_timestamp(self.conversation.get("create_time"))
        update_time = self._format_timestamp(self.conversation.get("update_time"))
        conv_id = escape(str(self.conversation.get("conversation_id", "N/A")))
        model = escape(str(self.conversation.get("default_model_slug", "N/A")))

        return f'''
        <div class="metadata">
            <h1>{title}</h1>
            <div class="info">
                <div class="info-item">
                    <strong>Created</strong>
                    {create_time}
                </div>
                <div class="info-item">
                    <strong>Updated</strong>
                    {update_time}
                </div>
                <div class="info-item">
                    <strong>Conversation ID</strong>
                    {conv_id}
                </div>
                <div class="info-item">
                    <strong>Model</strong>
                    {model}
                </div>
            </div>
        </div>'''

    def _html_message(self, message):
        """Generate HTML for a single message."""
        role = message.get("author", {}).get("role", "unknown")
        timestamp = self._format_timestamp(message.get("create_time"))

        # Extract content
        content = self._extract_message_content(message)
        content_html = self._format_content(content, message)

        return f'''
        <div class="message {escape(role)}">
            <div class="message-header">
                <span class="message-role">{escape(role)}</span>
                <span class="message-time">{timestamp}</span>
            </div>
            <div class="message-content">
                {content_html}
            </div>
        </div>'''

    def _extract_message_content(self, message):
        """Extract text content from message."""
        content = message.get("content", {})

        # Handle different content formats
        if isinstance(content, str):
            return content
        elif isinstance(content, dict):
            # OpenAI format: content.parts array
            parts = content.get("parts", [])
            if parts:
                return "\n".join(str(p) for p in parts if p)
            # Fallback to content_type
            return content.get("text", "")
        elif isinstance(content, list):
            # List of content blocks
            text_parts = []
            for block in content:
                if isinstance(block, str):
                    text_parts.append(block)
                elif isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
            return "\n".join(text_parts)

        return "(no content)"

    def _format_content(self, content, message):
        """
        Format message content HTML with inline images and attachments.
        """
        html = escape(content)

        # Add inline images if message has media
        if "media" in message:
            for media_file in message["media"]:
                # Look up hashed filename
                hashed_name = self.media_manifest.get(media_file, media_file)
                img_path = f"{self.media_dir}/{hashed_name}"

                # Check if it's an image
                if self._is_image(hashed_name):
                    html += f'<br><img src="{img_path}" alt="{escape(media_file)}">'
                else:
                    html += f'<br><a href="{img_path}" class="file-attachment">{escape(media_file)}</a>'

        return html

    def _is_image(self, filename):
        """Check if filename is an image."""
        img_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
        ext = os.path.splitext(filename.lower())[1]
        return ext in img_exts

    def _format_timestamp(self, timestamp):
        """Format Unix timestamp to readable string."""
        if not timestamp:
            return "N/A"

        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return str(timestamp)

    def _html_footer(self):
        """Generate HTML footer."""
        return '''
    </div>
</body>
</html>'''


def render_conversation_folder(folder_path, output_html=None):
    """
    Convenience function to render a conversation folder to HTML.

    Args:
        folder_path: Path to conversation folder
        output_html: Optional path to save HTML (default: same folder as index.html)

    Returns:
        HTML string
    """
    renderer = HTMLRenderer()
    html = renderer.render_conversation(folder_path)

    if output_html:
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html)
    elif output_html is None:
        # Save to folder as index.html
        output_html = os.path.join(folder_path, "index.html")
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html)

    return html
