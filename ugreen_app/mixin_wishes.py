# -*- coding: utf-8 -*-
"""Sidebar-Seite: Wünsche und Screenshots per E-Mail an die Entwicklung."""

from __future__ import annotations

import os
import smtplib
import socket
import ssl
import sys
import threading
import tkinter as tk
import webbrowser
from email.message import EmailMessage
from tkinter import filedialog, messagebox, ttk
from urllib.parse import quote, urlencode

from ugreen_app.scroll_helpers import smooth_bind_mousewheel_tree, smooth_canvas_scrollregion_cb, smooth_canvas_wheel_handlers
def ui(size: int, *style: str) -> tuple[str, int] | tuple[str, int, str]:
    """Schrift wie im übrigen Windows-Fenster.

    Args:
        size: Größe in Punkt.
        style: Optional ``bold`` oder ``italic``.

    Returns:
        Tk-Schrift mit Segoe UI.
    """
    if style:
        return ("Segoe UI", size, style[0])
    return ("Segoe UI", size)

WISH_TO = "ugna@posteo.de"
_MAX_FILES = 4
_MAX_FILE_BYTES = 7 * 1024 * 1024
_MAX_TOTAL_BYTES = 20 * 1024 * 1024
_IMAGE_EXT = {
    ".png": "png",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".gif": "gif",
    ".webp": "webp",
    ".bmp": "bmp",
}


def wish_smtp_context() -> ssl.SSLContext:
    """Baut den TLS-Kontext für den direkten Versand.

    Auf dem Mac kennt das mitgelieferte Python die System-Zertifikate nicht.
    Ohne die Datei ``/etc/ssl/cert.pem`` bricht die Verbindung ab und die Mail
    ginge fälschlich an das E-Mail-Programm.

    Returns:
        Kontext, der dem Serverzertifikat vertraut.
    """
    if sys.platform == "darwin":
        cafile = "/etc/ssl/cert.pem"
        if os.path.isfile(cafile):
            return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


def wish_smtp_error_code(exc: BaseException) -> str:
    """Ordnet einen SMTP-Fehler einem kurzen Code für die Oberfläche zu.

    Args:
        exc: Ausnahme aus der Verbindung oder der Anmeldung.

    Returns:
        ``cert``, ``auth``, ``network`` oder ``other``.
    """
    if isinstance(exc, ssl.SSLCertVerificationError):
        return "cert"
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "auth"
    if isinstance(exc, (TimeoutError, socket.timeout, socket.gaierror, ConnectionError)):
        return "network"
    return "other"


def wish_header_safe(value: str, limit: int = 200) -> str:
    """Entfernt Zeilenumbrüche aus einem Mail-Kopf, damit der Versand nicht bricht.

    Args:
        value: Rohtext aus dem Formular.
        limit: Höchste Länge des Kopfes.

    Returns:
        Eine einzelne Zeile, gekürzt auf ``limit``.
    """
    cleaned = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    return cleaned[:limit]


def wish_reply_email_ok(value: str) -> bool:
    """Prüft, ob die Antwortadresse eine einfache E-Mail-Form hat.

    Args:
        value: Eingabe aus dem Feld „Deine E-Mail“.

    Returns:
        True, wenn lokalteil und Domain mit Punkt vorhanden sind.
    """
    text = str(value or "").strip()
    if any(ch.isspace() for ch in text) or text.count("@") != 1:
        return False
    local, _, domain = text.partition("@")
    if not local or not domain or "." not in domain:
        return False
    if domain.startswith(".") or domain.endswith("."):
        return False
    return True


def wish_safe_filename(name: str) -> str:
    """Macht einen Dateinamen für den Anhang header-sicher.

    Args:
        name: Originaler Dateiname.

    Returns:
        Kurzer Name aus Buchstaben, Ziffern, Punkt, Unterstrich und Bindestrich.
    """
    base = os.path.basename(str(name or "")).replace("\\", "_").replace("/", "_")
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in base).strip("._")
    return (cleaned or "screenshot.png")[:80]


