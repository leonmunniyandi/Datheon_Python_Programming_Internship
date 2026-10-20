"""Organize files by extension, with a preview, confirmation, and CSV log.

Examples:
    python organizer.py
    python organizer.py "C:\\path\\to\\folder" --dry-run
    python organizer.py "C:\\path\\to\\folder" --recursive --yes
"""

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import stat
import sys
from uuid import uuid4


PROJECT_DIR = Path(__file__).resolve().parent
LOG_NAME = "organizer_log.csv"
LOG_FIELDS = ["run_id", "time_utc", "status", "source", "destination", "message"]
EXTENSIONS = {
    "Documents": {".txt", ".pdf", ".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".csv", ".ppt", ".pptx"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tif", ".tiff", ".ico", ".heic"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".m4v"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"},
    "Code": {".py", ".java", ".c", ".cpp", ".h", ".hpp", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm", ".css", ".json", ".xml", ".sql", ".sh", ".ps1", ".ipynb"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
}
CATEGORIES = set(EXTENSIONS) | {"Other"}
IGNORED_DIRECTORIES = {"__pycache__", "node_modules", "venv"}


@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path


def is_link(path):
    """Also detect Windows junctions/reparse points without following them."""
    info = Path(path).lstat()
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & 0x400)


def validate_folder(folder):
    path = Path(folder).expanduser()
    if is_link(path):
        raise ValueError("Choose a regular folder rather than a link or junction.")
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("The selected path is not a folder.")
    if root in {Path(root.anchor), Path.home().resolve(), PROJECT_DIR}:
        raise ValueError("Choose a specific folder of files, such as Downloads or a test folder.")
    return root


def category_for(path):
    extension = Path(path).suffix.lower()
    for category, extensions in EXTENSIONS.items():
        if extension in extensions:
            return category
    return "Other"


def scan_files(root, recursive=False):
    """Collect files before any moves, skipping links and output folders."""
    files, errors = [], []
    skipped = 0
    pending = [root]
    category_names = {name.casefold() for name in CATEGORIES}
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name.casefold())
        except OSError as error:
            errors.append((directory, str(error)))
            continue
        for entry in entries:
            path = Path(entry.path)
            try:
                attributes = getattr(path.lstat(), "st_file_attributes", 0)
                hidden = entry.name.startswith(".") or bool(attributes & 0x2)
                if (hidden or is_link(path) or entry.name.casefold() == LOG_NAME.casefold()
                        or (directory == root and entry.name.casefold() in category_names)):
                    skipped += 1
                elif entry.is_dir(follow_symlinks=False):
                    if (not recursive or path == PROJECT_DIR
                            or entry.name.casefold() in IGNORED_DIRECTORIES):
                        skipped += 1
                    else:
                        pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(path)
                else:
                    skipped += 1
            except OSError as error:
                errors.append((path, str(error)))
    return files, skipped, errors


def unique_destination(destination, reserved=None):
    """Avoid existing paths (including broken links) and planned collisions."""
    reserved = reserved if reserved is not None else set()
    suffix = "".join(destination.suffixes)
    stem = destination.name[:-len(suffix)] if suffix else destination.name
    candidate = destination
    number = 1
    while os.path.lexists(candidate) or os.path.normcase(str(candidate)) in reserved:
        candidate = destination.with_name(f"{stem} ({number}){suffix}")
        number += 1
    reserved.add(os.path.normcase(str(candidate)))
    return candidate


def plan_moves(files, root):
    reserved = set()
    return [Move(source, unique_destination(root / category_for(source) / source.name, reserved))
            for source in files]


def show_preview(plan, root, skipped, errors):
    print(f"\nSelected folder: {root}")
    print(f"Files to move: {len(plan)} | Skipped entries: {skipped} | Scan errors: {len(errors)}")
    print("-" * 65)
    for move in plan:
        print(f"{move.source.relative_to(root)} -> {move.destination.relative_to(root)}")
    for path, message in errors:
        print(f"SCAN ERROR: {path}: {message}")
    print("-" * 65)


