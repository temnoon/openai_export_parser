import os
import zipfile
import uuid
import shutil


def ensure_dir(path):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


# 4 GiB. OpenAI's 2025+ multi-GB exports are written as non-ZIP64 archives
# whose central-directory offsets wrap at this boundary and whose members use
# data descriptors. Python's zipfile (and Info-ZIP unzip / bsdtar) cannot read
# members past this point — only streaming extractors (macOS ditto / Archive
# Utility) succeed. For such archives we skip straight to ditto on macOS.
_ZIP64_WRAP_THRESHOLD = 4 * 1024 ** 3


def unzip(src, dst):
    """
    Extract zip archive to destination directory.
    Falls back to system unzip command if Python zipfile fails.
    Handles corrupted/malformed zips that macOS can still open.
    """
    import sys

    ensure_dir(dst)

    # Large OpenAI exports (>4 GiB) are broken non-ZIP64 archives that Python's
    # zipfile only partially extracts before raising. On macOS, go straight to
    # ditto (the same engine as Finder's Archive Utility), which streams members
    # via their local headers and handles these archives correctly.
    try:
        too_big = os.path.getsize(src) > _ZIP64_WRAP_THRESHOLD
    except OSError:
        too_big = False

    if too_big and sys.platform == "darwin":
        import subprocess
        try:
            subprocess.run(
                ["ditto", "-x", "-k", src, dst],
                check=True, capture_output=True, text=True
            )
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # Fall through to the normal Python-first path

    # Try Python's zipfile first
    try:
        with zipfile.ZipFile(src, "r") as z:
            z.extractall(dst)
        return
    except (zipfile.BadZipFile, OSError) as e:
        # Python zipfile failed, try system extraction tools
        import subprocess
        import sys

        # On macOS, try ditto first (same tool Archive Utility uses)
        if sys.platform == "darwin":
            try:
                subprocess.run(
                    ["ditto", "-x", "-k", src, dst],
                    check=True,
                    capture_output=True,
                    text=True
                )
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass  # Fall through to unzip

        # Try system unzip command
        try:
            result = subprocess.run(
                ["unzip", "-q", "-o", src, "-d", dst],
                capture_output=True,
                text=True
            )

            # Check if files were actually extracted (even with warnings)
            extracted_files = os.listdir(dst) if os.path.exists(dst) else []

            if extracted_files:
                # Success! Files were extracted despite warnings
                return

            # No files extracted
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode,
                    result.args,
                    result.stdout,
                    result.stderr
                )

        except subprocess.CalledProcessError as cmd_error:
            # Check one more time if files were extracted
            extracted_files = os.listdir(dst) if os.path.exists(dst) else []
            if extracted_files:
                # Files were extracted, ignore the error
                return

            # Truly failed
            raise RuntimeError(
                f"Failed to extract {src}:\n"
                f"  Python zipfile error: {e}\n"
                f"  System unzip error: {cmd_error.stderr}"
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Failed to extract {src} with Python zipfile: {e}\n"
                f"System 'unzip' command not found. Please install it or fix the zip file."
            )


def is_zip(path):
    """Check if file is a valid zip archive."""
    return zipfile.is_zipfile(path)


# Magic-byte signatures -> file extension. Used to recover the real type of
# 2025+ OpenAI export assets, which are all stored with a generic ".dat"
# extension regardless of their actual format.
_MAGIC_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"%PDF", ".pdf"),
    (b"BM", ".bmp"),
    (b"\x1aE\xdf\xa3", ".webm"),  # also Matroska
    (b"OggS", ".ogg"),
    (b"fLaC", ".flac"),
    (b"ID3", ".mp3"),
)


def sniff_extension(path, default=None):
    """
    Detect a file's real extension from its magic bytes.

    OpenAI's 2025+ exports strip extensions, storing every asset as ".dat".
    This restores a sensible extension so images/audio render in the HTML
    viewer. Handles container formats (RIFF -> wav/webp/avi, ISO-BMFF -> mp4/mov)
    that need a few extra bytes to disambiguate.

    Args:
        path: Path to the file to inspect
        default: Extension to return if the type can't be identified
                 (defaults to the file's current extension)

    Returns:
        An extension string including the leading dot (e.g. ".png").
    """
    if default is None:
        default = os.path.splitext(path)[1] or ".dat"

    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return default

    for sig, ext in _MAGIC_SIGNATURES:
        if head.startswith(sig):
            return ext

    # RIFF container: bytes 8-12 give the form type (WAVE, WEBP, AVI )
    if head[:4] == b"RIFF":
        form = head[8:12]
        return {b"WAVE": ".wav", b"WEBP": ".webp", b"AVI ": ".avi"}.get(form, default)

    # ISO base media (MP4/MOV/M4A): "ftyp" box at offset 4
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand[:3] == b"qt ":
            return ".mov"
        if brand in (b"M4A ", b"M4A\x00"):
            return ".m4a"
        return ".mp4"

    return default


def copy_file(src, dst):
    """Copy file from src to dst, creating parent directories if needed."""
    ensure_dir(os.path.dirname(dst))
    shutil.copy2(src, dst)


def generate_id(prefix="id"):
    """Generate a unique ID with optional prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def list_files_recursive(root):
    """Recursively list all files under root directory."""
    for dirpath, dirs, files in os.walk(root):
        for f in files:
            yield os.path.join(dirpath, f)


def hash_file(filepath):
    """
    Generate SHA256 hash of file for unique identification.

    Args:
        filepath: Path to file

    Returns:
        Hex string of first 12 characters of hash
    """
    import hashlib

    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:12]


def sanitize_filename(name, max_length=50):
    """
    Convert string to safe filename component.

    Args:
        name: Input string
        max_length: Maximum length of output

    Returns:
        Sanitized string safe for use in filenames
    """
    import re

    # Replace spaces with underscores
    name = name.replace(" ", "_")

    # Remove or replace unsafe characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)

    # Replace multiple underscores with single
    name = re.sub(r"_+", "_", name)

    # Trim to max length
    if len(name) > max_length:
        name = name[:max_length].rstrip("_")

    return name or "untitled"


def timestamp_to_iso(timestamp):
    """
    Convert Unix timestamp to ISO date string for folder naming.

    Args:
        timestamp: Unix timestamp (int or float)

    Returns:
        ISO formatted date string (YYYY-MM-DD)
    """
    from datetime import datetime

    if not timestamp:
        return "0000-00-00"

    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return "0000-00-00"
