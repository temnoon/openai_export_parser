# openai-export-parser

[![Tests](https://github.com/temnoon/openai_export_parser/workflows/Tests/badge.svg)](https://github.com/temnoon/openai_export_parser/actions)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Turn your ChatGPT (and Claude) data export into a browsable, self-contained archive — every conversation in its own folder, with its images, audio, and files restored and a searchable HTML viewer to read it all.**

OpenAI's export is a pile of nested zips and opaque JSON; the images are stored
under cryptic IDs (and, in recent exports, with their file extensions stripped
to `.dat`). This tool untangles all of that into something you can actually
read, search, and keep.

> ✅ **Updated for the latest 2026 ChatGPT export format** — the new multi-gigabyte,
> split-zip layout with `.dat` media files. See [Supported formats](#-supported-export-formats).

---

## 👋 New here? Start in 3 steps

**1. Get the tool**

```bash
git clone git@github.com:temnoon/openai_export_parser.git
cd openai_export_parser
pip install -e .
```

**2. Point it at your export**

```bash
openai-export-parser ~/Downloads/OpenAI-export.zip -o ~/Desktop/my-chatgpt-archive -v
```

(`-o` is where the output goes, `-v` shows progress. The export type — OpenAI or
Claude — is detected automatically.)

**3. Read your archive**

Open the output folder and double-click **`view.command`** (macOS). It starts a
tiny local web server and opens the master index in your browser.

> **Why not just double-click `index.html`?** Browsers sandbox pages opened as
> `file://`, which breaks links between conversations and stops images from
> loading. Viewing over a local `http://` server (what `view.command` does) makes
> everything work. See [Viewing your archive](#-viewing-your-archive).

That's it. You now have every conversation as its own folder plus a searchable
index of the whole archive.

### Where do I get my ChatGPT export?

1. In ChatGPT: **Settings → Data controls → Export data**.
2. Confirm. OpenAI emails you a download link (it expires in ~24 hours).
3. Download the `.zip` — that's the file you feed to this tool. Large accounts
   come as a single multi-GB zip containing several inner zips; that's expected
   and supported.

---

## ✨ Key Features

### 🖼️ Restores your media
- **Matches images, audio, and files** back to the messages that reference them,
  using a multi-strategy matcher (file-ID, content hash, filename+size, and more).
- **Recovers stripped extensions** — recent exports store every asset as a
  generic `.dat`; the parser sniffs each file's real type (PNG/JPEG/PDF/WAV/…)
  so it displays correctly.
- **DALL·E images & uploads** alike, with dimensions and metadata preserved.

### 📱 Beautiful, self-contained HTML viewer
- **One HTML file per conversation** — shareable and fully offline.
- **Master index** with live search, filtering, and stats.
- **Dark mode**, **Markdown + LaTeX** rendering, and **syntax-highlighted** code.
- **Responsive** — works on desktop and mobile.

### 🎙️ Voice mode support
- Extracts **voice transcripts** and embeds **HTML5 audio players** so you can
  re-listen to original recordings.

### 🔧 Robust, real-world processing
- **Handles the broken multi-GB zips OpenAI actually ships** (see
  [How it handles giant exports](#-how-it-handles-giant-exports)).
- **Recursive zip extraction** for arbitrarily nested archives.
- **Auto-detects** OpenAI vs Claude exports.
- **Graceful recovery** from incomplete or partial exports.

### 📊 Organization & discovery
- **Smart folder names** — `YYYY-MM-DD_Title_NNNNN`.
- **Shortcut folders** — `_with_media/` and `_with_assets/` for quick browsing.
- **Search & filter** by title, date, length, and content.

---

## 📦 Installation

**From source (recommended):**

```bash
git clone git@github.com:temnoon/openai_export_parser.git
cd openai_export_parser
pip install -e .
```

Requires **Python 3.8+**. The only runtime dependencies are `tqdm` and
`python-dateutil` (installed automatically). On **macOS**, giant exports are
extracted with the built-in `ditto` tool — no extra install needed.

---

## 🚀 Usage

### Command line

```bash
# OpenAI ChatGPT export (auto-detected)
openai-export-parser export.zip

# Claude conversation export (auto-detected)
openai-export-parser claude_data_export.zip

# Choose an output directory and show progress
openai-export-parser export.zip -o my_conversations -v

# JSON only (skip HTML), or HTML only
openai-export-parser export.zip --output-format json
openai-export-parser export.zip --output-format html

# Legacy flat layout instead of per-conversation folders
openai-export-parser export.zip --flat
```

### Python API

```python
from openai_export_parser import ExportParser

parser = ExportParser(verbose=True)              # output_format="both" by default
parser.parse_export("export.zip", "output_dir")
```

---

## 🖥️ Viewing your archive

The output is **static files**, but browsers restrict pages opened directly from
disk (`file://`): cross-folder links and local images silently fail. Serve the
folder over `http://` instead — any of these work:

**Easiest (macOS):** double-click **`view.command`** in the output folder. It
finds a free port, starts a local server, and opens the index for you. Close the
Terminal window to stop it.

**Manual (any OS):**

```bash
cd your-output-folder
python3 -m http.server 8000
# then open http://localhost:8000/index.html
```

In the viewer you can search and filter the conversation list, toggle dark mode,
and click into any conversation to see formatted text, inline images, audio
players, highlighted code, and rendered math.

---

## 📁 Output structure

```
my-chatgpt-archive/
├── index.html                     # Master index — start here (serve over http://)
├── index.json                     # Archive metadata + stats
├── view.command                   # Double-click to launch the local viewer (macOS)
├── _with_media/                   # Shortcuts to conversations that have media
├── _with_assets/                  # Shortcuts to conversations with code/canvas assets
├── 2023-10-04_Cosmic_Surreal_Art_Creation_01397/
│   ├── conversation.html          # Standalone, offline-capable viewer
│   ├── conversation.json          # Full original conversation data (mapping tree)
│   ├── media/                     # Restored images / audio (real extensions)
│   │   └── f6f61065525a_file-aZlh7eXXkKmbAT3s8OUOyknk.png
│   ├── media_manifest.json        # Maps original asset names → stored files
│   └── assets/                    # Extracted code blocks / canvas artifacts
└── … one folder per conversation
```

> Note: `view.command` is written into the output folder by the bundled viewer
> helper; if your output predates it, just use the manual `http.server` command
> above.

---

## 🧩 Supported export formats

OpenAI has changed the export format **many times**. This parser is built to
absorb those changes; here's what it handles today.

### OpenAI ChatGPT

| Era | Shape | Media | Status |
|-----|-------|-------|--------|
| **2026 (latest)** | One outer zip wrapping `Conversations__…part-00N.zip` + `Files__…files-00N.zip`, plus `Financial/`, `User Profile/`, etc. Conversations sharded as `conversations-NNN.json`. | Assets stored as **`file-<ID>.dat`** (extension stripped) and `personal/files/<name>` uploads. | ✅ Fully supported |
| **2024–2025** | Nested zips; `conversations.json` or sharded JSON. | `file-service://` and `sediment://` pointers; `dalle-generations/`, `user-…/`, `{uuid}/audio/`. | ✅ Supported |
| **Pre-2024** | Single `conversations.json`, flat media. | Simple filenames. | ✅ Supported |

All OpenAI conversations use the **`mapping` tree** (a DAG of message nodes with
`current_node`), which the parser linearizes for display. Media is referenced via
`image_asset_pointer` parts (`file-service://file-<ID>`) and message
`attachments`.

### Claude

A single zip containing `conversations.json`, `projects.json`, and `users.json`,
with a flat message structure. **Auto-detected** and converted to the same
organized output. To export: **Settings → Privacy → Export data** in the Claude
web or desktop app.

---

## 🐘 How it handles giant exports

Large ChatGPT accounts export as a single zip **bigger than 4 GiB** — and OpenAI
writes these as **non-ZIP64 archives whose internal offsets wrap at the 4 GiB
boundary**, with members stored using data descriptors. The practical result:

- `unzip`, `bsdtar`, and even Python's own `zipfile` **fail** on any file past
  the 4 GiB mark (`bad zipfile offset` / `Truncated file header`).
- Only **streaming extractors** that read members sequentially can open them.

So on macOS the parser sends any archive larger than 4 GiB straight to
**`ditto`** (the same engine as Finder's Archive Utility), which extracts these
archives correctly. Smaller and well-formed zips use the fast Python path. If a
zip is merely corrupted, the parser still falls back through `ditto` → system
`unzip`, accepting partial extractions when possible.

**Rule of thumb:** if Finder's Archive Utility can open your export, this parser
can too.

---

## 🔎 Media matching strategies

The matcher tries several approaches, most reliable first, and de-duplicates hits:

1. **Content hash** — `sediment://file_<hash>` → exact, content-addressed match.
2. **File-ID** — `file-service://file-<ID>` → `file-<ID>.dat` / `file-<ID>-name.ext`
   (handles the modern extension-stripped naming). *This carries most matches in
   recent exports.*
3. **Filename + size** — user uploads matched by original name and byte size.
4. **Conversation directory** — files stored under a conversation's own folder.
5. **Size + DALL·E metadata** — dimensions/generation id for generated images.
6. **Size only** — fallback when a size is unique across the archive.
7. **Filename only** — last-resort basename match.

> Some references simply have **no file in the export** — OpenAI has, in some
> periods, omitted image bytes entirely. Those show up as `UNMATCHED` in verbose
> logs and are expected, not a bug.

---

## 🛠️ Troubleshooting

**"`index.html` doesn't work / looks blank / links are dead."**
You're opening it as `file://`. Serve the folder over `http://` instead — use
`view.command` or `python3 -m http.server` (see
[Viewing your archive](#-viewing-your-archive)).

**"Bad magic number" / "Truncated file header" / extraction fails on a big zip.**
That's the >4 GiB ZIP64 wrap issue above. On macOS the parser uses `ditto`
automatically. If you're on Linux/Windows with a giant export, first extract the
**outer** zip with a streaming tool (e.g. macOS Archive Utility, `7z`, or The
Unarchiver) and run the parser against the extracted folder.

**"No conversations found."**
Confirm you passed the real export `.zip` (or its extracted folder). Re-run with
`-v` and check the log for extraction errors.

**"Images aren't showing."**
Make sure you're viewing over `http://` (not `file://`). If a specific image is
missing from `media/`, the asset may not be present in the export at all — check
the log for `UNMATCHED`.

**"Audio not playing."**
Verify `.wav` files exist in the conversation's `media/` folder and that you're
serving over `http://`.

---

## ⚙️ Performance

Measured on a recent Mac, organized output with HTML:

- **~2,000 conversations / ~6,000 media files**: ~30–60 s of processing after
  extraction (a real 5 GB / 1,968-conversation export matched 5,936 media files
  in ~32 s).
- Processing is **I/O bound** — wall-clock is dominated by unzipping and copying
  media, so it scales with disk speed.

---

## 🧱 Project structure

```
openai_export_parser/
├── parser.py                       # Orchestrates extract → scan → match → write
├── utils.py                        # Zip extraction, ditto fallback, type sniffing
├── conversation_organizer.py       # Per-conversation folders + media copying
├── html_generator.py               # HTML/CSS/JS for viewer and master index
├── comprehensive_media_indexer.py  # Builds file indices
├── comprehensive_media_matcher.py  # Multi-strategy media matching
├── media_reference_extractor.py    # Pulls media references out of conversations
└── claude_parser.py                # Converts Claude exports to the OpenAI shape
```

---

## 👩‍💻 Development

```bash
pip install -e ".[dev]"
pytest tests/
```

Where to make changes:
- **New media type** → rendering in `html_generator.py`, and `sniff_extension()`
  in `utils.py` if the type needs extension recovery.
- **New matching strategy** → `comprehensive_media_matcher.py` (+ an index in
  `comprehensive_media_indexer.py`).
- **New export layout** → extraction/scan in `parser.py` and `utils.py`.

---

## 🤝 Contributing

1. Fork and branch (`git checkout -b feature/your-feature`).
2. `pytest tests/`.
3. Open a pull request describing the export format or scenario you're improving —
   sample (anonymized) export structures are especially welcome, since the format
   keeps changing.

## License

MIT — see [LICENSE](LICENSE).

## Related projects

- [Humanizer](https://github.com/temnoon/humanizer_root) — local-first archive &
  knowledge tooling this parser feeds into.

---

**Found a bug or a new export format?** [Open an issue](https://github.com/temnoon/openai_export_parser/issues).