def build_wish_message(
    *,
    mail_from: str,
    reply_to: str,
    subject: str,
    body: str,
    shots: list[tuple[str, bytes, str]],
) -> EmailMessage:
    """Baut die Wunsch-Mail inklusive Bildanhängen.

    Args:
        mail_from: Absender aus den SMTP-Einstellungen.
        reply_to: Adresse, an die wir antworten sollen.
        subject: Betreffzeile.
        body: Klartext der Nachricht.
        shots: Liste aus Dateiname, Inhalt und Bild-Untertyp.

    Returns:
        Fertige Nachricht an ``ugna@posteo.de``.
    """
    msg = EmailMessage()
    msg["Subject"] = wish_header_safe(subject, 180)
    msg["From"] = wish_header_safe(mail_from, 200)
    msg["To"] = WISH_TO
    msg["Reply-To"] = wish_header_safe(reply_to, 200)
    msg.set_content(str(body or ""), subtype="plain", charset="utf-8")
    for filename, data, subtype in shots:
        msg.add_attachment(
            data,
            maintype="image",
            subtype=subtype or "png",
            filename=wish_safe_filename(filename),
        )
    return msg


def wish_mail_body(
    *,
    intro: str,
    labels: dict[str, str],
    name: str,
    reply_to: str,
    kind: str,
    where: str,
    wish: str,
    shot_names: list[str],
    version: str,
    no_shots: str,
) -> str:
    """Setzt den Klartext der Wunsch-Mail in fester Reihenfolge.

    Args:
        intro: Erste Zeile.
        labels: Feldnamen (name, reply, kind, where, body, shots, version).
        name: Absendername.
        reply_to: Antwortadresse.
        kind: Gewählte Art.
        where: Stelle in der App.
        wish: Freitext.
        shot_names: Original-Dateinamen.
        version: App-Version.
        no_shots: Text, wenn kein Bild dabei ist.

    Returns:
        Mehrzeiliger Mailtext.
    """
    shots = "\n".join(f"- {name_i}" for name_i in shot_names) if shot_names else no_shots
    return (
        f"{intro}\n"
        f"{labels['version']}: {version}\n\n"
        f"{labels['name']}: {name}\n"
        f"{labels['reply']}: {reply_to}\n"
        f"{labels['kind']}: {kind}\n"
        f"{labels['where']}: {where}\n\n"
        f"{labels['body']}:\n{wish.strip()}\n\n"
        f"{labels['shots']}:\n{shots}\n"
    )


