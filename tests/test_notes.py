import os
import re
from datetime import date

import pytest

from x.commands.notes import browse, store

TOPIC = """# pipx Stale Install

**Date:** 2026-07-04 | **Project:** toolbox | **Tags:** pipx, python

## Context
Some text.
"""
DAILY = """# Daily Report — Saturday, July 4, 2026

## Summary
Full debugging session around the toolbox CLI.
"""


@pytest.fixture
def journal(tmp_path):
    (tmp_path / "notes").mkdir()
    return tmp_path


def _write(path, text, mtime=None):
    path.write_text(text)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def _plain(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# --- headers --------------------------------------------------------------

def test_read_header_of_a_journal_agent_note(journal):
    path = _write(journal / "notes" / "pipx.md", TOPIC)

    assert store.read_header(path) == ("pipx Stale Install", "toolbox", "pipx, python", "Some text.")


def test_read_header_without_metadata(journal):
    path = _write(journal / "notes" / "bare.md", "# Just a title\n\nBody.\n")

    assert store.read_header(path) == ("Just a title", "", "", "Body.")


def test_read_header_of_an_empty_note(journal):
    path = _write(journal / "notes" / "empty.md", "")

    assert store.read_header(path) == ("", "", "", "")


# --- listing --------------------------------------------------------------

def test_list_notes_groups_and_order(journal):
    _write(journal / "2026-04-09.md", DAILY)
    _write(journal / "2026-07-04.md", DAILY)
    _write(journal / "notes" / "old.md", "# Old\n", mtime=1_000)
    _write(journal / "notes" / "new.md", "# New\n", mtime=2_000)
    _write(journal / "random.md", "# Not a journal note\n")

    notes = store.list_notes(str(journal))

    assert [(n.kind, os.path.basename(n.path)) for n in notes] == [
        ("tasks", "tasks.md"),
        ("dated", "2026-07-04.md"),
        ("dated", "2026-04-09.md"),
        ("topic", "new.md"),
        ("topic", "old.md"),
    ]


def test_list_notes_shows_tasks_before_it_exists(journal):
    tasks = store.list_notes(str(journal))[0]

    assert tasks.kind == "tasks" and tasks.mtime == 0.0


def test_dated_note_title_is_its_summary_not_the_date(journal):
    _write(journal / "2026-07-04.md", DAILY)

    dated = store.list_notes(str(journal))[1]

    assert dated.title == "Full debugging session around the toolbox CLI."
    assert dated.day == date(2026, 7, 4)


def test_topic_note_without_title_falls_back_to_its_name(journal):
    _write(journal / "notes" / "scratch.md", "")

    assert store.list_notes(str(journal))[-1].title == "scratch"


def test_list_notes_of_a_missing_journal(tmp_path):
    assert [n.kind for n in store.list_notes(str(tmp_path / "nope"))] == ["tasks"]


# --- creating -------------------------------------------------------------

@pytest.mark.parametrize("text, slug", [
    ("Docker buildx cache!", "docker-buildx-cache"),
    ("  k8s: probes / liveness  ", "k8s-probes-liveness"),
    ("Déploiement été", "déploiement-été"),
    ("???", ""),
])
def test_slugify(text, slug):
    assert store.slugify(text) == slug


def test_new_note_with_a_query_is_a_topic_note_with_a_header(journal):
    path = store.new_note("Docker buildx cache", str(journal), date(2026, 11, 9))

    assert path == str(journal / "notes" / "docker-buildx-cache.md")
    assert open(path).read() == (
        "# Docker buildx cache\n\n**Date:** 2026-11-09 | **Project:** | **Tags:**\n\n"
    )


def test_new_note_header_reads_back(journal):
    path = store.new_note("Docker buildx cache", str(journal), date(2026, 11, 9))

    assert store.read_header(path)[:3] == ("Docker buildx cache", "", "")


@pytest.mark.parametrize("query", ["", "   ", "???"])
def test_new_note_without_a_usable_query_is_today(journal, query):
    path = store.new_note(query, str(journal), date(2026, 11, 9))

    assert path == str(journal / "2026-11-09.md")


def test_new_note_never_overwrites(journal):
    existing = _write(journal / "notes" / "docker-buildx-cache.md", "keep me\n")
    _write(journal / "2026-11-09.md", "today, already written\n")

    assert store.new_note("Docker buildx cache", str(journal)) == str(existing)
    store.new_note("", str(journal), date(2026, 11, 9))

    assert existing.read_text() == "keep me\n"
    assert (journal / "2026-11-09.md").read_text() == "today, already written\n"


def test_new_note_creates_the_notes_folder(tmp_path):
    path = store.new_note("first", str(tmp_path))

    assert os.path.isfile(path)


def test_ensure_tasks_creates_it_empty_and_keeps_it_after(journal):
    path = store.ensure_tasks(str(journal))
    assert open(path).read() == ""

    _write(journal / "tasks.md", "- [ ] something\n")
    store.ensure_tasks(str(journal))
    assert (journal / "tasks.md").read_text() == "- [ ] something\n"


# --- trashing -------------------------------------------------------------

@pytest.fixture
def gio(monkeypatch):
    """Record gio calls instead of trashing for real."""
    calls = []
    monkeypatch.setattr(store.shutil, "which", lambda name: "/usr/bin/gio")
    return calls, lambda argv, **kw: calls.append(argv)


def test_trash_sends_the_note_to_gio(journal, gio):
    calls, run = gio
    note = _write(journal / "notes" / "old.md", "# Old\n")

    store.trash(str(note), str(journal), run=run)

    assert calls == [["gio", "trash", str(note)]]


def test_trash_refuses_the_task_file(journal, gio):
    calls, run = gio
    tasks = _write(journal / "tasks.md", "")

    with pytest.raises(store.TrashRefused):
        store.trash(str(tasks), str(journal), run=run)
    assert calls == []


def test_trash_refuses_anything_outside_the_journal(tmp_path, gio):
    calls, run = gio
    (tmp_path / "journal").mkdir()
    outside = _write(tmp_path / "elsewhere.md", "")

    with pytest.raises(store.TrashRefused):
        store.trash(str(outside), str(tmp_path / "journal"), run=run)
    with pytest.raises(store.TrashRefused):  # and the way out through ..
        store.trash(str(tmp_path / "journal" / ".." / "elsewhere.md"),
                    str(tmp_path / "journal"), run=run)
    assert calls == []


def test_trash_refuses_a_missing_note(journal, gio):
    calls, run = gio

    with pytest.raises(store.TrashRefused):
        store.trash(str(journal / "notes" / "gone.md"), str(journal), run=run)
    assert calls == []


def test_trash_without_gio_deletes_nothing(journal, monkeypatch):
    note = _write(journal / "notes" / "old.md", "")
    monkeypatch.setattr(store.shutil, "which", lambda name: None)

    with pytest.raises(store.TrashRefused):
        store.trash(str(note), str(journal), run=lambda *a, **kw: pytest.fail("ran gio"))
    assert note.exists()


# --- the fzf list ---------------------------------------------------------

def test_entries_have_three_headers_and_four_fields(journal):
    _write(journal / "2026-07-04.md", DAILY)
    _write(journal / "notes" / "pipx.md", TOPIC)

    lines = browse.entries(str(journal), width=60)

    headers = [l for l in lines if l.split("\t")[2] == ""]
    assert [_plain(l.split("\t")[0]) for l in headers] == ["TÂCHES", "JOURNAL", "NOTES"]
    assert all(len(l.split("\t")) == 4 for l in lines)
    assert [l.split("\t")[3] for l in lines if l.split("\t")[2]] == ["tasks", "dated", "topic"]


def test_entries_keep_full_tags_searchable_when_the_row_is_cut(journal):
    _write(journal / "notes" / "pipx.md", TOPIC.replace("pipx, python", "pipx, python, playbook"))

    line = browse.entries(str(journal), width=30)[-1]

    visible = _plain(line.split("\t")[1])[:30]
    assert "playbook" not in visible
    assert "playbook" in line.split("\t")[1]


@pytest.mark.parametrize("width", [30, 60, 90])
def test_rows_fit_their_width(journal, width):
    _write(journal / "2026-07-04.md", DAILY)
    _write(journal / "notes" / "pipx.md", TOPIC)
    now = os.path.getmtime(journal / "notes" / "pipx.md") + 3 * 86400

    for note in store.list_notes(str(journal)):
        assert len(_plain(browse.row(note, width, now))) <= width


@pytest.mark.parametrize("seconds, label", [
    (30, "< 1 min"), (240, "4 min"), (7200, "2 h"), (100_000, "hier"),
    (3 * 86400, "3 j"), (20 * 86400, "2 sem"), (90 * 86400, "3 mois"),
    (400 * 86400, "1 an"), (1100 * 86400, "3 ans"),
])
def test_ago(seconds, label):
    assert browse.ago(1_000_000_000, now=1_000_000_000 + seconds) == label
