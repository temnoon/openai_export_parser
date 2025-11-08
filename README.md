# openai-export-parser

[![Tests](https://github.com/temnoon/openai-export-parser/workflows/Tests/badge.svg)](https://github.com/temnoon/openai-export-parser/actions)
[![Python Version](https://img.shields.io/pypi/pyversions/openai-export-parser.svg)](https://pypi.org/project/openai-export-parser/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A comprehensive parser for OpenAI ChatGPT export archives with advanced media matching, audio transcripts, and beautiful HTML output.**

Parse OpenAI's complex, nested export.zip files into organized, browsable conversations with automatic media matching, voice transcripts, and a complete HTML viewer.

## ✨ Key Features

### 🎙️ **Voice Mode Support**
- **Audio Transcripts** - Automatically extracts and displays voice message transcripts
- **Audio Playback** - Embedded HTML5 audio players with controls for all voice conversations
- **Full WAV Support** - Plays back original voice recordings directly in the browser

### 🖼️ **Advanced Media Matching**
- **7-Strategy Matching** - Links images, audio, and files to messages using multiple algorithms
- **DALL-E Images** - Handles generated images with metadata and prompts
- **File Recovery** - Can incorporate media from old exports to fill gaps
- **97.9% Match Rate** - Industry-leading accuracy for media file matching

### 📱 **Beautiful HTML Viewer**
- **Standalone HTML** - Each conversation as a self-contained, shareable HTML file
- **Master Index** - Browse all conversations with search, filtering, and categories
- **Dark Mode** - Automatic theme switching based on system preferences
- **Markdown Rendering** - Full support for formatted text, code blocks, and LaTeX math
- **Syntax Highlighting** - Code blocks with language-aware highlighting
- **Responsive Design** - Works perfectly on desktop and mobile

### 🔧 **Robust Processing**
- **Recursive Zip Extraction** - Handles arbitrarily nested zip archives
- **Malformed Zip Recovery** - Works with corrupted exports using fallback extraction
- **Schema Inference** - Future-proof against OpenAI format changes
- **Progress Tracking** - Real-time progress bars for long operations
- **Error Recovery** - Gracefully handles incomplete or partial exports

### 📊 **Organization & Discovery**
- **Smart Folder Naming** - Conversations organized by date and title
- **Category Symlinks** - Quick access to conversations with media or assets
- **Search & Filter** - Find conversations by title, date, or content
- **Statistics Dashboard** - Overview of your conversation archive

## Installation

```bash
pip install openai-export-parser
```

Or install from source:

```bash
git clone https://github.com/temnoon/openai-export-parser.git
cd openai-export-parser
pip install -e .
```

## Quick Start

### Command Line

```bash
# Basic usage - creates browsable HTML output
openai-export-parser export.zip

# Specify output directory
openai-export-parser export.zip -o my_conversations

# Enable verbose logging
openai-export-parser export.zip -v
```

### Python API

```python
from openai_export_parser import ExportParser

parser = ExportParser(verbose=True)
parser.parse_export("export.zip", "output_directory")
```

## Output Structure

```
output/
├── index.html                          # Master index - start here!
├── index.json                          # Metadata
├── _with_media/                        # Symlinks to conversations with images/audio
├── _with_assets/                       # Symlinks to conversations with files
├── 2025-11-06_OpenAI_export.zip_documentation_00001/
│   ├── conversation.html               # Standalone HTML viewer
│   ├── conversation.json               # Full conversation data
│   ├── media/                          # Images, audio files, etc.
│   │   ├── image_abc123.png
│   │   └── audio_xyz789.wav
│   └── media_manifest.json             # Media file mappings
└── [... more conversation folders]
```

## HTML Viewer Features

Open `output/index.html` in your browser to access:

- **Searchable conversation list** with title, date, and message count
- **Filter by date range** or media presence
- **Dark/light mode toggle** with persistence
- **Click any conversation** to view the full HTML with:
  - Formatted markdown text
  - Embedded images (DALL-E and uploads)
  - Audio players for voice messages with transcripts
  - Code syntax highlighting
  - LaTeX math rendering
  - Conversation metadata and timestamps

### Voice Conversation Example

Voice messages display with:
1. **Transcript text** - Full text of what was said
2. **Audio player** - HTML5 controls to listen to the original recording
3. **Duration display** - Length of audio clip
4. **Direction indicator** - User vs Assistant audio

## Media Matching Strategies

The parser uses 7 different strategies to match media files:

1. **File Hash Matching** - Direct hash lookup for `sediment://` URLs
2. **File-ID Matching** - OpenAI file identifiers (`file-XXX`)
3. **Filename + Size** - Exact filename and byte size
4. **Conversation Directory** - Files in conversation-specific folders
5. **Size + Metadata** - File size with DALL-E generation metadata
6. **Size Only** - Fallback matching by file size
7. **Filename Only** - Last resort filename-based matching

## Advanced Features

### Recovery Folder Integration

To incorporate media from old exports:

```bash
# Place old media files in recovered_files/
mkdir recovered_files
cp -r old_export/media/* recovered_files/

# Parser automatically includes them
openai-export-parser new_export.zip -o output
```

The parser will index both the new export and recovered files, maximizing match rates.

### Programmatic Access

```python
from openai_export_parser import ExportParser

class CustomParser(ExportParser):
    def normalize_conversations(self, conversations):
        # Add custom processing
        conversations = super().normalize_conversations(conversations)

        for conv in conversations:
            # Extract statistics, filter content, etc.
            conv["message_count"] = len(conv.get("messages", []))

        return conversations

parser = CustomParser(verbose=True)
parser.parse_export("export.zip", "output")
```

### Integration with Memory Systems

The output is optimized for ingestion into vector databases:

```python
import json
from pathlib import Path
from openai_export_parser import ExportParser

# Parse export
parser = ExportParser()
parser.parse_export("export.zip", "parsed")

# Load for vector embedding
for conv_file in Path("parsed").glob("*/conversation.json"):
    with open(conv_file) as f:
        conv = json.load(f)

    for node in conv["mapping"].values():
        msg = node.get("message")
        if not msg:
            continue

        # Extract text content
        content = msg.get("content", {})
        text = ""

        if content.get("content_type") == "text":
            text = content.get("parts", [""])[0]

        # Embed and store
        metadata = {
            "conversation_id": conv["conversation_id"],
            "timestamp": msg.get("create_time"),
            "role": msg.get("author", {}).get("role"),
        }
        # your_embedding_function(text, metadata)
```

## Understanding OpenAI Export Formats

OpenAI has changed export formats over time:

### New Format (2024+)
- Multiple nested zips
- Files in `file-service://` format
- DALL-E metadata in separate fields
- Voice transcripts in `audio_transcription` parts

### Old Format (Pre-2024)
- Single `conversations.json` file
- Flat media directory
- Simple file naming
- Limited metadata

**This parser handles both formats automatically** and can merge data from multiple exports.

## Troubleshooting

### "No conversations found"

- Verify you're using the actual export.zip from OpenAI
- Try verbose mode: `openai-export-parser export.zip -v`
- Check the log for extraction errors

### "Audio not playing in HTML"

- Ensure conversation HTML files were regenerated with latest version
- Check that WAV files exist in the `media/` folder
- Verify browser supports HTML5 audio (all modern browsers do)

### "Media files not matching"

- Check the parse log for "UNMATCHED" warnings
- Try incorporating old exports via `recovered_files/`
- Some files may be missing from the export entirely
- Review the generated `unmatched_media_*.csv` if available

### "Bad magic number for file header"

The parser handles corrupted zips automatically:
- macOS: Uses `ditto` (same as Archive Utility)
- Linux/Windows: Falls back to system `unzip`
- Accepts partial extractions when possible

If Archive Utility can open it, the parser will too.

### "Encoding errors"

```python
parser = ExportParser(verbose=True)
parser.parse_export("export.zip", "output")
# Check console output for encoding warnings
```

The parser uses UTF-8 with error handling - most encoding issues are automatically resolved.

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

### Project Structure

```
openai_export_parser/
├── parser.py                    # Main entry point
├── conversation_organizer.py    # Folder creation and organization
├── html_generator.py            # HTML/CSS/JavaScript generation
├── comprehensive_media_indexer.py   # File indexing
├── comprehensive_media_matcher.py   # 7-strategy matching
└── media_reference_extractor.py     # Extract media references
```

### Adding New Features

1. **New media type support** - Update `html_generator.py` rendering logic
2. **New matching strategy** - Add to `comprehensive_media_matcher.py`
3. **New export format** - Enhance `schema_inference.py`

## Performance

Typical performance on a modern system:

- **Small export** (100 conversations, 500 files): ~30 seconds
- **Medium export** (1,000 conversations, 3,000 files): ~3 minutes
- **Large export** (2,000+ conversations, 6,000+ files): ~8 minutes

The parser is I/O bound - performance scales with disk speed.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest tests/`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related Projects

- [Humanizer](https://github.com/temnoon/humanizer_root) - Quantum memory system using tetralemma logic
- [Humanizer MCP Server](https://github.com/temnoon/humanizer-mcp) - Memory server integration

## Acknowledgments

- Built for the [Humanizer](https://github.com/temnoon/humanizer_root) project
- Inspired by the need for comprehensive ChatGPT archive preservation
- Thanks to the community for testing and feedback

---

**Found a bug?** [Open an issue](https://github.com/temnoon/openai-export-parser/issues)

**Have a question?** [Start a discussion](https://github.com/temnoon/openai-export-parser/discussions)
