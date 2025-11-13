import argparse
import zipfile
import os
from pathlib import Path
from .parser import ExportParser
from .claude_parser import ClaudeParser
from .version import __version__


def detect_export_type(archive_path):
    """
    Detect if the archive is OpenAI or Claude export.

    Returns:
        'openai', 'claude', or None if cannot determine
    """
    archive_path = Path(archive_path)

    # Check if it's a directory
    if archive_path.is_dir():
        if (archive_path / 'conversations.json').exists() and \
           (archive_path / 'users.json').exists():
            return 'claude'
        return 'openai'

    # Check if it's a zip file
    if archive_path.suffix == '.zip':
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                filenames = zf.namelist()

                # Claude exports have conversations.json, users.json at root
                if 'conversations.json' in filenames and 'users.json' in filenames:
                    return 'claude'

                # OpenAI exports have nested zips or conversations.json in subdirectories
                return 'openai'
        except zipfile.BadZipFile:
            return None

    return None


def main():
    """Command-line interface for OpenAI export parser."""
    parser = argparse.ArgumentParser(
        description="Parse OpenAI ChatGPT export.zip recursively",
        epilog="Example: openai-export-parser export.zip -o parsed_output -v"
    )

    parser.add_argument(
        "archive",
        help="Path to OpenAI export.zip file"
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="Output directory for parsed results (default: output)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Use flat output structure (legacy mode) instead of organized folders"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "html", "both"],
        default="both",
        help="Output format: json only, html only, or both (default: both)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"openai-export-parser {__version__}"
    )

    args = parser.parse_args()

    # Detect export type
    export_type = detect_export_type(args.archive)

    if export_type is None:
        print(f"Error: Could not determine export type for {args.archive}")
        print("Expected: OpenAI export.zip or Claude data export")
        return 1

    print(f"OpenAI Export Parser v{__version__}")
    print(f"Export type: {export_type.upper()}")
    print(f"Parsing: {args.archive}")
    print(f"Output:  {args.output}")
    print(f"Mode:    {'Flat' if args.flat else 'Organized (by conversation)'}")
    print(f"Format:  {args.output_format}\n")

    if export_type == 'claude':
        # Parse Claude export
        claude_parser = ClaudeParser(verbose=args.verbose)
        conversations = claude_parser.parse_export(args.archive)

        # Use ConversationOrganizer to generate output
        from .conversation_organizer import ConversationOrganizer
        from .html_generator import HTMLGenerator

        organizer = ConversationOrganizer(verbose=args.verbose, output_format=args.output_format)

        # Claude exports don't have separate media files (yet)
        # Media is referenced by filename but not extracted in current implementation
        all_media_files = []
        media_manifest = {}

        # Write organized output
        organizer.write_organized_output(
            conversations=conversations,
            all_media_files=all_media_files,
            out_dir=args.output,
            media_manifest=media_manifest
        )

        # Generate master index.html
        if args.output_format in ('html', 'both'):
            print("\nGenerating master index.html...")
            generator = HTMLGenerator()
            index_html = generator.generate_index_html(conversations, Path(args.output))

            # Write index.html
            index_path = Path(args.output) / 'index.html'
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(index_html)

            print(f"✓ Master index created: {index_path}")
    else:
        # Parse OpenAI export
        ep = ExportParser(verbose=args.verbose, organize_by_conversation=not args.flat, output_format=args.output_format)
        ep.parse_export(args.archive, args.output)

    print(f"\n✅ Parsing complete. Output saved to: {args.output}")
    if args.flat:
        print(f"   - conversations/ - Individual conversation JSON files")
        print(f"   - media/ - Extracted media files")
    else:
        print(f"   - <timestamp>_<title>_<id>/ - Self-contained conversation folders")
        print(f"     Each folder contains:")
        print(f"       • conversation.json - Full conversation data")
        print(f"       • media/ - Images and files for this conversation")
        print(f"       • media_manifest.json - Mapping of media files")
    print(f"   - index.json - Metadata and schema information\n")
