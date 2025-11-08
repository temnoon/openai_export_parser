# File-ID Matching: Code Examples and Edge Cases

## File-ID Pattern Specification

### Regular Expression
```python
FILE_ID_PATTERN = re.compile(r"file-[A-Za-z0-9]+")
```

### Characteristics
- **Prefix:** `file-` (literal)
- **Character Set:** `[A-Za-z0-9]+` (alphanumeric, one or more)
- **Case Sensitivity:** Case-sensitive (both uppercase and lowercase accepted)
- **No Length Limit:** Pattern is open-ended (matched in practice: 20-30 characters)

### Valid Examples
```
file-BTGHeayl9isKTp9kvyBzirg0         (uppercase and lowercase)
file-abc123xyz                         (lowercase with digits)
file-ABC123XYZ                         (uppercase with digits)
file-CSDzgtOhPLr3NzxdVkRcDgEC         (mixed case)
file-a                                 (minimal: just 'a')
```

### Invalid Examples (Won't Match)
```
file_BTGHeayl9isKTp9kvyBzirg0          (underscore instead of hyphen)
file BTGHeayl9isKTp9kvyBzirg0          (space instead of hyphen)
fileBTGHeayl9isKTp9kvyBzirg0           (no separator)
file-                                   (no characters after hyphen)
File-abc123                             (capital F breaks pattern)
```

---

## Index Building: File-ID Extraction

### Code Flow (MediaIndexer)

**File:** `/Users/tem/openai-export-parser/openai_export_parser/media_indexer.py`
**Function:** `_extract_file_id_from_name()` (Lines 176-200)

```python
def _extract_file_id_from_name(self, filename: str) -> str:
    """
    Extract file-ID from filename.
    
    Looks for patterns:
    - file-{ID}_{filename} (underscore separator) ← PRIMARY
    - file-{ID}-{filename} (hyphen separator)    ← SECONDARY
    
    Args:
        filename: Just the filename (not full path)
    
    Returns:
        file-ID (e.g., "file-CSDzgtOhPLr3NzxdVkRcDgEC") if found, None otherwise
    """
    # Try underscore separator first (most common)
    match = re.match(r'(file-[A-Za-z0-9]+)_', filename)
    if match:
        return match.group(1)  # Returns: "file-abc123"
    
    # Try hyphen separator (less common, but exists)
    match = re.match(r'(file-[A-Za-z0-9]+)-', filename)
    if match:
        return match.group(1)  # Returns: "file-abc123"
    
    return None
```

### Examples of Index Building

#### Example 1: Underscore Separator (Most Common)
```
Filename: file-BTGHeayl9isKTp9kvyBzirg0_document.pdf
           ↓ regex: (file-[A-Za-z0-9]+)_
Result:   file-BTGHeayl9isKTp9kvyBzirg0

Index Entry:
  file_id_index["file-BTGHeayl9isKTp9kvyBzirg0"] = 
    "/path/to/file-BTGHeayl9isKTp9kvyBzirg0_document.pdf"
```

#### Example 2: Hyphen Separator (Fallback)
```
Filename: file-CSDzgtOhPLr3NzxdVkRcDgEC-report.pdf
           ↓ regex: (file-[A-Za-z0-9]+)-
Result:   file-CSDzgtOhPLr3NzxdVkRcDgEC

Index Entry:
  file_id_index["file-CSDzgtOhPLr3NzxdVkRcDgEC"] = 
    "/path/to/file-CSDzgtOhPLr3NzxdVkRcDgEC-report.pdf"
```

#### Example 3: Failure Case (Not in Index)
```
Filename: document_file-BTGHeayl9isKTp9kvyBzirg0.pdf
           ↓ regex doesn't match at start
Result:   None (not indexed)

Reason:   Filename doesn't START with file-{ID}_ or file-{ID}-
          Index extraction uses re.match() which matches from start of string
```

---

## Matching: File-ID Lookup in Conversations

### Code Flow (MediaMatcher)

**File:** `/Users/tem/openai-export-parser/openai_export_parser/media_matcher.py`
**Function:** `_match_by_file_id()` (Lines 129-167)

