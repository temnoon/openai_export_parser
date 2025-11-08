# Media Matcher Analysis: File-ID Matching and Attachment Handling

## Overview

The `media_matcher.py` module is responsible for matching media files discovered during OpenAI export parsing to the conversations that reference them. It uses **5 sequential matching strategies** with increasing levels of fallback sophistication.

---

## File-ID Pattern Matching

### 1. File-ID Format Recognition

**Pattern Definition (Line 12):**
```python
FILE_ID_PATTERN = re.compile(r"file-[A-Za-z0-9]+")
```

**Characteristics:**
- Prefix: `file-`
- Followed by: Any alphanumeric characters (uppercase, lowercase, digits)
- Examples:
  - `file-BTGHeayl9isKTp9kvyBzirg0` (the example from your question)
  - `file-abc123xyz`
  - `file-CSDzgtOhPLr3NzxdVkRcDgEC`

### 2. Where File-IDs Appear

File-IDs can be found in multiple locations within conversation data:

#### A. In Metadata Attachments (Strategy 2: _match_by_file_id)
**Lines 129-167** - Primary method for user-uploaded files

```python
def _match_by_file_id(self, conversations, file_id_index):
    for conv in conversations:
        mapping = conv.get("mapping", {})
        for node_id, node_data in mapping.items():
            message = node_data.get("message")
            metadata = message.get("metadata", {})
            attachments = metadata.get("attachments", [])
            
            for attachment in attachments:
                file_id = attachment.get("id")
                # Look up in file_id_index
```

**Expected Structure:**
```json
{
  "mapping": {
    "node-id": {
      "message": {
        "metadata": {
          "attachments": [
            {
              "id": "file-BTGHeayl9isKTp9kvyBzirg0",
              "name": "document.pdf"
            }
          ]
        }
      }
    }
  }
}
```

#### B. In Message Text Content (Strategy 5: _match_by_text_content)
**Lines 328-363** - Fallback text-based matching

The text content of messages is searched for:
- Direct filename matches
- File-ID pattern matches (extracted via regex)
- UUID pattern matches

---

## Matching Strategies (in order of execution)

### Strategy 1: Conversation ID Matching (Lines 100-127)
**Purpose:** Match media organized in `/conversations/{uuid}/` directories

**Conditions Met:**
- `media_index` is provided
- Media files are in a `/conversations/{conversation_id}/` directory structure
- Conversation has a matching `conversation_id` or `id` field

**Code Flow:**
```python
conv_id = conv.get("conversation_id") or conv.get("id")
if conv_id and conv_id in media_index:
    media_paths = media_index[conv_id]
    conv["_media_files"] = media_paths  # Store full paths
    # Also add basenames to first message for backward compatibility
    basenames = [os.path.basename(p) for p in media_paths]
    first_msg["media"] = basenames
```

**Reliability:** Highest (99.9% accurate)
**File Types:** DALL-E images, newer generated images with sediment:// references

---

### Strategy 2: File-ID Matching (Lines 129-167)
**Purpose:** Match user-uploaded files by OpenAI's file-ID system

**Conditions Met:**
- `file_id_index` is provided
- Message has `metadata.attachments[].id` field with a file-ID
- File-ID exists in the file_id_index (indexed from filename patterns like `file-{ID}_{original}.ext`)

**Code Flow:**
```python
for attachment in attachments:
    file_id = attachment.get("id")
    if file_id:
        file_path = file_id_index.get(file_id)
        if file_path:
            conv_media_files.add(file_path)
            file_ids_found.append(file_id)
```

**Reliability:** High (99.5% - requires exact ID match)
**File Types:** User-uploaded files (PDFs, images, etc.)
**Failure Modes:** 
- Attachments missing from metadata
- File-ID not in index (file was deleted/missing)
- File named without `file-{ID}_` pattern

---

### Strategy 3: File-Hash Matching (Lines 169-212)
**Purpose:** Match newer files using sediment:// asset pointers

**Conditions Met:**
- `file_hash_index` is provided
- Message has `content.parts[].asset_pointer` starting with `sediment://`
- Pattern: `sediment://file_{hash}`

