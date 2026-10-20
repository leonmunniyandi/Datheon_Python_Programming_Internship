# Automated File Organizer & Cleanup Utility

A Python console utility that organizes files by extension into category
folders. Built for Task 3 using the supplied `shutil.html` documentation.

## Features

- Preview the source and destination of every planned move.
- Confirm before moving, or use `--yes` for unattended runs.
- Create category folders only when needed.
- Keep both files when names collide, using names such as `report (1).pdf`.
- Handle permission errors and naming conflicts per file and continue.
- Print moved/skipped/error counts and append actions to `organizer_log.csv`.
- Optionally organize files from a directory tree with `--recursive`.

## Requirements

Python 3.9 or later. Only standard-library modules are used; no packages need
to be installed. `shutil.html` is a reference document, not a runtime input.

## Run

Open a terminal in this project's folder:

```bash
python organizer.py
```

Enter the path to the folder you want to organize. Review the preview, then
type `YES` to move the listed files. Any other answer cancels the operation.
The program rejects a drive root, your whole home folder, and its own project
folder; select a specific folder of files instead.

You can also provide the folder directly:

```bash
python organizer.py "C:\Users\YourName\Downloads"
```

## Preview without changes

```bash
python organizer.py "C:\path\to\test-folder" --dry-run
```

Dry runs create no category folders or logs. Start with a small test folder
to see how the categories work.

## Sort subfolders too

```bash
python organizer.py "C:\path\to\test-folder" --recursive
```

Recursive mode moves files from eligible subfolders into the category folders
at the selected root. Original subfolders are left in place, even if empty.
The default mode processes top-level files only.

For unattended execution:

```bash
python organizer.py "C:\path\to\test-folder" --recursive --yes
```

## Categories

| Folder | Example extensions |
| --- | --- |
| Documents | `.txt`, `.pdf`, `.docx`, `.xlsx`, `.csv`, `.pptx` |
| Images | `.jpg`, `.png`, `.gif`, `.svg`, `.webp` |
| Videos | `.mp4`, `.mkv`, `.mov`, `.avi` |
| Archives | `.zip`, `.rar`, `.7z`, `.tar`, `.gz` |
| Code | `.py`, `.java`, `.cpp`, `.html`, `.css`, `.js`, `.json` |
| Audio | `.mp3`, `.wav`, `.flac`, `.m4a` |
| Other | Unrecognized extensions and files without extensions |

Extensions are matched without regard to case. Edit `EXTENSIONS` in
`organizer.py` to customize the mappings.

Existing root category entries, hidden entries, links/junctions/reparse points,
the program's own folder, `node_modules`, `venv`, and `__pycache__` are skipped.
Skipped directories count as one entry, rather than counting their contents.
The organizer log is also excluded from sorting.

## Logging and file behavior

`organizer_log.csv` is saved inside the folder being organized. Each record
contains a run ID, UTC time, status, original path, destination, and error
message where applicable. Previous records are preserved when the CSV header
is compatible. An incompatible or unwritable log stops the operation before
moving files.

Source files are moved with `shutil.move`. No duplicate files or empty folders
are deleted as a cleanup step. A move across filesystems can copy and then
remove its source; metadata preservation depends on the operating system.
There is no automatic undo, but the log records each completed move's paths.

## Tests

```bash
python -m unittest -v
```

Tests create their own temporary fixtures. They do not organize Downloads or
any other existing folder of user files.

## Files

- `organizer.py`: main program.
- `test_organizer.py`: file-move and preview tests.
- `README.md`: instructions and category rules.
- `shutil.html`: supplied Python documentation, preserved as provided.
- `.gitignore`: excludes local Python environments, caches, and generated logs.
