# -*- coding: utf-8 -*-
"""Auto-generiert von tools/split_ugreen_manager.py — Mixin für NASManager."""
from __future__ import annotations

import os
import posixpath
import shutil
import shlex
import stat
import sys
import uuid
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
import base64
import threading
import time
import unicodedata
import zipfile
import tempfile
import re
import string
import socket
import errno
import ctypes
import urllib.request
import urllib.parse

import nas_ssh
import nas_utils
from ugreen_app._paramiko import _paramiko
from ugreen_app.transfer_log import append_transfer_log

class MixinTransfer:
    def _fmt_bytes(self, n):
        return nas_utils.fmt_bytes(n)

    def _fmt_eta(self, seconds):
        try:
            seconds = int(max(0, seconds))
        except Exception:
            return "--:--"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _sftp_candidates(self, remote_path):
        c = [remote_path, remote_path.lstrip("/")]
        if remote_path.startswith("/volume1/"):
            c.append(remote_path.replace("/volume1/", "/", 1))
            c.append(remote_path.replace("/volume1", "", 1))
        if remote_path.startswith("/volume2/"):
            c.append(remote_path.replace("/volume2/", "/", 1))
            c.append(remote_path.replace("/volume2", "", 1))
        # de-dupe keep order
        out = []
        seen = set()
        for x in c:
            if x not in seen:
                out.append(x)
                seen.add(x)
        return out

    def _paramiko_tune_fast_transfer(self, ssh, for_upload=False):
        """Vor open_sftp: Keepalive immer. Upload = kleinere Fenster, kein extremes Rekey (stabiler auf NAS)."""
        try:
            tr = ssh.get_transport()
            if not tr:
                return
            if for_upload:
                # Wie Download: kleine Upload-Fenster brachen bei manchen NAS (Ugreen/Synology) den SFTP-Kanal („Socket is closed“).
                tr.default_window_size = min(2**32 - 1, 32 * 1024 * 1024)
                tr.default_max_packet_size = min(2**32 - 1, 256 * 1024)
            else:
                tr.default_window_size = min(2**32 - 1, 32 * 1024 * 1024)
                tr.default_max_packet_size = min(2**32 - 1, 256 * 1024)
            tr.set_keepalive(12)
            try:
                pk = tr.packetizer
                pk.REKEY_BYTES = max(pk.REKEY_BYTES, 1 << 36)
                pk.REKEY_PACKETS = max(pk.REKEY_PACKETS, 1 << 30)
            except Exception:
                pass
            sock = getattr(tr, "sock", None)
            if sock is not None:
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except OSError:
                    pass
                for size in (4 * 1024 * 1024, 1024 * 1024, 256 * 1024):
                    try:
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, size)
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, size)
                        break
                    except OSError:
                        continue
        except Exception:
            pass

    def _is_transfer_connection_lost(self, exc):
        if isinstance(exc, (EOFError, BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return True
        if isinstance(exc, OSError):
            e = getattr(exc, "errno", None)
            if e in (errno.EPIPE, errno.ECONNRESET, errno.ETIMEDOUT, errno.ECONNABORTED):
                return True
            if getattr(exc, "winerror", None) in (10053, 10054, 10060):
                return True
        msg = (str(exc) or "").lower()
        if any(
            w in msg
            for w in (
                "connection dropped",
                "server connection",
                "connection lost",
                "connection reset",
                "broken pipe",
                "eof",
                "closed",
                "socket is closed",
                "not connected",
                "unexpectedly closed",
                "timed out",
                "timeout",
            )
        ):
            return True
        try:
            pse = _paramiko().ssh_exception
            if isinstance(exc, (pse.SSHException,)) and any(
                x in msg for x in ("connection", "socket", "dropped", "closed", "eof", "reset", "timeout", "broken")
            ):
                return True
        except Exception:
            pass
        return False

    def _is_remote_path_missing_error(self, exc):
        """SFTP/SSH: Zielpfad existiert nicht (Errno 2 / SSH_FX_NO_SUCH_FILE)."""
        if exc is None:
            return False
        if getattr(exc, "errno", None) == 2:
            return True
        msg = (str(exc) or "").lower()
        if "no such file" in msg or "errno 2" in msg:
            return True
        if "file_put_contents" in msg:
            return True
        try:
            pk = _paramiko()
            sfe = getattr(pk, "SFTPError", None)
            if sfe is None and hasattr(pk, "sftp"):
                sfe = getattr(pk.sftp, "SFTPError", None)
            if sfe and isinstance(exc, sfe) and getattr(exc, "code", None) == 2:
                return True
        except Exception:
            pass
        return False

    def _sftp_try_remove_remote(self, sftp, remote_path):
        if not sftp:
            return
        for rp in self._sftp_candidates(remote_path):
            try:
                sftp.remove(rp)
            except Exception:
                pass

    def _upload_is_permission_denied(self, exc):
        if exc is None:
            return False
        if isinstance(exc, PermissionError):
            return True
        if isinstance(exc, OSError) and getattr(exc, "errno", None) == 13:
            return True
        msg = str(exc).lower()
        return "permission denied" in msg or "errno 13" in msg

    def _win_long_path_local(self, path):
        """Windows: optional \\\\?\\-Präfix bei langen Pfaden (open/getsize)."""
        if sys.platform != "win32" or not path:
            return path
        try:
            ap = os.path.abspath(os.path.normpath(path))
        except Exception:
            return path
        if ap.startswith("\\\\?\\") or ap.startswith("\\\\.\\"):
            return ap
        if len(ap) > 220 and not ap.startswith("\\\\"):
            return "\\\\?\\" + ap
        return ap

    def _local_path_variants(self, path):
        w = self._win_long_path_local(path)
        out = []
        for p in (w, path):
            if p and p not in out:
                out.append(p)
        return out

    def _local_resolve_upload_path(self, path: str) -> str:
        """Stabilster existierender lokaler Pfad (Windows: Leerzeichen, normpath, \\\\?\\)."""
        if not path:
            return path
        seen: list[str] = []
        candidates = [path, os.path.normpath(path)]
        try:
            candidates.append(os.path.abspath(os.path.normpath(path)))
        except Exception:
            pass
        candidates.append(self._win_long_path_local(path))
        try:
            candidates.append(
                self._win_long_path_local(os.path.abspath(os.path.normpath(path)))
            )
        except Exception:
            pass
        for c in candidates:
            if not c or c in seen:
                continue
            seen.append(c)
            try:
                if os.path.isfile(c):
                    return c
            except OSError:
                continue
        try:
            return os.path.abspath(os.path.normpath(path))
        except Exception:
            return path

    def _upload_exc_is_probably_remote_missing(self, exc, local_resolved: str) -> bool:
        """SFTP-Fehler 2 / ENOENT auf dem NAS — nur wenn die lokale Datei wirklich da ist."""
        if not self._local_isfile_for_upload(local_resolved):
            return False
        if isinstance(exc, PermissionError):
            return False
        en = getattr(exc, "errno", None)
        if en in (errno.ENOENT, 2):
            return True
        if getattr(exc, "winerror", None) == 2:
            return True
        lo = str(exc).lower()
        if "lokal nicht gefunden" in lo:
            return False
        for needle in (
            "no such file",
            "no such file or directory",
            "fx_no_such_file",
            "errno 2",
            "cannot find the file",
            "cannot find the path",
            "the system cannot find",
            "nicht gefunden",
            "die datei ist nicht vorhanden",
            "path not found",
        ):
            if needle in lo:
                return True
        return False

    def _local_file_size_for_upload(self, path):
        for p in self._local_path_variants(path):
            try:
                return os.path.getsize(p)
            except OSError:
                continue
        return 0

    def _local_isfile_for_upload(self, path):
        for p in self._local_path_variants(path):
            try:
                if os.path.isfile(p):
                    return True
            except OSError:
                continue
        return False

    def _open_local_for_upload(self, path):
        """Liest lokal fürs SFTP; Retries bei Win32 „Datei von anderem Prozess verwendet“ (DLLs in bin/Debug)."""
        variants = self._local_path_variants(path)
        last_exc = None
        for attempt in range(12):
            for vp in variants:
                try:
                    return open(vp, "rb")
                except OSError as e:
                    last_exc = e
                    w = getattr(e, "winerror", None)
                    if w in (32, 33):
                        break
                    if w == 2:
                        continue
                    raise
            else:
                if last_exc is not None and getattr(last_exc, "winerror", None) not in (32, 33):
                    raise last_exc
            time.sleep(0.2 + 0.1 * attempt)
        if last_exc is not None:
            raise last_exc
        raise OSError(f"Lokal nicht lesbar: {path}")

    def _ssh_sudo_bash(self, ssh, inner_bash_script):
        """sudo bash -c '...' mit Passwort auf stdin (kein Passwort in der Shell-Zeile)."""
        pw = self.entry_pwd.get()
        if pw is None:
            pw = ""
        cmd = "sudo -S bash -c " + shlex.quote(inner_bash_script)
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        stdin.write(pw + "\n")
        stdin.flush()
        stdin.channel.shutdown_write()
        out_b = stdout.read()
        err_b = stderr.read()
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            err_s = err_b.decode(errors="replace").strip()
            out_s = out_b.decode(errors="replace").strip()
            hint = err_s or out_s or f"exit {exit_status}"
            raise OSError(f"sudo auf dem NAS fehlgeschlagen ({exit_status}): {hint[:800]}")

    def _ssh_sudo_mkdir_chown(self, ssh, remote_path):
        """Zielordner anlegen und Besitzer = SSH-User (für SFTP-Upload)."""
        rp = posixpath.normpath((remote_path or "").strip())
        if not rp.startswith("/") or rp == "/":
            raise ValueError(f"Ungültiger Remote-Pfad: {remote_path!r}")
        user = self.entry_user.get()
        inner = f"mkdir -p {shlex.quote(rp)} && chown -R {shlex.quote(user)}:{shlex.quote(user)} {shlex.quote(rp)}"
        self._ssh_sudo_bash(ssh, inner)

    def _ssh_sudo_exec_standalone(self, inner_bash_script):
        """Eigene SSH-Verbindung — nie dieselbe Session wie SFTP (sonst oft „Socket is closed“)."""
        pk = _paramiko()
        ssh = pk.SSHClient()
        ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
        try:
            ssh.connect(
                self.entry_ip.get(),
                **self._ssh_connect_kwargs(timeout=25, banner_timeout=40, auth_timeout=40),
            )
            self._ssh_sudo_bash(ssh, inner_bash_script)
        finally:
            try:
                ssh.close()
            except Exception:
                pass

    def _ssh_sudo_mkdir_chown_standalone(self, remote_path):
        rp = posixpath.normpath((remote_path or "").strip())
        if not rp.startswith("/") or rp == "/":
            raise ValueError(f"Ungültiger Remote-Pfad: {remote_path!r}")
        user = self.entry_user.get()
        inner = f"mkdir -p {shlex.quote(rp)} && chown -R {shlex.quote(user)}:{shlex.quote(user)} {shlex.quote(rp)}"
        self._ssh_sudo_exec_standalone(inner)

    def _ssh_unzip_bundle_on_nas(self, remote_zip, dest_dir):
        """ZIP per sudo entpacken: unzip → busybox → python3/python (UGREEN hat oft kein unzip)."""
        rz = shlex.quote(posixpath.normpath(remote_zip))
        dd = shlex.quote(posixpath.normpath(dest_dir))
        py_src = (
            "import zipfile,sys,os;"
            "d=sys.argv[2];"
            "os.makedirs(d,exist_ok=True);"
            "z=zipfile.ZipFile(sys.argv[1]);"
            "z.extractall(d);"
            "z.close()"
        )
        py_q = shlex.quote(py_src)
        chains = [
            f"unzip -o -q {rz} -d {dd} && rm -f {rz}",
            f"busybox unzip -o -q {rz} -d {dd} && rm -f {rz}",
            f"python3 -c {py_q} {rz} {dd} && rm -f {rz}",
            f"python -c {py_q} {rz} {dd} && rm -f {rz}",
        ]
        last = None
        for inner in chains:
            try:
                self._ssh_sudo_exec_standalone(inner)
                return
            except Exception as e:
                last = e
                continue
        raise OSError(
            "Auf dem NAS fehlt unzip und es konnte weder busybox unzip noch "
            "python3/python zum Entpacken genutzt werden. "
            "Bitte per App-Store/SSH nachinstallieren (z. B. Paket „unzip“ oder python3)."
        ) from last

    def _prepare_remote_file_for_ugreen_sftp(self, remote_file_path):
        """UGREEN: SFTP-Schicht nutzt PHP file_put_contents — Zieldatei muss existieren + chown SSH-User."""
        rp = posixpath.normpath((remote_file_path or "").strip())
        if not rp.startswith("/") or rp == "/":
            raise ValueError(f"Ungültiger Remote-Pfad: {remote_file_path!r}")
        user = (self.entry_user.get() or "").strip()
        if not user:
            raise ValueError("SSH-Benutzer fehlt")
        parent = posixpath.dirname(rp)
        if parent and parent not in ("/", ""):
            inner = (
                f"mkdir -p {shlex.quote(parent)} && "
                f"rm -f {shlex.quote(rp)} && "
                f"touch {shlex.quote(rp)} && "
                f"chown {shlex.quote(user)}:{shlex.quote(user)} {shlex.quote(rp)}"
            )
        else:
            inner = (
                f"rm -f {shlex.quote(rp)} && touch {shlex.quote(rp)} && "
                f"chown {shlex.quote(user)}:{shlex.quote(user)} {shlex.quote(rp)}"
            )
        self._ssh_sudo_exec_standalone(inner)

    def _upload_local_file_via_ssh_cat(self, local_path, remote_path, callback=None):
        """Große Datei nur per SSH-STDIN → shell cat > Ziel (ohne SFTP; UGREEN-SFTP/PHP ist unzuverlässig)."""
        rp = posixpath.normpath((remote_path or "").strip())
        if not rp.startswith("/") or rp == "/":
            raise ValueError(f"Ungültiger Remote-Pfad: {remote_path!r}")
        pk = _paramiko()
        ssh = pk.SSHClient()
        ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
        ssh.connect(
            self.entry_ip.get(),
            **self._ssh_connect_kwargs(
                timeout=30,
                banner_timeout=60,
                auth_timeout=60,
                look_for_keys=False,
                allow_agent=False,
                compress=False,
            ),
        )
        try:
            inner = f"cat > {shlex.quote(rp)}"
            cmd = "/bin/sh -c " + shlex.quote(inner)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdin.channel.settimeout(None)
            fs = self._local_file_size_for_upload(local_path)
            read_chunk = 256 * 1024
            cb_min_interval = 0.12
            cb_min_step = 2 * 1024 * 1024
            last_cb_t = 0.0
            last_cb_done = 0
            done = 0
            with self._open_local_for_upload(local_path) as lf:
                while True:
                    chunk = lf.read(read_chunk)
                    if not chunk:
                        break
                    offset = 0
                    while offset < len(chunk):
                        n = stdin.channel.send(chunk[offset:])
                        if n == 0:
                            time.sleep(0.02)
                            continue
                        offset += n
                    done += len(chunk)
                    if callback:
                        now = time.monotonic()
                        ttot = fs if fs > 0 else max(done, 1)
                        if (
                            (now - last_cb_t) >= cb_min_interval
                            or (done - last_cb_done) >= cb_min_step
                        ):
                            callback(done, ttot)
                            last_cb_t = now
                            last_cb_done = done
            if callback:
                callback(done, fs if fs > 0 else max(done, 1))
            try:
                stdin.flush()
            except Exception:
                pass
            stdin.channel.shutdown_write()
            err_b = stderr.read()
            out_b = stdout.read()
            ex = stdout.channel.recv_exit_status()
            if ex != 0:
                hint = (err_b or out_b or b"").decode(errors="replace").strip()[:1200]
                raise OSError(f"SSH cat-Upload exit {ex}: {hint}")
        finally:
            try:
                ssh.close()
            except Exception:
                pass
        return rp

    def _ensure_remote_dir_for_upload(self, ssh, sftp, path, created_set):
        path = posixpath.normpath((path or "").strip())
        if not path or path == "/" or path in created_set:
            return
        try:
            self._sftp_ensure_dir(sftp, path)
        except (OSError, IOError) as e:
            if self._upload_is_permission_denied(e):
                self._ssh_sudo_mkdir_chown_standalone(path)
            else:
                raise
        created_set.add(path)

    def _sftp_put_via_stream(self, sftp, local_path, remote_path, callback=None, confirm=True):
        """Große Blöcke statt Paramiko put() (32 KiB) — weniger Roundtrips, höherer Durchsatz."""
        fs = self._local_file_size_for_upload(local_path)
        read_chunk = 256 * 1024
        cb_min_interval = 0.12
        cb_min_step = 2 * 1024 * 1024
        last_cb_t = 0.0
        last_cb_done = 0
        done = 0
        ch = sftp.get_channel()
        if ch is not None:
            try:
                ch.settimeout(None)
            except Exception:
                pass
        with sftp.open(remote_path, "wb") as wf:
            with self._open_local_for_upload(local_path) as lf:
                while True:
                    chunk = lf.read(read_chunk)
                    if not chunk:
                        break
                    wf.write(chunk)
                    done += len(chunk)
                    if callback:
                        now = time.monotonic()
                        ttot = fs if fs > 0 else max(done, 1)
                        if (
                            (now - last_cb_t) >= cb_min_interval
                            or (done - last_cb_done) >= cb_min_step
                        ):
                            callback(done, ttot)
                            last_cb_t = now
                            last_cb_done = done
            if callback:
                callback(done, fs if fs > 0 else max(done, 1))
        if confirm:
            st = sftp.stat(remote_path)
            if int(st.st_size) != done:
                raise OSError(f"Upload-Größe: erwartet {done}, remote {st.st_size}")
        return remote_path

    def _sftp_put_via_tmp_sudo_mv(self, ssh, sftp, local_path, remote_path, callback=None):
        bn = posixpath.basename(remote_path) or "upload.bin"
        tmp = posixpath.join("/tmp", f".na_{uuid.uuid4().hex}_{bn}")
        try:
            self._sftp_put_via_stream(sftp, local_path, tmp, callback=callback, confirm=True)
        except Exception:
            try:
                sftp.remove(tmp)
            except Exception:
                pass
            raise
        user = self.entry_user.get()
        inner = f"mv -f {shlex.quote(tmp)} {shlex.quote(remote_path)} && chown {shlex.quote(user)}:{shlex.quote(user)} {shlex.quote(remote_path)}"
        try:
            self._ssh_sudo_exec_standalone(inner)
        except Exception:
            try:
                sftp.remove(tmp)
            except Exception:
                pass
            raise
        return remote_path

    def _sftp_put_try_sudo_fallback(self, ssh, sftp, local_path, remote_path, callback=None):
        try:
            return self._sftp_put_try(sftp, local_path, remote_path, callback=callback)
        except (OSError, IOError, PermissionError) as e:
            if not self._upload_is_permission_denied(e):
                raise
        parent = posixpath.dirname(remote_path)
        if parent and parent not in ("/", ""):
            self._ssh_sudo_mkdir_chown_standalone(parent)
        try:
            return self._sftp_put_try(sftp, local_path, remote_path, callback=callback)
        except (OSError, IOError, PermissionError) as e2:
            if not self._upload_is_permission_denied(e2):
                raise
        return self._sftp_put_via_tmp_sudo_mv(ssh, sftp, local_path, remote_path, callback=callback)

    def _sftp_ensure_dir(self, sftp, remote_dir_path):
        """Remote-Ordner rekursiv per SFTP anlegen — gleicher User wie put(), kein sudo (vermeidet Passwort/Sonderzeichen-Probleme)."""
        path = posixpath.normpath((remote_dir_path or "").strip())
        if not path or path == "/":
            return
        try:
            st = sftp.stat(path)
            if stat.S_ISDIR(st.st_mode):
                return
            raise OSError(f"Existiert, ist aber kein Ordner: {path}")
        except (OSError, IOError):
            pass
        parent = posixpath.dirname(path)
        if parent and parent not in ("/", "") and parent != path:
            self._sftp_ensure_dir(sftp, parent)
        try:
            sftp.mkdir(path, 0o755)
        except (OSError, IOError):
            try:
                st = sftp.stat(path)
                if stat.S_ISDIR(st.st_mode):
                    return
            except (OSError, IOError):
                pass
            raise

    def _sftp_put_try(self, sftp, local_path, remote_path, callback=None):
        last_exc = None
        for rp in self._sftp_candidates(remote_path):
            try:
                self._sftp_put_via_stream(sftp, local_path, rp, callback=callback, confirm=True)
                return rp
            except FileNotFoundError as e:
                last_exc = e
            except OSError as e:
                last_exc = e
                msg = str(e)
                if "No such file" not in msg and "errno 2" not in msg.lower():
                    raise
        if last_exc is not None:
            raise last_exc
        raise FileNotFoundError(remote_path)

    def _sftp_get_via_stream(self, sftp, rp, local_path, callback=None):
        """Download ohne sftp.get() — große Blöcke; Callback gedrosselt (sonst Tk after()-Flut bremst alles)."""
        read_chunk = 8 * 1024 * 1024
        cb_min_interval = 0.12
        cb_min_step = 2 * 1024 * 1024
        with sftp.open(rp, "rb") as rf:
            try:
                sz = int(rf.stat().st_size)
            except Exception:
                sz = 0
            done = 0
            last_cb_t = 0.0
            last_cb_done = 0
            with open(local_path, "wb") as lf:
                while True:
                    chunk = rf.read(read_chunk)
                    if not chunk:
                        break
                    lf.write(chunk)
                    done += len(chunk)
                    if callback:
                        ttot = sz if sz > 0 else max(done, 1)
                        now = time.monotonic()
                        if (
                            (now - last_cb_t) >= cb_min_interval
                            or (done - last_cb_done) >= cb_min_step
                        ):
                            callback(done, ttot)
                            last_cb_t = now
                            last_cb_done = done
                if callback:
                    ttot = sz if sz > 0 else max(done, 1)
                    callback(done, ttot)
        return rp

    def _sftp_get_try(self, sftp, remote_path, local_path, callback=None):
        last_exc = None
        for rp in self._sftp_candidates(remote_path):
            try:
                self._sftp_get_via_stream(sftp, rp, local_path, callback=callback)
                return rp
            except FileNotFoundError as e:
                last_exc = e
            except OSError as e:
                last_exc = e
                msg = str(e)
                if "No such file" not in msg and "errno 2" not in msg.lower():
                    raise
            except IOError as e:
                last_exc = e
                msg = str(e)
                if "No such file" not in msg and "errno 2" not in msg.lower():
                    raise
        if last_exc is not None:
            raise last_exc
        raise FileNotFoundError(remote_path)

    def _remote_file_size_via_ssh(self, ssh, remote_path):
        rp = posixpath.normpath((remote_path or "").strip())
        if not rp.startswith("/") or rp == "/":
            return 0
        inner = f"stat -c %s {shlex.quote(rp)} 2>/dev/null || wc -c < {shlex.quote(rp)} 2>/dev/null || echo 0"
        cmd = "/bin/sh -c " + shlex.quote(inner)
        _stdin, stdout, _stderr = ssh.exec_command(cmd)
        out = (stdout.read() or b"").decode(errors="replace").strip().splitlines()
        if not out:
            return 0
        try:
            return max(int(out[-1].strip()), 0)
        except Exception:
            return 0

    def _download_remote_file_via_ssh_cat(self, ssh, remote_path, local_path, callback=None, expected_size=0):
        rp = posixpath.normpath((remote_path or "").strip())
        if not rp.startswith("/") or rp == "/":
            raise ValueError(f"Ungültiger Remote-Pfad: {remote_path!r}")
        cmd = "/bin/sh -c " + shlex.quote(f"cat {shlex.quote(rp)}")
        _stdin, stdout, stderr = ssh.exec_command(cmd)
        ch = stdout.channel
        ch.settimeout(None)
        done = 0
        read_chunk = 256 * 1024
        cb_min_interval = 0.12
        cb_min_step = 2 * 1024 * 1024
        last_cb_t = 0.0
        last_cb_done = 0
        local_write_path = self._win_long_path_local(local_path)
        with open(local_write_path, "wb") as lf:
            while True:
                chunk = stdout.read(read_chunk)
                if not chunk:
                    break
                lf.write(chunk)
                done += len(chunk)
                if callback:
                    now = time.monotonic()
                    ttot = expected_size if expected_size and expected_size > 0 else max(done, 1)
                    if (
                        (now - last_cb_t) >= cb_min_interval
                        or (done - last_cb_done) >= cb_min_step
                    ):
                        callback(done, ttot)
                        last_cb_t = now
                        last_cb_done = done
        err_b = stderr.read()
        ex = ch.recv_exit_status()
        if ex != 0:
            hint = (err_b or b"").decode(errors="replace").strip()[:1200]
            raise OSError(f"SSH cat-Download exit {ex}: {hint}")
        # Kein harter Abgleich mit vorherigem stat: NAS kann 0/1 byte falsch melden; cat+exit 0 ist maßgeblich.
        if callback:
            ttot = expected_size if expected_size and expected_size > 0 else max(done, 1)
            callback(done, ttot)
        return done

    def _explorer_remote_target_dir(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item_id = sel[-1]
        path = self.get_full_path(item_id)
        vals = self.tree.item(item_id, "values")
        if self._explorer_type("file") in vals:
            return posixpath.dirname(path) or "/"
        return path

    def explorer_upload_files(self):
        remote_dir = self._explorer_remote_target_dir()
        if not remote_dir:
            messagebox.showinfo(self.t("msg.upload_title"), self.t("msg.upload_pick_nas"))
            return
        local_paths = filedialog.askopenfilenames(title=self.t("msg.upload_pick_files"))
        if not local_paths:
            return

        items = []
        for p in local_paths:
            items.append((p, os.path.basename(p)))

        self._start_upload_queue(remote_dir, items, title_suffix=self.t("msg.upload_suffix_files"))

    def explorer_upload_folder(self):
        remote_dir = self._explorer_remote_target_dir()
        if not remote_dir:
            messagebox.showinfo(self.t("msg.upload_title"), self.t("msg.upload_pick_nas"))
            return
        local_dir = filedialog.askdirectory(title=self.t("msg.upload_pick_folder"))
        if not local_dir:
            return

        base_name = os.path.basename(os.path.normpath(local_dir))
        items = []
        for root_dir, _, files in os.walk(local_dir):
            for fn in files:
                lp = os.path.join(root_dir, fn)
                rel = os.path.relpath(lp, local_dir).replace("\\", "/")
                items.append((lp, f"{base_name}/{rel}"))

        if not items:
            messagebox.showinfo(self.t("msg.upload_title"), self.t("msg.upload_empty"))
            return

        self._start_upload_queue(remote_dir, items, title_suffix=self.t("msg.upload_suffix_folder"))

    def explorer_upload_file(self):
        # Backward compatibility: single-file upload from other callers
        return self.explorer_upload_files()

    def _start_upload_queue(self, remote_dir, items, title_suffix="Upload"):
        if not self._danger_gate():
            return
        # items: list[(local_path, remote_rel_path)]
        remote_dir = unicodedata.normalize("NFC", (remote_dir or "").strip())
        items = sorted(items, key=lambda it: (it[1].replace("\\", "/").lower(), it[0].lower()))
        total_bytes = 0
        for lp, _ in items:
            total_bytes += self._local_file_size_for_upload(lp)

        effective_total_ref = [max(total_bytes, 1)]

        pw = tk.Toplevel(self.root)
        pw.title(self.t("msg.upload_running_title", suffix=title_suffix))
        pw.geometry("560x300")
        pw.configure(bg=self.color_surface_alt)
        pw.transient(self.root)

        header = tk.Frame(pw, bg=self.color_btn_blue, pady=10, padx=12)
        header.pack(fill=tk.X)
        tk.Label(header, text=self.t("msg.upload_header_nas"), bg=self.color_btn_blue, fg="white", font=self.font_head).pack(anchor=tk.W)

        body = tk.Frame(pw, bg=self.color_surface_alt, padx=18, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        lbl_file = tk.Label(body, text=self.t("msg.upload_file_label"), bg=self.color_surface_alt, fg=self.color_text, font=self.font_bold, anchor="w")
        lbl_file.pack(fill=tk.X)
        lbl_target = tk.Label(body, text=self.t("msg.upload_target_folder", remote_dir=remote_dir), bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_base, anchor="w", wraplength=520, justify=tk.LEFT)
        lbl_target.pack(fill=tk.X, pady=(6, 10))

        tk.Label(body, text=self.t("msg.upload_progress_total"), bg=self.color_surface_alt, fg=self.color_text, font=self.font_base, anchor="w").pack(fill=tk.X)
        pb_total = ttk.Progressbar(body, orient="horizontal", mode="determinate", maximum=(total_bytes if total_bytes > 0 else 1))
        pb_total.pack(fill=tk.X, pady=(4, 10))

        tk.Label(body, text=self.t("msg.upload_current_file"), bg=self.color_surface_alt, fg=self.color_text, font=self.font_base, anchor="w").pack(fill=tk.X)
        pb_file = ttk.Progressbar(body, orient="horizontal", mode="determinate", maximum=1)
        pb_file.pack(fill=tk.X, pady=(4, 10))

        info_row = tk.Frame(body, bg=self.color_surface_alt)
        info_row.pack(fill=tk.X)
        lbl_left = tk.Label(info_row, text="0% (0 B / ?)", bg=self.color_surface_alt, fg=self.color_text, font=self.font_base, anchor="w")
        lbl_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        lbl_right = tk.Label(info_row, text="0 B/s • ETA --:--", bg=self.color_surface_alt, fg=self.color_text, font=self.font_base, anchor="e")
        lbl_right.pack(side=tk.RIGHT)

        btn_row = tk.Frame(body, bg=self.color_surface_alt)
        btn_row.pack(fill=tk.X, pady=(12, 0))
        cancel_evt = threading.Event()

        def on_cancel():
            cancel_evt.set()
            try:
                pw.title(self.t("msg.upload_cancelling"))
            except Exception:
                pass

        btn_cancel = self.create_modern_btn(btn_row, self.t("msg.upload_cancel"), on_cancel, self.color_root)
        btn_cancel.pack(side=tk.RIGHT)

        state = {"last_t": time.time(), "last_b": 0, "speed": 0.0}
        progress = {"overall_done": 0, "file_base": 0, "file_size": 0, "file_done": 0, "current_remote": None}
        # Ein Tk-after pro ~50 ms statt pro Chunk — sonst staut sich die Eventqueue (Balken steht, dann „Socket is closed“).
        ui_coalesce = {"armed": False, "dirty": False}

        def touch_progress_ui():
            def on_main():
                ui_coalesce["dirty"] = True
                if ui_coalesce["armed"]:
                    return
                ui_coalesce["armed"] = True

                def apply():
                    ui_coalesce["armed"] = False
                    if not ui_coalesce["dirty"]:
                        return
                    ui_coalesce["dirty"] = False
                    od = progress["file_base"] + progress["file_done"]
                    ft = progress["file_size"] if progress["file_size"] else 1
                    ui_update(od, effective_total_ref[0], progress["file_done"], ft)
                    if ui_coalesce["dirty"]:
                        ui_coalesce["armed"] = True
                        pw.after(50, apply)

                pw.after(50, apply)

            self.root.after(0, on_main)

        def ui_update(overall_done, overall_total, file_done, file_total):
            overall_total = overall_total if overall_total and overall_total > 0 else effective_total_ref[0]
            if overall_total and overall_total > 0:
                pb_total["maximum"] = overall_total
                pb_total["value"] = min(overall_done, overall_total)
                pct = int((overall_done / overall_total) * 100)
                lbl_left.config(text=f"{pct}% ({self._fmt_bytes(overall_done)} / {self._fmt_bytes(overall_total)})")
            else:
                pb_total["maximum"] = 1
                pb_total["value"] = 0
                lbl_left.config(text=f"{self._fmt_bytes(overall_done)} übertragen")

            file_total = file_total if file_total and file_total > 0 else 1
            pb_file["maximum"] = file_total
            pb_file["value"] = min(file_done, file_total)

            now = time.time()
            dt = max(0.001, now - state["last_t"])
            db = max(0, overall_done - state["last_b"])
            inst_speed = db / dt
            state["speed"] = (state["speed"] * 0.80) + (inst_speed * 0.20)
            state["last_t"] = now
            state["last_b"] = overall_done

            eta = "--:--"
            if overall_total and overall_total > 0 and state["speed"] > 1:
                eta = self._fmt_eta((overall_total - overall_done) / state["speed"])
            lbl_right.config(text=f"{self._fmt_bytes(state['speed'])}/s • ETA {eta}")

        def worker():
            ssh = None
            sftp = None
            err = None
            created_remote_dirs = set()
            uploaded_paths = []
            uploaded_meta = []
            upload_fail_note = [""]
            upload_verify_bad = []
            upload_verify_checked = 0
            upload_verify_note = ""

            def connect_sftp(*, frequent=False):
                """Neue SSH+SFTP; frequent=kurze Pausen bei Upload mit vielen Dateien (Session pro Datei)."""
                nonlocal ssh, sftp
                pause_close = 0.06 if frequent else 0.2
                pause_open = 0.06 if frequent else 0.15
                if ssh is not None:
                    try:
                        if sftp:
                            sftp.close()
                    except Exception:
                        pass
                    try:
                        ssh.close()
                    except Exception:
                        pass
                    time.sleep(pause_close)
                pk = _paramiko()
                ssh = pk.SSHClient()
                ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
                ssh.connect(
                    self.entry_ip.get(),
                    **self._ssh_connect_kwargs(
                        timeout=30,
                        banner_timeout=60,
                        auth_timeout=60,
                        look_for_keys=False,
                        allow_agent=False,
                        compress=False,
                    ),
                )
                self._paramiko_tune_fast_transfer(ssh, for_upload=True)
                sftp = ssh.open_sftp()
                ch0 = sftp.get_channel()
                if ch0 is not None:
                    try:
                        ch0.settimeout(None)
                    except Exception:
                        pass
                self._ensure_remote_dir_for_upload(ssh, sftp, remote_dir.rstrip("/"), created_remote_dirs)
                time.sleep(pause_open)

            try:
                # Ab mehreren Dateien: ein ZIP lokal, eine SFTP-Übertragung, unzip auf dem NAS —
                # vermeidet hunderte SFTP-OPEN/WRITE (Paramiko „Socket is closed“ / NAS-Limits).
                zip_bundle_threshold = 8
                if len(items) >= zip_bundle_threshold:
                    upload_fail_note[0] = (
                        f"ZIP-Bundle ({len(items)} Dateien)\n"
                        f"Ziel: {remote_dir}"
                    )
                    zfd, zpath = tempfile.mkstemp(prefix="na_ul_", suffix=".zip")
                    os.close(zfd)
                    try:
                        self.root.after(
                            0,
                            lambda n=len(items): lbl_file.config(text=f"Packe {n} Dateien lokal (ZIP)…"),
                        )
                        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                            for i, (local_path, remote_rel) in enumerate(items, start=1):
                                if cancel_evt.is_set():
                                    raise RuntimeError("Upload abgebrochen")
                                arc = unicodedata.normalize(
                                    "NFC", remote_rel.replace("\\", "/").lstrip("/")
                                )
                                arc = posixpath.normpath(arc)
                                if not arc or arc == ".":
                                    continue
                                if arc.startswith("..") or "/../" in ("/" + arc + "/"):
                                    raise ValueError(f"Unzulässiger Zielpfad: {remote_rel!r}")
                                if not self._local_isfile_for_upload(local_path):
                                    raise FileNotFoundError(f"Lokal nicht gefunden: {local_path}")
                                zf.write(
                                    self._win_long_path_local(local_path),
                                    arcname=arc,
                                )
                                if i % 50 == 0 or i == len(items):
                                    self.root.after(
                                        0,
                                        lambda ii=i, nn=len(items): lbl_file.config(
                                            text=f"Packe ZIP ({ii}/{nn})…"
                                        ),
                                    )
                        zsz = 0
                        for _zp in self._local_path_variants(zpath):
                            try:
                                zsz = os.path.getsize(_zp)
                                break
                            except OSError:
                                continue
                        if zsz < 22:
                            raise OSError("ZIP-Archiv ist leer oder zu klein — nichts zu übertragen.")
                        effective_total_ref[0] = max(zsz, 1)
                        rd_base = unicodedata.normalize("NFC", remote_dir.rstrip("/"))

                        try:
                            self._ssh_sudo_mkdir_chown_standalone(rd_base)
                        except Exception:
                            pass

                        zip_base = f".na_{uuid.uuid4().hex}.upload.zip"
                        remote_zip_candidates = [
                            posixpath.join(rd_base, zip_base),
                            posixpath.join("/volume1", zip_base),
                            posixpath.join("/tmp", zip_base),
                        ]
                        progress["file_base"] = 0
                        progress["file_size"] = zsz
                        progress["file_done"] = 0
                        progress["overall_done"] = 0

                        def cb_zip(transferred, total):
                            if cancel_evt.is_set():
                                raise RuntimeError("Upload abgebrochen")
                            progress["file_done"] = transferred
                            touch_progress_ui()

                        self.root.after(
                            0,
                            lambda s=zsz: lbl_file.config(
                                text=f"Übertrage ZIP per SSH (ohne SFTP)… ({self._fmt_bytes(s)})"
                            ),
                        )

                        remote_zip = None
                        put_last_exc = None
                        for cand in remote_zip_candidates:
                            try:
                                self._prepare_remote_file_for_ugreen_sftp(cand)
                            except Exception as prep_e:
                                put_last_exc = prep_e
                                continue
                            try:
                                self._upload_local_file_via_ssh_cat(
                                    zpath, cand, callback=cb_zip
                                )
                                remote_zip = cand
                                put_last_exc = None
                                break
                            except RuntimeError:
                                raise
                            except Exception as e:
                                put_last_exc = e
                                if cancel_evt.is_set():
                                    raise RuntimeError("Upload abgebrochen")
                                fn = getattr(e, "filename", None)
                                if fn is not None:
                                    try:
                                        if os.path.normcase(
                                            os.path.normpath(str(fn))
                                        ) == os.path.normcase(os.path.normpath(zpath)):
                                            raise OSError(
                                                f"Lokale ZIP-Datei fehlt oder ist gesperrt: {zpath}\n{e!r}"
                                            ) from e
                                    except OSError:
                                        raise
                                    except Exception:
                                        pass
                                try:
                                    self._ssh_sudo_exec_standalone(
                                        f"rm -f {shlex.quote(cand)}"
                                    )
                                except Exception:
                                    pass

                        if not remote_zip:
                            raise OSError(
                                "ZIP-Upload (SSH cat): kein Ziel hat funktioniert "
                                f"(versucht: {remote_zip_candidates!r}). "
                                f"Letzter Fehler: {put_last_exc!r}"
                            ) from put_last_exc

                        self.root.after(
                            0,
                            lambda: lbl_file.config(text="Entpacke auf dem NAS…"),
                        )
                        try:
                            self._ssh_unzip_bundle_on_nas(remote_zip, rd_base)
                        finally:
                            try:
                                self._ssh_sudo_exec_standalone(
                                    f"rm -f {shlex.quote(remote_zip)}"
                                )
                            except Exception:
                                pass

                        progress["overall_done"] = zsz
                        progress["file_done"] = zsz
                        touch_progress_ui()
                    finally:
                        try:
                            os.remove(zpath)
                        except OSError:
                            pass
                else:
                    try:
                        self._ssh_sudo_mkdir_chown_standalone(
                            unicodedata.normalize("NFC", remote_dir.rstrip("/"))
                        )
                    except Exception:
                        pass
                    connect_sftp(frequent=False)
                    files_since_full = 0
                    # Wenige Dateien: klassisch einzeln; Reconnect alle N < 12 (Kanal-Limit).
                    full_refresh_every = 5
                    pause_before_reconnect = 0.35

                    for idx, (local_path, remote_rel) in enumerate(items, start=1):
                        if cancel_evt.is_set():
                            raise RuntimeError("Upload abgebrochen")

                        local_resolved = self._local_resolve_upload_path(local_path)
                        fsz = self._local_file_size_for_upload(local_resolved)

                        progress["file_base"] = progress["overall_done"]
                        progress["file_size"] = fsz
                        progress["file_done"] = 0

                        # Remote = immer POSIX (NAS); NFC: Umlaute (z. B. öffentlich) sonst manchmal SFTP/Server-Probleme.
                        rel_clean = unicodedata.normalize("NFC", remote_rel.replace("\\", "/").lstrip("/"))
                        rd_base = unicodedata.normalize("NFC", remote_dir.rstrip("/"))
                        remote_path = posixpath.normpath(
                            posixpath.join(rd_base, rel_clean) if rel_clean else rd_base
                        )
                        remote_parent = posixpath.dirname(remote_path)

                        upload_fail_note[0] = (
                            f"Datei [{idx}/{len(items)}]\n"
                            f"Rel.: {remote_rel}\n"
                            f"Lokal: {local_resolved}\n"
                            f"(Tree: {local_path})\n"
                            f"NAS:   {remote_path}"
                        )

                        if remote_parent and remote_parent not in created_remote_dirs:
                            self._ensure_remote_dir_for_upload(ssh, sftp, remote_parent, created_remote_dirs)

                        if not self._local_isfile_for_upload(local_resolved):
                            raise FileNotFoundError(
                                f"Lokal nicht gefunden: {local_resolved}\n(Explorer-Pfad: {local_path})"
                            )

                        def cb(transferred, total):
                            if cancel_evt.is_set():
                                raise RuntimeError("Upload abgebrochen")
                            progress["file_done"] = transferred
                            touch_progress_ui()

                        self.root.after(
                            0,
                            lambda rp=remote_rel, i=idx, n=len(items): lbl_file.config(
                                text=f"[{i}/{n}] {rp}"
                            ),
                        )

                        try:
                            self._prepare_remote_file_for_ugreen_sftp(remote_path)
                        except Exception:
                            pass

                        max_put_attempts = 12
                        attempt = 0
                        ugreen_second_prepare = False
                        cat_tried = False

                        def _after_upload_success(used: str):
                            nonlocal files_since_full
                            uploaded_paths.append(used)
                            if fsz > 0:
                                uploaded_meta.append((used, fsz))
                            progress["overall_done"] = progress["file_base"] + fsz
                            progress["file_done"] = fsz
                            touch_progress_ui()
                            if idx < len(items):
                                files_since_full += 1
                                if files_since_full >= full_refresh_every:
                                    time.sleep(pause_before_reconnect)
                                    connect_sftp(frequent=True)
                                    files_since_full = 0

                        while True:
                            try:
                                used = self._sftp_put_try_sudo_fallback(
                                    ssh, sftp, local_resolved, remote_path, callback=cb
                                )
                                _after_upload_success(used)
                                break
                            except RuntimeError:
                                raise
                            except Exception as e:
                                if cancel_evt.is_set():
                                    raise RuntimeError("Upload abgebrochen")
                                cur = e
                                if self._upload_exc_is_probably_remote_missing(
                                    cur, local_resolved
                                ) and not cat_tried:
                                    cat_tried = True
                                    try:
                                        used = self._upload_local_file_via_ssh_cat(
                                            local_resolved, remote_path, callback=cb
                                        )
                                        _after_upload_success(used)
                                        break
                                    except Exception as cat_e:
                                        cur = cat_e
                                if self._upload_exc_is_probably_remote_missing(
                                    cur, local_resolved
                                ) and not ugreen_second_prepare:
                                    ugreen_second_prepare = True
                                    try:
                                        self._prepare_remote_file_for_ugreen_sftp(remote_path)
                                        continue
                                    except Exception:
                                        pass
                                attempt += 1
                                if attempt >= max_put_attempts or not self._is_transfer_connection_lost(cur):
                                    raise cur
                                time.sleep(0.6 + 0.2 * attempt)
                                connect_sftp(frequent=False)
                                files_since_full = 0
                                self._sftp_try_remove_remote(sftp, remote_path)

            except Exception as e:
                err = e
                if cancel_evt.is_set():
                    # best-effort cleanup
                    try:
                        for rp in uploaded_paths[-10:]:
                            self.run_ssh_cmd(f"rm -f {shlex.quote(rp)}", True, update_status=False)
                    except Exception:
                        pass
            finally:
                if err is None and not cancel_evt.is_set():
                    try:
                        if len(items) >= 8:
                            upload_verify_note = self.t("msg.upload_zip_note")
                        elif uploaded_meta:
                            pkv = _paramiko()
                            sshv = pkv.SSHClient()
                            sshv.set_missing_host_key_policy(pkv.AutoAddPolicy())
                            sshv.connect(
                                self.entry_ip.get(),
                                **self._ssh_connect_kwargs(
                                    timeout=20,
                                    banner_timeout=40,
                                    auth_timeout=40,
                                    look_for_keys=False,
                                    allow_agent=False,
                                ),
                            )
                            try:
                                for rp, exs in uploaded_meta:
                                    got = self._remote_file_size_via_ssh(sshv, rp)
                                    upload_verify_checked += 1
                                    if int(got) != int(exs):
                                        upload_verify_bad.append((rp, exs, got))
                            finally:
                                try:
                                    sshv.close()
                                except Exception:
                                    pass
                    except Exception:
                        pass
                try:
                    if sftp:
                        sftp.close()
                except Exception:
                    pass
                try:
                    if ssh:
                        ssh.close()
                except Exception:
                    pass

            def done():
                try:
                    btn_cancel.config(state="disabled")
                except Exception:
                    pass
                try:
                    pw.destroy()
                except Exception:
                    pass
                if err:
                    if cancel_evt.is_set():
                        messagebox.showinfo(self.t("msg.upload_title"), self.t("msg.upload_aborted"))
                        append_transfer_log(
                            self._app_data_dir(),
                            self.t("msg.transfer_log_upload_aborted", n=len(items)),
                            "INFO",
                        )
                    else:
                        note = upload_fail_note[0] if upload_fail_note[0] else ""
                        body = str(err) if err else self.t("msg.transfer_unknown_error")
                        if note:
                            body = f"{body}\n\n{note}"
                        messagebox.showerror(self.t("msg.upload_failed_title"), body)
                        append_transfer_log(
                            self._app_data_dir(),
                            self.t("msg.transfer_log_upload_error", body=body[:500]),
                            "ERROR",
                        )
                else:
                    if upload_verify_bad:
                        lines = []
                        for rp, exs, got in upload_verify_bad[:8]:
                            lines.append(
                                self.t("msg.upload_verify_line", path=rp, expected=exs, remote=got)
                            )
                        more_suffix = ""
                        if len(upload_verify_bad) > 8:
                            more_suffix = self.t(
                                "msg.transfer_verify_more", n=len(upload_verify_bad) - 8
                            )
                        messagebox.showwarning(
                            self.t("msg.upload_verify_warn_title"),
                            self.t(
                                "msg.upload_verify_warn_body",
                                n_files=len(items),
                                checked=upload_verify_checked,
                                mismatches=len(upload_verify_bad),
                                details="\n".join(lines),
                                more_suffix=more_suffix,
                            ),
                        )
                        append_transfer_log(
                            self._app_data_dir(),
                            self.t(
                                "msg.transfer_log_upload_warn",
                                n_files=len(items),
                                n_bad=len(upload_verify_bad),
                            ),
                            "WARN",
                        )
                    else:
                        suffix = ""
                        if upload_verify_checked > 0:
                            suffix += self.t(
                                "msg.upload_complete_verified_suffix", n=upload_verify_checked
                            )
                        if upload_verify_note:
                            suffix += ("\n" if suffix else "") + upload_verify_note
                        messagebox.showinfo(
                            self.t("msg.upload_title"),
                            self.t("msg.upload_complete", n_files=len(items), suffix=suffix),
                        )
                        append_transfer_log(
                            self._app_data_dir(),
                            self.t("msg.transfer_log_upload_ok", n_files=len(items), extra=suffix),
                            "INFO",
                        )
                    self.root.after(300, self.scan_nas)

            self.root.after(0, done)

        pw.protocol("WM_DELETE_WINDOW", on_cancel)
        threading.Thread(target=worker, daemon=True).start()

    def _start_download_queue(self, pairs):
        """pairs: list of (remote_abs_posix_path, local_abs_path)."""
        if not pairs:
            return

        pw = tk.Toplevel(self.root)
        pw.title(self.t("msg.download_running_title"))
        pw.geometry("560x300")
        pw.configure(bg=self.color_surface_alt)
        pw.transient(self.root)

        header = tk.Frame(pw, bg=self.color_user, pady=10, padx=12)
        header.pack(fill=tk.X)
        tk.Label(header, text=self.t("msg.download_header_nas"), bg=self.color_user, fg="white", font=self.font_head).pack(anchor=tk.W)

        body = tk.Frame(pw, bg=self.color_surface_alt, padx=18, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        lbl_file = tk.Label(body, text=self.t("msg.upload_file_label"), bg=self.color_surface_alt, fg=self.color_text, font=self.font_bold, anchor="w")
        lbl_file.pack(fill=tk.X)
        lbl_target = tk.Label(body, text=self.t("msg.download_target_local", path=self.explorer_local_cwd), bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_base, anchor="w", wraplength=520, justify=tk.LEFT)
        lbl_target.pack(fill=tk.X, pady=(6, 10))

        tk.Label(body, text=self.t("msg.upload_progress_total"), bg=self.color_surface_alt, fg=self.color_text, font=self.font_base, anchor="w").pack(fill=tk.X)
        pb_total = ttk.Progressbar(body, orient="horizontal", mode="determinate", maximum=1)
        pb_total.pack(fill=tk.X, pady=(4, 10))

        tk.Label(body, text=self.t("msg.upload_current_file"), bg=self.color_surface_alt, fg=self.color_text, font=self.font_base, anchor="w").pack(fill=tk.X)
        pb_file = ttk.Progressbar(body, orient="horizontal", mode="determinate", maximum=1)
        pb_file.pack(fill=tk.X, pady=(4, 10))

        info_row = tk.Frame(body, bg=self.color_surface_alt)
        info_row.pack(fill=tk.X)
        lbl_left = tk.Label(info_row, text="0%", bg=self.color_surface_alt, fg=self.color_text, font=self.font_base, anchor="w")
        lbl_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        lbl_right = tk.Label(info_row, text="0 B/s • ETA --:--", bg=self.color_surface_alt, fg=self.color_text, font=self.font_base, anchor="e")
        lbl_right.pack(side=tk.RIGHT)

        btn_row = tk.Frame(body, bg=self.color_surface_alt)
        btn_row.pack(fill=tk.X, pady=(12, 0))
        cancel_evt = threading.Event()

        def on_cancel():
            cancel_evt.set()
            try:
                pw.title(self.t("msg.upload_cancelling"))
            except Exception:
                pass

        btn_cancel = self.create_modern_btn(btn_row, self.t("msg.upload_cancel"), on_cancel, self.color_root)
        btn_cancel.pack(side=tk.RIGHT)

        state = {"last_t": time.time(), "last_b": 0, "speed": 0.0}
        progress = {"overall_done": 0, "file_base": 0, "file_size": 0}

        def ui_update(overall_done, overall_total, file_done, file_total):
            ot = overall_total if overall_total and overall_total > 0 else 1
            pb_total["maximum"] = ot
            pb_total["value"] = min(overall_done, ot)
            pct = int((overall_done / ot) * 100) if ot else 0
            lbl_left.config(text=f"{pct}% ({self._fmt_bytes(overall_done)} / {self._fmt_bytes(ot)})")

            ft = file_total if file_total and file_total > 0 else 1
            pb_file["maximum"] = ft
            pb_file["value"] = min(file_done, ft)

            now = time.time()
            dt = max(0.001, now - state["last_t"])
            db = max(0, overall_done - state["last_b"])
            inst_speed = db / dt
            state["speed"] = (state["speed"] * 0.80) + (inst_speed * 0.20)
            state["last_t"] = now
            state["last_b"] = overall_done

            eta = "--:--"
            if ot > 0 and state["speed"] > 1:
                eta = self._fmt_eta((ot - overall_done) / state["speed"])
            lbl_right.config(text=f"{self._fmt_bytes(state['speed'])}/s • ETA {eta}")

        def worker():
            ssh = None
            err = None
            total_bytes = 0
            sizes = []
            dl_fail_note = [""]
            verify_bad = []
            verify_checked = 0

            def connect_ssh_dl():
                nonlocal ssh
                if ssh is not None:
                    try:
                        ssh.close()
                    except Exception:
                        pass
                    time.sleep(0.12)
                pk = _paramiko()
                ssh = pk.SSHClient()
                ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
                ssh.connect(
                    self.entry_ip.get(),
                    **self._ssh_connect_kwargs(
                        timeout=30,
                        banner_timeout=60,
                        auth_timeout=60,
                        look_for_keys=False,
                        allow_agent=False,
                        compress=False,
                    ),
                )
                self._paramiko_tune_fast_transfer(ssh, for_upload=False)

            try:
                connect_ssh_dl()

                for remote_path, _lp in pairs:
                    if cancel_evt.is_set():
                        raise RuntimeError("Download abgebrochen")
                    fsz = self._remote_file_size_via_ssh(ssh, remote_path)
                    sizes.append(fsz)
                    total_bytes += max(fsz, 1)

                done_b = 0
                for idx, (remote_path, local_path) in enumerate(pairs, start=1):
                    if cancel_evt.is_set():
                        raise RuntimeError("Download abgebrochen")

                    fsz = sizes[idx - 1]
                    progress["file_base"] = done_b
                    progress["file_size"] = fsz

                    parent = os.path.dirname(local_path)
                    if parent:
                        os.makedirs(self._win_long_path_local(parent), exist_ok=True)

                    dl_fail_note[0] = (
                        f"Datei [{idx}/{len(pairs)}]\n"
                        f"NAS:   {remote_path}\n"
                        f"Lokal: {local_path}"
                    )
                    self.root.after(0, lambda r=remote_path, lp=local_path, i=idx, n=len(pairs): lbl_file.config(text=f"[{i}/{n}] {r} → {lp}"))

                    def cb(transferred, total, _done=done_b, _fsz=fsz, _tb=total_bytes):
                        if cancel_evt.is_set():
                            raise RuntimeError("Download abgebrochen")
                        ttot = total if total and total > 0 else _fsz
                        overall_done = _done + transferred
                        self.root.after(0, lambda od=overall_done, ot=_tb, fd=transferred, ft=ttot: ui_update(od, ot, fd, ft))

                    attempt = 0
                    while True:
                        attempt += 1
                        try:
                            self._download_remote_file_via_ssh_cat(
                                ssh,
                                remote_path,
                                local_path,
                                callback=cb,
                                expected_size=fsz,
                            )
                            lpv = self._win_long_path_local(local_path)
                            lsz = os.path.getsize(lpv) if os.path.isfile(lpv) else -1
                            verify_checked += 1
                            if int(lsz) != int(fsz):
                                verify_bad.append((remote_path, local_path, fsz, lsz))
                            break
                        except RuntimeError:
                            raise
                        except Exception as e:
                            if cancel_evt.is_set():
                                raise RuntimeError("Download abgebrochen")
                            if attempt >= 6 or not self._is_transfer_connection_lost(e):
                                raise
                            try:
                                lp = self._win_long_path_local(local_path)
                                if os.path.isfile(lp):
                                    os.remove(lp)
                            except OSError:
                                pass
                            time.sleep(0.35 + 0.15 * attempt)
                            connect_ssh_dl()
                    done_b += max(fsz, 1)
                    self.root.after(0, lambda od=done_b, ot=total_bytes, fd=fsz, ft=fsz: ui_update(od, ot, fd, ft))

            except Exception as e:
                err = e
            finally:
                try:
                    if ssh:
                        ssh.close()
                except Exception:
                    pass

            def done():
                try:
                    btn_cancel.config(state="disabled")
                except Exception:
                    pass
                try:
                    pw.destroy()
                except Exception:
                    pass
                if err:
                    if cancel_evt.is_set():
                        messagebox.showinfo(self.t("msg.download_title"), self.t("msg.download_aborted"))
                        append_transfer_log(
                            self._app_data_dir(),
                            self.t("msg.transfer_log_download_aborted", n=len(pairs)),
                            "INFO",
                        )
                    else:
                        note = dl_fail_note[0] if dl_fail_note[0] else ""
                        body = str(err) if err else self.t("msg.transfer_unknown_error")
                        if note:
                            body = f"{body}\n\n{note}"
                        messagebox.showerror(self.t("msg.download_failed_title"), body)
                        append_transfer_log(
                            self._app_data_dir(),
                            self.t("msg.transfer_log_download_error", body=body[:500]),
                            "ERROR",
                        )
                else:
                    if verify_bad:
                        lines = []
                        for r, lp, exs, got in verify_bad[:8]:
                            lines.append(
                                self.t(
                                    "msg.download_verify_line",
                                    path=r,
                                    expected=exs,
                                    local=got,
                                    local_path=lp,
                                )
                            )
                        more_suffix = ""
                        if len(verify_bad) > 8:
                            more_suffix = self.t("msg.transfer_verify_more", n=len(verify_bad) - 8)
                        messagebox.showwarning(
                            self.t("msg.download_verify_warn_title"),
                            self.t(
                                "msg.upload_verify_warn_body",
                                n_files=len(pairs),
                                checked=verify_checked,
                                mismatches=len(verify_bad),
                                details="\n".join(lines),
                                more_suffix=more_suffix,
                            ),
                        )
                        append_transfer_log(
                            self._app_data_dir(),
                            self.t(
                                "msg.transfer_log_download_warn",
                                n_files=len(pairs),
                                n_bad=len(verify_bad),
                            ),
                            "WARN",
                        )
                    else:
                        messagebox.showinfo(
                            self.t("msg.download_title"),
                            self.t(
                                "msg.download_complete",
                                n_files=len(pairs),
                                checked=verify_checked,
                            ),
                        )
                        append_transfer_log(
                            self._app_data_dir(),
                            self.t(
                                "msg.transfer_log_download_ok",
                                n_files=len(pairs),
                                checked=verify_checked,
                            ),
                            "INFO",
                        )
                    self.root.after(200, self.explorer_local_refresh)

            self.root.after(0, done)

        pw.protocol("WM_DELETE_WINDOW", on_cancel)
        threading.Thread(target=worker, daemon=True).start()
