import os
import zipfile
import uuid
import shutil
import struct
import zlib


def ensure_dir(path):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


# 4 GiB. OpenAI's 2025+ multi-GB exports are written as non-ZIP64 archives
# whose central-directory offsets wrap at this boundary and whose members use
# data descriptors. Python's zipfile (and Info-ZIP unzip / bsdtar) cannot read
# members past this point. We recover these with macOS `ditto` when available,
# and otherwise with a pure-Python streaming extractor (works on every OS).
_ZIP64_WRAP_THRESHOLD = 4 * 1024**3

_LFH_SIG = b"PK\x03\x04"  # local file header
_CFH_SIG = b"PK\x01\x02"  # central directory file header
_EOCD_SIG = b"PK\x05\x06"  # end of central directory


def unzip(src, dst):
    """
    Extract a zip archive to ``dst``, recovering from the malformed multi-GB
    archives that recent OpenAI exports ship.

    Strategy, in order:
      1. Python's ``zipfile`` — fast path for normal/well-formed archives
         (skipped for >4 GiB archives, which are the known-broken kind).
      2. macOS ``ditto`` — streams members correctly (Archive Utility's engine).
      3. Pure-Python streaming extractor — cross-platform recovery that walks
         local file headers and reads member sizes from the (intact) central
         directory, so it works on Windows and Linux with no external tools.
      4. System ``unzip`` — last resort if present.
    """
    import sys
    import subprocess

    ensure_dir(dst)

    try:
        too_big = os.path.getsize(src) > _ZIP64_WRAP_THRESHOLD
    except OSError:
        too_big = False

    # 1. Fast path: Python zipfile for normal archives. The broken >4 GiB
    #    exports only partially extract before raising, so skip straight to the
    #    recovery extractors for them.
    if not too_big:
        try:
            with zipfile.ZipFile(src, "r") as z:
                z.extractall(dst)
            return
        except (zipfile.BadZipFile, OSError):
            pass

    # 2. macOS ditto — handles both giant and corrupted archives natively.
    if sys.platform == "darwin":
        try:
            subprocess.run(
                ["ditto", "-x", "-k", src, dst],
                check=True,
                capture_output=True,
                text=True,
            )
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    # 3. Pure-Python streaming extractor (cross-platform, no external tools).
    try:
        if _stream_extract(src, dst) > 0:
            return
    except Exception:
        pass

    # 4. Last resort: system unzip, if available.
    try:
        result = subprocess.run(
            ["unzip", "-q", "-o", src, "-d", dst], capture_output=True, text=True
        )
        if os.path.exists(dst) and os.listdir(dst):
            return
        raise RuntimeError(
            f"Failed to extract {src} (unzip exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    except FileNotFoundError:
        raise RuntimeError(
            f"Failed to extract {src}. Python's zipfile and the built-in "
            f"streaming extractor could not read it, and no 'unzip' command is "
            f"available. On Windows, extract the .zip with File Explorer "
            f"(right-click -> Extract All) and run the parser against the "
            f"resulting folder instead of the .zip."
        )


def _stream_extract(src, dst):
    """
    Recover a malformed (non-ZIP64-wrapped) zip by streaming it.

    Recent OpenAI exports exceed 4 GiB but are written as non-ZIP64 archives:
    the central-directory *offsets* have wrapped at 2**32 and members use data
    descriptors, so offset-based tools fail. The member *names* and *sizes* in
    the central directory are still intact, and members are laid out
    sequentially. So we read the central directory for sizes, then walk the
    local file headers from the start of the file, copying/inflating each
    member by its known size. Handles stored (0) and deflated (8) members.

    Returns the number of members extracted.
    """
    file_size = os.path.getsize(src)
    with open(src, "rb") as f:
        sizes = _central_directory_sizes(f, file_size)
        if not sizes:
            raise ValueError("could not read central directory")

        pos = _find_first_local_header(f)
        count = 0
        while pos is not None and pos < file_size:
            f.seek(pos)
            hdr = f.read(30)
            if hdr[:4] != _LFH_SIG:
                break  # reached the central directory / end of members

            flags = struct.unpack("<H", hdr[6:8])[0]
            local_method = struct.unpack("<H", hdr[8:10])[0]
            local_comp = struct.unpack("<I", hdr[18:22])[0]
            nlen = struct.unpack("<H", hdr[26:28])[0]
            elen = struct.unpack("<H", hdr[28:30])[0]
            name = f.read(nlen).decode("utf-8", "replace")
            f.seek(elen, os.SEEK_CUR)  # skip extra field
            data_start = pos + 30 + nlen + elen

            cd = sizes.get(name)
            method = cd[0] if cd else local_method
            # Prefer the central-directory size; local headers are 0 when a
            # data descriptor is used (flag bit 3).
            if cd and cd[1] is not None:
                comp_size = cd[1]
            elif not (flags & 0x08):
                comp_size = local_comp
            else:
                raise ValueError(f"unknown size for member {name!r}")

            _write_member(f, data_start, comp_size, method, dst, name)
            count += 1

            # Advance past the data (and any data descriptor) to the next record.
            pos = _find_next_record(f, data_start + comp_size)

        if count == 0:
            raise ValueError("no members extracted")
        return count


def _find_first_local_header(f):
    """Return the offset of the first local file header (usually 0)."""
    f.seek(0)
    if f.read(4) == _LFH_SIG:
        return 0
    f.seek(0)
    window = f.read(1024 * 1024)
    i = window.find(_LFH_SIG)
    return i if i >= 0 else None


def _find_next_record(f, from_pos):
    """
    Find the next local-file-header or central-directory signature at/after
    ``from_pos``, skipping an optional data descriptor (<= 24 bytes).
    """
    f.seek(from_pos)
    window = f.read(64)
    for sig in (_LFH_SIG, _CFH_SIG):
        i = window.find(sig)
        if i >= 0:
            if sig == _CFH_SIG:
                return None  # central directory reached; stop
            return from_pos + i
    return None


def _write_member(f, data_start, comp_size, method, dst, name):
    """Write a single member to ``dst/name``, inflating if deflated."""
    # Normalize and guard against path traversal in member names.
    out_path = os.path.normpath(os.path.join(dst, name))
    if not out_path.startswith(
        os.path.abspath(dst) + os.sep
    ) and out_path != os.path.abspath(dst):
        out_path = os.path.normpath(os.path.join(dst, os.path.basename(name)))

    if name.endswith("/"):
        ensure_dir(out_path)
        return

    ensure_dir(os.path.dirname(out_path))
    f.seek(data_start)
    remaining = comp_size

    if method == 0:  # stored
        with open(out_path, "wb") as out:
            while remaining > 0:
                chunk = f.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                out.write(chunk)
                remaining -= len(chunk)
    elif method == 8:  # deflate
        decompressor = zlib.decompressobj(-15)
        with open(out_path, "wb") as out:
            while remaining > 0:
                chunk = f.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                out.write(decompressor.decompress(chunk))
                remaining -= len(chunk)
            out.write(decompressor.flush())
    else:
        raise ValueError(f"unsupported compression method {method} for {name!r}")


def _central_directory_sizes(f, file_size):
    """
    Return ``{name: (method, compressed_size)}`` from the central directory.

    The central directory sits just before the end-of-central-directory record;
    its recorded *offset* may have wrapped, but its *size* has not, so we locate
    it as ``eocd_position - cd_size`` rather than trusting the stored offset.
    """
    read_len = min(file_size, 65536 + 22)
    f.seek(file_size - read_len)
    tail = f.read(read_len)
    i = tail.rfind(_EOCD_SIG)
    if i < 0:
        return {}

    eocd = tail[i : i + 22]
    cd_size = struct.unpack("<I", eocd[12:16])[0]
    eocd_pos = (file_size - read_len) + i
    cd_start = eocd_pos - cd_size
    if cd_start < 0 or cd_size == 0 or cd_size == 0xFFFFFFFF:
        return {}

    f.seek(cd_start)
    data = f.read(cd_size)
    return _parse_central_directory(data)


def _parse_central_directory(data):
    """Parse central-directory bytes into ``{name: (method, compressed_size)}``."""
    sizes = {}
    p = 0
    n = len(data)
    while p + 46 <= n and data[p : p + 4] == _CFH_SIG:
        method = struct.unpack("<H", data[p + 10 : p + 12])[0]
        comp = struct.unpack("<I", data[p + 20 : p + 24])[0]
        uncomp = struct.unpack("<I", data[p + 24 : p + 28])[0]
        nlen = struct.unpack("<H", data[p + 28 : p + 30])[0]
        elen = struct.unpack("<H", data[p + 30 : p + 32])[0]
        clen = struct.unpack("<H", data[p + 32 : p + 34])[0]
        name = data[p + 46 : p + 46 + nlen].decode("utf-8", "replace")
        extra = data[p + 46 + nlen : p + 46 + nlen + elen]

        if comp == 0xFFFFFFFF:  # true ZIP64 member; read size from extra field
            comp = _zip64_compressed_size(extra, uncomp_is_ff=(uncomp == 0xFFFFFFFF))

        sizes[name] = (method, comp)
        p += 46 + nlen + elen + clen
    return sizes


def _zip64_compressed_size(extra, uncomp_is_ff):
    """Pull the 8-byte compressed size out of a ZIP64 extended-info extra field."""
    p = 0
    while p + 4 <= len(extra):
        header_id, size = struct.unpack("<HH", extra[p : p + 4])
        body = extra[p + 4 : p + 4 + size]
        if header_id == 0x0001:
            # Order: [uncompressed][compressed][...], only for fields that were
            # 0xFFFFFFFF. Uncompressed comes first when it was also 0xFFFFFFFF.
            idx = 8 if uncomp_is_ff else 0
            if len(body) >= idx + 8:
                return struct.unpack("<Q", body[idx : idx + 8])[0]
        p += 4 + size
    return None


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
