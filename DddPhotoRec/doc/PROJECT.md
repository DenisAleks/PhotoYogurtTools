# DddPhotoRec — Photo Recovery Toolkit

A small desktop application that helps you clean up the output of photo/video
recovery tools. After a disk-recovery run you usually end up with a huge
"recovered" folder that contains many files you *already have* in your organized
library. This tool compares the recovered files against your existing originals
and splits them into two buckets:

- **duplicates** — recovered files that byte-for-byte match a file you already own
- **recovered** (unique) — files that have no match among your originals and are
  therefore genuinely worth keeping

The comparison is content-based (SHA-256), so it does not rely on filenames,
timestamps, or folder structure.

---

The app is a **toolkit** — a tabbed desktop UI hosting several media utilities.
Beyond recovery it also renames & sorts a library by capture date (see
[The Renamer](#the-renamer-photo--video-renamer-tab)).

---

## Status

- **Version:** 0.1.0 (early / work-in-progress)
- **Python:** >= 3.10 (`@dataclass(slots=True)` is used across the code)
- Tabs:
  - **Photo Recovery** — functional.
  - **Photo & Video Renamer** — functional (v1: rename + date-sort in place, with Undo).
  - **Duplicates Finder** — functional (scan → report → flag in place, with Undo).
- Recovery **copies** files by default; a UI toggle switches it to move mode.
  The Renamer **moves** files in place and offers an **Undo** button as its
  safety net (see [Safety notes](#safety-notes)).

---

## Tech stack

| Concern        | Choice                                            |
|----------------|---------------------------------------------------|
| Language       | Python 3.10+                                       |
| GUI            | [Flet](https://flet.dev) `0.28.3` (desktop app)   |
| Hashing        | `hashlib.sha256` (stdlib)                          |
| Photo metadata | Pillow EXIF + `pillow-heif` (HEIC)                 |
| Geocoding      | `reverse-geocode` (offline, on-device)            |
| Folder picker  | Tkinter `filedialog`, launched as a subprocess    |
| Build backend  | Hatchling                                          |
| Declared deps  | `flet[all]`, `jpegio`, `pillow`, `pillow-heif`, `reverse-geocode` |

> `pillow` / `pillow-heif` read capture date-time and GPS from photos;
> `reverse-geocode` turns GPS into a place name **offline** (coordinates never
> leave the machine). `jpegio` is still declared but currently unused.

---

## Project layout

The code is organized **by feature**. Everything belonging to a single tab lives
in its own folder under `features/`, so a feature can be read, changed, or
removed in one place. Cross-feature building blocks live in `shared/`, and the
application shell (window, header, tab bar) lives in `shell/`.

```
DddPhotoRec/
├── pyproject.toml            # project metadata + dependencies
├── uv.lock                   # locked dependency versions (uv)
├── doc/
│   └── PROJECT.md            # this document
└── src/photorec/
    ├── main.py               # Flet entry point
    │
    ├── shell/                # application shell (feature-agnostic)
    │   ├── main_window.py    # window config + top-level layout
    │   ├── app_header.py     # title bar
    │   └── app_tabs.py       # wires the tabs together
    │
    ├── shared/               # reusable across features
    │   ├── folder_card.py    # folder-selection card widget
    │   ├── future_tab.py     # "coming soon" placeholder tab (unused now)
    │   ├── file_picker.py    # native folder dialog via Tkinter subprocess
    │   ├── media_scanner.py  # MediaScanner + image/video extension sets
    │   ├── hash_calculator.py# HashCalculator: full + partial SHA-256
    │   └── rename_ops.py     # RenameOperation + undo_operations()
    │
    └── features/
        ├── recovery/         # ← the Photo Recovery tab, in one folder
        │   ├── recovery_tab.py       # the tab's Flet UI
        │   ├── service.py            # PhotoRecoveryService: orchestrates a run
        │   ├── image_signature.py    # decode image → pixel hash (+ dimensions)
        │   ├── original_index.py     # OriginalIndex: content-signature index
        │   ├── duplicate_finder.py   # DuplicateFinder: content match → MatchResult
        │   └── duplicate_processor.py# DuplicateProcessor: copy/move into output
        │
        ├── renamer/          # ← the Photo & Video Renamer tab
        │   ├── renamer_tab.py        # UI: input folder, pattern, Rename/Undo
        │   ├── service.py            # RenamerService: scan → resolve → move
        │   ├── date_resolver.py      # capture date: EXIF → filename → filesystem
        │   ├── exif_reader.py        # Pillow / pillow-heif: date-time + GPS
        │   ├── geocoder.py           # offline GPS → place name (reverse-geocode)
        │   └── name_builder.py       # pattern tokens → folder/filename
        │
        └── duplicates/       # ← the Duplicates Finder tab
            ├── duplicates_tab.py     # UI: input folder, Scan/Rename/Undo, log
            ├── service.py            # DuplicatesService: scan (read-only) + rename
            ├── duplicate_scanner.py  # size → quick-hash → full-hash funnel
            ├── report_writer.py      # the Markdown report
            ├── naming.py             # _dup_ suffix + already-flagged detection
            └── models.py             # DuplicateGroup
```

> **Shared, not cross-imported:** features depend on `shared/` (scanner, hashing,
> rename+undo), never on each other. Adding a feature = a new `features/<name>/`
> with its own `*_tab.py`, reusing `shared/`, registered in `shell/app_tabs.py`.

---

## The Recovery tool (how it works)

The user picks three folders and presses **Process files**:

1. **ORIGINAL** — your existing, organized library (the source of truth).
2. **RECOVERED** — the messy output from a recovery tool.
3. **OUTPUT** — where results are written.

The run is driven by `PhotoRecoveryService.run()`
(`features/recovery/service.py`):

### 1. Scan originals
`MediaScanner` recursively walks the ORIGINAL folder (`rglob("*")`) and keeps
only files whose extension is in the supported media set:

- images: `.jpg .jpeg .png .webp .heic`
- videos: `.mp4 .mov .m4v .avi .mkv .3gp`

### 2. Build the index (content signatures)
`OriginalIndex.build()` (async, with progress + cancel) computes a **content
signature** for every library file and stores `dict[signature → path]`:

- **Images** → SHA-256 of the **decoded pixel data** (`image_signature`). This
  ignores the file container, trailing padding, and EXIF metadata — so a photo
  and its recovered copy hash the same even when their raw bytes differ. This is
  the key: recovery tools pad files and strip/rewrite EXIF, which changes bytes
  but **not the pixels**.
- **Videos** → SHA-256 of the **raw bytes** (`HashCalculator`); pixels can't be
  cheaply decoded, so videos stay on exact-byte matching.

It also remembers the set of image dimensions seen, used only for diagnostics.

### 3. Scan & classify recovered files
For each file in the RECOVERED folder, `DuplicateFinder.find_original()` computes
the same content signature (pixels for images, bytes for videos) and looks it up
in the index. A hit → **duplicate** (the matched library file); a miss →
**recovered**. Misses are split for the log: a recovered image whose dimensions
match a library photo but whose pixels differ is flagged as a likely
**re-compressed/edited** version rather than genuinely new (catching those would
need fuzzy/perceptual matching).

### 4. Route the output
`DuplicateProcessor` writes each file under OUTPUT:

- **Duplicates** → `OUTPUT/duplicates/<original-relative-path>/<name>_DUP.<ext>`
  — mirrors the original's location in your library, so you can see which
  existing file the recovered copy corresponds to.
- **Unique** → `OUTPUT/recovered/<recovered-folder-name>/<relative-path>`
  — preserves the recovered folder's own structure.

Files are **copied** (`shutil.copy2`) by default; set `move_files=True` to move
instead (`shutil.move`).

### 5. Progress & cancellation
The service reports progress through a `log` callback (wired to the on-screen log
panel) and checks a `cancel_check` callback frequently, so a run can be stopped
mid-way. The loop yields control to the async event loop (`asyncio.sleep(0)`)
periodically so the Flet UI stays responsive.

---

## Key components

| Component            | Responsibility |
|----------------------|----------------|
| `MediaScanner`       | Recursively find supported media files (shared). |
| `image_signature`    | Decode an image and hash its **pixels** (+ dimensions). |
| `OriginalIndex`      | Index library files by content signature (pixels/bytes). |
| `DuplicateFinder`    | Match a recovered file by content; returns `MatchResult`. |
| `DuplicateProcessor` | Copy/move a file into the correct output subtree. |
| `HashCalculator`     | Chunked (8 MB) SHA-256, cancellable mid-file (shared). |
| `PhotoRecoveryService` | Orchestrates scan → index → classify → route. |
| `PhotoRecoveryTab`   | The Flet UI for selecting folders and running the process. |

All of the above (except the shared/shell helpers) live under
`features/recovery/`.

---

## The Renamer (Photo & Video Renamer tab)

Renames media by **capture date-time** and sorts it into dated subfolders
(`2024/10/…`), turning `IMG_1234.HEIC` into e.g.
`2024/10/2024-10-05_14-30-22.heic`. The flow is deliberately minimal: pick one
**input folder**, choose a pattern, press **Rename all**. Files are **moved in
place** inside that folder, and an **Undo** button reverses the whole run.

### Where the date comes from
`DateResolver` tries sources in order and records which one won:

1. **EXIF** `DateTimeOriginal` — real capture time (photos; HEIC via
   `pillow-heif`). Read by `ExifReader`.
2. **Filename** — dates embedded in names like `IMG_20241005_143022`,
   `PXL_…`, WhatsApp `IMG-20241005-WA0001` (date-only → midnight).
3. **Filesystem** — `st_birthtime` / `st_mtime`, always available as a last
   resort. **Videos** use this path (no video-metadata library in v1).

### The naming pattern
The UI offers a **preset dropdown**, an editable **pattern field**, and a **live
preview**. A pattern is a mix of literal text, date tokens, and `/` (which
creates subfolders). `NameBuilder` translates tokens, formats the date,
substitutes the extras, sanitizes each path component (illegal chars, over-long
names), and lowercases the extension.

| Token | Meaning | | Token | Meaning |
|-------|---------|-|-------|---------|
| `YYYY` / `YY` | year | | `HH` / `hh` | hour 24h / 12h |
| `MM` / `MMM` / `MMMM` | month num / Oct / October | | `mm` `ss` | minute, second |
| `DD` | day | | `{name}` | original filename (stem) |
| `/` | subfolder separator | | `{loc}` | place name (see below) |

Default pattern: `YYYY/MM/YYYY-MM-DD_HH-mm-ss`. If two files map to the same
name, `_1`, `_2`… is appended.

### Location (`{loc}`)
Only computed when the pattern contains `{loc}`. `Geocoder` reads EXIF GPS and
resolves it to the nearest city via `reverse-geocode` — a bundled dataset,
**fully offline**, so coordinates never leave the machine. Files without GPS
(most videos, screenshots) simply drop the segment and the name stays valid.

### Applying & Undo
`RenamerService.run()` scans, resolves each file, computes its destination, and
`shutil.move`s it — skipping files already at their target — while logging
progress and honoring Cancel (same async pattern as recovery). It returns the
list of `RenameOperation(source, target)` moves. `undo_operations()` replays
them in reverse (`target → source`) and prunes emptied folders. Undo is
**session-scoped**: it reverses the most recent run until you run another rename
or close the app.

### Key components

| Component | Responsibility |
|-----------|----------------|
| `DateResolver`   | Capture date-time via EXIF → filename → filesystem. |
| `ExifReader`     | Pillow / pillow-heif: `DateTimeOriginal` and GPS. |
| `Geocoder`       | Offline GPS → place name, with an in-run cache. |
| `NameBuilder`    | Pattern tokens → sanitized folder + filename. |
| `RenamerService` | Orchestrates scan → resolve → build → move. |
| `undo_operations`| Reverses a run and cleans empty folders. |
| `RenamerTab`     | The Flet UI: input folder, pattern, Rename/Undo/Cancel. |

---

## The Duplicates Finder

Finds **byte-identical** files anywhere under one input folder and flags the
redundant copies **in place** — it never deletes or moves anything, so you stay
the final judge. Deliberately two-step:

1. **Scan** (read-only) → finds duplicate groups, fills the log, and writes a
   Markdown report. Touches nothing.
2. Review, then **Rename duplicates** (a separate, explicit click) → applies a
   `_dup_` suffix to the redundant copies.
3. **Undo** reverses the last rename batch (shared `undo_operations`).

### Detection funnel (correct + scalable)
`DuplicateScanner.scan()` narrows candidates in three stages so unique files are
never fully read — important for large libraries:

1. **Group by size** — a unique size can't have a duplicate; dropped unread.
2. **Quick hash** (first 64 KB, `HashCalculator.calculate_partial`) within each
   size group — cheap, eliminates most non-matches.
3. **Full SHA-256** only on files that still collide → confirmed groups.

Groups are sorted by reclaimable space (biggest first). Runs async with progress
logging and Cancel.

### Keeper & the `_dup_` suffix
In each group the **oldest** file (earliest `st_birthtime`/`st_mtime`) is the
**keeper** and is left untouched. Every other copy is renamed:

`b/IMG_5678.jpg` (copy of keeper `a/IMG_1234.jpg`) → `b/IMG_5678_dup_IMG_1234.jpg`

So `{dup-stem}_dup_{keeper-stem}{ext}` (`naming.flagged_name`). Searching `_dup_`
lists every flagged file, and the name says what it duplicates. Files already
containing `_dup_` are skipped, so re-running is idempotent; clashes get `_1`…

### The report
`ReportWriter` saves `_DUPLICATES_REPORT_<date>_<time>.md` in the input folder:
a summary header (files scanned, groups, redundant count, reclaimable space) and
one section per group listing the keeper and each duplicate with its planned new
name. The on-screen log mirrors this but caps at the first 100 groups (the report
always holds all of them).

### Key components

| Component | Responsibility |
|-----------|----------------|
| `DuplicateScanner` | size → quick-hash → full-hash → `DuplicateGroup[]`. |
| `DuplicateGroup`   | A hash-identical set: keeper + duplicates + size. |
| `ReportWriter`     | Renders the Markdown report. |
| `naming`           | `_dup_` suffix + already-flagged detection. |
| `DuplicatesService`| Orchestrates scan (read-only) and rename (explicit). |
| `DuplicatesTab`    | The Flet UI: input folder, Scan/Rename/Undo/Cancel, log. |

---

## Running the app

The project uses [uv](https://docs.astral.sh/uv/) (an `uv.lock` is committed).

```bash
# from the project root
uv sync
uv run python -m photorec.main
```

Or, with a plain virtualenv:

```bash
pip install -e .
python -m photorec.main
```

A `1000×760` desktop window opens with three tabs. Use the **Photo Recovery**
tab, pick the three folders, and press **Process files**. The **Process files**
button stays disabled until all three folders are selected.

---

## UI overview

- **Header** (`app_header.py`) — app title and subtitle.
- **Tabs** (`app_tabs.py`):
  - *Photo Recovery* — working feature.
  - *Photo & Video Renamer* — working feature (rename + date-sort, Undo).
  - *Duplicates Finder* — working feature (scan → report → flag, Undo).
- **Recovery tab** (`recovery_tab.py`) — three folder cards (ORIGINAL /
  RECOVERED / OUTPUT), a move/copy toggle, Process/Cancel buttons, and a
  read-only diagnostics log.
- **Renamer tab** (`renamer_tab.py`) — one INPUT folder card, a preset dropdown +
  pattern field + live preview, and Rename/Undo/Cancel buttons over a log.
- **Duplicates tab** (`duplicates_tab.py`) — one INPUT folder card,
  Scan/Rename/Undo/Cancel buttons, and a large log (the report holds the rest).
- **Folder picker** (`shared/file_picker.py`) — spawns a separate Python process
  that opens a native Tkinter directory dialog (defaulting to `~/Downloads`) and
  returns the chosen path over stdout. Running it out-of-process avoids mixing
  the Tkinter and Flet event loops.

---

## Safety notes

- `DuplicateProcessor` defaults to **copy** mode. A **"Move files instead of
  copying"** toggle in the Photo Recovery tab flips it to move mode; the value is
  threaded UI → `PhotoRecoveryService` → `DuplicateProcessor`. The switch is
  **off** by default (safe copy) and the active mode is printed to the log at the
  start of each run. In copy mode nothing in the source folders is touched.
- Classification is exact-content (SHA-256) — no false "duplicate" from matching
  filenames alone, and full-content hashing means no collision risk in practice.
- The **Renamer moves files in place** (destructive by nature). Its safety net is
  the **Undo** button, which reverses the most recent run. Undo is in-memory /
  session-scoped — it is lost once you start another rename or close the app.
- The **Duplicates Finder never deletes or moves** files. Scanning is read-only;
  flagging only renames redundant copies in place, as an explicit second step,
  and is reversible via Undo (same session-scoped caveat). You decide what to
  actually delete, by hand, after reviewing the report.
- Geocoding is **offline** (`reverse-geocode`); GPS coordinates never leave the
  machine.

---

## Known rough edges / TODO

These are visible in the current source and worth cleaning up:

- `features/recovery/service.py` logs the literal string `"SHIT"` in a `finally`
  block — leftover debug output that should be removed or made meaningful.
- There is no hash caching, so every run re-reads and re-hashes files. A
  persistent cache (keyed by path + size + mtime) would speed up repeated runs.
- `OriginalIndex.build()` ignores the `progress` callback for the hashing phase
  (only the sizing phase reports progress).
- `jpegio` is declared but unused so far.
- `shared/future_tab.py` is now unused (all three tabs are real) — kept for reuse.
- Recovery matches images by **exact pixels**, so re-compressed / resized copies
  of a library photo are still reported as "recovered" (would need perceptual
  matching). Videos remain exact-byte only, so a padded/re-wrapped video won't
  match its library copy.
- Recovery now decodes every library image up front (to build the signature
  index) — reliable, but slower than the old size-only pass on large libraries.
- **Undo** (Renamer + Duplicates) does not survive app restart — no on-disk
  journal yet. Videos are dated from filename/filesystem only (no video-metadata
  library).
```