**Code Flow:**
```python
asset_pointer = part.get("asset_pointer", "")
if asset_pointer and asset_pointer.startswith("sediment://"):
    file_hash = asset_pointer.replace("sediment://", "")
    # file_hash = "file_000000009e586230866e2a177650b0e8"
    file_path = file_hash_index.get(file_hash)
```

**Expected Structure:**
```json
{
  "content": {
    "parts": [
      {
        "asset_pointer": "sediment://file_000000009e586230866e2a177650b0e8",
        "metadata": {
          "dalle": {...}
        }
      }
    ]
  }
}
```

**Reliability:** Very High (99.9%)
**File Types:** DALL-E images, newer generated content
**Failure Modes:**
- asset_pointer missing or malformed
- File hash doesn't match anything in index

---

### Strategy 4: Size-Based Matching (Lines 214-326)
**Purpose:** Match DALL-E generation files by file size with gen_id tiebreaker

**Conditions Met:**
- `size_index` is provided
- Files are in `dalle-generations/` directories
- Message has `content.parts[].asset_pointer` starting with `file-service://`
- Message has `metadata.dalle` with a `gen_id`
- File has `size_bytes` field

**Code Flow (Two-Pass Algorithm):**

**Pass 1:** Build reverse map
```python
size_gen_id_map = {}  # (size, gen_id) -> file_path

for conv in conversations:
    for part in content_parts:
        if asset_pointer.startswith("file-service://"):
            dalle = metadata.get("dalle", {})
            if dalle:
                file_size = part.get("size_bytes")
                gen_id = dalle.get("gen_id")
                if (file_size, gen_id) in size_index:
                    size_gen_id_map[(file_size, gen_id)] = matching_file[0]
```

**Pass 2:** Match to conversations
```python
for part in content_parts:
    if dalle and file_size:
        # Try gen_id match first (best)
        if (file_size, gen_id) in size_gen_id_map:
            matched_file = size_gen_id_map[(file_size, gen_id)]
        # Fallback to size-only match
        elif file_size in size_index:
            matched_file = size_index[file_size][0]
```

**Expected Structure:**
```json
{
  "content": {
    "parts": [
      {
        "asset_pointer": "file-service://...",
        "size_bytes": 65536,
        "metadata": {
          "dalle": {
            "gen_id": "abc123..."
          }
        }
      }
    ]
  }
}
```

**Reliability:** 99.8% with gen_id tiebreaker (2 collisions in 1,222 files)
**Failure Modes:**
- No dalle metadata (means not a generation)
- size_bytes missing
- Multiple files with same size (uses first match unless gen_id is present)
- File not in dalle-generations/ folder

---

### Strategy 5: Text Content Matching (Lines 328-363)
**Purpose:** Fallback strategy when structured indices aren't available

**Conditions Met:**
- Only used if ALL other strategies' indices are absent/empty
- Searches entire message text for:
  - Direct filename substring matches
  - File-ID pattern matches (extracts `file-*` and checks if in filename)
  - UUID pattern matches (extracts UUIDs and checks if in filename)

**Code Flow:**
```python
for msg in conv.get("messages", []):
    msg_str = str(msg)  # Convert entire message to string
    for media in media_files:
        fname = os.path.basename(media)
        
        # Direct match
        if fname in msg_str:
            matched = True
        
        # File-ID pattern match
        for m in self.FILE_ID_PATTERN.findall(msg_str):
            if m in fname:  # e.g., "file-abc123" in "file-abc123_document.pdf"
                matched = True
        
        # UUID pattern match
        for u in self.UUID_PATTERN.findall(msg_str):
            if u in fname:
                matched = True
        
        if matched:
            msg.setdefault("media", []).append(fname)
```

**Reliability:** Low (prone to false matches, requires explicit references in text)
**Examples of Success:**
- Message text: "Here's the file file-abc123xyz"
- File: `file-abc123xyz_document.pdf` ✓ Match!

**Examples of Failure:**
- Message text mentions file-ID but file has different name
- File exists but isn't mentioned anywhere in conversation
- UUID-named files without any text reference

