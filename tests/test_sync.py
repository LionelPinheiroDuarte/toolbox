import os

import pytest

from x.commands import sync


@pytest.fixture
def journal(tmp_path, monkeypatch):
    monkeypatch.setattr(sync, "JOURNAL_DIR", str(tmp_path))
    return tmp_path


def _rel(files, root):
    """(local_path, remote_dir) pairs with local paths relative to root."""
    return [(os.path.relpath(path, root), remote_dir) for path, remote_dir in files]


def test_journal_files_covers_dated_notes_tasks_and_topic_notes(journal):
    (journal / "2026-11-09.md").write_text("")
    (journal / "tasks.md").write_text("")
    (journal / "notes").mkdir()
    (journal / "notes" / "pipx-editable.md").write_text("")

    assert _rel(sync._journal_files(), journal) == [
        ("2026-11-09.md", "backups/journal"),
        ("tasks.md", "backups/journal"),
        ("notes/pipx-editable.md", "backups/journal/notes"),
    ]


def test_journal_files_skips_other_files(journal):
    (journal / "draft.txt").write_text("")
    (journal / "random.md").write_text("")
    (journal / "notes").mkdir()
    (journal / "notes" / "image.png").write_text("")

    assert sync._journal_files() == []


def test_journal_files_without_notes_dir(journal):
    (journal / "2026-11-09.md").write_text("")

    assert _rel(sync._journal_files(), journal) == [("2026-11-09.md", "backups/journal")]


def test_journal_files_missing_journal(tmp_path, monkeypatch):
    monkeypatch.setattr(sync, "JOURNAL_DIR", str(tmp_path / "nope"))

    assert sync._journal_files() == []


@pytest.mark.parametrize("remote_dir, expected", [
    ("backups/journal", "/home/u/journal/2026-11-09.md"),
    ("backups/journal/notes", "/home/u/journal/notes/2026-11-09.md"),
])
def test_local_path_mirrors_remote_subfolders(remote_dir, expected):
    assert sync._local_path(
        "backups/journal", "/home/u/journal", remote_dir, "2026-11-09.md"
    ) == expected
