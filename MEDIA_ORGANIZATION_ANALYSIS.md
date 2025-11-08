# Media Organization Analysis - OpenAI Export

**Date:** 2025-11-07
**Export Version:** Analyzed from user's OpenAI export
**Status:** In Progress - Multiple organization patterns discovered

---

## Summary

OpenAI organizes media files in **at least 3 different ways** in their exports:

1. **DALL-E Generated Images** - Organized by `conversation_id` in subdirectories
2. **User Uploaded Files (with file-IDs)** - Flat directory with `file-{ID}_{name}` pattern
3. **Code Interpreter Files** - Nested by conversation_id then session_id
4. **Audio Files** - `.dat` files in conversations directory

---

## Pattern 1: DALL-E Images by Conversation ID

**Location:**
```
Dall-E__user-xxx_dallelabs_N.zip/
  personal/dallelabs/user-data/chatgptgenerations/user-xxx/
    conversations/
      {conversation_id}/
        Z9OIdCXqnSiaH6bc.png
        PtReZyop2mwtYYA9.png
```

**Characteristics:**
- Files have random alphanumeric names (no extension info in name)
- Organized by conversation_id (UUID format)
- Extensions: `.png`, `.webp`
- **Current status:** ✅ Working (88 conversations matched)

**JSON Reference:**
```json
{
  "metadata": {
    "dalle": {
      "gen_id": "...",
      "prompt": "..."
    }
  }
}
```

---

## Pattern 2: User Uploaded Files with file-IDs

**Location:**
```
Files__user-xxx_files_N.zip/
  personal/files/
    file-CSDzgtOhPLr3NzxdVkRcDgEC_IMG_7897.JPG
    file-W5KHEi88dA9dpd6i88Weww4I_IMG_7890.JPG
```

**Characteristics:**
- Files have pattern: `file-{file-ID}_{original_name}.{ext}`
- Flat directory (not organized by conversation)
- The `file-ID` matches the `id` field in conversation JSON attachments
- Extensions: `.jpg`, `.JPG`, `.jpeg`, `.png`, `.pdf`, etc.
- **Current status:** ❌ Not working (724+ conversations missing media)

**JSON Reference:**
```json
{
  "metadata": {
    "attachments": [
      {
        "id": "file-CSDzgtOhPLr3NzxdVkRcDgEC",
        "name": "IMG_7897.JPG",
        "mime_type": "image/jpeg",
        "width": 1434,
        "height": 1434
      }
    ]
  }
}
```

**Matching Strategy:**
- Extract `file-ID` from `metadata.attachments[].id`
- Search for file matching pattern: `file-{file-ID}_*`
- Match by file-ID prefix, not by filename

---

## Pattern 3: Code Interpreter Files by Conversation + Session

**Location:**
```
Files__user-xxx_files_N.zip/
  personal/files/
    {conversation_id}/
      {session_id}/
        mnt/data/
          filename.json
          filename.csv
          filename.png
```

**Characteristics:**
- Nested structure: conversation_id → session_id → mnt/data/ → files
- Preserves original filenames
- Can include data files (JSON, CSV) and visualizations (PNG, JPG)
- **Current status:** ❌ Not indexed

**Example:**
```
68964edc-58f8-832c-a66e-d0fbf89ce2ee/
  49127d96-152d-46e7-87ae-d6105deaa6e9/
    mnt/data/
      Operator_Effectiveness__Target_vs_Collateral.json
```

---

## Pattern 4: Audio/Video .dat Files

**Location:**
```
Conversations__user-xxx_conversations_1_export.zip/
  personal/conversations/
    file_000000005964622f956e35ecda2b6907.dat  (WAVE audio)
    file_00000000e828622f8b9408a188c44fc3.dat
```

**Characteristics:**
- Files have `.dat` extension but are actually audio/video
- Can be identified by file magic number (RIFF for WAV, etc.)
- Naming pattern: `file_{hash}.dat`
- **Current status:** ❌ Not handled

---

## Pattern 5: Other Files in Flat Directory