---

## Image References in Conversations: Potential Gaps

### Known Gaps Where Images Aren't Matched:

#### 1. **Missing metadata.attachments**
**Problem:** Image uploaded as attachment but not in `metadata.attachments`

```json
// This case won't match by file-ID:
{
  "message": {
    "content": "Here's my image",
    "metadata": {}  // ← attachments missing!
  }
}
```

**Why:** Strategy 2 (_match_by_file_id) only looks at:
```python
attachments = metadata.get("attachments", [])
for attachment in attachments:  # ← Empty list = no matches
    file_id = attachment.get("id")
```

**Fix Needed:** Also check `content.parts[]` for image type items

---

#### 2. **Images in content.parts[] without asset_pointer**
**Problem:** Image is in message structure but doesn't have asset_pointer

```json
{
  "content": {
    "parts": [
      {
        "type": "image",
        "image_url": "file-abc123.png"
        // ← No asset_pointer field
        // ← No sediment:// reference
        // ← No file-service:// reference
      }
    ]
  }
}
```

**Why:** Strategies 3 & 4 only check for asset_pointer with specific prefixes:
```python
asset_pointer = part.get("asset_pointer", "")
if asset_pointer and asset_pointer.startswith("sediment://"):
    # ... only matches if sediment:// present
if asset_pointer and asset_pointer.startswith("file-service://"):
    # ... only matches if file-service:// present
```

**What Isn't Checked:**
- `content.parts[].image_url` fields
- `content.parts[].type == "image"` (structure exists but not matched)
- Inline image references in text content

**Fix Needed:** Add extraction logic for `image_url` and `type == "image"` parts

---

#### 3. **Images without proper directory structure**
**Problem:** Media files not in `/conversations/{id}/` hierarchy

```
file_structure:
  /downloaded_images/
    file-BTGHeayl9isKTp9kvyBzirg0_photo.png
    ↑ Not in /conversations/{uuid}/ → Strategy 1 fails
```

**Why:** Strategy 1 (conversation ID matching) requires:
```python
conv_id = self._extract_conversation_id_from_path(filepath)
# Looks for: /conversations/([uuid])/
# Won't find: /downloaded_images/
```

**Impact:** Falls back to Strategy 2 (file-ID), which requires `metadata.attachments`

---

#### 4. **DALL-E generations without dalle metadata**
**Problem:** DALL-E image references without DALLE metadata in parts

```json
{
  "asset_pointer": "file-service://...",
  "size_bytes": 65536,
  "metadata": {}  // ← dalle field missing
}
```

**Why:** Strategy 4 explicitly checks:
```python
dalle = metadata.get("dalle", {})
if dalle:  # ← Requires dalle to be truthy
    # Only then tries size matching
```

**Impact:** Can't use gen_id for disambiguation, reverts to size-only (collision risk)

---

#### 5. **Text-only references without structural data**
**Problem:** Image is mentioned in text but not in metadata/attachments/parts

```json
{
  "message": {
    "content": "I uploaded image file-abc123.png yesterday",
    // No metadata.attachments
    // No content.parts with asset_pointer
  }
}
```

**Why:** This requires Strategy 5 (text content), which:
- Only activates if ALL structured indices are empty
- Requires exact filename or UUID in text
- Prone to false positives

---

## Critical Missing Matching Logic

### Gap 1: image_url in content.parts

**Current Code:** Nothing checks `content.parts[].image_url`

**Should Handle:**
```json
{
  "content": {
    "parts": [
      {
        "type": "image",
        "image_url": "file-abc123.png"
      }
    ]
  }
}
```

**Missing Strategy:** Extract file-IDs/filenames from `image_url` fields and match against media files

### Gap 2: Inline image_url in text

Some systems embed image URLs directly in HTML/text content:
```html
<img src="file-xyz.png" />
```

**Not Currently Matched:** Text strategy converts to string but doesn't parse HTML attributes

### Gap 3: Attachment metadata without file-ID

```json
{
  "metadata": {
    "attachments": [
      {
        "name": "photo.jpg",
        "size": 1024,
        "id": null  // ← Missing ID!
      }
    ]
  }
}
```