```python
def _match_by_file_id(self, conversations, file_id_index):
    """
    Match media files using file-IDs from attachments metadata.
    
    This strategy extracts file-IDs from metadata.attachments[].id fields
    and looks them up in the file_id_index.
    """
    for conv in conversations:
        conv_media_files = set(conv.get("_media_files", []))
        file_ids_found = []
        
        # Scan all messages for attachments
        mapping = conv.get("mapping", {})
        for node_id, node_data in mapping.items():
            message = node_data.get("message")
            if not message:
                continue
            
            metadata = message.get("metadata", {})
            attachments = metadata.get("attachments", [])
            
            for attachment in attachments:
                file_id = attachment.get("id")  # ← Extract file-ID
                if not file_id:
                    continue
                
                # Look up file path in index
                file_path = file_id_index.get(file_id)
                if file_path:
                    conv_media_files.add(file_path)
                    file_ids_found.append(file_id)
        
        # Update conversation with found files
        if file_ids_found:
            conv["_media_files"] = list(conv_media_files)
            self.stats['file_id_matches'] += 1
            self.log(f"  Matched {len(file_ids_found)} file-IDs to conversation...")
    
    return conversations
```

### Matching Examples

#### Example 1: Successful Match (Happy Path)

**Conversation Data:**
```json
{
  "conversation_id": "conv-uuid-1234",
  "mapping": {
    "node-abc": {
      "message": {
        "role": "user",
        "content": "Here's my document",
        "metadata": {
          "attachments": [
            {
              "id": "file-BTGHeayl9isKTp9kvyBzirg0",  ← FILE-ID EXTRACTED
              "name": "document.pdf",
              "size": 1024
            }
          ]
        }
      }
    }
  }
}
```

**File on Disk:**
```
/tmp/extract/file-BTGHeayl9isKTp9kvyBzirg0_document.pdf
```

**Index (Built Previously):**
```python
file_id_index = {
    "file-BTGHeayl9isKTp9kvyBzirg0": 
        "/tmp/extract/file-BTGHeayl9isKTp9kvyBzirg0_document.pdf"
}
```

**Matching Process:**
```python
# Step 1: Extract file-ID from attachment
file_id = attachment.get("id")
# Result: "file-BTGHeayl9isKTp9kvyBzirg0"

# Step 2: Look up in index
file_path = file_id_index.get("file-BTGHeayl9isKTp9kvyBzirg0")
# Result: "/tmp/extract/file-BTGHeayl9isKTp9kvyBzirg0_document.pdf"

# Step 3: Add to conversation
if file_path:
    conv_media_files.add(file_path)
    file_ids_found.append("file-BTGHeayl9isKTp9kvyBzirg0")

# Result
conv["_media_files"] = ["/tmp/extract/file-BTGHeayl9isKTp9kvyBzirg0_document.pdf"]
stats['file_id_matches'] += 1  # ✓ SUCCESS
```

#### Example 2: Missing Attachment Metadata

**Conversation Data:**
```json
{
  "conversation_id": "conv-uuid-5678",
  "mapping": {
    "node-def": {
      "message": {
        "role": "user",
        "content": "Here's my image",
        "metadata": {}  // ← Empty metadata!
      }
    }
  }
}
```

**File on Disk:**
```
/tmp/extract/file-BTGHeayl9isKTp9kvyBzirg0_photo.png
```

**Matching Process:**
```python
# Step 1: Get attachments from metadata
metadata = message.get("metadata", {})
attachments = metadata.get("attachments", [])
# Result: [] (empty list)

# Step 2: Loop over attachments
for attachment in attachments:  # ← Loop doesn't execute!
    file_id = attachment.get("id")
    # Never reaches here

# Result
file_ids_found = []
stats['file_id_matches'] += 0  # ✗ NO MATCH
# File remains unmatched!
```

**Why This Happens:**
- Image was uploaded as an attachment
- But `metadata.attachments` wasn't populated
- Common in older OpenAI exports or specific UI paths

#### Example 3: File-ID Not in Index

**Conversation Data:**
```json
{
  "mapping": {
    "node-ghi": {
      "message": {
        "metadata": {
          "attachments": [
            {
              "id": "file-unknown123456789",  ← This ID exists in conversation
              "name": "deleted_file.pdf"
            }
          ]
        }
      }
    }
  }
}
```

**Files on Disk:**
```
/tmp/extract/file-BTGHeayl9isKTp9kvyBzirg0_document.pdf  ← Different ID
/tmp/extract/file-other999_photo.png                     ← Different ID
```

**Index (Built Previously):**
```python
file_id_index = {
    "file-BTGHeayl9isKTp9kvyBzirg0": "/tmp/extract/file-BTGHeayl9isKTp9kvyBzirg0_document.pdf",
    "file-other999": "/tmp/extract/file-other999_photo.png"
}
```