class MixinWishes:
    """Formular unter Einstellungen und Versand an die Entwicklung."""

    def setup_wishes_tab(self) -> None:
        """Baut die Seite mit nummerierten Feldern für Wunsch und Screenshots."""
        tab = self.tab_wishes
        for child in tab.winfo_children():
            child.destroy()
        self._wish_shots: list[str] = []
        self._wish_sending = False

        wrap = tk.Frame(tab, bg=self.color_bg_left)
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        card = self._ui_rounded_card_pack(wrap, fill=tk.BOTH, expand=True)
        sheet = tk.Frame(card, bg=self.color_surface)
        sheet.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        header = tk.Frame(
            sheet,
            bg=self.color_surface,
            highlightbackground=self.color_border,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            header,
            text=self.t("wish.title"),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_head,
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            header,
            text=self.t("wish.intro"),
            bg=self.color_surface,
            fg=self.color_text,
            font=ui(10),
            anchor="w",
            justify=tk.LEFT,
            wraplength=860,
        ).pack(fill=tk.X, pady=(6, 2))
        tk.Label(
            header,
            text=self.t("wish.required_legend"),
            bg=self.color_surface,
            fg=self.color_text,
            font=ui(9, "bold"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=860,
        ).pack(fill=tk.X, pady=(2, 4))
        clarity = tk.Label(
            header,
            text=self.t("wish.clarity"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=ui(8, "italic"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=860,
        )
        clarity.pack(fill=tk.X)

        outer = tk.Frame(sheet, bg=self.color_surface)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)
        canvas = tk.Canvas(outer, bg=self.color_surface, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        form = tk.Frame(canvas, bg=self.color_surface)
        window = canvas.create_window((0, 0), window=form, anchor="nw")
        hints: list[tk.Label] = [clarity]

        def _fit_width(event: tk.Event) -> None:
            canvas.itemconfigure(window, width=max(int(event.width) - 2, 1))
            span = max(280, int(event.width) - 48)
            for lab in hints:
                try:
                    lab.configure(wraplength=span)
                except tk.TclError:
                    pass

        canvas.bind("<Configure>", _fit_width)
        form.bind("<Configure>", smooth_canvas_scrollregion_cb(self.root, canvas))
        on_wheel, on_up, on_dn = smooth_canvas_wheel_handlers(canvas)

        def _block(number: str, title_key: str, hint_key: str) -> tk.Frame:
            box = tk.Frame(
                form,
                bg=self.color_surface,
                highlightbackground=self.color_border,
                highlightthickness=1,
                padx=12,
                pady=10,
            )
            box.pack(fill=tk.X, pady=(0, 10))
            tk.Label(
                box,
                text=f"{number}.  {self.t(title_key)}",
                bg=self.color_surface,
                fg=self.color_text,
                font=self.font_bold,
                anchor="w",
            ).pack(fill=tk.X)
            hint = tk.Label(
                box,
                text=self.t(hint_key),
                bg=self.color_surface,
                fg=self.color_text_muted,
                font=ui(8),
                anchor="w",
                justify=tk.LEFT,
                wraplength=860,
            )
            hint.pack(fill=tk.X, pady=(2, 8))
            hints.append(hint)
            return box

        def _entry(parent: tk.Widget) -> tk.Entry:
            field = tk.Entry(
                parent,
                font=self.font_base,
                relief="flat",
                highlightbackground=self.color_border,
                highlightthickness=1,
                bg=self.color_input_bg,
                fg=self.color_input_fg,
                insertbackground=self.color_input_fg,
            )
            field.pack(fill=tk.X, ipady=4)
            return field

        name_box = _block("1", "wish.field.name", "wish.hint.name")
        self.entry_wish_name = _entry(name_box)

        mail_box = _block("2", "wish.field.email", "wish.hint.email")
        self.entry_wish_email = _entry(mail_box)

        kind_box = _block("3", "wish.field.kind", "wish.hint.kind")
        self.var_wish_kind = tk.StringVar(value=self.t("wish.kind.placeholder"))
        self.combo_wish_kind = ttk.Combobox(
            kind_box,
            state="readonly",
            font=self.font_base,
            textvariable=self.var_wish_kind,
        )
        self._wish_kind_values = (
            self.t("wish.kind.new"),
            self.t("wish.kind.change"),
            self.t("wish.kind.both"),
        )
        self.combo_wish_kind["values"] = (self.t("wish.kind.placeholder"),) + self._wish_kind_values
        self.combo_wish_kind.pack(fill=tk.X, ipady=2)

        where_box = _block("4", "wish.field.where", "wish.hint.where")
        self.entry_wish_where = _entry(where_box)

        body_box = _block("5", "wish.field.body", "wish.hint.body")
        self.text_wish_body = tk.Text(
            body_box,
            height=8,
            wrap=tk.WORD,
            font=self.font_base,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            insertbackground=self.color_input_fg,
            padx=6,
            pady=6,
        )
        self.text_wish_body.pack(fill=tk.X)
        body_note = tk.Label(
            body_box,
            text=self.t("wish.clarity"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=ui(8, "italic"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=860,
        )
        body_note.pack(fill=tk.X, pady=(6, 0))
        hints.append(body_note)

        shot_box = _block("6", "wish.field.shots", "wish.hint.shots")
        self.list_wish_shots = tk.Listbox(
            shot_box,
            height=4,
            font=self.font_base,
            activestyle="dotbox",
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            highlightbackground=self.color_border,
            highlightthickness=1,
            selectbackground=self.color_btn_blue,
        )
        self.list_wish_shots.pack(fill=tk.X, pady=(0, 6))
        self.lbl_wish_shots = tk.Label(
            shot_box,
            text=self.t("wish.shots.empty"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=ui(8),
            anchor="w",
        )
        self.lbl_wish_shots.pack(fill=tk.X, pady=(0, 8))
        shot_btns = tk.Frame(shot_box, bg=self.color_surface)
        shot_btns.pack(fill=tk.X)
        self.create_modern_btn(
            shot_btns,
            self.t("wish.btn.add_shot"),
            self._wish_add_shots,
            self.color_btn_blue,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.create_modern_btn(
            shot_btns,
            self.t("wish.btn.remove_shot"),
            self._wish_remove_shot,
            self.color_btn_secondary,
        ).pack(side=tk.LEFT)

        actions = tk.Frame(form, bg=self.color_surface)
        actions.pack(fill=tk.X, pady=(4, 0))
        self.create_modern_btn(
            actions,
            self.t("wish.btn.send"),
            self.wishes_send,
            self.color_user,
        ).pack(anchor="w")
        mail_note = tk.Label(
            actions,
            text=self.t("wish.mail_note"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=ui(8, "italic"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=860,
        )
        mail_note.pack(fill=tk.X, pady=(8, 4))
        hints.append(mail_note)
        self.lbl_wish_status = tk.Label(
            actions,
            text=self.t("wish.status.ready"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=ui(9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=860,
        )
        self.lbl_wish_status.pack(fill=tk.X)
        hints.append(self.lbl_wish_status)

        smooth_bind_mousewheel_tree(form, on_wheel, on_up, on_dn)
        self._wish_refresh_shot_label()

    def _wish_set_status(self, text: str) -> None:
        """Schreibt die Statuszeile unter dem Senden-Knopf.

        Args:
            text: Kurzer Stand des Versands.
        """
        lbl = getattr(self, "lbl_wish_status", None)
        if lbl is None:
            return
        try:
            lbl.configure(text=text)
        except tk.TclError:
            pass

    def _wish_refresh_shot_label(self) -> None:
        """Zeigt, wie viele Bilder in der Liste stehen."""
        paths = list(getattr(self, "_wish_shots", []) or [])
        lbl = getattr(self, "lbl_wish_shots", None)
        if lbl is None:
            return
        if len(paths) == 1:
            text = self.t("wish.shots.one")
        elif paths:
            text = self.t("wish.shots.many", n=len(paths))
        else:
            text = self.t("wish.shots.empty")
        try:
            lbl.configure(text=text)
        except tk.TclError:
            pass

    def _wish_add_shots(self) -> None:
        """Öffnet die Dateiauswahl und übernimmt nur passende Bilder."""
        picked = filedialog.askopenfilenames(
            parent=self.root,
            title=self.t("wish.field.shots"),
            filetypes=[
                (self.t("wish.filetypes"), "*.png *.jpg *.jpeg *.gif *.webp *.bmp"),
                (self.t("wish.filetypes"), "*.*"),
            ],
        )
        if not picked:
            return
        problems: list[str] = []
        current = list(self._wish_shots)
        for raw in picked:
            path = os.path.abspath(str(raw))
            if path in current:
                continue
            reason = self._wish_shot_problem(path, current)
            if reason:
                problems.append(reason)
                continue
            if len(current) >= _MAX_FILES:
                problems.append(self.t("wish.shot.max_files", n=_MAX_FILES))
                break
            current.append(path)
        self._wish_shots = current
        self._wish_fill_shot_list()
        if problems:
            messagebox.showwarning(self.t("wish.shot.title"), "\n".join(problems), parent=self.root)

    def _wish_shot_problem(self, path: str, already: list[str]) -> str:
        """Prüft Typ, Größe und Summe eines neuen Bildes.

        Args:
            path: Gewählte Datei.
            already: Schon übernommene Pfade.

        Returns:
            Leerer Text, wenn die Datei passt, sonst der Hinweis für den Nutzer.
        """
        ext = os.path.splitext(path)[1].lower()
        name = os.path.basename(path)
        if ext not in _IMAGE_EXT:
            return self.t("wish.shot.bad_type", name=name)
        if not os.path.isfile(path):
            return self.t("wish.shot.missing", name=name)
        try:
            size = os.path.getsize(path)
        except OSError:
            return self.t("wish.shot.missing", name=name)
        if size > _MAX_FILE_BYTES:
            return self.t("wish.shot.too_big", name=name, mb=_MAX_FILE_BYTES // (1024 * 1024))
        total = size
        for old in already:
            try:
                total += os.path.getsize(old)
            except OSError:
                continue
        if total > _MAX_TOTAL_BYTES:
            return self.t("wish.shot.total", mb=_MAX_TOTAL_BYTES // (1024 * 1024))
        return ""

    def _wish_fill_shot_list(self) -> None:
        """Schreibt die gewählten Dateinamen in die Liste."""
        box = getattr(self, "list_wish_shots", None)
        if box is None:
            return
        try:
            box.delete(0, tk.END)
            for path in self._wish_shots:
                box.insert(tk.END, os.path.basename(path))
        except tk.TclError:
            return
        self._wish_refresh_shot_label()

    def _wish_remove_shot(self) -> None:
        """Nimmt das markierte Bild aus der Liste."""
        box = getattr(self, "list_wish_shots", None)
        if box is None:
            return
        try:
            sel = box.curselection()
        except tk.TclError:
            return
        if not sel:
            self._wish_set_status(self.t("wish.shot.none_selected"))
            return
        idx = int(sel[0])
        if 0 <= idx < len(self._wish_shots):
            del self._wish_shots[idx]
        self._wish_fill_shot_list()

    def _wish_form_error(self) -> str:
        """Prüft die Pflichtfelder von oben nach unten.

        Returns:
            Der erste fehlende Hinweis, oder ein leerer Text.
        """
        name = self.entry_wish_name.get().strip()
        email = self.entry_wish_email.get().strip()
        kind = self.var_wish_kind.get().strip()
        where = self.entry_wish_where.get().strip()
        body = self.text_wish_body.get("1.0", tk.END).strip()
        if len(name) < 2:
            return self.t("wish.err.name")
        if not wish_reply_email_ok(email):
            return self.t("wish.err.email")
        if kind not in self._wish_kind_values:
            return self.t("wish.err.kind")
        if len(where) < 2:
            return self.t("wish.err.where")
        if not body:
            return self.t("wish.err.body")
        if len(body) < 20:
            return self.t("wish.err.body_short")
        return ""

    def _wish_compose(self) -> dict[str, object]:
        """Liest das Formular und baut Betreff und Text.

        Returns:
            Daten für SMTP und für das E-Mail-Programm.
        """
        name = self.entry_wish_name.get().strip()
        reply_to = self.entry_wish_email.get().strip()
        kind = self.var_wish_kind.get().strip()
        where = self.entry_wish_where.get().strip()
        wish = self.text_wish_body.get("1.0", tk.END).strip()
        shots = [p for p in list(self._wish_shots) if os.path.isfile(p)]
        subject = self.t("wish.mail.subject", kind=wish_header_safe(kind, 40), where=wish_header_safe(where, 60))
        body = wish_mail_body(
            intro=self.t("wish.mail.intro"),
            labels={
                "version": self.t("wish.mail.version"),
                "name": self.t("wish.mail.name"),
                "reply": self.t("wish.mail.reply"),
                "kind": self.t("wish.mail.kind"),
                "where": self.t("wish.mail.where"),
                "body": self.t("wish.mail.body"),
                "shots": self.t("wish.mail.shots"),
            },
            name=name,
            reply_to=reply_to,
            kind=kind,
            where=where,
            wish=wish,
            shot_names=[os.path.basename(p) for p in shots],
            version=str(getattr(self, "_app_version", "") or ""),
            no_shots=self.t("wish.mail.no_shots"),
        )
        return {
            "reply_to": reply_to,
            "subject": subject,
            "body": body,
            "shots": shots,
        }

    def wishes_send(self) -> None:
        """Prüft das Formular und schickt den Wunsch an ugna@posteo.de."""
        if getattr(self, "_wish_sending", False):
            return
        error = self._wish_form_error()
        if error:
            messagebox.showwarning(self.t("wish.err.title"), error, parent=self.root)
            return
        payload = self._wish_compose()
        cfg = self._load_app_settings()
        if _smtp_ready(cfg):
            self._wish_sending = True
            self._wish_set_status(self.t("wish.status.sending"))
            threading.Thread(
                target=self._wish_send_thread,
                args=(payload, cfg),
                daemon=True,
                name="wish-mail",
            ).start()
            return
        self._wish_open_mailto(payload, smtp_error="")

    def _wish_send_thread(self, payload: dict[str, object], cfg: dict) -> None:
        """Sendet die Mail im Hintergrund und meldet das Ergebnis in die UI.

        Args:
            payload: Betreff, Text, Antwortadresse und Bildpfade.
            cfg: Gespeicherte App-Einstellungen inklusive SMTP.
        """
        ok, err = _send_wish_smtp(cfg, payload)

        def _done() -> None:
            self._wish_sending = False
            if ok:
                self._wish_set_status(self.t("wish.status.sent"))
                self._wish_clear_after_send()
                messagebox.showinfo(self.t("wish.send.title"), self.t("wish.send.ok"), parent=self.root)
                return
            self._wish_set_status(self._wish_smtp_fail_text(err))
            messagebox.showerror(self.t("wish.send.title"), self._wish_smtp_fail_text(err), parent=self.root)

        try:
            self.root.after(0, _done)
        except tk.TclError:
            pass

    def _wish_clear_after_send(self) -> None:
        """Leert Wunschtext und Bilder, lässt Name und E-Mail stehen."""
        try:
            self.text_wish_body.delete("1.0", tk.END)
            self.entry_wish_where.delete(0, tk.END)
            self.var_wish_kind.set(self.t("wish.kind.placeholder"))
        except tk.TclError:
            return
        self._wish_shots = []
        self._wish_fill_shot_list()

    def _wish_smtp_fail_text(self, code: str) -> str:
        """Text, wenn der direkte Versand fehlschlägt.

        Args:
            code: Kurzer Fehlercode aus dem SMTP-Versuch.

        Returns:
            Hinweis, ohne das E-Mail-Programm zu öffnen.
        """
        key = {
            "cert": "wish.send.smtp_cert",
            "auth": "wish.send.smtp_auth",
            "network": "wish.send.smtp_network",
            "missing": "wish.send.smtp_missing",
            "tls": "wish.send.smtp_tls",
        }.get(str(code or ""), "wish.send.smtp_other")
        return self.t(key)

    def _wish_open_mailto(self, payload: dict[str, object], smtp_error: str) -> None:
        """Öffnet das E-Mail-Programm mit Betreff und Text.

        Args:
            payload: Betreff, Text und Bildpfade.
            smtp_error: Fehler vom SMTP-Versuch, sonst leer.
        """
        subject = str(payload.get("subject") or "")
        body = str(payload.get("body") or "")
        shots = [str(p) for p in list(payload.get("shots") or [])]
        opened = False
        try:
            query = urlencode({"subject": subject, "body": body}, quote_via=quote)
            webbrowser.open(f"mailto:{WISH_TO}?{query}", new=2)
            opened = True
        except Exception:
            try:
                webbrowser.open(f"mailto:{WISH_TO}", new=2)
                opened = True
            except Exception:
                opened = False
        if not opened:
            self._wish_set_status(self.t("wish.send.mailto_fail"))
            messagebox.showerror(self.t("wish.send.title"), self.t("wish.send.mailto_fail"), parent=self.root)
            return
        if shots:
            files = "\n".join(shots)
            notice = self.t("wish.send.mailto_attach", files=files)
        else:
            notice = self.t("wish.send.mailto_ok")
        if smtp_error:
            notice = self.t("wish.send.smtp_fail", err=smtp_error) + "\n\n" + notice
        self._wish_set_status(self.t("wish.send.mailto_ok"))
        messagebox.showinfo(self.t("wish.send.title"), notice, parent=self.root)


def _smtp_ready(cfg: dict) -> bool:
    """Prüft, ob Host und Absender für den direkten Versand da sind.

    Args:
        cfg: Geladene App-Einstellungen.

    Returns:
        True, wenn SMTP Host und Absender ausgefüllt sind.
    """
    em = dict(cfg.get("email") or {})
    return bool(str(em.get("smtp_host") or "").strip() and str(em.get("smtp_from") or "").strip())


def _send_wish_smtp(cfg: dict, payload: dict[str, object]) -> tuple[bool, str]:
    """Sendet die Wunsch-Mail über den SMTP-Server aus den Einstellungen.

    Args:
        cfg: App-Einstellungen mit aufgelösten Geheimnissen.
        payload: Betreff, Text, Antwortadresse und Bildpfade.

    Returns:
        Erfolg und ein kurzer Fehlername, wenn der Versand scheitert.
    """
    em = dict(cfg.get("email") or {})
    host = str(em.get("smtp_host") or "").strip()
    mail_from = str(em.get("smtp_from") or "").strip()
    if not host or not mail_from:
        return False, "missing"
    try:
        port = int(em.get("smtp_port") or 587)
    except (TypeError, ValueError):
        port = 587
    port = max(1, min(65535, port))
    user = str(em.get("smtp_user") or "").strip()
    password = str(em.get("smtp_pass") or "")
    use_ssl = bool(em.get("smtp_ssl", False))
    use_tls = bool(em.get("smtp_starttls", True))
    if (user or password) and not (use_ssl or use_tls):
        return False, "tls"
    shots: list[tuple[str, bytes, str]] = []
    for path in list(payload.get("shots") or []):
        ext = os.path.splitext(str(path))[1].lower()
        subtype = _IMAGE_EXT.get(ext)
        if not subtype or not os.path.isfile(str(path)):
            continue
        try:
            size = os.path.getsize(str(path))
        except OSError:
            continue
        if size > _MAX_FILE_BYTES:
            continue
        try:
            with open(str(path), "rb") as handle:
                data = handle.read(_MAX_FILE_BYTES + 1)
        except OSError:
            continue
        if len(data) > _MAX_FILE_BYTES:
            continue
        shots.append((os.path.basename(str(path)), data, subtype))
    msg = build_wish_message(
        mail_from=mail_from,
        reply_to=str(payload.get("reply_to") or ""),
        subject=str(payload.get("subject") or ""),
        body=str(payload.get("body") or ""),
        shots=shots,
    )
    try:
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        return False, wish_smtp_error_code(exc)
    try:
        ctx = wish_smtp_context()
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=45, context=ctx) as smtp:
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
        elif use_tls:
            with smtplib.SMTP(host, port, timeout=45) as smtp:
                smtp.starttls(context=ctx)
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=45) as smtp:
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
    except Exception as exc:
        return False, wish_smtp_error_code(exc)
    return True, ""
