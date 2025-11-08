"""
Comprehensive media indexer that catalogs ALL files in the archive.

This module builds multiple indices to support robust media matching:
1. All files by (basename, size) - universal fallback
2. All files by file-ID prefix
3. All files by file hash (sediment://)
4. All files by conversation_id (path-based)
5. All files by size alone (for DALL-E matching)
6. All files by gen_id (extracted from metadata if available)
"""

import os
import re
from typing import Dict, List, Tuple, Set
from pathlib import Path


class ComprehensiveMediaIndexer:
    """
    Builds comprehensive indices of ALL media files in the archive.

    This indexer makes no assumptions about filename patterns - it catalogs
    everything and builds multiple indices for different matching strategies.
    """

    MEDIA_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff',
        '.pdf', '.svg',
        '.mp3', '.wav', '.m4a', '.ogg', '.flac',
        '.mp4', '.mov', '.avi', '.mkv', '.webm'
    }

    def __init__(self, verbose=False):
        self.verbose = verbose

        # Primary indices
        self.all_files = []  # List of all media file paths
        self.basename_size_to_path = {}  # (basename, size) -> path
        self.file_id_to_path = {}  # file-ID -> path
        self.file_hash_to_path = {}  # file_hash -> path
        self.conversation_to_paths = {}  # conversation_id -> [paths]
        self.size_to_paths = {}  # size -> [paths]

        # Secondary indices for disambiguation
        self.path_to_metadata = {}  # path -> {size, basename, ext, dir, ...}

    def log(self, msg):
        """Print log message if verbose mode is enabled."""
        if self.verbose:
            print(msg)

    def build_index(self, tmp_dir: str, recovery_dir: str = None) -> Dict:
        """
        Build comprehensive index of ALL media files in the archive.

        This method walks the entire directory tree and catalogs every file
        that appears to be media, building multiple indices for matching.

        Args:
            tmp_dir: Path to temporary extraction directory
            recovery_dir: Optional path to recovery folder for files from old exports

        Returns:
            Dict with all indices
        """
        self.log("Building comprehensive media index...")
        self.log(f"Scanning directory: {tmp_dir}")

        # Build list of directories to scan
        dirs_to_scan = [tmp_dir]
        if recovery_dir and os.path.exists(recovery_dir):
            dirs_to_scan.append(recovery_dir)
            self.log(f"Including recovery directory: {recovery_dir}")

        total_files = 0
        file_id_count = 0
        file_hash_count = 0
        conversation_files = 0

        # Walk ALL files in all scan directories
        for scan_dir in dirs_to_scan:
            for root, dirs, files in os.walk(scan_dir):
                for filename in files:
                    filepath = os.path.join(root, filename)

                    # Check if it's a media file
                    _, ext = os.path.splitext(filename.lower())
                    if ext not in self.MEDIA_EXTENSIONS:
                        continue

                    # It's a media file - catalog it
                    total_files += 1
                    self.all_files.append(filepath)

                    # Get file metadata
                    try:
                        file_size = os.path.getsize(filepath)
                    except OSError:
                        continue

                    basename = os.path.basename(filepath)
                    dirname = os.path.dirname(filepath)

                    # Store metadata
                    self.path_to_metadata[filepath] = {
                        'size': file_size,
                        'basename': basename,
                        'ext': ext,
                        'dirname': dirname,
                        'filename_only': filename
                    }

                    # Index 1: By (basename, size) - UNIVERSAL FALLBACK
                    self.basename_size_to_path[(basename, file_size)] = filepath

                    # Index 2: By file-ID if present (file-{ID}_* or file-{ID}-*)
                    file_id = self._extract_file_id(filename)
                    if file_id:
                        self.file_id_to_path[file_id] = filepath
                        file_id_count += 1

                    # Index 3: By file hash if present (file_{hash}-{uuid}.ext)
                    file_hash = self._extract_file_hash(filename)
                    if file_hash:
                        self.file_hash_to_path[file_hash] = filepath
                        file_hash_count += 1

                    # Index 4: By conversation_id from path if present
                    conv_id = self._extract_conversation_id(filepath)
                    if conv_id:
                        if conv_id not in self.conversation_to_paths:
                            self.conversation_to_paths[conv_id] = []
                        self.conversation_to_paths[conv_id].append(filepath)
                        conversation_files += 1

                    # Index 5: By file size (for DALL-E matching)
                    if file_size not in self.size_to_paths:
                        self.size_to_paths[file_size] = []
                    self.size_to_paths[file_size].append(filepath)

        self.log(f"✓ Indexed {total_files} total media files")
        self.log(f"  - {file_id_count} files with file-ID prefixes")
        self.log(f"  - {file_hash_count} files with file_{{hash}}-{{uuid}} pattern")
        self.log(f"  - {conversation_files} files in conversation directories")
        self.log(f"  - {len(self.basename_size_to_path)} unique (basename, size) pairs")
        self.log(f"  - {len(self.size_to_paths)} unique file sizes")

        return {
            'all_files': self.all_files,
            'basename_size_to_path': self.basename_size_to_path,
            'file_id_to_path': self.file_id_to_path,
            'file_hash_to_path': self.file_hash_to_path,
            'conversation_to_paths': self.conversation_to_paths,
            'size_to_paths': self.size_to_paths,
            'path_to_metadata': self.path_to_metadata
        }

    def _extract_file_id(self, filename: str) -> str:
        """
        Extract file-ID from filename.

        Patterns:
        - file-{ID}_{filename}
        - file-{ID}-{filename}

        Returns:
            file-ID or None
        """
        # Try underscore separator
        match = re.match(r'(file-[A-Za-z0-9]+)_', filename)
        if match:
            return match.group(1)

        # Try hyphen separator
        match = re.match(r'(file-[A-Za-z0-9]+)-', filename)
        if match:
            return match.group(1)

        return None

    def _extract_file_hash(self, filename: str) -> str:
        """
        Extract file hash from sediment:// pattern filename.

        Pattern: file_{32-hex}-{uuid}.ext

        Returns:
            "file_{hash}" or None
        """
        match = re.match(r'(file_[a-f0-9]{32})-[a-f0-9-]{36}\.', filename)
        if match:
            return match.group(1)
        return None

    def _extract_conversation_id(self, filepath: str) -> str:
        """
        Extract conversation_id from file path.

        Looks for /conversations/{uuid}/ pattern

        Returns:
            conversation_id or None
        """
        # Standard UUID: 8-4-4-4-12
        match = re.search(
            r'/conversations/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/',
            filepath
        )
        if match:
            return match.group(1)

        # Alternative UUID: 8-4-4-4-8
        match = re.search(
            r'/conversations/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{8})/',
            filepath
        )
        if match:
            return match.group(1)

        return None

    def get_stats(self) -> Dict:
        """Get indexing statistics."""
        return {
            'total_files': len(self.all_files),
            'file_id_files': len(self.file_id_to_path),
            'file_hash_files': len(self.file_hash_to_path),
            'conversation_dirs': len(self.conversation_to_paths),
            'unique_sizes': len(self.size_to_paths),
            'unique_basename_size_pairs': len(self.basename_size_to_path)
        }