**Location:**
```
Files__user-xxx_files_N.zip/
  personal/files/
    IMG_1645.jpg                    # iPhone photos
    0404e116-be70-4d8d...           # UUID no extension (PNG/JPEG)
    0055012D-F735-47BD-...jpeg      # iOS UUID format
    polar_graph.png                 # Named files
```

**Characteristics:**
- Mixed naming conventions
- No conversation_id in path
- Files without extensions can be images (check with `file` command)
- **Current status:** ❌ Not indexed

---

## Statistics from User's Export

```
Total conversations:                  1,823
Conversations with attachments:         812
Conversations with media matched:        88
Conversations missing media:            724+

Custom GPTs (gizmo_ids):                 66
Most used gizmo (g-FmQp1Tm1G):        1,791 conversations
```

**Top Gizmo IDs:**
- `g-FmQp1Tm1G`: 1,791 conversations (likely "Image Name Echo & Bounce")
- `g-5X3Njz7oO`: 1,570 conversations
- `g-FB0R5egnl`: 651 conversations
- `g-rNNpOLRg9`: 328 conversations

---

## Implementation Plan

### Phase 1: File-ID Matching (High Priority)

Update `media_indexer.py` to add:

```python
def scan_file_archives(self, tmp_dir):
    """
    Scan Files archives for file-ID patterns.

    Returns:
        Dict mapping file-ID -> full path
    """
    file_id_to_path = {}

    for root, dirs, files in os.walk(tmp_dir):
        if '/Files_' not in root:
            continue

        for filename in files:
            # Match pattern: file-{ID}_*
            match = re.match(r'file-([A-Za-z0-9]+)_', filename)
            if match:
                file_id = f"file-{match.group(1)}"
                filepath = os.path.join(root, filename)
                file_id_to_path[file_id] = filepath

    return file_id_to_path
```

Update `media_matcher.py` to:
1. Extract file-IDs from `metadata.attachments[].id`
2. Look up files in the file-ID index
3. Add to conversation's `_media_files` list

**Expected impact:** Match 724+ additional conversations

### Phase 2: Code Interpreter Files (Medium Priority)

Add conversation_id + nested directory scanning for Code Interpreter outputs.

### Phase 3: .dat File Handling (Low Priority)

- Detect file type using magic numbers
- Rename with proper extension
- Add to media index

### Phase 4: Flat File Matching (Low Priority)

- Build index of all files by hash/checksum
- Attempt fuzzy matching for files without clear references

---

## Test Cases

**Test 1: User Uploaded Image**
- Conversation: "Mandala Image Description" (1a953fc1-e78d-449f-a54f-5bff11c4ff3b)
- Expected files: `file-CSDzgtOhPLr3NzxdVkRcDgEC_IMG_7897.JPG`
- Current: Empty media folder
- After fix: Should have 2 images

**Test 2: DALL-E Images**
- Conversation: "Children's Book Illustrations" (23e85562-f7fe-44a7-ae4e-c7121b7770e7)
- Expected files: 104 PNG files
- Current: ✅ 54 files (duplicates collapsed)
- Status: Working

**Test 3: Custom GPT with Mixed Media**
- Gizmo: g-FmQp1Tm1G (used in 1,791 conversations)
- Should have both user uploads and DALL-E images
- Test with "mandala" conversations

---

## Questions to Investigate

1. ✅ **How are file-IDs mapped to filenames?**
   Answer: Files are named `file-{ID}_{original_name}.{ext}` in flat directory

2. ❓ **Is there a master index file?**
   Need to check: Look for JSON files in root of Files archives

3. ❓ **Are .dat files always audio?**
   Partial: Found WAVE audio, need to check if video/images also use .dat

4. ❓ **Why are some files UUIDs without extensions?**
   Answer: Likely iOS/macOS file system artifacts - use `file` command to detect type

5. ✅ **How to identify Custom GPT names from gizmo_ids?**
   Could build manifest from conversation titles that use each gizmo_id

---

## Next Steps

1. Implement file-ID matching in media_indexer.py
2. Test on mandala conversations
3. Run full re-parse
4. Verify 724+ conversations now have media
5. Document gizmo_id → Custom GPT name mappings
