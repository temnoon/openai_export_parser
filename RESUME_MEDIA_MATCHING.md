# Resume: Fix Media Matching for OpenAI Export Parser

**Status:** In Progress - Critical Bug Identified
**Date:** 2025-01-07
**Priority:** HIGH - 110 conversations missing their media files

---

## Problem Summary

The parser successfully creates organized conversation folders but **fails to match media files to conversations in most cases**. Out of 3,646 conversations:
- ✅ Media extracted: 10,488 files found
- ❌ Media matched: Only ~36 conversations have media
- ⚠️ **Missing: ~110 conversations should have media but don't**

### Root Cause

The current `MediaMatcher` class only looks for media references in **message text content**, using:
- Direct filename mentions (e.g., "image.png")
- `file-xxxx` pattern matching
- UUID pattern matching

**But it completely misses:**
1. **Conversation-based organization**: Media files are stored in directories named by `conversation_id`:
   ```
   /conversations/8fd0fa6d-7609-4539-bca6-81be74d48e8f/
     └── Z9OIdCXqnSiaH6bc.png
   ```

2. **Structured JSON references**: Media is referenced in deeply nested JSON fields, not text:
   ```json
   {
     "mapping": {
       "e6f1192a-b2fa-4f39-a6ee-bdd9c01a7c8e": {
         "message": {
           "metadata": {
             "aggregate_result": {
               "messages": [{
                 "image_url": "file-service://885ecbfd-4489-4a2f-b407-8c7680732561"
               }]
             }
           }
         }
       }
     }
   }
   ```

3. **No OpenAI-provided index**: OpenAI doesn't include a mapping file that links:
   - `file-service://UUID` → actual filename
   - `file-xxx` IDs → actual files
   - Conversation IDs → media files

---

## What We Know

### Discovered Media Organization

**DALL-E Images:**
```
User Online Activity/
  Dall-E__user-xxx_dallelabs_19.zip/
    personal/dallelabs/user-data/chatgptgenerations/user-xxx/
      conversations/
        {conversation_id}/
          Z9OIdCXqnSiaH6bc.png
          PtReZyop2mwtYYA9.png
```

**User Uploaded Files:**
```
User Online Activity/
  Files__user-xxx_files_2.zip/
    personal/files/user-xxx/
      {file_id}/
        filename.pdf
```

### Key Data Points

1. **60 conversation directories with media** found in extracted temp files
2. **110 organized conversations** have matching `conversation_id` in those directories
3. Current location: `output_organized/_tmp/User Online Activity/`

### Evidence from Testing

```python
# Verified that conversation.json has conversation_id field
conv.get("conversation_id")  # e.g., "8d8aa66c-2d80-4aa5-a600-0d42752325ec"

# And media exists in matching directory structure
/conversations/8d8aa66c-2d80-4aa5-a600-0d42752325ec/
  └── image1.png
  └── image2.png
```

---

## Solution Architecture

### Phase 1: Build Comprehensive Media Index

Create a new module: `media_indexer.py`

**Purpose:** Scan the temporary extraction directory and build mappings:

```python
{
  "conversation_to_media": {
    "8fd0fa6d-7609-4539-bca6-81be74d48e8f": [
      {
        "path": ".../conversations/8fd0fa6d-7609-4539-bca6-81be74d48e8f/Z9OIdCXqnSiaH6bc.png",
        "filename": "Z9OIdCXqnSiaH6bc.png",
        "type": "dalle_generation"
      }
    ]
  },

  "file_service_to_media": {
    "885ecbfd-4489-4a2f-b407-8c7680732561": {
      "path": ".../image.png",
      "conversation_id": "8d8aa66c-2d80-4aa5-a600-0d42752325ec"
    }
  },

  "file_id_to_media": {
    "file-abc123xyz": {
      "path": ".../document.pdf",
      "original_name": "research_paper.pdf"
    }
  }
}
```

### Phase 2: Enhanced Media Matcher

Update `media_matcher.py` to use three strategies:

**Strategy 1: Conversation ID Matching (NEW - PRIMARY)**
```python
def match_by_conversation_id(self, conversations, media_index):
    """Match media using conversation_id from JSON."""
    for conv in conversations:
        conv_id = conv.get("conversation_id") or conv.get("id")
        if conv_id in media_index["conversation_to_media"]:
            # Found media for this conversation!
            return media_index["conversation_to_media"][conv_id]
```

**Strategy 2: Structured Field Matching (NEW - SECONDARY)**
```python
def match_by_json_fields(self, conversation, media_index):
    """Extract file-service:// and file-xxx from JSON structure."""
    # Recursively search for:
    # - image_url fields with file-service://
    # - file_ids arrays
    # - asset_pointer fields
```

**Strategy 3: Text Content Matching (EXISTING - FALLBACK)**
```python
def match_by_text_content(self, message_text, media_files):
    """Current implementation - keep as fallback."""
    # Existing filename/UUID/file-ID matching in text
```

### Phase 3: Update Parser Flow

Modify `parser.py` → `parse_export()` method:

```python
def parse_export(self, zip_path, output_dir):
    # ... existing extraction code ...

    # NEW: Build media index BEFORE matching
    self.log("Building media index from directory structure...")
    media_index = self.indexer.build_media_index(tmp_dir)

    # Save index for debugging/reference
    with open(os.path.join(output_dir, "media_index.json"), "w") as f:
        json.dump(media_index, f, indent=2)

    # Enhanced matching with all strategies
    conversations = self.matcher.match(
        conversations,
        self.media_files,
        media_index=media_index  # NEW parameter
    )
```

