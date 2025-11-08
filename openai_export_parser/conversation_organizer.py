"""
Organize conversations into self-contained folders with media.

Each conversation gets its own folder with format:
{timestamp}_{title}_{conv_id}/
  ├── conversation.json
  └── media/
      ├── {hash}_{filename1}
      └── {hash}_{filename2}
"""

import os
import json
import shutil
from collections import defaultdict

from .utils import (
    ensure_dir,
    hash_file,
    sanitize_filename,
    timestamp_to_iso,
    copy_file,
)
from .html_generator import HTMLGenerator


class ConversationOrganizer:
    """
    Organizes parsed conversations into human-readable folder structure
    with self-contained media.
    """

    def __init__(self, verbose=False, output_format="both"):
        self.verbose = verbose
        self.output_format = output_format
        self.media_by_conversation = defaultdict(list)  # conv_index -> [media_paths]
        self.html_generator = HTMLGenerator()

    def log(self, *args):
        """Print log message if verbose mode is enabled."""
        if self.verbose:
            print("[ORGANIZER]", *args)

    def assign_media_to_conversations(self, conversations, media_matcher):
        """
        Build mapping of which media files belong to which conversations.

        Args:
            conversations: List of conversation dicts (with media fields added)
            media_matcher: MediaMatcher instance with matched media

        Returns:
            Dict mapping conversation index to list of media file paths
        """
        for conv_idx, conv in enumerate(conversations):
            media_files = set()

            # Extract media references from all messages
            for msg in conv.get("messages", []):
                if "media" in msg:
                    media_files.update(msg["media"])

            self.media_by_conversation[conv_idx] = list(media_files)

        return self.media_by_conversation

    def generate_folder_name(self, conversation, conv_index):
        """
        Generate human-readable folder name for conversation.

        Format: {timestamp}_{title}_{conv_id}

        Args:
            conversation: Conversation dict
            conv_index: Index of conversation in list

        Returns:
            Folder name string
        """
        # Get timestamp
        create_time = conversation.get("create_time")
        timestamp = timestamp_to_iso(create_time)

        # Get title (sanitized)
        title = conversation.get("title", "untitled")
        title_safe = sanitize_filename(title, max_length=50)

        # Generate folder name
        folder_name = f"{timestamp}_{title_safe}_{conv_index:05d}"

        return folder_name

    def extract_assets_from_conversation(self, conversation):
        """
        Extract code blocks and canvas artifacts from conversation.

        Args:
            conversation: Conversation dict

        Returns:
            List of (filename, content) tuples
        """
        assets = []
        asset_counter = {'code_block': 0, 'canvas': 0}

        mapping = conversation.get('mapping', {})

        for node_id, node_data in mapping.items():
            message = node_data.get('message')
            if not message:
                continue

            content = message.get('content', {})

            # Extract canvas/artifacts
            if content.get('content_type') == 'canvas':
                asset_counter['canvas'] += 1
                text = content.get('text', '')
                language = content.get('language', 'txt')
                filename = f"canvas_{node_id[:8]}_{asset_counter['canvas']}.{language}"
                assets.append((filename, text))

            # Extract code blocks from text content
            elif content.get('content_type') == 'code':
                asset_counter['code_block'] += 1
                text = content.get('text', '')
                language = content.get('language', 'txt')
                filename = f"code_block_{node_id[:8]}_{asset_counter['code_block']}.{language}"
                assets.append((filename, text))

        return assets

    def write_organized_output(
        self, conversations, all_media_files, out_dir, media_manifest
    ):
        """
        Write conversations to organized folder structure.

        Args:
            conversations: List of conversation dicts
            all_media_files: List of all discovered media file paths
            out_dir: Base output directory
            media_manifest: Dict mapping conversation index to media basenames

        Returns:
            List of created conversation folders
        """
        ensure_dir(out_dir)
        created_folders = []

        # Build lookup for media files by basename
        media_lookup = {}
        for media_path in all_media_files:
            basename = os.path.basename(media_path)
            media_lookup[basename] = media_path

        self.log(f"Processing {len(conversations)} conversations...")

        for conv_idx, conv in enumerate(conversations):
            # Generate folder name
            folder_name = self.generate_folder_name(conv, conv_idx)
            conv_dir = os.path.join(out_dir, folder_name)
            media_dir = os.path.join(conv_dir, "media")

            ensure_dir(conv_dir)
            ensure_dir(media_dir)

            # Write conversation.json (unless output format is html-only)
            if self.output_format in ["json", "both"]:
                conv_path = os.path.join(conv_dir, "conversation.json")
                with open(conv_path, "w", encoding="utf-8") as f:
                    json.dump(conv, f, indent=2, ensure_ascii=False)

            # Extract assets (code blocks, canvas artifacts)
            assets = self.extract_assets_from_conversation(conv)
            asset_filenames = []

            if assets:
                assets_dir = os.path.join(conv_dir, "assets")
                ensure_dir(assets_dir)

                for filename, content in assets:
                    asset_path = os.path.join(assets_dir, filename)
                    with open(asset_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    asset_filenames.append(filename)

            # Copy media files for this conversation
            # First try to use the new _media_files field (from conversation_id matching)
            media_paths = conv.get("_media_files", [])
            media_mapping = {}  # basename -> hashed_filename

            if media_paths:
                # New method: use full paths from media index
                for src_path in media_paths:
                    if not os.path.exists(src_path):
                        self.log(f"Warning: Media file not found: {src_path}")
                        continue

                    basename = os.path.basename(src_path)

                    # Generate hash for unique naming
                    try:
                        file_hash = hash_file(src_path)
                        # Keep original extension
                        _, ext = os.path.splitext(basename)
                        # Use hash + original name for uniqueness and recognition
                        hashed_name = f"{file_hash}_{basename}"

                        dst_path = os.path.join(media_dir, hashed_name)
                        copy_file(src_path, dst_path)

                        media_mapping[basename] = hashed_name

                    except Exception as e:
                        self.log(f"Error processing media {basename}: {e}")
            else:
                # Fallback to old method: use media_manifest lookup
                media_basenames = media_manifest.get(conv_idx, [])

                for basename in media_basenames:
                    if basename not in media_lookup:
                        self.log(f"Warning: Media file not found: {basename}")
                        continue

                    src_path = media_lookup[basename]

                    # Generate hash for unique naming
                    try:
                        file_hash = hash_file(src_path)
                        # Keep original extension
                        _, ext = os.path.splitext(basename)
                        # Use hash + original name for uniqueness and recognition
                        hashed_name = f"{file_hash}_{basename}"

                        dst_path = os.path.join(media_dir, hashed_name)
                        copy_file(src_path, dst_path)

                        media_mapping[basename] = hashed_name

                    except Exception as e:
                        self.log(f"Error processing media {basename}: {e}")

            # Write media manifest for this conversation
            if media_mapping:
                manifest_path = os.path.join(conv_dir, "media_manifest.json")
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(media_mapping, f, indent=2, ensure_ascii=False)

            # Generate HTML viewer for this conversation (unless output format is json-only)
            if self.output_format in ["html", "both"]:
                media_filenames = list(media_mapping.values()) if media_mapping else []
                conv['_folder_name'] = folder_name  # Store for index generation
                conv['_assets'] = bool(asset_filenames)  # Mark if has assets

                html_content = self.html_generator.generate_conversation_html(
                    conversation=conv,
                    media_files=media_filenames,
                    assets=asset_filenames,
                    folder_name=folder_name,
                    media_mapping=media_mapping
                )

                html_path = os.path.join(conv_dir, "conversation.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
            else:
                # Still store metadata even if not generating HTML
                conv['_folder_name'] = folder_name
                conv['_assets'] = bool(asset_filenames)

            created_folders.append(conv_dir)

            if (conv_idx + 1) % 100 == 0:
                self.log(f"Processed {conv_idx + 1}/{len(conversations)} conversations")

        # Create convenience symlink folders
        self._create_convenience_symlinks(out_dir, created_folders)

        self.log(f"✅ Created {len(created_folders)} conversation folders")
        return created_folders

    def _create_convenience_symlinks(self, out_dir, created_folders):
        """
        Create convenience symlink folders:
        - _with_media/ - symlinks to conversations with non-empty media/ folder
        - _with_assets/ - symlinks to conversations with non-empty assets/ folder

        Args:
            out_dir: Output directory
            created_folders: List of conversation folder paths
        """
        media_symlink_dir = os.path.join(out_dir, "_with_media")
        assets_symlink_dir = os.path.join(out_dir, "_with_assets")

        # Remove existing symlink dirs if they exist
        if os.path.exists(media_symlink_dir):
            shutil.rmtree(media_symlink_dir)
        if os.path.exists(assets_symlink_dir):
            shutil.rmtree(assets_symlink_dir)

        ensure_dir(media_symlink_dir)
        ensure_dir(assets_symlink_dir)

        media_count = 0
        assets_count = 0

        for conv_dir in created_folders:
            folder_name = os.path.basename(conv_dir)
            media_dir = os.path.join(conv_dir, "media")
            assets_dir = os.path.join(conv_dir, "assets")

            # Check if media folder exists and has files
            if os.path.exists(media_dir) and os.listdir(media_dir):
                # Create relative symlink
                symlink_path = os.path.join(media_symlink_dir, folder_name)
                # Use relative path from symlink location to target
                target_path = os.path.join("..", folder_name)
                try:
                    os.symlink(target_path, symlink_path)
                    media_count += 1
                except Exception as e:
                    self.log(f"Warning: Could not create media symlink for {folder_name}: {e}")

            # Check if assets folder exists and has files
            if os.path.exists(assets_dir) and os.listdir(assets_dir):
                # Create relative symlink
                symlink_path = os.path.join(assets_symlink_dir, folder_name)
                # Use relative path from symlink location to target
                target_path = os.path.join("..", folder_name)
                try:
                    os.symlink(target_path, symlink_path)
                    assets_count += 1
                except Exception as e:
                    self.log(f"Warning: Could not create assets symlink for {folder_name}: {e}")

        self.log(f"✅ Created {media_count} symlinks in _with_media/")
        self.log(f"✅ Created {assets_count} symlinks in _with_assets/")
