import os
import zipfile
import uuid
import shutil


def ensure_dir(path):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def unzip(src, dst):
    """
    Extract zip archive to destination directory.
    Falls back to system unzip command if Python zipfile fails.
    Handles corrupted/malformed zips that macOS can still open.
    """
    ensure_dir(dst)

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
