import os
import json
from tqdm import tqdm
from dateutil.parser import parse as parse_dt

from .utils import ensure_dir, unzip, is_zip, copy_file
from .comprehensive_media_indexer import ComprehensiveMediaIndexer
from .media_reference_extractor import MediaReferenceExtractor
from .comprehensive_media_matcher import ComprehensiveMediaMatcher
from .schema_inference import SchemaInference
from .threader import ConversationThreader
from .conversation_organizer import ConversationOrganizer

MEDIA_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif",
             ".mp3", ".wav", ".mp4", ".mov", ".pdf"}


class ExportParser:
    """
    Main parser for OpenAI ChatGPT export archives.

    Handles:
    - Recursive zip extraction
    - Conversation JSON discovery and loading
    - Media file detection and matching
    - Schema inference for future-proofing
    - Output generation with normalized structure
    """

    def __init__(self, verbose=False, organize_by_conversation=True, output_format="both"):
        self.verbose = verbose
        self.organize_by_conversation = organize_by_conversation
        self.output_format = output_format

        self.indexer = ComprehensiveMediaIndexer(verbose=verbose)
        self.extractor = MediaReferenceExtractor(verbose=verbose)
        self.matcher = ComprehensiveMediaMatcher(verbose=verbose)
        self.infer = SchemaInference()
        self.threader = ConversationThreader()
        self.organizer = ConversationOrganizer(verbose=verbose, output_format=output_format)

        self.conversation_files = []
        self.media_files = []
        self.media_index = None

    def log(self, *args):
        """Print log message if verbose mode is enabled."""
        if self.verbose:
            print("[EXPORT]", *args)

    # ----------------------------------------
    # ENTRY POINT
    # ----------------------------------------

    def parse_export(self, zip_path, output_dir):
        """
        Parse an OpenAI export archive.

        Args:
            zip_path: Path to the export.zip file
            output_dir: Directory to write parsed results

        Generates:
            - conversations/ directory with individual JSON files
            - media/ directory with extracted media files
            - index.json with metadata and schema information
        """
        ensure_dir(output_dir)
        tmp_dir = os.path.join(output_dir, "_tmp")
        ensure_dir(tmp_dir)

        self.log("Unzipping top-level archive...")
        unzip(zip_path, tmp_dir)

        self.log("Scanning for conversations and media...")
        self.scan(tmp_dir)

        self.log(f"Found {len(self.conversation_files)} conversation files")
        self.log(f"Found {len(self.media_files)} media files")

        conversations = self.load_conversations()
        conversations = self.normalize_conversations(conversations)

        # Build comprehensive media index from directory structure
        self.log("Building comprehensive media index...")

        # Add recovery folder for files from old exports (Session 8 recovery)
        recovery_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recovered_files")
        if not os.path.exists(recovery_dir):
            recovery_dir = "/Users/tem/openai-export-parser/recovered_files"  # Fallback to absolute path

        file_indices = self.indexer.build_index(tmp_dir, recovery_dir=recovery_dir)

        # Log index stats
        index_stats = self.indexer.get_stats()
        self.log(f"✓ Indexed {index_stats['total_files']} total media files")
        self.log(f"  - Files with file-ID prefixes: {index_stats['file_id_files']}")
        self.log(f"  - Files with file_{{hash}}-{{uuid}} pattern: {index_stats['file_hash_files']}")
        self.log(f"  - Files in conversation directories: {index_stats['conversation_dirs']}")
        self.log(f"  - Unique (filename, size) pairs: {index_stats['unique_basename_size_pairs']}")

        self.log("Matching media to conversations...")
        conversations = self.matcher.match(
            conversations,
            file_indices,
            self.extractor
        )

        # Log matching stats
        self.matcher.print_summary()

        self.log("Inferring schemas...")
        schemas = self.infer.infer_global_schema(conversations)

        self.log("Writing output...")
        self.write_output(conversations, schemas, output_dir)

        self.log("✅ Parsing complete")

    # ----------------------------------------
    # Recursive scan for conversations and media
    # ----------------------------------------

    def scan(self, root):
        """
        Recursively scan directory tree for:
        - Nested zip files (extracted recursively)
        - Conversation JSON files
        - Media files (images, audio, video, PDFs)

        Args:
            root: Root directory to scan
        """
        for dirpath, dirs, files in os.walk(root):
            for f in files:
                full = os.path.join(dirpath, f)
                ext = os.path.splitext(f)[1].lower()

                # Handle nested zip archives
                if is_zip(full):
                    self.log(f"Extracting nested zip: {f}")
                    out = full + "_unzipped"
                    unzip(full, out)
                    self.scan(out)
                    continue

                # Detect conversation files
                if f == "conversations.json":
                    self.conversation_files.append(full)
                elif ext == ".json" and "conversation" in f.lower():
                    self.conversation_files.append(full)

                # Detect media files
                elif ext in MEDIA_EXT:
                    self.media_files.append(full)

    # ----------------------------------------
    # Load & normalize conversations
    # ----------------------------------------

    def load_conversations(self):
        """
        Load all discovered conversation JSON files.

        Returns:
            List of conversation dicts
        """
        conversations = []

        for path in tqdm(self.conversation_files, desc="Loading conversations"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Handle both list and single-object formats
                if isinstance(data, list):
                    conversations.extend(data)
                elif isinstance(data, dict):
                    conversations.append(data)
                else:
                    self.log(f"Warning: Unexpected format in {path}")
                    conversations.append({"raw": data})

            except Exception as e:
                self.log(f"Error reading {path}: {e}")

        return conversations

    def normalize_conversations(self, conversations):
        """
        Normalize conversation structures and add threading.

        Args:
            conversations: List of raw conversation dicts

        Returns:
            List of normalized conversation dicts
        """
        out = []
        for c in conversations:
            # Ensure messages field exists
            c.setdefault("messages", [])
            # Add threading metadata
            out.append(self.threader.thread(c))
        return out

    # ----------------------------------------
    # Write output
    # ----------------------------------------

    def write_output(self, conversations, schemas, out_dir):
        """
        Write parsed output to disk.

        Args:
            conversations: Normalized conversation list
            schemas: Inferred schema information
            out_dir: Output directory
        """
        if self.organize_by_conversation:
            self._write_organized_output(conversations, schemas, out_dir)
        else:
            self._write_flat_output(conversations, schemas, out_dir)

    def _write_organized_output(self, conversations, schemas, out_dir):
        """
        Write conversations to organized folder structure.
        Each conversation gets its own folder with media.
        """
        ensure_dir(out_dir)

        # Build media manifest (which media belongs to which conversation)
        media_manifest = {}
        for conv_idx, conv in enumerate(conversations):
            media_files = set()
            for msg in conv.get("messages", []):
                if "media" in msg:
                    media_files.update(msg["media"])
            media_manifest[conv_idx] = list(media_files)

        # Create organized folders
        created_folders = self.organizer.write_organized_output(
            conversations, self.media_files, out_dir, media_manifest
        )

        # Generate master HTML index (unless output format is json-only)
        if self.output_format in ["html", "both"]:
            self.log("Generating master index.html...")
            index_html = self.organizer.html_generator.generate_index_html(
                conversations, out_dir
            )
            index_html_path = os.path.join(out_dir, "index.html")
            with open(index_html_path, "w", encoding="utf-8") as f:
                f.write(index_html)

        # Create global index (JSON)
        index = {
            "conversation_count": len(conversations),
            "media_count": len(self.media_files),
            "schema_inference": schemas,
            "organization_mode": "by_conversation",
            "folders": [os.path.basename(f) for f in created_folders],
        }

        with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        self.log(f"✅ Wrote {len(conversations)} conversations in organized folders")
        if self.output_format in ["html", "both"]:
            self.log(f"✅ Generated HTML viewer with {len(conversations)} conversation pages")
        self.log(f"✅ Processed {len(self.media_files)} media file references")

    def _write_flat_output(self, conversations, schemas, out_dir):
        """
        Write conversations to flat structure (legacy mode).
        All conversations in one folder, all media in another.
        """
        conv_dir = os.path.join(out_dir, "conversations")
        media_dir = os.path.join(out_dir, "media")

        ensure_dir(conv_dir)
        ensure_dir(media_dir)

        # Write individual conversation files
        for i, conv in enumerate(conversations):
            path = os.path.join(conv_dir, f"conv_{i:05d}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(conv, f, indent=2, ensure_ascii=False)

        # Copy media files
        for src in self.media_files:
            dst = os.path.join(media_dir, os.path.basename(src))
            try:
                copy_file(src, dst)
            except Exception as e:
                self.log(f"Error copying {src}: {e}")

        # Create global index
        index = {
            "conversation_count": len(conversations),
            "media_count": len(self.media_files),
            "schema_inference": schemas,
            "organization_mode": "flat",
        }

        with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        self.log(f"✅ Wrote {len(conversations)} conversations")
        self.log(f"✅ Wrote {len(self.media_files)} media files")