**Matching Process:**
```python
# Step 1: Extract file-ID
file_id = attachment.get("id")
# Result: "file-unknown123456789"

# Step 2: Look up in index
file_path = file_id_index.get("file-unknown123456789")
# Result: None (not in index!)

# Step 3: Check if found
if file_path:  # ← Condition is False
    conv_media_files.add(file_path)

# Result
file_ids_found = []
stats['file_id_matches'] += 0  # ✗ NO MATCH
# File-ID exists in conversation but file doesn't exist in export
```

**Why This Happens:**
- File was deleted from user account before export
- File metadata remains in conversation JSON
- File binary doesn't exist in export

---

## Text Content Fallback Matching

### Code Flow (MediaMatcher)

**File:** `/Users/tem/openai-export-parser/openai_export_parser/media_matcher.py`
**Function:** `_match_by_text_content()` (Lines 328-363)

```python
def _match_by_text_content(self, conversations, media_files):
    """
    Match media files by searching for references in message text.
    
    This is a fallback strategy used when conversation_id matching is not available.
    """
    for conv in conversations:
        for msg in conv.get("messages", []):
            msg_str = str(msg)  # Convert entire message to string
            
            for media in media_files:
                fname = os.path.basename(media)
                matched = False
                
                # Direct substring match
                if fname in msg_str:
                    matched = True
                
                # Match file-id pattern
                for m in self.FILE_ID_PATTERN.findall(msg_str):
                    if m in fname:  # Does "file-xyz" appear in filename?
                        matched = True
                        break
                
                # Match UUID pattern
                if not matched:
                    for u in self.UUID_PATTERN.findall(msg_str):
                        if u in fname:
                            matched = True
                            break
                
                if matched:
                    msg.setdefault("media", []).append(fname)
                    self.stats['text_matches'] += 1
    
    return conversations
```

### Text Matching Examples

#### Example 1: File-ID in Text (Success)

**Message:**
```json
{
  "role": "user",
  "content": "I uploaded the file file-abc123xyz earlier"
}
```

**File on Disk:**
```
file-abc123xyz_document.pdf
```

**Matching Process:**
```python
# Convert message to string
msg_str = str(msg)
# Result: "{'role': 'user', 'content': 'I uploaded the file file-abc123xyz earlier'}"

# Get filename
fname = "file-abc123xyz_document.pdf"

# Try 1: Direct substring match
if "file-abc123xyz_document.pdf" in msg_str:
    matched = True  # ✗ NO - full filename not in text
    
# Try 2: File-ID pattern matching
for m in FILE_ID_PATTERN.findall(msg_str):
    # Result: ["file-abc123xyz"]
    if "file-abc123xyz" in "file-abc123xyz_document.pdf":
        matched = True  # ✓ YES - file-ID found in filename!
        break

# Result
msg["media"] = ["file-abc123xyz_document.pdf"]
stats['text_matches'] += 1  # ✓ SUCCESS
```

#### Example 2: No Reference in Text (Failure)

**Message:**
```json
{
  "role": "user",
  "content": "I uploaded an important document today"
}
```

**File on Disk:**
```
file-abc123xyz_document.pdf
```

**Matching Process:**
```python
msg_str = str(msg)
fname = "file-abc123xyz_document.pdf"

# Try 1: Direct substring match
if "file-abc123xyz_document.pdf" in msg_str:
    matched = True  # ✗ NO

# Try 2: File-ID pattern matching
for m in FILE_ID_PATTERN.findall(msg_str):
    # Result: [] (empty - no file-ID in text!)
    # Loop doesn't execute

# Try 3: UUID pattern matching
for u in UUID_PATTERN.findall(msg_str):
    # Result: [] (empty - no UUID in text!)
    # Loop doesn't execute

# Result
matched = False
# File NOT matched, even though it exists!
```

---

## Matching Statistics

### Stats Tracking

**Location:** `media_matcher.py` Lines 21-30 and throughout matching methods

```python
self.stats = {
    'conversation_id_matches': 0,  # Strategy 1
    'file_id_matches': 0,          # Strategy 2
    'file_hash_matches': 0,        # Strategy 3
    'size_matches': 0,             # Strategy 4
    'text_matches': 0,             # Strategy 5
    'no_matches': 0
}
```

### Example Output (from parser.py Lines 110-116)

```
✓ Matched 45 conversations by conversation_id
✓ Matched 12 conversations by file-ID
✓ Matched 8 conversations by file-hash (sediment://)
✓ Matched 3 conversations by file-size (DALL-E generations)
✓ Matched 2 files by text content
```