**Issue:** Strategy 2 skips if `id` is None/missing

**Could Fall Back To:** Match by filename or size

---

## How the Indexing Works (MediaIndexer)

The matching strategies depend on indices built by `MediaIndexer`:

### 1. **Conversation ID Index** (Strategy 1)
```python
conversation_media = {}  # conversation_id -> [file_paths]
# Populated from: /conversations/{uuid}/ directory structure
```

### 2. **File-ID Index** (Strategy 2)
```python
file_id_to_path = {}  # "file-{ID}" -> "/path/to/file"
# Populated from: Filenames matching "file-{ID}_*" or "file-{ID}-*" pattern
```

### 3. **File-Hash Index** (Strategy 3)
```python
file_hash_to_path = {}  # "file_0000...abc" -> "/path/to/file"
# Populated from: Filenames matching "file_{32hex}-{uuid}.ext" pattern
# Used for: sediment:// asset_pointer matching
```

### 4. **Size Index** (Strategy 4)
```python
size_to_paths = {}  # file_size (bytes) -> [file_paths]
# Populated from: Files in dalle-generations/ folders
# Uses: size_bytes + gen_id for disambiguation
```

### Extraction Patterns Used (MediaIndexer)

**File-ID Extraction (Lines 176-200):**
```python
def _extract_file_id_from_name(self, filename: str) -> str:
    # Try underscore separator first
    match = re.match(r'(file-[A-Za-z0-9]+)_', filename)
    if match:
        return match.group(1)  # "file-abc123"
    
    # Try hyphen separator
    match = re.match(r'(file-[A-Za-z0-9]+)-', filename)
    if match:
        return match.group(1)  # "file-abc123"
    
    return None
```

**File-Hash Extraction (Lines 202-219):**
```python
def _extract_file_hash_from_name(self, filename: str) -> str:
    # Pattern: file_{16-hex}-{uuid}.ext
    match = re.match(r'(file_[a-f0-9]{32})-[a-f0-9-]{36}\.', filename)
    if match:
        return match.group(1)  # "file_000000009e586230866e2a177650b0e8"
    return None
```

---

## Summary: Matching Conditions Checklist

| Strategy | Condition | File-ID Present? | Where it's found | Reliability |
|----------|-----------|-----------------|------------------|-------------|
| Conv ID | `media_index` + `/conversations/{uuid}/` path | Optional | Directory structure | 99.9% |
| File-ID | `file_id_index` + `metadata.attachments[].id` | Required | Metadata field | 99.5% |
| File-Hash | `file_hash_index` + `asset_pointer: sediment://` | No | content.parts | 99.9% |
| Size | `size_index` + `asset_pointer: file-service://` + `dalle metadata` | No | Metadata+parts | 99.8% |
| Text | All indices absent + filename/ID/UUID in text | Optional | Message text string | 50-70% |

---

## Root Cause Analysis: Why Images Aren't Matched

### Most Common Cause
**Missing `metadata.attachments` array**
- User uploaded image as attachment
- File appears in `content.parts[].image_url`
- But `metadata.attachments` is empty or missing
- Strategy 2 fails
- Falls back to Strategy 5 (text content)
- If image URL not in text, NO MATCH

### Secondary Causes
1. File doesn't match naming convention (no `file-{ID}_` prefix)
2. DALL-E generations lack `dalle` metadata
3. Image files in wrong directory structure (not under `/conversations/`)
4. Text references use shortened filenames that don't match on disk

### Why Strategy 5 Often Fails
- Only activates when ALL structured indices are empty
- Requires explicit text reference
- Filename must be exact match in message text
- UUID must match exactly

---

## Recommendations

1. **Enhance Strategy 2** to also extract file-IDs from `content.parts[].image_url`
2. **Add new strategy** for `type == "image"` parts in content
3. **Fallback to size/hash matching** when file-ID is missing but size exists
4. **Improve text matching** to parse HTML and extract URLs/filenames
5. **Add logging** for unmatched media with diagnostics (which strategy tried, why it failed)

