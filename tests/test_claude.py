import json
import os
import re

import pytest

from x.commands.claude import edits, projects
from x.utils import popup

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def plain(lines):
    return [ANSI.sub("", line) for line in lines]


# --- popup -----------------------------------------------------------------

@pytest.mark.parametrize("age, expected", [
    (10, "< 1 min"), (4 * 60, "4 min"), (2 * 3600, "2 h"), (30 * 3600, "hier"),
    (3 * 86400, "3 j"), (20 * 86400, "2 sem"), (90 * 86400, "3 mois"),
    (400 * 86400, "1 an"), (3 * 365 * 86400, "3 ans"),
])
def test_ago(age, expected):
    assert popup.ago(1_000_000_000 - age, now=1_000_000_000) == expected


def test_ago_without_a_date():
    assert popup.ago("") == ""
    assert popup.ago(None) == ""


def test_since():
    now = 1_000_000_000
    assert popup.since(now - 5, now) == "à l'instant"
    assert popup.since(now - 30 * 3600, now) == "hier"
    assert popup.since(now - 300, now) == "il y a 5 min"


def test_info_file(tmp_path):
    path = tmp_path / "info"
    popup.write_info(str(path), 3, "2 ouverts · ")
    assert path.read_text() == "3\n2 ouverts · \n"


# --- projects --------------------------------------------------------------

def test_session_name():
    assert projects.session_name(popup.HOME) == "home"
    assert projects.session_name("/x/my.repo") == "my_repo"
    assert projects.session_name("/x/a:b/") == "a_b"


def test_repo_status_parses_porcelain(monkeypatch):
    out = "\n".join([
        "# branch.oid abc", "# branch.head main", "# branch.upstream origin/main",
        "# branch.ab +2 -1", "1 .M N... 100644 100644 100644 a b x.py", "? new.txt",
    ])
    monkeypatch.setattr(projects, "run", lambda *a, **k: out)
    assert projects.repo_status("/x") == {"branch": "main", "ahead": "2", "behind": "1", "dirty": 2}


def test_repo_status_without_upstream(monkeypatch):
    monkeypatch.setattr(projects, "run", lambda *a, **k: "# branch.head dev")
    assert projects.repo_status("/x") == {"branch": "dev", "ahead": "", "behind": "", "dirty": 0}


def test_repo_status_outside_a_repo(monkeypatch):
    monkeypatch.setattr(projects, "run", lambda *a, **k: None)
    assert projects.repo_status("/x") is None


def _transcript(folder, *msgs):
    folder.mkdir(parents=True)
    # compact, as Claude Code writes it (the filter looks for "type":"user")
    (folder / "s.jsonl").write_text("".join(json.dumps(m, separators=(",", ":")) + "\n" for m in msgs))


def test_last_exchange(tmp_path, monkeypatch):
    monkeypatch.setattr(projects, "HOME", str(tmp_path))
    _transcript(tmp_path / ".claude" / "projects" / "-repo-a",
                {"type": "user", "message": {"content": "first"}},
                {"type": "user", "message": {"content": "fix   the\nbug"}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "Looking"}]}},
                {"type": "user", "isMeta": True, "message": {"content": "meta"}},
                {"type": "user", "message": {"content": "<command-name>/clear"}},
                {"type": "assistant", "message": {"content": [{"type": "tool_use"}]}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "Fixed it"}]}})
    assert projects.last_exchange("/repo/a") == ("fix the bug", "Fixed it")


def test_last_exchange_without_transcript(tmp_path, monkeypatch):
    monkeypatch.setattr(projects, "HOME", str(tmp_path))
    assert projects.last_exchange("/nowhere") is None


def test_tail_reads_the_last_lines(tmp_path):
    f = tmp_path / "big"
    f.write_text("".join(f"line {i}\n" for i in range(10_000)))
    assert projects._tail(str(f), 3, block=64) == ["line 9997", "line 9998", "line 9999"]


def test_set_state_is_a_noop_outside_tmux(monkeypatch):
    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.setattr(projects, "tmux", lambda *a: pytest.fail("tmux called"))
    projects.set_state("running")


