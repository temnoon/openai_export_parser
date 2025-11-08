# openai-export-parser

[![Tests](https://github.com/yourusername/openai-export-parser/workflows/Tests/badge.svg)](https://github.com/yourusername/openai-export-parser/actions)
[![Python Version](https://img.shields.io/pypi/pyversions/openai-export-parser.svg)](https://pypi.org/project/openai-export-parser/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A robust parser for OpenAI ChatGPT export archives with future-proof schema inference.**

Parse OpenAI's complex, nested export.zip files into clean, normalized JSON conversations with automatic media matching, threading, and schema detection.

## Features

- **Recursive Zip Extraction** - Handles arbitrarily nested zip archives
- **Robust Zip Handling** - Works with malformed exports using fallback extraction (ditto/unzip)
- **Automatic Schema Inference** - Future-proofs against OpenAI format changes
- **Media Matching** - Links images, audio, and files to their messages
- **Conversation Threading** - Adds parent/child relationships to messages
- **Progress Tracking** - Real-time progress bars with `tqdm`
- **Robust Error Handling** - Gracefully handles malformed or incomplete exports
- **Humanizer-Ready Output** - Optimized for ingestion into memory systems

## Installation

```bash
pip install openai-export-parser
```

Or install from source:

```bash
git clone https://github.com/yourusername/openai-export-parser.git
cd openai-export-parser
pip install -e .
```

## Quick Start

### Command Line

```bash
# Basic usage
openai-export-parser export.zip

# Specify output directory
openai-export-parser export.zip -o my_parsed_data

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
├── conversations/
│   ├── conv_00000.json
│   ├── conv_00001.json
│   └── ...
├── media/
│   ├── image_abc123.png
│   ├── document_xyz789.pdf
│   └── ...
└── index.json
```

### index.json

Global metadata and statistics:

```json
{
  "conversation_count": 42,
  "media_count": 18,
  "schema_inference": [
    {
      "root_fields": ["id", "title", "create_time", "messages"],
      "message_count": 12,
      "message_schema": {
        "fields": ["id", "role", "content", "create_time"],
        "has_content_list": false,
        "has_text": true,
        "has_files": false,
        "has_image_blocks": false
      }
    }
  ]
}
```

### conversations/conv_XXXXX.json

Individual conversation with threading:

```json
{
  "id": "conv-abc123",
  "title": "Python Debugging Help",
  "create_time": 1704067200,
  "messages": [
    {
      "id": "msg_00001",
      "role": "user",
      "content": "How do I fix this error?",
      "create_time": 1704067200
    },
    {
      "id": "msg_00002",
      "role": "assistant",
      "content": "Let me help you debug that...",
      "create_time": 1704067245,
      "parent": "msg_00001",
      "media": ["screenshot_abc123.png"]
    }
  ]
}
```

## How It Works

### 1. Recursive Zip Extraction

OpenAI exports can contain nested zips:

```
export.zip
  └── conversations.zip
      └── 2024-01.zip
          └── conversation_abc123.json
```

The parser automatically detects and extracts all nested archives.

### 2. Schema Inference

As OpenAI's export format evolves, the parser automatically detects:

- Message field types (text, multimodal content arrays)
- File attachments (`file_id`, `asset_pointer`, etc.)
- Image blocks in content arrays
- New fields and structures

Results are saved in `index.json` for analysis.

### 3. Media Matching

The parser links media files to messages using:

- **Direct filename mentions** - "Here's `image_abc123.png`"
- **OpenAI file IDs** - `file-aBc123XyZ`
- **UUIDs** - `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

Matched media filenames are added to each message's `media` array.

### 4. Conversation Threading

Each message receives:

- **Unique ID** - `msg_00001`, `msg_00002`, etc.
- **Parent reference** - Links to previous message for tree visualization

## Advanced Usage

### Programmatic Access with Custom Processing

```python
from openai_export_parser import ExportParser

class CustomParser(ExportParser):
    def normalize_conversations(self, conversations):
        # Add custom processing
        conversations = super().normalize_conversations(conversations)

        for conv in conversations:
            # Extract timestamps, calculate statistics, etc.
            conv["message_count"] = len(conv.get("messages", []))

        return conversations

parser = CustomParser(verbose=True)
parser.parse_export("export.zip", "output")
```

### Integration with Memory Systems

The output format is designed for ingestion into vector databases and memory systems:

```python
import json
from openai_export_parser import ExportParser

# Parse export
parser = ExportParser()
parser.parse_export("export.zip", "parsed")

# Load for vector embedding
for conv_file in Path("parsed/conversations").glob("*.json"):
    with open(conv_file) as f:
        conv = json.load(f)

    for msg in conv["messages"]:
        # Embed and store in ChromaDB, Pinecone, etc.
        text = msg["content"]
        metadata = {
            "conversation_id": conv["id"],
            "timestamp": msg.get("create_time"),
            "role": msg["role"]
        }
        # your_embedding_function(text, metadata)
```

## Understanding the Export Format

OpenAI's ChatGPT export format varies by:

- Export date (format has evolved over time)
- Account type (Free, Plus, Team, Enterprise)
- Data types (text, DALL-E images, code interpreter results)

This parser handles all known variations and uses schema inference to adapt to new formats.

### Common Variations

**Single conversations.json:**
```json
[
  {"id": "conv1", "messages": [...]},
  {"id": "conv2", "messages": [...]}
]
```

**Multiple conversation files:**
```
conversations/
  ├── conversation_001.json
  ├── conversation_002.json
  └── ...
```

**Nested by date:**
```
2024-01/
  ├── conversations.json
  └── media/
```

The parser automatically detects and handles all structures.

## Troubleshooting

### "No conversations found"

- Ensure you're using the correct export.zip (not a manual selection)
- Try verbose mode: `openai-export-parser export.zip -v`
- Check for nested zips that weren't extracted

### "Bad magic number for file header" or zip errors

The parser automatically handles malformed zip files:
- On macOS: Uses `ditto` (same as Archive Utility)
- On all platforms: Falls back to system `unzip` command
- Accepts partial extractions if files are recovered

If you see this error but Archive Utility can open the file, the parser should still work.

### "Media files not matching"

- Media matching uses heuristics (filenames, IDs, UUIDs)
- Some generated filenames may not be referenced in message text
- Check `index.json` to see what was detected

### "Encoding errors"

The parser uses UTF-8 with error handling. If you see mojibake:

```python
parser = ExportParser(verbose=True)
# Check parser.log output for encoding warnings
```

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

### Adding New Schema Patterns

Edit `schema_inference.py` to detect new fields:

```python
def infer_message_schema(self, msg):
    return {
        "fields": list(msg.keys()),
        "has_your_new_field": "new_field" in msg,
        # ...
    }
```

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

- [Humanizer MCP Server](https://github.com/yourusername/humanizer-mcp) - Quantum memory system using tetralemma logic
- [ChatGPT-to-JSON](https://github.com/example/chatgpt-to-json) - Alternative parser approach

## Acknowledgments

- Built for the [Humanizer](https://github.com/yourusername/humanizer_root) project
- Inspired by the need for robust ChatGPT archive analysis
- Thanks to the OpenAI community for format documentation

---

**Found a bug?** [Open an issue](https://github.com/yourusername/openai-export-parser/issues)

**Have a question?** [Start a discussion](https://github.com/yourusername/openai-export-parser/discussions)
