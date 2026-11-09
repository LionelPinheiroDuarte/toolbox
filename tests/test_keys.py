import re

from x.commands import keys


def _plain(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


LIST_KEYS = """C-a     Last window
h       Select the pane (vi direction)
j       Select the pane (vi direction)
?       These shortcuts
o       Select the next pane
"""


def test_parse_reads_key_and_note():
    assert keys.parse(LIST_KEYS)[:2] == [
        ("C-a", "Last window"),
        ("h", "Select the pane (vi direction)"),
    ]


def test_parse_skips_blank_lines():
    assert keys.parse("\n\nC-a  Last window\n") == [("C-a", "Last window")]


def test_group_merges_keys_sharing_a_note():
    assert keys.group(keys.parse(LIST_KEYS))[1] == (["h", "j"], "Select the pane (vi direction)")


def test_custom_drops_unchanged_tmux_defaults():
    mine = keys.parse(LIST_KEYS)
    defaults = [("o", "Select the next pane"), ("?", "List key bindings")]
    # o is tmux's own; ? is rebound with another note, so it is mine
    assert ("o", "Select the next pane") not in keys.custom(mine, defaults)
    assert ("?", "These shortcuts") in keys.custom(mine, defaults)


def test_in_config_order_follows_the_file():
    config = 'bind -N "These shortcuts" ?\nbind -N "Last window" C-a\n'
    groups = [(["C-a"], "Last window"), (["x"], "Not in the file"), (["?"], "These shortcuts")]
    assert [note for _, note in keys.in_config_order(groups, config)] == [
        "These shortcuts", "Last window", "Not in the file",
    ]


def test_render_aligns_keys_across_sections():
    out = _plain(keys.render(
        [(None, [(["h", "j", "k", "l"], "Select")]), ("without prefix", [(["C-y"], "Nested")])],
        "C-a",
    ))
    assert "prefix C-a" in out
    assert "  h j k l  Select" in out
    assert "  C-y      Nested" in out


def test_render_skips_empty_sections():
    out = _plain(keys.render([(None, [(["g"], "Projects")]), ("without prefix", [])], "C-a"))
    assert "without prefix" not in out


def test_render_hints_at_notes_when_nothing_to_show():
    assert "bind -N" in _plain(keys.render([(None, [])], "C-a"))