# --- edits -----------------------------------------------------------------

@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(edits, "LOG", str(tmp_path / "edits.log"))
    monkeypatch.setattr(edits, "SNAPSHOTS", str(tmp_path / "snapshots"))
    monkeypatch.setenv("LIST_COLS", "100")
    return tmp_path


def _edit(state, ts, session, path, before=None):
    """Log an edit of <path> and snapshot <before> (None: Claude created it)."""
    with open(state / "edits.log", "a") as f:
        f.write(f"{ts}\t{session}\t{path}\n")
    d = edits.snapshot_dir(session, str(path))
    os.makedirs(d, exist_ok=True)
    if before is None:
        open(os.path.join(d, "new"), "w").close()
        open(os.path.join(d, "0001-t.orig"), "w").close()
    else:
        with open(os.path.join(d, "0001-t.orig"), "w") as f:
            f.write(before)


def test_logged_groups_files_by_their_last_session(state):
    with open(state / "edits.log", "w") as f:
        f.write("1\ts1\t/a\n2\ts1\t/b\n3\ts2\t/a\n4\ts2\t/c\n")
    assert edits.logged() == [("4", "s2", "/c"), ("3", "s2", "/a"), ("2", "s1", "/b")]


def test_entries_marks_and_counts(state):
    repo = state / "repo"
    repo.mkdir()
    (repo / "changed.py").write_text("a\nB\nc\n")
    (repo / "created.py").write_text("x\ny\n")
    (repo / "reverted.py").write_text("same\n")
    _edit(state, 100, "s1", repo / "changed.py", "a\nb\nc\n")
    _edit(state, 101, "s1", repo / "created.py")
    _edit(state, 102, "s1", repo / "reverted.py", "same\n")
    info = state / "info"
    lines = plain(edits.entries(str(repo), str(info)))
    assert lines[0].startswith("DERNIÈRE SESSION")
    rows = {l.split("\t")[2].rsplit("/", 1)[1]: l.split("\t")[1] for l in lines[1:]}
    assert rows["changed.py"].split()[:4] == ["~", "changed.py", "+1", "-1"]
    assert rows["created.py"].split()[:4] == ["✚", "created.py", "+2", "·"]
    assert rows["reverted.py"].split()[:3] == ["↶", "reverted.py", "annulé"]
    assert info.read_text().startswith("1\n")


def test_entries_scope_and_deleted_files(state):
    (state / "kept.py").write_text("x\n")
    _edit(state, 1, "s1", state / "kept.py", "x\n")
    _edit(state, 2, "s1", state / "gone.py", "x\n")
    _edit(state, 3, "s1", "/elsewhere/other.py", "x\n")
    paths = [l.split("\t")[2] for l in edits.entries(str(state)) if l.split("\t")[2]]
    assert paths == [str(state / "kept.py")]


def test_fit_keeps_the_file_name():
    assert edits._fit("short.py", 20) == "short.py"
    assert edits._fit("a/b/c/deep/file.py", 14) == "…/deep/file.py"
    assert edits._fit("a/averyveryverylongname.py", 10) == "…ngname.py"


def test_show_diff_numbers_lines():
    u = "--- a\n+++ b\n@@ -1,3 +1,3 @@ def f():\n a\n-b\n+B\n c\n"
    out = plain(edits.show_diff(u, 20))
    assert out[0] == "@@ 1,3 → 1,3 @@ def f():"
    assert out[1] == "   1    1    a"
    assert out[2] == "   2       - b      "
    assert out[3] == "        2  + B      "
    assert out[4] == "   3    3    c"


def test_toggle_and_scope(tmp_path):
    mode, scope = tmp_path / "mode", tmp_path / "scope"
    mode.write_text("diff\n")
    edits.toggle(str(mode))
    assert mode.read_text() == "file\n"
    edits.toggle(str(mode))
    assert mode.read_text() == "diff\n"
    scope.write_text("")
    edits.flip_scope(str(scope), "/repo")
    assert scope.read_text() == "/repo\n"
    edits.flip_scope(str(scope), "/repo")
    assert scope.read_text() == ""
