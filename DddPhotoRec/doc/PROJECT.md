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
[The Renamer](#the-renamer-photo--video-renamer-tab)) and finds duplicates.

> 🇷🇺 На русском: [PROJECT.ru.md](PROJECT.ru.md). New to the app? Jump to
> [How to use each tab](#how-to-use-each-tab-plain-guide).

---

## Status

- **Version:** 0.1.0 (early / work-in-progress)
- **Python:** >= 3.10 (`@dataclass(slots=True)` is used across the code)
- Tabs:
  - **Photo Recovery** — functional.
  - **Photo & Video Renamer** — functional (v1: rename + date-sort in place, with Undo).
  - **Duplicates Finder** — functional (scan → report → flag in place, with Undo).
  - **Photo Compressor** — functional (shrink to a target size into OUTPUT; convert
    HEIC/HEIF/PNG → JPEG; originals untouched, videos skipped).
- Recovery **copies** files by default; a UI toggle switches it to move mode.
  The Renamer **moves** files in place and offers an **Undo** button as its
  safety net (see [Safety notes](#safety-notes)).

---

## How to use each tab (plain guide)

The app has four tools, one per tab. **Nothing here ever deletes your files** —
the worst case is a copy or a rename you can undo. Every tab has a **log panel**
at the bottom that shows what is happening while it works.

### 📸 Tab 1 — Photo Recovery

**What it's for.** After you rescue photos from a broken or formatted disk (with
a tool like PhotoRec), you get one big messy folder. Many of those photos you
*already have* in your normal library. This tab sorts the recovered photos into
"already have it" vs "genuinely new".

**You choose three folders:**
- **ORIGINAL** — your existing, tidy photo library (what you already own).
- **RECOVERED** — the messy folder the recovery tool produced.
- **OUTPUT** — an empty folder where the sorted results are written.

**Steps:**
1. Click each *Select … folder* button and pick the folder.
2. *(Optional)* turn on **"Move files instead of copying"** to move recovered
   files instead of copying them. Off (the default) is safe — it only copies.
3. Click **Process files** and watch the log.

**What you get in OUTPUT:**
- `duplicates/…` — recovered photos you already had in your library.
- `recovered/…` — genuinely new photos worth keeping.

**Good to know.** Photos are matched by their **actual image**, not the raw file,
so a recovered copy still matches even if the recovery tool padded it or stripped
its date info.

### 🗂️ Tab 2 — Photo & Video Renamer

**What it's for.** Turns messy names like `IMG_1234.HEIC` into clean, date-based
names and sorts them into year/month folders — e.g.
`2024/10/2024-10-05_14-30-22.heic`.

**Steps:**
1. Click **Select INPUT folder** — the folder of photos/videos to tidy.
2. Pick a **naming pattern** from the dropdown, or type your own. The
   **Example** line shows exactly how a file will be named.
3. Click **Rename all**.
4. Not happy? Click **Undo last rename**.

**Where the date comes from.** The photo's real capture date (from its metadata),
or a date found in the filename, or the file's own date — in that order.

**Optional place name.** If your pattern includes `{loc}`, the city where a photo
was taken is added to the name (read from the photo's GPS, **fully offline**).
Photos without GPS just leave it out.

**Good to know.** Files are **moved** into the new date folders inside the same
folder. Undo puts them back (until you close the app).

### 🔍 Tab 3 — Duplicates Finder

**What it's for.** Finds duplicate photos/videos **inside one folder** (and its
subfolders) — the same picture saved several times. Nothing is deleted; you
decide what to remove.

**Steps:**
1. Click **Select INPUT folder**.
2. Click **Scan for duplicates** — this only *looks*, it changes nothing. It
   writes a `.md` report into the folder and lists the duplicate groups in the log.
3. Then choose one action:
   - **Move to DUP folder** *(recommended)* — moves the extra copies into a
     `DUP/` folder that mirrors your folder structure, so you can browse, compare,
     and delete them together.
   - **Rename in place** — adds a `DUP_` prefix to the extra copies so you can
     spot and search them.
4. **Undo** reverses the last action.

**Which copy is kept?** The **oldest** file in each group is left untouched; the
newer copies are the ones flagged or moved.

**Good to know.** Photos are compared by their **actual image**, so exact copies
are caught even when their file sizes differ slightly (padding, edited metadata).

### 🗜️ Tab 4 — Photo Compressor

**What it's for.** Makes large photos smaller **without changing their
resolution** and (optionally) converts HEIC/HEIF/PNG to JPEG so they open
everywhere (e.g. Windows). Compressed copies go into a separate OUTPUT folder;
your originals are never changed.

**Steps:**
1. Click **Select INPUT folder** and **Select OUTPUT folder**.
2. Choose the **Target max size** (default 2 MB).
3. Leave **"Convert HEIC / HEIF / PNG to JPEG"** on (recommended for Windows) or
   turn it off to keep original formats.
4. *(Optional)* turn on **"Compress in place"** to replace files inside the INPUT
   folder instead of writing to OUTPUT — originals are safely moved to a
   `_Backup/` folder, and any videos are moved to a `_Video/` folder (never
   compressed). With this on, OUTPUT isn't needed.
5. Click **Compress**. A progress bar and the log show what's happening.

**How the size target works.** For each photo the app picks the **highest JPEG
quality that still fits your target** (so it stays under, e.g., 2 MB) — it does
not just drop quality blindly. It never enlarges a file beyond its original size,
and never shrinks the picture's resolution. If a very large photo can't reach the
target without going below a safe quality floor, it's kept at the best quality it
can and noted in the log.

**Good to know.** Capture date, GPS, and orientation are preserved. **Videos are
skipped** entirely. HEIC is already efficient, so converting it to JPEG is mainly
for compatibility — the big space savings come from large JPEGs and PNGs.

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
| Declared deps  | `flet[all]`, `pillow`, `pillow-heif`, `reverse-geocode` |

> `pillow` / `pillow-heif` read capture date-time and GPS from photos;
> `reverse-geocode` turns GPS into a place name **offline** (coordinates never
> leave the machine). Pillow also drives the Photo Compressor (JPEG re-encoding).

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
│   ├── PROJECT.md            # this document
│   ├── PROJECT.ru.md         # Russian translation of this document
│   └── RUN_ON_WINDOWS.md     # step-by-step Windows + VS Code setup
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
    │   ├── file_picker.py    # native folder dialog via Tkinter subprocess
    │   ├── media_scanner.py  # MediaScanner + image/video extension sets
    │   ├── hash_calculator.py# HashCalculator: full + partial SHA-256
    │   ├── image_signature.py# decode image → pixel hash (+ dimensions)
    │   └── rename_ops.py     # RenameOperation + undo_operations()
    │
    └── features/
        ├── recovery/         # ← the Photo Recovery tab, in one folder
        │   ├── recovery_tab.py       # the tab's Flet UI
        │   ├── service.py            # PhotoRecoveryService: orchestrates a run
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
        ├── duplicates/       # ← the Duplicates Finder tab
        │   ├── duplicates_tab.py     # UI: Scan / Move / Rename / Undo, log
        │   ├── service.py            # DuplicatesService: scan (read-only) + rename
        │   ├── duplicate_scanner.py  # images by pixels, videos by byte funnel
        │   ├── report_writer.py      # the Markdown report
        │   ├── naming.py             # DUP_ prefix, DUP/ folder, flag detection
        │   └── models.py             # DuplicateGroup
        │
        └── compressor/       # ← the Photo Compressor tab
            ├── compressor_tab.py     # UI: INPUT/OUTPUT, convert toggle, target
            ├── service.py            # CompressorService: per-image → OUTPUT
            └── encoder.py            # JPEG re-encode to a size target (keeps EXIF)
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

Finds duplicate files anywhere under one input folder and flags the redundant
copies — it never deletes anything, so you stay the final judge. Deliberately
two-step:

1. **Scan** (read-only) → finds duplicate groups, fills the log, and writes a
   Markdown report. Touches nothing.
2. Review, then pick one of two explicit actions:
   - **Move to DUP folder** (recommended) → relocates each duplicate to
     `DUP/<same relative path>`, so all copies collect in one browsable tree that
     mirrors the original structure (the keeper sits at the matching path outside
     `DUP/`). The `DUP/` folder is skipped on future scans, so it's idempotent.
   - **Rename in place** → prepends a `DUP_` prefix to each duplicate.
3. **Undo** reverses the last action (shared `undo_operations`, works for both).

### How matches are decided
`DuplicateScanner.scan()` splits files by type and uses the same content logic as
the Recovery tab, so copies that differ only in padding or EXIF still group:

- **Images → decoded pixel content.** A cheap **dimensions** pass
  (`read_dimensions`, no decode) buckets candidates first; only same-dimension
  groups are decoded and **pixel-hashed** (`image_signature`). Two images match
  when their pixels are identical, regardless of byte differences.
- **Videos → exact bytes**, via a size → quick-hash (64 KB) → full-SHA-256 funnel
  so unique videos are never fully read.

Groups are sorted by reclaimable space (biggest first, summed from each
duplicate's actual byte size). Runs async with progress logging and Cancel.

### Keeper & flagging
In each group the **oldest** file (earliest `st_birthtime`/`st_mtime`) is the
**keeper** and is left untouched; the other copies are flagged. The `DUP_` prefix
(`naming.flagged_name`) is used rather than an infix marker because Finder/Explorer
truncate long names in the middle (`start…end.ext`), which would hide an infix —
a prefix stays visible. Files already prefixed `DUP_`, and anything already inside
the `DUP/` folder, are skipped, so both actions are idempotent; name clashes get
`_1`, `_2`…

### The report
`ReportWriter` saves `_DUPLICATES_REPORT_<date>_<time>.md` in the input folder:
a summary header (files scanned, groups, redundant count, reclaimable space) and
one section per group listing the keeper and each duplicate path. The on-screen
log mirrors this but caps at the first 100 groups (the report always holds all).

### Key components

| Component | Responsibility |
|-----------|----------------|
| `DuplicateScanner` | images by pixel content, videos by byte funnel → `DuplicateGroup[]`. |
| `DuplicateGroup`   | A content-identical set: keeper + duplicates; reclaimable size. |
| `ReportWriter`     | Renders the Markdown report. |
| `naming`           | `DUP_` prefix, `DUP/` folder name, already-flagged detection. |
| `DuplicatesService`| Scan (read-only), rename-in-place, and move-to-`DUP/` (all explicit). |
| `DuplicatesTab`    | The Flet UI: input folder, Scan / Move / Rename / Undo / Cancel, log. |

---

## The Photo Compressor

Shrinks large photos without changing resolution, and optionally converts
HEIC/HEIF/PNG to JPEG. Two modes:

- **OUTPUT mode** (default): compressed copies go to an OUTPUT folder (mirroring
  the input structure); **originals are never modified and videos are skipped.**
- **In-place mode**: files are replaced inside the INPUT folder. Each original is
  first moved to `_Backup/<relative path>` (the safety net), and **videos are
  moved to `_Video/`** (never compressed). Both `_Backup/` and `_Video/` are
  skipped on re-runs, so it's idempotent. OUTPUT is ignored.

### Fitting a size target
`encoder.encode_jpeg_to_target()` re-encodes an image to JPEG and finds the
**highest quality that fits the byte budget**: it tries qualities from 92 down a
fixed ladder to a floor of 70 and returns the first that fits. If even the floor
is over budget, it returns the floor result (best effort) — quality never drops
below the floor, so the image is never wrecked to hit a number. It bakes EXIF
orientation into the pixels and preserves the rest of EXIF (date, GPS — the nested
IFDs are force-loaded so they survive re-serialization) plus the ICC profile.
Alpha is flattened onto white (JPEG has no transparency).

### Per-file decision (`CompressorService`)
For each image (`MediaScanner` → `is_image`; videos are dropped):

- **HEIC / HEIF / PNG** with the convert option on → re-encoded to **JPEG**.
- **JPEG over the target** → recompressed (kept only if actually smaller).
- **Anything already small enough and not being converted** → copied unchanged.

The encode budget is `min(target, original size)`, so a file is **never enlarged**
beyond its original (and never beyond the global target). Output is written to
`OUTPUT/<relative path>` with a `.jpg` extension when converted; name clashes get
`_1`, `_2`. The run is async with progress + Cancel and logs total bytes saved.

> Note on HEIC → JPEG: HEIC is already an efficient (HEVC) format, so converting
> it to JPEG is mainly for **compatibility** (e.g. viewing on Windows). At the
> same visual quality JPEG is larger, which is why the size target drives the
> quality rather than a fixed quality driving the size.

### Nested folders (in-place mode)
`MediaScanner` walks the input folder **recursively at any depth**, so the whole
tree is handled in one pass. In in-place mode, `_Backup/` and `_Video/` are
created once at the **root** of the input folder and **mirror each file's original
path**, so you can always tell where something came from:

| File type | What happens | Where |
|-----------|--------------|-------|
| **Photo** (jpg/png/heic/heif…) | compressed / converted **in place** | stays in its subfolder; original → `_Backup/<same path>` |
| **Video** (mp4/mov…) | moved, never compressed | `_Video/<same path>` |
| **Other files** (txt, pdf…) | **left untouched** | stay where they are |

Example — before:

```
A/
├── vacation/
│   ├── IMG_1.heic
│   ├── clip1.mp4
│   └── beach/
│       ├── IMG_2.jpg      (large)
│       └── clip2.mov
├── notes.txt
└── photo3.png
```

after in-place compression:

```
A/
├── vacation/
│   ├── IMG_1.jpg          ← converted in place
│   └── beach/
│       └── IMG_2.jpg      ← recompressed in place
├── notes.txt             ← untouched (not media)
├── photo3.jpg            ← png converted in place
├── _Backup/              ← originals, structure mirrored
│   ├── vacation/IMG_1.heic
│   ├── vacation/beach/IMG_2.jpg
│   └── photo3.png
└── _Video/               ← videos, structure mirrored
    └── vacation/
        ├── clip1.mp4
        └── beach/clip2.mov
```

Notes: non-media files are never touched; a small photo that isn't being
converted stays as-is (no backup); emptied folders are **not** removed (a
subfolder that held only a video becomes empty after the move); re-runs are safe
(`_Backup/`/`_Video/` are skipped); don't name your own folders `_Backup` or
`_Video`, as those are treated as the app's and skipped while scanning.

### Key components

| Component | Responsibility |
|-----------|----------------|
| `encode_jpeg_to_target` | Re-encode to JPEG at the best quality that fits a byte budget; keep EXIF/ICC. |
| `CompressorService` | Decide per file (convert / recompress / copy), write to OUTPUT, skip video. |
| `CompressorTab`     | The Flet UI: INPUT/OUTPUT, convert toggle, target-size dropdown, Compress/Cancel. |

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

A desktop window opens with four tabs. For recovery, use the **Photo Recovery**
tab, pick the three folders, and press **Process files** (the button stays
disabled until all three folders are selected).

---

## UI overview

- **Header** (`app_header.py`) — app title and subtitle.
- **Tabs** (`app_tabs.py`):
  - *Photo Recovery* — working feature.
  - *Photo & Video Renamer* — working feature (rename + date-sort, Undo).
  - *Duplicates Finder* — working feature (scan → report → flag, Undo).
  - *Photo Compressor* — working feature (shrink to target, convert to JPEG).
- **Recovery tab** (`recovery_tab.py`) — three folder cards (ORIGINAL /
  RECOVERED / OUTPUT), a move/copy toggle, Process/Cancel buttons, and a
  read-only diagnostics log.
- **Renamer tab** (`renamer_tab.py`) — one INPUT folder card, a preset dropdown +
  pattern field + live preview, and Rename/Undo/Cancel buttons over a log.
- **Duplicates tab** (`duplicates_tab.py`) — one INPUT folder card, and
  Scan / Move to DUP folder / Rename in place / Undo / Cancel buttons over a
  large log (the report holds the rest).
- **Compressor tab** (`compressor_tab.py`) — INPUT/OUTPUT folder cards, a
  target-size dropdown, "convert to JPEG" and "compress in place" toggles,
  Compress/Cancel, and a log.

All long-running tabs also show a **progress bar** (driven by a `progress(done,
total)` callback the services report; the bar hides when idle).
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

- There is no hash/signature caching, so every run re-reads and re-hashes files.
  A persistent cache (keyed by path + size + mtime) would speed up repeated runs.
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
