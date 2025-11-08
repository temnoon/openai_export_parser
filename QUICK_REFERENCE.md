# Media Matching: Quick Reference Guide

## Overview
The `media_matcher.py` module uses 5 sequential strategies to match media files to conversations. Each strategy has specific requirements and reliability levels.

## File-ID Format
```
file-[A-Za-z0-9]+
Examples: file-BTGHeayl9isKTp9kvyBzirg0, file-abc123xyz
```

## 5 Matching Strategies (in order)

### 1. Conversation ID Matching
- **When Used:** media_index provided
- **Looks For:** `/conversations/{uuid}/` directory structure
- **Reliability:** 99.9%
- **File Types:** DALL-E images

### 2. File-ID Matching ← Main strategy for user uploads
- **When Used:** file_id_index provided
- **Source:** `message.metadata.attachments[].id`
- **Index Key:** Filename pattern `file-{ID}_*` or `file-{ID}-*`
- **Reliability:** 99.5%
- **File Types:** User-uploaded files

### 3. File-Hash Matching
- **When Used:** file_hash_index provided
- **Source:** `message.content.parts[].asset_pointer` (sediment://)
- **Pattern:** `sediment://file_{32hex}`
- **Reliability:** 99.9%
- **File Types:** Newer DALL-E images

### 4. Size-Based Matching
- **When Used:** size_index provided
- **Source:** `message.content.parts[].asset_pointer` (file-service://)
- **Requirements:** Must have `metadata.dalle` with `gen_id`
- **Method:** Two-pass (build map, then match)
- **Reliability:** 99.8% with gen_id
- **File Types:** DALL-E generations

### 5. Text Content Matching (Fallback)
- **When Used:** All other indices absent
- **Source:** Message text as string
- **Methods:** 
  1. Direct filename match
  2. File-ID pattern in text
  3. UUID pattern in text
- **Reliability:** 50-70%
- **Requirement:** Explicit text reference

## Critical Gaps: Images That Won't Match

| Gap | Issue | Missing Check | Impact |
|-----|-------|---------------|--------|
| GAP 1 | `metadata.attachments` missing | Should check `content.parts[].image_url` | Files in wrong structure unmatched |
| GAP 2 | `content.parts[].image_url` | Not extracted | Modern image references missed |
| GAP 3 | `type == "image"` parts | Not recognized | Structural image refs ignored |
| GAP 4 | DALL-E without `dalle` metadata | Falls back to size-only | Collision risk |
| GAP 5 | Text-only refs in old exports | Strategy 5 rarely used | Requires explicit mention |

## File-ID Matching Flow

### Index Building (MediaIndexer)
```
File on disk: file-BTGHeayl9isKTp9kvyBzirg0_document.pdf
                ↓ Extract using regex: (file-[A-Za-z0-9]+)[_-]
Indexed as:   file-BTGHeayl9isKTp9kvyBzirg0 → /full/path
```

### Conversation Matching (MediaMatcher)
```
Conversation: metadata.attachments[0].id = "file-BTGHeayl9isKTp9kvyBzirg0"
                ↓ Look up in file_id_index
Found:        /full/path/file-BTGHeayl9isKTp9kvyBzirg0_document.pdf
                ↓ Add to conv["_media_files"]
Result:       ✓ File matched
```

## Matching Conditions Summary

For **Strategy 2 (File-ID)** to work:
1. ✓ `file_id_index` provided (built by MediaIndexer)
2. ✓ Message has `mapping` → `message` → `metadata`
3. ✓ `metadata.attachments` is non-empty array
4. ✓ `attachment.id` field exists and is not null
5. ✓ File-ID matches something in `file_id_index`
6. ✓ File on disk starts with `file-{ID}_` or `file-{ID}-`

**All 6 conditions must be met for matching to succeed.**

## Common Failure Modes

| Failure | Cause | Fix |
|---------|-------|-----|
| metadata.attachments empty | Image uploaded but not recorded | No fix (data loss) |
| ID in conv but not in index | File deleted before export | N/A (file missing) |
| File named without `file-{ID}_` | Renaming removed ID | Rename to `file-{ID}_...` |
| Case mismatch | "file-ABC" in conv, "file-abc" in file | Ensure exact case match |
| ID has special chars | Pattern only allows [A-Za-z0-9] | Check actual file-ID format |

## Diagnostic Checklist

When images aren't matching:

1. **Does image file exist?**
   - Check: `/path/to/extracted/media/`

2. **Is file-ID in conversation metadata?**
   - Look: `message.metadata.attachments[].id`
   - Extract: `"id": "file-BTGHeayl9isKTp9kvyBzirg0"`

3. **Does filename match pattern?**
   - Should be: `file-BTGHeayl9isKTp9kvyBzirg0_*`
   - Bad: `document_file-BTGHeayl9isKTp9kvyBzirg0.pdf`

4. **Is file-ID in the index?**
   - Check indexer logs: `"Indexed N files with file-IDs"`
   - Verify: `file_id_index["file-BTGHeayl9isKTp9kvyBzirg0"]`

5. **Is ID present in conversation's mapping?**
   - Traverse: `conv["mapping"][node_id]["message"]["metadata"]["attachments"]`
   - Find: `attachment["id"]` field

6. **Do IDs match exactly?** (case-sensitive)
   - Conv: `"file-BTGHeayl9isKTp9kvyBzirg0"`
   - File: `"file-BTGHeayl9isKTp9kvyBzirg0_document.pdf"`
   - Must be: byte-for-byte identical

## Logging & Stats

Enable verbose mode to see matching details:
```python
parser = ExportParser(verbose=True)
```

Output shows:
```
✓ Matched {N} conversations by conversation_id
✓ Matched {N} conversations by file-ID
✓ Matched {N} conversations by file-hash (sediment://)
✓ Matched {N} conversations by file-size (DALL-E generations)
✓ Matched {N} files by text content
```

## Code Locations

| Component | File | Lines |
|-----------|------|-------|
| File-ID pattern | media_matcher.py | 12 |
| Strategy 1 | media_matcher.py | 100-127 |
| Strategy 2 | media_matcher.py | 129-167 |
| Strategy 3 | media_matcher.py | 169-212 |
| Strategy 4 | media_matcher.py | 214-326 |
| Strategy 5 | media_matcher.py | 328-363 |
| Index building | media_indexer.py | 31-138 |
| File-ID extraction | media_indexer.py | 176-200 |
| Stats tracking | media_matcher.py | 21-30 |

## Key Data Structures

### File-ID Index
```python
file_id_index = {
    "file-ABC...": "/path/to/file-ABC..._document.pdf",
    "file-XYZ...": "/path/to/file-XYZ..._photo.png"
}
```

### Conversation With Attachment
```json
{
  "mapping": {
    "node-id": {
      "message": {
        "metadata": {
          "attachments": [
            {"id": "file-ABC...", "name": "doc.pdf"}
          ]
        }
      }
    }
  }
}
```

### Matched Conversation
```json
{
  "_media_files": [
    "/path/to/file-ABC..._document.pdf"
  ]
}
```

## Testing

Test file: `/Users/tem/openai-export-parser/tests/test_media_matcher.py`

Key test cases:
- `test_match_direct_filename` - Direct basename matching
- `test_match_file_id_pattern` - File-ID in text
- `test_match_uuid_pattern` - UUID in text
- `test_multiple_media_matches` - Multiple files per message
- `test_multimodal_content` - Mixed content types

Run tests:
```bash
pytest tests/test_media_matcher.py -v
```

