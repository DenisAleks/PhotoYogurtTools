# Running DddPhotoRec on Windows (VS Code)

Start-to-finish setup for running the app from source on a Windows PC, after
cloning the repo. The project uses [uv](https://docs.astral.sh/uv/) (there's a
`uv.lock` in the repo), which is the smoothest route — it installs Python and all
dependencies for you.

---

## Prerequisites (install once)

1. **VS Code** + the **Python extension** (Microsoft).
   VS Code → Extensions (`Ctrl+Shift+X`) → search "Python" → Install.

2. **uv** — open **PowerShell** and run:

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   Then **close and reopen** PowerShell / VS Code so `uv` is on your PATH.

---

## Steps

### 1. Open the project
VS Code → File → Open Folder → select the cloned `DddPhotoRec` folder (the one
that contains `pyproject.toml`).

### 2. Open the terminal
Terminal → New Terminal (`` Ctrl+` ``). Confirm the prompt is in the project
root (you should see the `DddPhotoRec` folder name).

### 3. Install the environment
```powershell
uv sync
```
This downloads Python 3.10+ if needed, creates a `.venv` folder, and installs all
dependencies (Flet, Pillow, pillow-heif, reverse-geocode, …). The first run takes
a couple of minutes (scipy/numpy are ~25 MB).

### 4. Select the interpreter
`Ctrl+Shift+P` → **Python: Select Interpreter** → choose the one inside `.venv`
(shown as `.venv\Scripts\python.exe`). This makes the Run button and IntelliSense
use the right environment.

### 5. Run the app
```powershell
uv run python -m photorec.main
```
The "Photo Recovery Toolkit" window opens with the three tabs.

---

## Everyday running

After the one-time setup, pick whichever you like:

- **Terminal:** `uv run python -m photorec.main`
- **F5 / Run button:** with the `.venv` interpreter selected (step 4), press `F5`.
  A `.vscode/launch.json` is included, so this runs the app directly — you don't
  need to open `main.py` first.
- **Live reload while editing UI:**
  ```powershell
  uv run flet run src/photorec/main.py
  ```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `uv` is not recognized | You didn't reopen the terminal after installing uv. Close VS Code fully and reopen. |
| "Select folder" button does nothing | The dialog uses Python's `tkinter`. uv's Python includes it — so `uv sync` covers it. **Avoid the Microsoft Store Python**, which omits tkinter; let uv manage Python instead. |
| First HEIC / GPS photo errors | Make sure `uv sync` finished cleanly — `pillow-heif` (HEIC) and `reverse-geocode` (offline location) come from it. Nothing is downloaded at runtime; the city database is bundled. |
| Imports show as unresolved in VS Code | Redo step 4 (Select Interpreter → `.venv`). |
| Want to start clean | Delete the `.venv` folder and run `uv sync` again. |

---

## Notes

- **Nothing is deleted** by any tool. Recovery copies by default; the Renamer and
  Duplicates Finder rename/move in place and each offer an **Undo** button.
- Running **from source** (this guide) is different from building a standalone
  `.exe`. Packaging must be done **on Windows** (you can't cross-build from a Mac)
  and needs extra setup for the bundled data — ask before doing that.
