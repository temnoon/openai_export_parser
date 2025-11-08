"""
Comprehensive media reference extractor that finds ALL media references in JSON.

This module scans conversation JSON files and extracts ALL possible media
references with their metadata, including:
- asset_pointer URLs (sediment://, file-service://)
- attachment metadata (file-IDs, names, sizes)
- DALL-E generation metadata (gen_id, size_bytes)
- Text-embedded references (filenames, UUIDs)
"""

import re
from typing import Dict, List, Tuple, Set


class MediaReferenceExtractor:
    """
    Extracts ALL media references from conversation JSON.

    This extractor makes no assumptions about reference format - it looks
    everywhere for any hint of media files.
    """

    def __init__(self, verbose=False):
        self.verbose = verbose

    def log(self, msg):
        """Print log message if verbose mode is enabled."""
        if self.verbose:
            print(msg)

    def extract_all_references(self, conversation: Dict) -> Dict:
        """
        Extract ALL media references from a conversation JSON.

        Returns a dict with different types of references:
        {
            'asset_pointers': [
                {
                    'pointer': 'sediment://file_...',
                    'type': 'sediment',
                    'file_hash': 'file_...',
                    'size_bytes': 1234,
                    'metadata': {...}
                }
            ],
            'attachments': [
                {
                    'id': 'file-ABC123...',
                    'name': 'photo.jpg',
                    'size': 1234,
                    'mime_type': 'image/jpeg'
                }
            ],
            'dalle_generations': [
                {
                    'gen_id': 'uuid...',
                    'size_bytes': 1234,
                    'width': 1024,
                    'height': 1024,
                    'asset_pointer': 'file-service://...'
                }
            ],
            'text_references': [
                {
                    'filename': 'photo.jpg',
                    'context': '...text around reference...'
                }
            ]
        }
        """
        references = {
            'asset_pointers': [],
            'attachments': [],
            'dalle_generations': [],
            'text_references': []
        }

        mapping = conversation.get("mapping", {})

        for node_id, node_data in mapping.items():
            message = node_data.get("message")
            if not message:
                continue

            # Extract from message content
            content = message.get("content", {})
            parts = content.get("parts", [])

            for part in parts:
                # Handle dict parts (asset_pointer, metadata)
                if isinstance(part, dict):
                    self._extract_from_part(part, references)

                # Handle string parts (text content)
                elif isinstance(part, str):
                    self._extract_from_text(part, references)

            # Extract from message metadata (attachments)
            metadata = message.get("metadata", {})
            self._extract_from_metadata(metadata, references)

        return references

    def _extract_from_part(self, part: Dict, references: Dict):
        """Extract media references from a content part dict."""

        # Extract asset_pointer
        asset_pointer = part.get("asset_pointer", "")
        if asset_pointer:
            ref = {
                'pointer': asset_pointer,
                'size_bytes': part.get("size_bytes"),
                'width': part.get("width"),
                'height': part.get("height"),
                'metadata': part.get("metadata", {})
            }

            # Classify by pointer type
            if asset_pointer.startswith("sediment://"):
                ref['type'] = 'sediment'
                ref['file_hash'] = asset_pointer.replace("sediment://", "")
                references['asset_pointers'].append(ref)

            elif asset_pointer.startswith("file-service://"):
                ref['type'] = 'file-service'

                # Check for DALL-E metadata
                metadata = part.get("metadata") or {}
                dalle_metadata = metadata.get("dalle", {})
                if dalle_metadata:
                    gen_ref = {
                        'gen_id': dalle_metadata.get("gen_id"),
                        'size_bytes': part.get("size_bytes"),
                        'width': part.get("width"),
                        'height': part.get("height"),
                        'asset_pointer': asset_pointer,
                        'dalle_metadata': dalle_metadata
                    }
                    references['dalle_generations'].append(gen_ref)

                references['asset_pointers'].append(ref)

            elif asset_pointer.startswith("file://"):
                ref['type'] = 'file'
                # Extract filename from file:// URL if possible
                filename = asset_pointer.replace("file://", "").split("/")[-1]
                ref['filename'] = filename
                references['asset_pointers'].append(ref)

            else:
                # Unknown pointer type
                ref['type'] = 'unknown'
                references['asset_pointers'].append(ref)

    def _extract_from_text(self, text: str, references: Dict):
        """Extract media references from text content."""

        # Look for common filename patterns
        filename_patterns = [
            r'[\w\-]+\.(jpg|jpeg|png|gif|webp|pdf|mp3|wav|mp4|mov)',
            r'file-[A-Za-z0-9]+',  # file-IDs
            r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'  # UUIDs
        ]

        for pattern in filename_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Get context around the match (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]

                ref = {
                    'match': match.group(0),
                    'context': context
                }
                references['text_references'].append(ref)

    def _extract_from_metadata(self, metadata: Dict, references: Dict):
        """Extract media references from message metadata."""

        # Extract attachments
        attachments = metadata.get("attachments", [])
        for attachment in attachments:
            ref = {
                'id': attachment.get("id"),
                'name': attachment.get("name"),
                'size': attachment.get("size"),
                'mime_type': attachment.get("mimeType"),
                'width': attachment.get("width"),
                'height': attachment.get("height")
            }
            references['attachments'].append(ref)

    def count_references(self, references: Dict) -> Dict:
        """Count references by type."""
        return {
            'asset_pointers': len(references.get('asset_pointers', [])),
            'attachments': len(references.get('attachments', [])),
            'dalle_generations': len(references.get('dalle_generations', [])),
            'text_references': len(references.get('text_references', []))
        }

    def get_all_sizes(self, references: Dict) -> Set[int]:
        """Get all unique file sizes mentioned in references."""
        sizes = set()

        for ref in references.get('asset_pointers', []):
            if ref.get('size_bytes'):
                sizes.add(ref['size_bytes'])

        for ref in references.get('attachments', []):
            if ref.get('size'):
                sizes.add(ref['size'])

        for ref in references.get('dalle_generations', []):
            if ref.get('size_bytes'):
                sizes.add(ref['size_bytes'])

        return sizes

    def get_all_file_ids(self, references: Dict) -> Set[str]:
        """Get all file-IDs mentioned in references."""
        file_ids = set()

        # Extract from asset_pointers (file-service://file-XXXXX)
        for ref in references.get('asset_pointers', []):
            pointer = ref.get('pointer', '')
            if pointer.startswith('file-service://'):
                # Extract file-ID from URL: file-service://file-XXXXX
                file_id = pointer.replace('file-service://', '')
                if file_id.startswith('file-'):
                    file_ids.add(file_id)

        # Extract from attachments
        for ref in references.get('attachments', []):
            if ref.get('id'):
                file_ids.add(ref['id'])

        # Extract from text references
        for ref in references.get('text_references', []):
            match = ref.get('match', '')
            if match.startswith('file-'):
                file_ids.add(match)

        return file_ids

    def get_all_file_hashes(self, references: Dict) -> Set[str]:
        """Get all file hashes (sediment://) mentioned in references."""
        hashes = set()

        for ref in references.get('asset_pointers', []):
            if ref.get('type') == 'sediment' and ref.get('file_hash'):
                hashes.add(ref['file_hash'])

        return hashes

    def get_all_filenames(self, references: Dict) -> Set[str]:
        """Get all filenames mentioned in references."""
        filenames = set()

        for ref in references.get('attachments', []):
            if ref.get('name'):
                filenames.add(ref['name'])

        for ref in references.get('text_references', []):
            match = ref.get('match', '')
            # Check if it looks like a filename (has extension)
            if '.' in match and not match.startswith('file-'):
                filenames.add(match)

        return filenames