---

## Implementation Plan

### Step 1: Create Media Indexer Module

**File:** `openai_export_parser/media_indexer.py`

**Key functions:**
- `build_media_index(tmp_dir)` - Main entry point
- `scan_dalle_archives(path)` - Find DALL-E images by conversation_id
- `scan_file_archives(path)` - Find uploaded files by file_id
- `extract_file_service_refs(conversation)` - Parse JSON for file-service:// UUIDs

**Expected output:**
```json
{
  "summary": {
    "conversations_with_media": 110,
    "total_media_files": 5244,
    "dalle_images": 4800,
    "uploaded_files": 444
  },
  "conversation_to_media": { ... },
  "file_service_to_media": { ... },
  "file_id_to_media": { ... }
}
```

### Step 2: Update Media Matcher

**File:** `openai_export_parser/media_matcher.py`

**Changes:**
- Add `match()` parameter: `media_index=None`
- Implement conversation_id matching first (highest confidence)
- Fall back to JSON field matching
- Fall back to text matching
- Log which strategy was used for each match

### Step 3: Update Conversation Organizer

**File:** `openai_export_parser/conversation_organizer.py`

**Changes:**
- Use media_index to get media files for each conversation
- Copy files based on conversation_id match
- Update media_manifest.json to include source information

### Step 4: Add CLI Flag for Re-matching

For users who already parsed, add:
```bash
openai-export-parser rematch-media output_organized/ -v
```

This would:
1. Load existing index.json
2. Rebuild media_index from _tmp directory (if still exists)
3. Re-run media matching with new strategies
4. Update conversation folders with newly found media

---

## Testing Strategy

### Test Case 1: Known Conversation with Media

```python
conv_id = "8fd0fa6d-7609-4539-bca6-81be74d48e8f"
# Should find: Z9OIdCXqnSiaH6bc.png
```

### Test Case 2: Conversation with file-service References

```python
conv_id = "8d8aa66c-2d80-4aa5-a600-0d42752325ec"
# Should find images via file-service:// mapping
```

### Test Case 3: Count Improvement

Before: ~36 conversations with media
After: ~110+ conversations with media
Success: >100 conversations matched

---

## Files to Modify

1. **NEW:** `openai_export_parser/media_indexer.py`
2. **UPDATE:** `openai_export_parser/media_matcher.py`
3. **UPDATE:** `openai_export_parser/conversation_organizer.py`
4. **UPDATE:** `openai_export_parser/parser.py`
5. **UPDATE:** `openai_export_parser/cli.py` (add rematch-media command)

---

## Current State

### What Works
- ✅ Zip extraction (including malformed zips)
- ✅ Conversation JSON parsing
- ✅ Organized folder creation with timestamps
- ✅ Hash-based media naming (prevents collisions)
- ✅ HTML rendering with inline images
- ✅ Text-based media matching (limited success)

### What's Broken
- ❌ Conversation ID → media mapping
- ❌ file-service:// URL resolution
- ❌ Structured JSON field parsing for media references
- ❌ ~110 conversations missing their media

### Location of Test Data
- Organized output: `~/openai-export-parser/output_organized/`
- Temp files: `~/openai-export-parser/output_organized/_tmp/`
- Sample conversation with expected media:
  - `output_organized/2023-07-07_Code_Interpreter_Plugin_Features_01354/`
  - Should have media from conversation_id `8d8aa66c-2d80-4aa5-a600-0d42752325ec`

---

## Quick Start for Next Session

```bash
cd ~/openai-export-parser
source venv/bin/activate

# Verify the issue
python3 << 'EOF'
import os
found_media = 0
for folder in os.listdir("output_organized"):
    if folder.startswith("_"): continue
    media_dir = f"output_organized/{folder}/media"
    if os.path.exists(media_dir) and os.listdir(media_dir):
        found_media += 1
print(f"Conversations with media: {found_media}/3646")
EOF

# Expected output: ~36 (should be ~110+)

# Start implementation
touch openai_export_parser/media_indexer.py
```

---

## Questions to Answer

1. **File-service UUID mapping**: How to map `file-service://885ecbfd-...` to actual files?
   - May need to search temp directory for files and build reverse index
   - Check if DALL-E archives include any metadata files

2. **File ID format**: Are there other file reference formats we're missing?
   - Look for `attachment` fields
   - Look for `asset_pointer` fields
   - Check `file_ids` arrays

3. **Performance**: Building index for 10K+ files
   - Should we cache the media_index.json?
   - Can we incrementally update it?

---

## Success Criteria

1. ✅ Media index successfully builds mapping for all 60+ conversation dirs
2. ✅ At least 100 conversations now have media (up from ~36)
3. ✅ HTML renderer shows images for conversations with media
4. ✅ No duplicate media files (hash-based naming still works)
5. ✅ Global `media_index.json` documents all mappings
6. ✅ Tests pass with new matching strategies

---

## Notes

- The _tmp directory is large (~2.5GB) - don't delete it until media matching is fixed
- DALL-E images are in predictable directory structure (by conversation_id)
- User uploaded files may have different structure (by file_id)
- Some conversations may have BOTH DALL-E images AND uploaded files
- The `file-service://` UUIDs may not have a direct mapping - might need filename-based fuzzy matching

---

**Next Steps:** Implement media_indexer.py first, then test on a small subset before running on full dataset.
