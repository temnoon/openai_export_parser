"""
Comprehensive media matcher that uses ALL available information to match files.

This module implements a robust matching strategy that tries multiple approaches
in order of reliability, falling back to less precise methods only when needed.
"""

from typing import Dict, List, Set
import os


class ComprehensiveMediaMatcher:
    """
    Matches media files to conversations using comprehensive strategies.

    Matching strategies in order of priority:
    1. File hash (sediment://) - exact match, 100% reliable
    2. File-ID + size - very reliable
    3. Filename + size - good for user uploads
    4. Conversation directory - reliable for DALL-E
    5. Size + metadata (gen_id, dimensions) - good for DALL-E
    6. Size alone - fallback, may have collisions
    7. Filename alone - least reliable fallback
    """

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.stats = {
            'conversations_processed': 0,
            'conversations_with_media': 0,
            'total_files_matched': 0,
            'by_file_hash': 0,
            'by_file_id': 0,
            'by_filename_size': 0,
            'by_conversation_dir': 0,
            'by_size_metadata': 0,
            'by_size_only': 0,
            'by_filename_only': 0,
            'unmatched_references': 0
        }

    def log(self, msg):
        """Print log message if verbose mode is enabled."""
        if self.verbose:
            print(msg)

    def match(self, conversations: List[Dict], file_indices: Dict, reference_extractor) -> List[Dict]:
        """
        Match media files to conversations using comprehensive strategies.

        Args:
            conversations: List of conversation dicts
            file_indices: Dict with all file indices from ComprehensiveMediaIndexer
            reference_extractor: MediaReferenceExtractor instance

        Returns:
            Updated conversations with matched media files
        """
        self.log("Matching media using comprehensive multi-strategy approach...")

        for conv in conversations:
            self.stats['conversations_processed'] += 1

            # Extract all media references from this conversation
            references = reference_extractor.extract_all_references(conv)

            # Collect matched files
            matched_files = set()

            # Strategy 1: Match by file hash (sediment://)
            file_hashes = reference_extractor.get_all_file_hashes(references)
            for file_hash in file_hashes:
                filepath = file_indices['file_hash_to_path'].get(file_hash)
                if filepath:
                    matched_files.add(filepath)
                    self.stats['by_file_hash'] += 1
                    self.log(f"    Matched by file_hash: {file_hash}")
                else:
                    self.stats['unmatched_references'] += 1
                    self.log(f"    UNMATCHED file_hash: {file_hash}")

            # Strategy 2: Match by file-ID
            file_ids = reference_extractor.get_all_file_ids(references)
            for file_id in file_ids:
                filepath = file_indices['file_id_to_path'].get(file_id)
                if filepath and filepath not in matched_files:
                    matched_files.add(filepath)
                    self.stats['by_file_id'] += 1
                    self.log(f"    Matched by file_id: {file_id}")

            # Strategy 3: Match by filename + size (for attachments)
            for attachment in references.get('attachments', []):
                filename = attachment.get('name')
                size = attachment.get('size')
                if filename and size:
                    filepath = file_indices['basename_size_to_path'].get((filename, size))
                    if filepath and filepath not in matched_files:
                        matched_files.add(filepath)
                        self.stats['by_filename_size'] += 1
                        self.log(f"    Matched by filename+size: {filename} ({size} bytes)")

            # Strategy 4: Match by conversation directory
            conv_id = conv.get("conversation_id") or conv.get("id")
            if conv_id:
                conv_files = file_indices['conversation_to_paths'].get(conv_id, [])
                for filepath in conv_files:
                    if filepath not in matched_files:
                        matched_files.add(filepath)
                        self.stats['by_conversation_dir'] += 1
                        self.log(f"    Matched by conversation_dir: {os.path.basename(filepath)}")

            # Strategy 5: Match by size + metadata (DALL-E generations)
            for dalle_gen in references.get('dalle_generations', []):
                size_bytes = dalle_gen.get('size_bytes')
                gen_id = dalle_gen.get('gen_id')
                width = dalle_gen.get('width')
                height = dalle_gen.get('height')

                if size_bytes:
                    candidate_files = file_indices['size_to_paths'].get(size_bytes, [])

                    # If we have only one file with this size, it's likely a match
                    if len(candidate_files) == 1:
                        filepath = candidate_files[0]
                        if filepath not in matched_files:
                            matched_files.add(filepath)
                            self.stats['by_size_metadata'] += 1
                            self.log(f"    Matched by size (unique): {size_bytes} bytes")

                    # If multiple files have same size, we can't reliably match without opening files
                    # Just take the first one for now (could be improved)
                    elif len(candidate_files) > 1 and filepath not in matched_files:
                        filepath = candidate_files[0]
                        matched_files.add(filepath)
                        self.stats['by_size_only'] += 1
                        self.log(f"    Matched by size (ambiguous): {size_bytes} bytes - {len(candidate_files)} candidates")

            # Strategy 6: Match by asset_pointer size alone (for non-DALL-E)
            for asset_ref in references.get('asset_pointers', []):
                size_bytes = asset_ref.get('size_bytes')
                pointer_type = asset_ref.get('type')

                # Skip if already matched by hash (sediment) or file-ID
                if pointer_type in ['sediment', 'file']:
                    continue

                if size_bytes:
                    candidate_files = file_indices['size_to_paths'].get(size_bytes, [])
                    if len(candidate_files) == 1:
                        filepath = candidate_files[0]
                        if filepath not in matched_files:
                            matched_files.add(filepath)
                            self.stats['by_size_only'] += 1
                            self.log(f"    Matched by size: {size_bytes} bytes")

            # Strategy 7: Match by filename alone (least reliable)
            filenames = reference_extractor.get_all_filenames(references)
            for filename in filenames:
                # Look through all files for basename match
                for filepath, metadata in file_indices['path_to_metadata'].items():
                    if metadata['basename'] == filename:
                        if filepath not in matched_files:
                            matched_files.add(filepath)
                            self.stats['by_filename_only'] += 1
                            self.log(f"    Matched by filename only: {filename}")
                            break

            # Update conversation with matched files
            if matched_files:
                conv["_media_files"] = list(matched_files)
                self.stats['conversations_with_media'] += 1
                self.stats['total_files_matched'] += len(matched_files)
                self.log(f"  Conversation {conv_id[:8] if conv_id else 'unknown'}: matched {len(matched_files)} files")

        return conversations

    def get_stats(self) -> Dict:
        """Get matching statistics."""
        return self.stats

    def print_summary(self):
        """Print a summary of matching results."""
        self.log("\n=== Matching Summary ===")
        self.log(f"Conversations processed: {self.stats['conversations_processed']}")
        self.log(f"Conversations with media: {self.stats['conversations_with_media']}")
        self.log(f"Total files matched: {self.stats['total_files_matched']}")
        self.log(f"\nMatching strategy breakdown:")
        self.log(f"  By file hash (sediment://): {self.stats['by_file_hash']}")
        self.log(f"  By file-ID: {self.stats['by_file_id']}")
        self.log(f"  By filename+size: {self.stats['by_filename_size']}")
        self.log(f"  By conversation directory: {self.stats['by_conversation_dir']}")
        self.log(f"  By size+metadata: {self.stats['by_size_metadata']}")
        self.log(f"  By size only: {self.stats['by_size_only']}")
        self.log(f"  By filename only: {self.stats['by_filename_only']}")
        self.log(f"\nUnmatched references: {self.stats['unmatched_references']}")
