# -*- coding: utf-8 -*-
"""Einfaches Shell-/Bash-Syntax-Highlighting und Zeilennummern-Gutter für Tk Text."""

from __future__ import annotations

import re
import tkinter as tk

_SH_KEYWORDS = frozenset(
    "if then else elif fi for select in do done case esac while until function return break continue "
    "echo export readonly local cd pwd test [ ] eval exec source exit read set unset shift trap umask wait".split()
)


def configure_shell_editor_tags(text_widget: tk.Text, *, dark: bool) -> None:
    if dark:
        text_widget.tag_configure("sh_comment", foreground="#8b949e")
        text_widget.tag_configure("sh_kw", foreground="#79c0ff")
        text_widget.tag_configure("sh_string", foreground="#a5d6ff")
        text_widget.tag_configure("sh_var", foreground="#ffa657")
        text_widget.tag_configure("sh_num", foreground="#d2a8ff")
    else:
        text_widget.tag_configure("sh_comment", foreground="#6a737d")
        text_widget.tag_configure("sh_kw", foreground="#0550ae")
        text_widget.tag_configure("sh_string", foreground="#0a3069")
        text_widget.tag_configure("sh_var", foreground="#953800")
        text_widget.tag_configure("sh_num", foreground="#8250df")


def highlight_shell_buffer(text_widget: tk.Text) -> None:
    for t in ("sh_comment", "sh_kw", "sh_string", "sh_var", "sh_num"):
        text_widget.tag_remove(t, "1.0", tk.END)
    content = text_widget.get("1.0", "end-1c")
    lines = content.split("\n") if content else [""]
    kw_pattern = re.compile(
        r"\b(" + "|".join(re.escape(k) for k in sorted(_SH_KEYWORDS, key=len, reverse=True)) + r")\b"
    )

    for li, line in enumerate(lines, start=1):
        items: list[tuple[str, int, int]] = []
        for m in re.finditer(r"#.*$", line):
            items.append(("sh_comment", m.start(), m.end()))
        idx = 0
        while idx < len(line):
            ch = line[idx]
            if ch in "'\"" and not any(a <= idx < b for _t, a, b in items if _t == "sh_comment"):
                quote = ch
                j = idx + 1
                while j < len(line):
                    if line[j] == "\\":
                        j += min(2, len(line) - j)
                        continue
                    if line[j] == quote:
                        items.append(("sh_string", idx, j + 1))
                        idx = j + 1
                        break
                    j += 1
                else:
                    items.append(("sh_string", idx, len(line)))
                    break
                continue
            idx += 1
        comment_ranges = [(a, b) for t, a, b in items if t == "sh_comment"]
        str_ranges = [(a, b) for t, a, b in items if t == "sh_string"]

        def _masked(pos: int) -> bool:
            return any(a <= pos < b for a, b in comment_ranges + str_ranges)

        for m in kw_pattern.finditer(line):
            if not _masked(m.start()):
                items.append(("sh_kw", m.start(), m.end()))
        for m in re.finditer(r"\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*", line):
            if not _masked(m.start()):
                items.append(("sh_var", m.start(), m.end()))
        for m in re.finditer(r"(?<![A-Za-z0-9_])(\d+)(?![A-Za-z0-9_])", line):
            if not _masked(m.start()):
                items.append(("sh_num", m.start(), m.end()))

        n = len(line)
        cov = [False] * max(1, n)
        for tag_name in ("sh_comment", "sh_string", "sh_kw", "sh_var", "sh_num"):
            for tname, a, b in items:
                if tname != tag_name or a >= b:
                    continue
                hi = min(b, n)
                lo = min(a, n)
                if lo >= hi or any(cov[lo:hi]):
                    continue
                for i in range(lo, hi):
                    cov[i] = True
                text_widget.tag_add(tag_name, f"{li}.{lo}", f"{li}.{hi}")


def sync_editor_gutter(editor: tk.Text, gutter: tk.Text) -> None:
    try:
        n = int(editor.index("end-1c").split(".")[0])
    except (tk.TclError, ValueError):
        n = 1
    n = max(1, n)
    body = "\n".join(str(i) for i in range(1, n + 1))
    gutter.configure(state=tk.NORMAL)
    gutter.delete("1.0", tk.END)
    gutter.insert("1.0", body)
    gutter.configure(state=tk.DISABLED)
