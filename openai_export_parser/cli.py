import argparse
from .parser import ExportParser
from .version import __version__


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

    print(f"OpenAI Export Parser v{__version__}")
    print(f"Parsing: {args.archive}")
    print(f"Output:  {args.output}")
    print(f"Mode:    {'Flat' if args.flat else 'Organized (by conversation)'}")
    print(f"Format:  {args.output_format}\n")

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
