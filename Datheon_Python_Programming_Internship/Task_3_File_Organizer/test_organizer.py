"""Filesystem tests using only temporary files created by this suite."""

import contextlib
import csv
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import organizer as app


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="organizer_test_", dir=app.PROJECT_DIR)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def make_file(self, relative, content="example"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_cli(self, *arguments):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = app.main([str(self.root), *arguments])
        return result, output.getvalue() + errors.getvalue()

    def log_records(self):
        with (self.root / app.LOG_NAME).open(newline="", encoding="utf-8") as log:
            return list(csv.DictReader(log))

    def test_dry_run_changes_nothing(self):
        self.make_file("report.pdf", "keep these bytes")
        self.make_file("sub/photo.JPG", "another file")
        before = {str(path.relative_to(self.root)): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        result, output = self.run_cli("--dry-run", "--recursive")
        after = {str(path.relative_to(self.root)): path.read_bytes()
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(result, 0)
        self.assertIn("Preview only", output)
        self.assertEqual(before, after)
        self.assertFalse((self.root / "Documents").exists())
        self.assertFalse((self.root / app.LOG_NAME).exists())

    def test_declined_confirmation_changes_nothing(self):
        source = self.make_file("report.pdf")
        with patch("builtins.input", return_value="no"):
            result, output = self.run_cli()
        self.assertEqual(result, 0)
        self.assertIn("Cancelled", output)
        self.assertTrue(source.exists())
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_categories_uppercase_and_unknown_extensions(self):
        examples = {
            "report.pdf": "Documents", "photo.JPG": "Images", "clip.mp4": "Videos",
            "backup.tar.gz": "Archives", "main.py": "Code", "sound.mp3": "Audio",
            "mystery.xyz": "Other", "LICENSE": "Other",
        }
        for name in examples:
            self.make_file(name, name)
        result, _ = self.run_cli("--yes")
        self.assertEqual(result, 0)
        for name, category in examples.items():
            self.assertFalse((self.root / name).exists())
            self.assertEqual((self.root / category / name).read_text(encoding="utf-8"), name)
        self.assertEqual(len(self.log_records()), len(examples))
        self.assertTrue(all(row["status"] == "MOVED" for row in self.log_records()))

    def test_existing_names_are_preserved_and_compound_suffixes_retained(self):
        self.make_file("Archives/backup.tar.gz", "old")
        self.make_file("Archives/backup (1).tar.gz", "also old")
        self.make_file("backup.tar.gz", "new")
        result, _ = self.run_cli("--yes")
        self.assertEqual(result, 0)
        self.assertEqual((self.root / "Archives/backup.tar.gz").read_text(), "old")
        self.assertEqual((self.root / "Archives/backup (1).tar.gz").read_text(), "also old")
        self.assertEqual((self.root / "Archives/backup (2).tar.gz").read_text(), "new")

    def test_recursive_duplicate_names_are_both_kept(self):
        self.make_file("one/report.pdf", "one")
        self.make_file("two/report.pdf", "two")
        self.make_file("Documents/existing.pdf", "already organized")
        result, _ = self.run_cli("--recursive", "--yes")
        self.assertEqual(result, 0)
        moved_contents = {(self.root / "Documents/report.pdf").read_text(),
                          (self.root / "Documents/report (1).pdf").read_text()}
        self.assertEqual(moved_contents, {"one", "two"})
        self.assertEqual((self.root / "Documents/existing.pdf").read_text(), "already organized")
        self.assertTrue((self.root / "one").is_dir())
        self.assertTrue((self.root / "two").is_dir())

    def test_default_skips_subfolders_and_repeated_runs_are_stable(self):
        self.make_file("nested/report.pdf", "nested")
        self.make_file("main.py", "code")
        self.run_cli("--yes")
        first_log = (self.root / app.LOG_NAME).read_bytes()
        result, output = self.run_cli("--yes")
        self.assertEqual(result, 0)
        self.assertIn("No eligible files", output)
        self.assertEqual((self.root / app.LOG_NAME).read_bytes(), first_log)
        self.assertTrue((self.root / "nested/report.pdf").exists())
        self.assertTrue((self.root / "Code/main.py").exists())

    def test_permission_error_is_logged_and_other_files_continue(self):
        blocked = self.make_file("blocked.txt", "blocked")
        self.make_file("okay.jpg", "okay")
        real_move = shutil.move

        def move_with_denied_file(source, destination):
            if Path(source) == blocked:
                raise PermissionError("File is locked for this test")
            return real_move(source, destination)

        with patch.object(app.shutil, "move", side_effect=move_with_denied_file):
            result, output = self.run_cli("--yes")
        self.assertEqual(result, 1)
        self.assertIn("1 moved", output)
        self.assertTrue(blocked.exists())
        self.assertEqual((self.root / "Images/okay.jpg").read_text(), "okay")
        self.assertEqual({row["status"] for row in self.log_records()}, {"ERROR", "MOVED"})

    def test_file_occupying_category_is_not_overwritten(self):
        self.make_file("Documents", "keep this original file")
        self.make_file("report.pdf", "report")
        result, _ = self.run_cli("--yes")
        self.assertEqual(result, 1)
        self.assertEqual((self.root / "Documents").read_text(), "keep this original file")
        self.assertTrue((self.root / "report.pdf").exists())
        self.assertEqual(self.log_records()[0]["status"], "ERROR")

    def test_incompatible_log_blocks_moves(self):
        source = self.make_file("report.pdf")
        self.make_file(app.LOG_NAME, "unexpected,header\noriginal,data\n")
        result, output = self.run_cli("--yes")
        self.assertEqual(result, 1)
        self.assertIn("incompatible", output)
        self.assertTrue(source.exists())
        self.assertFalse((self.root / "Documents").exists())
        self.assertEqual((self.root / app.LOG_NAME).read_text(), "unexpected,header\noriginal,data\n")

    def test_hidden_entries_and_links_are_skipped(self):
        self.make_file(".private.txt", "private")
        link_like = self.make_file("shortcut.txt", "mocked link")
        self.make_file("node_modules/package/code.js", "dependency")
        self.make_file("report.txt", "report")
        real_is_link = app.is_link
        with patch.object(app, "is_link", side_effect=lambda path: Path(path) == link_like or real_is_link(path)):
            result, _ = self.run_cli("--recursive", "--yes")
        self.assertEqual(result, 0)
        self.assertTrue(link_like.exists())
        self.assertTrue((self.root / ".private.txt").exists())
        self.assertTrue((self.root / "node_modules/package/code.js").exists())
        self.assertTrue((self.root / "Documents/report.txt").exists())

    def test_later_runs_append_new_run_ids(self):
        self.make_file("first.txt")
        self.run_cli("--yes")
        self.make_file("second.txt")
        self.run_cli("--yes")
        rows = self.log_records()
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["run_id"], rows[1]["run_id"])
        self.assertEqual({Path(row["destination"]).name for row in rows}, {"first.txt", "second.txt"})

    def test_missing_path_file_and_program_folder_are_rejected(self):
        with self.assertRaises(OSError):
            app.validate_folder(self.root / "missing")
        source = self.make_file("ordinary.txt")
        with self.assertRaises(ValueError):
            app.validate_folder(source)
        with self.assertRaises(ValueError):
            app.validate_folder(app.PROJECT_DIR)
        with self.assertRaises(ValueError):
            app.validate_folder(Path(self.root.anchor))


if __name__ == "__main__":
    unittest.main()