**Interpretation:**
- 45 conversations had media organized in `/conversations/{uuid}/` folders
- 12 conversations had user uploads with `metadata.attachments[].id` fields
- 8 conversations had newer DALL-E images with sediment:// references
- 3 conversations had DALL-E generation files matched by size + gen_id
- 2 media files were only found via text content matching

---

## Common Failure Scenarios

### Scenario 1: File-ID Mismatch in Filename

**Conversation has:**
```
metadata.attachments[0].id = "file-abc123"
```

**File on disk is:**
```
"document_file-abc123.pdf"  ← ID is NOT at start
```

**Why it fails:**
- Index extraction uses `re.match(r'(file-[A-Za-z0-9]+)_', filename)`
- `re.match()` only matches from the START of string
- "document_file-abc123.pdf" doesn't start with "file-abc123_"
- File never gets indexed

**Fix:** Rename file to `file-abc123_document.pdf`

### Scenario 2: Case Mismatch

**Conversation has:**
```
metadata.attachments[0].id = "file-ABC123"
```

**Index lookup:**
```python
file_id_index.get("file-ABC123")  # Returns None
```

**Why it fails:**
- Indices are case-sensitive dictionaries
- If index has "file-abc123" and conversation has "file-ABC123"
- The lookups don't match

**Note:** The regex pattern `[A-Za-z0-9]` accepts both cases, so indexing should work
But if there's case mismatch between attachment.id and filename, it will fail

### Scenario 3: Special Characters in File-ID

**File on disk:**
```
"file-abc_123-xyz_document.pdf"  ← Underscore in ID part
```

**Index extraction:**
```python
match = re.match(r'(file-[A-Za-z0-9]+)_', filename)
# Extracts: "file-abc"
# Stops at underscore (not in [A-Za-z0-9])
```

**Result:**
- Index stores: `"file-abc" -> file-abc_123-xyz_document.pdf`
- Conversation has: `metadata.attachments[0].id = "file-abc_123-xyz"`
- Lookup fails: `file_id_index.get("file-abc_123-xyz")` = None

**Why:** Pattern doesn't allow underscores, hyphens, or other special characters in the file-ID itself

---

## Data Structure Reference

### Conversation Structure for Matching

```json
{
  "conversation_id": "uuid-1234...",
  "id": "uuid-1234...",  // Fallback if conversation_id missing
  "mapping": {
    "node-id-1": {
      "message": {
        "role": "user",
        "content": {
          "content_type": "text",
          "parts": [
            {
              "type": "text",
              "text": "Some text"
            },
            {
              "type": "image",
              "image_url": "file-xyz123.png"  // ← Not currently matched!
            }
          ]
        },
        "metadata": {
          "attachments": [
            {
              "id": "file-BTGHeayl9isKTp9kvyBzirg0",  // ← Strategy 2 matches
              "name": "document.pdf",
              "size": 1024
            }
          ]
        }
      }
    }
  }
}
```

### File-ID Index Structure

```python
file_id_index = {
    "file-BTGHeayl9isKTp9kvyBzirg0": 
        "/path/to/tmp/file-BTGHeayl9isKTp9kvyBzirg0_document.pdf",
    "file-CSDzgtOhPLr3NzxdVkRcDgEC":
        "/path/to/tmp/file-CSDzgtOhPLr3NzxdVkRcDgEC_photo.png",
    "file-abc123":
        "/path/to/tmp/file-abc123_report.pdf"
}
```

---

## Summary Table: File-ID Matching Conditions

| Condition | Required? | Example | Result |
|-----------|-----------|---------|--------|
| `metadata.attachments` array exists | YES | `metadata: { attachments: [...] }` | Matched |
| `metadata.attachments` is empty | NO | `metadata: { attachments: [] }` | Not matched |
| `attachment.id` is present | YES | `"id": "file-abc123"` | Looked up |
| `attachment.id` is null | NO | `"id": null` | Skipped |
| File-ID in index | YES | `file_id_index["file-abc123"]` | Found and matched |
| File-ID NOT in index | NO | File deleted from export | Not matched |
| Filename has `file-{ID}_` prefix | YES | `file-abc123_document.pdf` | Indexed |
| Filename has `file-{ID}-` prefix | YES | `file-abc123-document.pdf` | Indexed |
| Filename has ID elsewhere | NO | `document_file-abc123.pdf` | Not indexed |
| File-ID case matches | YES | Both `file-ABC123` (exact match required) | Matched |

