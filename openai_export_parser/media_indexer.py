"""
Media indexer module for building conversation_id to media file mappings.

This module scans the temporary extraction directory and creates a comprehensive
index mapping conversation IDs to their associated media files.
"""

import os
import re
from typing import Dict, List, Set


class MediaIndexer:
    """Builds an index mapping conversation IDs to media files."""

    MEDIA_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.svg', '.mp3', '.wav', '.mp4', '.mov'}

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.conversation_media = {}  # conversation_id -> list of file paths
        self.file_id_to_path = {}  # file-ID -> file path
        self.file_hash_to_path = {}  # file_{hash} -> file path (for sediment://)
        self.size_to_paths = {}  # file_size -> list of file paths (for DALL-E generations)
        self.size_gen_id_to_path = {}  # (file_size, gen_id) -> file path (for collision resolution)
        self.filename_size_to_path = {}  # (filename, size) -> file path (for files without file-ID prefix)

    def log(self, msg):
        """Print log message if verbose mode is enabled."""
        if self.verbose:
            print(msg)

    def build_index(self, tmp_dir: str) -> Dict[str, List[str]]:
        """
        Build a comprehensive index of media files.

        Indexes media in two ways:
        1. By conversation_id (for DALL-E images)
        2. By file-ID (for user-uploaded files)

        Args:
            tmp_dir: Path to temporary extraction directory

        Returns:
            Dictionary mapping conversation_id to list of media file paths
        """
        self.log("Building media index from directory structure...")

        conversation_media = {}
        file_id_to_path = {}
        file_hash_to_path = {}
        filename_size_to_path = {}  # NEW: Index all media files by (filename, size)
        total_files = 0
        dalle_files = 0
        file_id_files = 0
        file_hash_files = 0

        # Walk through all files in temp directory
        for root, dirs, files in os.walk(tmp_dir):
            for filename in files:
                filepath = os.path.join(root, filename)

                # Check if it's a media file (by extension or by checking file-ID pattern)
                _, ext = os.path.splitext(filename.lower())
                has_media_ext = ext in self.MEDIA_EXTENSIONS

                # NEW: Index ALL media files by (filename, size) for fallback matching
                if has_media_ext:
                    file_size = os.path.getsize(filepath)
                    filename_size_to_path[(filename, file_size)] = filepath

                # Pattern 1: DALL-E images organized by conversation_id
                # Pattern: /conversations/{conversation_id}/filename
                if has_media_ext:
                    conv_id = self._extract_conversation_id_from_path(filepath)
                    if conv_id:
                        if conv_id not in conversation_media:
                            conversation_media[conv_id] = []
                        conversation_media[conv_id].append(filepath)
                        total_files += 1
                        dalle_files += 1
                        continue

                # Pattern 2: User uploaded files with file-ID prefix
                # Pattern: file-{ID}_{original_name}.ext
                file_id = self._extract_file_id_from_name(filename)
                if file_id:
                    file_id_to_path[file_id] = filepath
                    total_files += 1
                    file_id_files += 1
                    continue

                # Pattern 3: Newer files with file_{hash}-{uuid}.ext pattern (sediment://)
                # Pattern: file_{16-hex}-{uuid}.{ext}
                file_hash = self._extract_file_hash_from_name(filename)
                if file_hash:
                    # Extract conversation_id from parent path if available
                    conv_id = self._extract_conversation_id_from_path(filepath)
                    if conv_id:
                        if conv_id not in conversation_media:
                            conversation_media[conv_id] = []
                        conversation_media[conv_id].append(filepath)

                    # Also index by hash for sediment:// matching
                    file_hash_to_path[file_hash] = filepath
                    total_files += 1
                    file_hash_files += 1
                    continue

                # Pattern 4: Files without extension (might be images)
                # We'll check these if they match UUID patterns
                if not ext and self._is_uuid_filename(filename):
                    # Could be image without extension - add to file_id index
                    # Use filename as pseudo file-ID for potential matching
                    file_id_to_path[filename] = filepath
                    total_files += 1

        # Pattern 5: DALL-E generations in dalle-generations/ folders
        # These are UUID-named files that need to be matched by file size
        size_to_paths = {}
        dalle_generation_files = 0
        for root, dirs, files in os.walk(tmp_dir):
            if 'dalle-generations' in root:
                for filename in files:
                    filepath = os.path.join(root, filename)
                    _, ext = os.path.splitext(filename.lower())
                    if ext in self.MEDIA_EXTENSIONS:
                        file_size = os.path.getsize(filepath)
                        if file_size not in size_to_paths:
                            size_to_paths[file_size] = []
                        size_to_paths[file_size].append(filepath)
                        dalle_generation_files += 1

        self.conversation_media = conversation_media
        self.file_id_to_path = file_id_to_path
        self.file_hash_to_path = file_hash_to_path
        self.size_to_paths = size_to_paths
        self.filename_size_to_path = filename_size_to_path  # NEW

        self.log(f"✓ Indexed {total_files} total media files")
        self.log(f"  - {dalle_files} DALL-E images (by conversation_id)")
        self.log(f"  - {file_id_files} files with file-IDs")
        self.log(f"  - {file_hash_files} files with file_{{hash}}-{{uuid}} pattern")
        self.log(f"  - {dalle_generation_files} DALL-E generation files (UUID-named)")
        self.log(f"  - {len(filename_size_to_path)} files indexed by (filename, size)")
        self.log(f"✓ Found {len(conversation_media)} conversations with DALL-E media")

        return conversation_media

    def _extract_conversation_id_from_path(self, filepath: str) -> str:
        """
        Extract conversation_id from file path.

        Looks for pattern: /conversations/{uuid}/

        Args:
            filepath: Full path to media file

        Returns:
            conversation_id if found, None otherwise
        """
        # UUID pattern: 8-4-4-4-12 hex characters
        match = re.search(r'/conversations/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/', filepath)
        if match:
            return match.group(1)

        # Also try 8-4-4-4-4-8 pattern (some UUIDs have this format)
        match = re.search(r'/conversations/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{8})/', filepath)
        if match:
            return match.group(1)

        return None

    def get_media_for_conversation(self, conversation_id: str) -> List[str]:
        """
        Get all media files for a specific conversation.

        Args:
            conversation_id: The conversation UUID

        Returns:
            List of file paths for this conversation's media
        """
        return self.conversation_media.get(conversation_id, [])

    def _extract_file_id_from_name(self, filename: str) -> str:
        """
        Extract file-ID from filename.

        Looks for patterns:
        - file-{ID}_{filename} (underscore separator)
        - file-{ID}-{filename} (hyphen separator)

        Args:
            filename: Just the filename (not full path)

        Returns:
            file-ID (e.g., "file-CSDzgtOhPLr3NzxdVkRcDgEC") if found, None otherwise
        """
        # Try underscore separator first (most common)
        match = re.match(r'(file-[A-Za-z0-9]+)_', filename)
        if match:
            return match.group(1)

        # Try hyphen separator (less common, but exists)
        match = re.match(r'(file-[A-Za-z0-9]+)-', filename)
        if match:
            return match.group(1)

        return None

    def _extract_file_hash_from_name(self, filename: str) -> str:
        """
        Extract file hash from newer filename pattern.

        Looks for pattern: file_{16-hex}-{uuid}.ext
        This is used for sediment:// references.

        Args:
            filename: Just the filename (not full path)

        Returns:
            "file_{hash}" (e.g., "file_000000009e586230866e2a177650b0e8") if found, None otherwise
        """
        # Match: file_{16 hex chars}-{uuid}.ext
        match = re.match(r'(file_[a-f0-9]{32})-[a-f0-9-]{36}\.', filename)
        if match:
            return match.group(1)
        return None

    def _is_uuid_filename(self, filename: str) -> bool:
        """
        Check if filename looks like a UUID (files without extensions).

        Args:
            filename: Just the filename (not full path)

        Returns:
            True if filename matches UUID pattern
        """
        # Standard UUID: 8-4-4-4-12
        if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', filename):
            return True
        # iOS UUID: 8-4-4-4-12 (uppercase)
        if re.match(r'^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$', filename):
            return True
        return False

    def get_file_by_id(self, file_id: str) -> str:
        """
        Get file path for a specific file-ID.

        Args:
            file_id: The file-ID (e.g., "file-CSDzgtOhPLr3NzxdVkRcDgEC")

        Returns:
            Full file path if found, None otherwise
        """
        return self.file_id_to_path.get(file_id)

    def get_file_by_hash(self, file_hash: str) -> str:
        """
        Get file path for a specific file hash.

        Args:
            file_hash: The file hash (e.g., "file_000000009e586230866e2a177650b0e8")

        Returns:
            Full file path if found, None otherwise
        """
        return self.file_hash_to_path.get(file_hash)

    def get_stats(self) -> Dict:
        """
        Get statistics about indexed media.

        Returns:
            Dictionary with statistics
        """
        total_dalle_files = sum(len(files) for files in self.conversation_media.values())
        total_dalle_generation_files = sum(len(files) for files in self.size_to_paths.values())

        return {
            'total_conversations_with_media': len(self.conversation_media),
            'total_dalle_files': total_dalle_files,
            'total_file_id_files': len(self.file_id_to_path),
            'total_file_hash_files': len(self.file_hash_to_path),
            'total_dalle_generation_files': total_dalle_generation_files,
            'total_media_files': total_dalle_files + len(self.file_id_to_path) + len(self.file_hash_to_path) + total_dalle_generation_files,
            'avg_files_per_conversation': total_dalle_files / len(self.conversation_media) if self.conversation_media else 0
        }
