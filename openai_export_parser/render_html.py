"""
CLI tool to render conversation folders as HTML.
"""

import argparse
import os
import sys
from pathlib import Path

from .html_renderer import render_conversation_folder
from .version import __version__


def main():
    """Command-line interface for HTML rendering."""
    parser = argparse.ArgumentParser(
        description="Render OpenAI conversation folder as HTML",
        epilog="Example: openai-render-html ./2025-01-06_My_Conversation_00001"
    )

    parser.add_argument(
        "folder",
        help="Path to conversation folder (containing conversation.json)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output HTML file path (default: <folder>/index.html)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"openai-export-parser {__version__}"
    )

    args = parser.parse_args()

    # Check folder exists
    if not os.path.isdir(args.folder):
        print(f"Error: Folder not found: {args.folder}", file=sys.stderr)
        sys.exit(1)

    # Check conversation.json exists
    conv_file = os.path.join(args.folder, "conversation.json")
    if not os.path.exists(conv_file):
        print(f"Error: No conversation.json found in {args.folder}", file=sys.stderr)
        sys.exit(1)

    # Render
    print(f"Rendering: {args.folder}")

    output_html = args.output or os.path.join(args.folder, "index.html")

    try:
        render_conversation_folder(args.folder, output_html)
        print(f"✅ HTML saved to: {output_html}")
    except Exception as e:
        print(f"Error rendering HTML: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
