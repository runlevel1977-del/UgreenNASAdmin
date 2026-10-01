# -*- coding: utf-8 -*-
"""Wiederverwendbare SSH-Sitzung für kurze Befehle (run_ssh_cmd). Langläufer (Download/Upload) nutzen eigene Verbindungen."""

from __future__ import annotations

import base64
import hashlib
import io
import os
import posixpath
import re
import shlex
import threading
import uuid
from dataclasses import dataclass
from typing import Callable, Optional
import time

from ugreen_app.root_runtime import ROOT_RUNTIME_DIR, private_runtime_directory_code
from ugreen_app.ssh_host_keys import (
    HostKeyChangedError,
    HostKeyRejectedError,
    is_host_key_error,
    prepare_ssh_client,
    set_store_path as set_host_keys_store_path,
)

_paramiko_mod = None


def _atomic_root_write_code(path: str, mode: int, data_code: str) -> str:
    """Remote Python: publish a new root-owned inode only after a complete write."""
    if path.startswith(ROOT_RUNTIME_DIR + "/") and posixpath.dirname(path) != ROOT_RUNTIME_DIR:
        raise ValueError("Bundled helper files must be direct children of the private runtime directory")
    return (
        "import base64,hashlib,os,stat,tempfile\n"
        + (private_runtime_directory_code() if path.startswith(ROOT_RUNTIME_DIR + "/") else "")
        + data_code
        + "\n"
        + f"target = {path!r}\n"
        "if os.path.islink(target):\n"
        "    raise ValueError('Refusing symbolic-link destination')\n"
        "fd, temporary = tempfile.mkstemp(prefix='.ugreen-root-', dir=os.path.dirname(target))\n"
        "try:\n"
        "    with os.fdopen(fd, 'wb') as output:\n"
        "        output.write(data)\n"
        "        output.flush()\n"
        "        os.fsync(output.fileno())\n"
        "        os.fchown(output.fileno(), 0, 0)\n"
        + f"        os.fchmod(output.fileno(), {mode})\n"
        "    os.replace(temporary, target)\n"
        "finally:\n"
        "    if os.path.exists(temporary):\n"
        "        os.unlink(temporary)\n"
    )


def _paramiko():
    global _paramiko_mod
    if _paramiko_mod is None:
        import paramiko as p

        _paramiko_mod = p
    return _paramiko_mod


def _decode_out(data: bytes) -> str:
    if not data:
        return ""
    return data.decode("utf-8", errors="replace")


def quote_remote_bash_lc(script: str) -> str:
    """Einfachquoting für bash -lc auf dem *Linux-NAS* — unabhängig vom Client-OS (Windows-shlex.quote ist für cmd.exe und zerstört sudo-Pipelines)."""
    return "'" + script.replace("'", "'\"'\"'") + "'"


@dataclass(frozen=True)
class SSHRunResult:
    output: str
    exit_code: int
    ok: bool
    timed_out: bool = False
    connection_error: bool = False


def _read_stdout_stderr_with_timeout(stdout, stderr, *, deadline: float | None) -> tuple[str, str]:
    ch = stdout.channel
    out_chunks: list[bytes] = []
    err_chunks: list[bytes] = []
    while True:
        if deadline is not None and time.monotonic() > deadline:
            try:
                ch.close()
            except Exception:
                pass
            raise TimeoutError("SSH command timed out")
        if ch.recv_ready():
            out_chunks.append(ch.recv(65536))
        if ch.recv_stderr_ready():
            err_chunks.append(ch.recv_stderr(65536))
        if ch.exit_status_ready():
            while ch.recv_ready():
                out_chunks.append(ch.recv(65536))
            while ch.recv_stderr_ready():
                err_chunks.append(ch.recv_stderr(65536))
            break
        if not ch.recv_ready() and not ch.recv_stderr_ready():
            time.sleep(0.05)
    return _decode_out(b"".join(out_chunks)), _decode_out(b"".join(err_chunks))