def prepare_category(root, category):
    destination = root / category
    if os.path.lexists(destination) and is_link(destination):
        raise ValueError(f"Category folder {category} is a link or junction.")
    destination.mkdir(exist_ok=True)
    if destination.resolve().parent != root:
        raise ValueError("The category folder resolves outside the selected folder.")
    return destination


def apply_moves(plan, root, scan_errors=()):
    """Move each file independently and append results to the CSV audit log."""
    log_path = root / LOG_NAME
    if os.path.lexists(log_path) and is_link(log_path):
        raise ValueError("The organizer log must not be a link or junction.")
    needs_header = not log_path.exists() or log_path.stat().st_size == 0
    if not needs_header:
        with log_path.open(newline="", encoding="utf-8") as existing:
            if next(csv.reader(existing), None) != LOG_FIELDS:
                raise ValueError(f"Existing {LOG_NAME} has an incompatible header. No files were moved.")

    moved = 0
    failed = len(scan_errors)
    run_id = uuid4().hex
    # Open the log before moving files so an unwritable log stops the run early.
    with log_path.open("a", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        if needs_header:
            writer.writerow(LOG_FIELDS)
            output.flush()

        def log(status, source, destination="", message=""):
            writer.writerow([run_id, datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             status, str(source), str(destination), message])
            output.flush()

        for path, message in scan_errors:
            log("SCAN_ERROR", path, message=message)
        for move in plan:
            destination = move.destination
            try:
                if is_link(move.source) or not move.source.is_file():
                    raise ValueError("Source is no longer a regular file.")
                if not move.source.resolve().is_relative_to(root):
                    raise ValueError("Source resolves outside the selected folder.")
                prepare_category(root, destination.parent.name)
                # Recheck collisions in case a file appeared after the preview.
                if os.path.lexists(destination):
                    destination = unique_destination(destination)
                shutil.move(str(move.source), str(destination))
            except (OSError, shutil.Error, ValueError) as error:
                failed += 1
                print(f"ERROR: {move.source.name}: {error}")
                log("ERROR", move.source, destination, str(error))
            else:
                moved += 1
                print(f"MOVED: {move.source.name} -> {destination.relative_to(root)}")
                log("MOVED", move.source, destination)
    return moved, failed, log_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?", help="Folder to organize; prompted if omitted.")
    parser.add_argument("--recursive", action="store_true", help="Also sort files from subfolders into root categories.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview only; create no folders or logs.")
    mode.add_argument("--yes", action="store_true", help="Apply the plan without asking for confirmation.")
    args = parser.parse_args(argv)
    try:
        folder = args.folder or input("Folder to organize: ").strip().strip('"')
        if not folder:
            print("No folder selected. Nothing was changed.")
            return 0
        root = validate_folder(folder)
        files, skipped, errors = scan_files(root, args.recursive)
        plan = plan_moves(files, root)
        show_preview(plan, root, skipped, errors)
        if not plan:
            print("No eligible files to move.")
            return 1 if errors else 0
        if args.dry_run:
            print("Preview only. No files, folders, or logs were changed.")
            return 1 if errors else 0
        if not args.yes and input("Type YES to move these files: ").strip().upper() != "YES":
            print("Cancelled. Nothing was changed.")
            return 0

        moved, failed, log_path = apply_moves(plan, root, errors)
        print(f"\nSummary: {moved} moved | {skipped} skipped entries | {failed} errors")
        print(f"Log: {log_path}")
        return 1 if failed else 0
    except (EOFError, KeyboardInterrupt):
        print("\nStopped. Check organizer_log.csv and the preview for any changes already made.")
        return 130
    except (OSError, csv.Error, ValueError, shutil.Error) as error:
        print(f"Organizer error: {error}", file=sys.stderr)
        print("Check the folder, permissions, and any log from completed moves.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
