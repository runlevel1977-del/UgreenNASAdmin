# -*- coding: utf-8 -*-
"""Eingeschränkter Modus: gefährliche UI-Elemente bis zur Bestätigung deaktiviert."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox


class MixinSafetyLock:
    def _init_danger_lock_state(self) -> None:
        self.danger_functions_unlocked = False
        self._reset_danger_widget_registry()

    def _reset_danger_widget_registry(self) -> None:
        self._danger_rounded_buttons: list = []
        self._danger_ttk_widgets: list[tuple[object, str]] = []
        self._danger_tk_widgets: list[tk.Widget] = []
        self._danger_tk_buttons: list[tk.Button] = []

    def _register_danger_rounded(self, w):
        if w is not None:
            self._danger_rounded_buttons.append(w)
        return w

    def _register_danger_ttk_combobox(self, w, unlocked_state: str = "readonly") -> None:
        self._danger_ttk_widgets.append((w, unlocked_state))

    def _register_danger_tk_widget(self, w: tk.Widget | None) -> None:
        if w is not None:
            self._danger_tk_widgets.append(w)

    def _register_danger_tk_button(self, w: tk.Button | None) -> None:
        if w is not None:
            self._danger_tk_buttons.append(w)

    def _danger_gate(self) -> bool:
        if getattr(self, "danger_functions_unlocked", False):
            return True
        try:
            messagebox.showinfo(self.t("safety.need_unlock_title"), self.t("safety.need_unlock_msg"))
        except Exception:
            pass
        return False

    def _update_danger_header_button(self) -> None:
        btn = getattr(self, "btn_danger_power", None)
        if btn is None:
            return
        btn.set_enabled(True)
        if self.danger_functions_unlocked:
            btn.set_text(self.t("header.danger_lock_again"))
            btn.set_theme("#b45309", "white")
        else:
            btn.set_text(self.t("header.danger_unlock"))
            btn.set_theme("#dc2626", "white")

    def _apply_danger_lock_ui(self) -> None:
        on = self.danger_functions_unlocked
        for b in self._danger_rounded_buttons:
            try:
                if hasattr(b, "set_enabled"):
                    b.set_enabled(on)
            except tk.TclError:
                pass
        for w, st in self._danger_ttk_widgets:
            try:
                w.configure(state=st if on else "disabled")
            except tk.TclError:
                pass
        for w in self._danger_tk_widgets:
            try:
                w.configure(state=tk.NORMAL if on else tk.DISABLED)
            except tk.TclError:
                pass
        for w in self._danger_tk_buttons:
            try:
                w.configure(state=tk.NORMAL if on else tk.DISABLED)
            except tk.TclError:
                pass
        self._update_danger_header_button()

    def on_header_danger_power_click(self) -> None:
        if self.danger_functions_unlocked:
            if messagebox.askyesno(self.t("header.danger_lock_title"), self.t("header.danger_lock_confirm")):
                self.danger_functions_unlocked = False
                self._apply_danger_lock_ui()
            return
        if messagebox.askyesno(self.t("header.danger_unlock_title"), self.t("header.danger_unlock_confirm")):
            self.danger_functions_unlocked = True
            self._apply_danger_lock_ui()