class SSHManager:
    """Eine SSH-Verbindung pro Auth-Kontext, serialisiert mit Lock."""

    def __init__(self):
        self._client = None
        self._lock = threading.RLock()
        self._last_key: Optional[tuple] = None

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
            self._last_key = None

    def close_best_effort(self) -> None:
        """Beim App-Exit: nicht ewig auf laufenden Befehl warten (Windows „keine Rückmeldung“)."""
        acquired = self._lock.acquire(timeout=0.15)
        try:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
            self._last_key = None
        finally:
            if acquired:
                self._lock.release()

    def _ensure_client(
        self,
        host: str,
        user: str,
        password: str,
        *,
        ssh_port: int = 22,
        ssh_use_key: bool = False,
        ssh_key_path: str = "",
        ssh_key_passphrase: str = "",
    ) -> None:
        key = (
            host.strip(),
            user,
            password,
            int(ssh_port or 22),
            bool(ssh_use_key),
            (ssh_key_path or "").strip(),
            ssh_key_passphrase or "",
        )
        if self._client is not None and self._last_key == key:
            try:
                t = self._client.get_transport()
                if t is not None and t.is_active():
                    return
            except Exception:
                pass
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        pk = _paramiko()
        ssh = pk.SSHClient()
        prepare_ssh_client(ssh, host.strip(), int(ssh_port or 22))
        conn_kwargs = {
            "username": user,
            "password": password,
            "port": int(ssh_port or 22),
            "timeout": 12,
            "banner_timeout": 30,
            "auth_timeout": 30,
            "look_for_keys": False,
            "allow_agent": False,
            "compress": True,
        }
        key_path = (ssh_key_path or "").strip()
        if ssh_use_key and key_path:
            conn_kwargs["key_filename"] = key_path
            if ssh_key_passphrase:
                conn_kwargs["passphrase"] = ssh_key_passphrase
        try:
            ssh.connect(host.strip(), **conn_kwargs)
        except Exception as exc:
            if isinstance(exc, pk.BadHostKeyException):
                raise HostKeyChangedError.from_bad_host_key(
                    host.strip(), int(ssh_port or 22), exc
                ) from exc
            if is_host_key_error(exc):
                raise
            raise
        try:
            tr = ssh.get_transport()
            if tr is not None:
                # SSH-Idle-Timeouts vermeiden ⇒ weniger neue Sitzungen (= oft weniger NAS-„Login“-Meldungen).
                tr.set_keepalive(45)
        except Exception:
            pass
        self._client = ssh
        self._last_key = key

    def run_ex(
        self,
        host: str,
        user: str,
        password: str,
        cmd: str,
        *,
        ssh_port: int = 22,
        ssh_use_key: bool = False,
        ssh_key_path: str = "",
        ssh_key_passphrase: str = "",
        use_sudo: bool = False,
        command_timeout: int | None = 120,
        set_status: Optional[Callable[[str, object], None]] = None,
        connected_flag: bool = True,
        status_connected: Optional[str] = None,
        status_failed: Optional[str] = None,
        error_message_fmt: Optional[str] = None,
        timeout_message: Optional[str] = None,
    ) -> SSHRunResult:
        """Führt Befehl aus; liefert Exit-Code. command_timeout: Sekunden, 0/None = unbegrenzt."""
        ok_msg = status_connected or "SSH verbunden"
        fail_msg = status_failed or "SSH Fehler"
        err_fmt = error_message_fmt or "Fehler bei SSH-Verbindung: {err}"
        to_msg = timeout_message or "SSH-Befehl abgebrochen (Timeout)."
        unlimited = command_timeout is None or int(command_timeout) <= 0
        deadline = None if unlimited else time.monotonic() + max(1, int(command_timeout))
        with self._lock:
            try:
                self._ensure_client(
                    host,
                    user,
                    password,
                    ssh_port=ssh_port,
                    ssh_use_key=ssh_use_key,
                    ssh_key_path=ssh_key_path,
                    ssh_key_passphrase=ssh_key_passphrase,
                )
                if set_status:
                    set_status(ok_msg, connected=connected_flag)
                if use_sudo:
                    inner = cmd
                    full = f"sudo -S bash -lc {quote_remote_bash_lc(inner)}"
                    stdin, stdout, stderr = self._client.exec_command(full)
                    stdin.write((password or "") + "\n")
                    stdin.flush()
                    try:
                        stdin.channel.shutdown_write()
                    except Exception:
                        pass
                else:
                    stdin, stdout, stderr = self._client.exec_command(cmd)
                    try:
                        stdin.close()
                    except Exception:
                        pass
                try:
                    decoded_out, decoded_err = _read_stdout_stderr_with_timeout(stdout, stderr, deadline=deadline)
                except TimeoutError:
                    return SSHRunResult(
                        output=to_msg,
                        exit_code=-1,
                        ok=False,
                        timed_out=True,
                    )
                code = stdout.channel.recv_exit_status()
                if use_sudo and code == 0:
                    return SSHRunResult(output=decoded_out, exit_code=code, ok=True)
                combined = decoded_out + decoded_err
                return SSHRunResult(output=combined, exit_code=code, ok=(code == 0))
            except Exception as e:
                try:
                    self.close()
                except Exception:
                    pass
                if set_status:
                    set_status(fail_msg, connected=False)
                return SSHRunResult(
                    output=err_fmt.format(err=str(e)),
                    exit_code=-1,
                    ok=False,
                    connection_error=True,
                )

    def run(
        self,
        host: str,
        user: str,
        password: str,
        cmd: str,
        *,
        ssh_port: int = 22,
        ssh_use_key: bool = False,
        ssh_key_path: str = "",
        ssh_key_passphrase: str = "",
        use_sudo: bool = False,
        command_timeout: int | None = 120,
        set_status: Optional[Callable[[str, object], None]] = None,
        connected_flag: bool = True,
        status_connected: Optional[str] = None,
        status_failed: Optional[str] = None,
        error_message_fmt: Optional[str] = None,
        timeout_message: Optional[str] = None,
    ) -> str:
        """Führt Befehl aus. Bei sudo: Passwort über stdin an sudo -S (nicht in der Shell-Zeile)."""
        res = self.run_ex(
            host,
            user,
            password,
            cmd,
            ssh_port=ssh_port,
            ssh_use_key=ssh_use_key,
            ssh_key_path=ssh_key_path,
            ssh_key_passphrase=ssh_key_passphrase,
            use_sudo=use_sudo,
            command_timeout=command_timeout,
            set_status=set_status,
            connected_flag=connected_flag,
            status_connected=status_connected,
            status_failed=status_failed,
            error_message_fmt=error_message_fmt,
            timeout_message=timeout_message,
        )
        return res.output

    def pull_remote_file_via_exec(
        self,
        host: str,
        user: str,
        password: str,
        remote_posix_path: str,
        local_dest_path: str,
        *,
        ssh_port: int = 22,
        ssh_use_key: bool = False,
        ssh_key_path: str = "",
        ssh_key_passphrase: str = "",
        chunk_bytes: int = 1024 * 1024,
    ) -> None:
        """Datei ohne SFTP ziehen: gleiche Rechte wie Shell-SSH.

        Bei manchen NAS-Umgebungen ist SFTP chroot-gekoppelt; dann können Pfade unter
        /volume1 über SFTP fehlen oder leer wirken — `exec`/cat nutzt denselben
        Namensraum wie `run_ssh_cmd` / tar.
        """
        rp = str(remote_posix_path or "").strip()
        lp = os.path.abspath(str(local_dest_path or "").strip())
        if not rp:
            raise ValueError("remote_posix_path missing")
        if not lp:
            raise ValueError("local_dest_path missing")
        os.makedirs(os.path.dirname(lp) or ".", exist_ok=True)

        remote_cmd = f"/bin/cat {shlex.quote(rp)}"

        def _unlink_quiet(path: str) -> None:
            try:
                if path and os.path.isfile(path):
                    os.unlink(path)
            except OSError:
                pass

        with self._lock:
            self._ensure_client(
                host,
                user,
                password,
                ssh_port=ssh_port,
                ssh_use_key=ssh_use_key,
                ssh_key_path=ssh_key_path,
                ssh_key_passphrase=ssh_key_passphrase,
            )
            stdin, stdout, stderr = self._client.exec_command(remote_cmd)
            try:
                stdin.close()
            except Exception:
                pass
            cb = max(8192, int(chunk_bytes))
            tmp_path = lp + ".part"
            _unlink_quiet(tmp_path)
            try:
                with open(tmp_path, "wb") as out_f:
                    while True:
                        chunk = stdout.read(cb)
                        if not chunk:
                            break
                        out_f.write(chunk)
                err_msg = stderr.read() or b""
                code = stdout.channel.recv_exit_status()
                if code != 0:
                    snippet = err_msg.strip().decode("utf-8", errors="replace")[:900]
                    _unlink_quiet(tmp_path)
                    raise RuntimeError(
                        snippet or f"pull exit {code}"
                    )
            except Exception:
                _unlink_quiet(tmp_path)
                raise
            if os.path.isfile(lp):
                os.unlink(lp)
            os.replace(tmp_path, lp)
            if os.path.getsize(lp) <= 0:
                raise RuntimeError("Downloaded file is empty (remote path inaccessible via exec?).")

    def _remote_home_for_sftp(self, login_user: str) -> str:
        """HOME per SSH (ohne sudo). Fallback /home/<user> bzw. /root — für SFTP-Chroots ohne /tmp."""
        try:
            stdin, stdout, stderr = self._client.exec_command("printf %s \"$HOME\"")
            try:
                stdin.close()
            except Exception:
                pass
            home = _decode_out(stdout.read()).strip()
            stdout.channel.recv_exit_status()
            if home.startswith("/"):
                return home
        except Exception:
            pass
        u = (login_user or "").strip()
        if u == "root":
            return "/root"
        return f"/home/{u}"

    def _write_remote_file_sudo_base64(
        self,
        password: str,
        local_bytes: bytes,
        rp_final: str,
        chmod_mode: str,
    ) -> tuple[bool, str]:
        """Ohne SFTP: denselben atomaren Root-Schreibweg mit Base64 verwenden."""
        b64 = base64.b64encode(local_bytes).decode("ascii")
        try:
            mode_oct = int(str(chmod_mode).strip(), 8)
        except ValueError:
            return False, "Invalid file mode"
        py_code = _atomic_root_write_code(
            rp_final, mode_oct, f"data = base64.b64decode({b64!r}, validate=True)"
        )
        return self._exec_root_write_code(password, py_code)

    def _exec_root_write_code(self, password: str, py_code: str) -> tuple[bool, str]:
        # Neither helper source nor configuration values belong in argv (ps,
        # /proc/*/cmdline and ordinary sudo command logs can expose them).
        # sudo may consume the password line, or leave it on stdin when a
        # timestamp/NOPASSWD rule is active. A fresh marker handles both cases.
        marker = "UGREEN_STDIN_" + uuid.uuid4().hex
        bootstrap = (
            "import base64,hashlib,sys\n"
            f"marker = {marker.encode('ascii')!r} + b'\\n'\n"
            "stream = sys.stdin.buffer\n"
            "while True:\n"
            "    line = stream.readline()\n"
            "    if not line:\n"
            "        raise SystemExit('Missing root-write input')\n"
            "    if line == marker:\n"
            "        break\n"
            "source = base64.b64decode(stream.read(), validate=True)\n"
            f"if hashlib.sha256(source).hexdigest() != {hashlib.sha256(py_code.encode('utf-8')).hexdigest()!r}:\n"
            "    raise SystemExit('Incomplete root-write input')\n"
            "exec(compile(source, '<ugreen-root-write>', 'exec'))\n"
        )
        cmd = f"sudo -S -p '' /usr/bin/python3 -c {shlex.quote(bootstrap)}"
        stdin, stdout, stderr = self._client.exec_command(cmd)
        stdin.write((password or "") + "\n")
        stdin.write(marker + "\n")
        stdin.write(base64.b64encode(py_code.encode("utf-8")).decode("ascii"))
        stdin.flush()
        try:
            stdin.channel.shutdown_write()
        except Exception:
            pass
        out_b = stdout.read() or b""
        err_b = stderr.read() or b""
        code = stdout.channel.recv_exit_status()
        msg = (_decode_out(out_b) + _decode_out(err_b)).strip()
        if code != 0:
            return False, msg or f"exit {code}"
        return True, ""

    def write_remote_file_sudo(
        self,
        host: str,
        user: str,
        password: str,
        local_bytes: bytes,
        remote_final_path: str,
        *,
        chmod_mode: str = "644",
        ssh_port: int = 22,
        ssh_use_key: bool = False,
        ssh_key_path: str = "",
        ssh_key_passphrase: str = "",
    ) -> tuple[bool, str]:
        """Datei atomar als root veröffentlichen; SFTP-Staging oder Base64-Fallback."""
        rp_final = remote_final_path.strip()
        mode = str(chmod_mode).strip()
        if not posixpath.isabs(rp_final) or rp_final == "/" or "\x00" in rp_final:
            return False, "Absolute remote file path required"
        if not re.fullmatch(r"0?[0-7]{3}", mode):
            return False, "Invalid file mode (expected 000 through 777)"
        chmod_mode = mode
        with self._lock:
            try:
                self._ensure_client(
                    host,
                    user,
                    password,
                    ssh_port=ssh_port,
                    ssh_use_key=ssh_use_key,
                    ssh_key_path=ssh_key_path,
                    ssh_key_passphrase=ssh_key_passphrase,
                )
                home = self._remote_home_for_sftp(user)
                uid = uuid.uuid4().hex[:12]
                candidates = [
                    f"nas_admin_{uid}.upload",
                    f"{home}/.nas_admin_upload_{uid}.tmp",
                    f"/tmp/nas_admin_{uid}.tmp",
                ]
                tmp_abs: str | None = None
                staging_cand: str | None = None
                try:
                    sftp = self._client.open_sftp()
                except Exception:
                    return self._write_remote_file_sudo_base64(
                        password, local_bytes, rp_final, chmod_mode
                    )
                try:
                    for cand in candidates:
                        created = False
                        try:
                            with sftp.file(cand, "wx") as fh:
                                created = True
                                fh.chmod(0o600)
                                fh.write(local_bytes)
                            staging_cand = cand
                            if cand.startswith("/"):
                                tmp_abs = cand
                            else:
                                try:
                                    cwd = sftp.getcwd()
                                except Exception:
                                    cwd = None
                                if cwd:
                                    tmp_abs = posixpath.join(cwd, cand)
                                else:
                                    tmp_abs = posixpath.join(home, cand)
                            break
                        except OSError:
                            if created:
                                try:
                                    sftp.remove(cand)
                                except OSError:
                                    pass
                            continue
                finally:
                    try:
                        sftp.close()
                    except Exception:
                        pass

                if tmp_abs is None or staging_cand is None:
                    return self._write_remote_file_sudo_base64(
                        password, local_bytes, rp_final, chmod_mode
                    )

                data_code = (
                    f"source_fd = os.open({tmp_abs!r}, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)\n"
                    "with os.fdopen(source_fd, 'rb') as source:\n"
                    "    if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):\n"
                    "        raise ValueError('Staging source is not a regular file')\n"
                    + f"    data = source.read({len(local_bytes) + 1})\n"
                    + f"if hashlib.sha256(data).hexdigest() != {hashlib.sha256(local_bytes).hexdigest()!r}:\n"
                    "    raise ValueError('Staging content changed or upload incomplete')"
                )
                try:
                    return self._exec_root_write_code(
                        password, _atomic_root_write_code(rp_final, int(mode, 8), data_code)
                    )
                finally:
                    try:
                        cleanup_sftp = self._client.open_sftp()
                        try:
                            cleanup_sftp.remove(staging_cand)
                        finally:
                            cleanup_sftp.close()
                    except Exception:
                        pass
            except Exception as e:
                try:
                    self.close()
                except Exception:
                    pass
                return False, str(e)

    def write_remote_file_user(
        self,
        host: str,
        user: str,
        password: str,
        local_bytes: bytes,
        remote_path: str,
        *,
        ssh_port: int = 22,
        ssh_use_key: bool = False,
        ssh_key_path: str = "",
        ssh_key_passphrase: str = "",
    ) -> tuple[bool, str]:
        """Schreibt per SFTP direkt (ohne sudo), wenn der Nutzer Schreibrechte hat."""
        rp = remote_path.strip()
        with self._lock:
            try:
                self._ensure_client(
                    host,
                    user,
                    password,
                    ssh_port=ssh_port,
                    ssh_use_key=ssh_use_key,
                    ssh_key_path=ssh_key_path,
                    ssh_key_passphrase=ssh_key_passphrase,
                )
                sftp = self._client.open_sftp()
                try:
                    f = sftp.file(rp, "wb")
                    f.write(local_bytes)
                    f.close()
                finally:
                    try:
                        sftp.close()
                    except Exception:
                        pass
                return True, ""
            except Exception as e:
                return False, str(e)
