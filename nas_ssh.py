# -*- coding: utf-8 -*-
"""Wiederverwendbare SSH-Sitzung für kurze Befehle (run_ssh_cmd). Langläufer (Download/Upload) nutzen eigene Verbindungen."""

from __future__ import annotations

import base64
import io
import posixpath
import shlex
import threading
import uuid
from typing import Callable, Optional

_paramiko_mod = None


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
        ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
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
        ssh.connect(host.strip(), **conn_kwargs)
        self._client = ssh
        self._last_key = key

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
        set_status: Optional[Callable[[str, object], None]] = None,
        connected_flag: bool = True,
        status_connected: Optional[str] = None,
        status_failed: Optional[str] = None,
        error_message_fmt: Optional[str] = None,
    ) -> str:
        """Führt Befehl aus. Bei sudo: Passwort über stdin an sudo -S (nicht in der Shell-Zeile)."""
        ok_msg = status_connected or "SSH verbunden"
        fail_msg = status_failed or "SSH Fehler"
        err_fmt = error_message_fmt or "Fehler bei SSH-Verbindung: {err}"
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
                    full = f"sudo -S bash -lc {shlex.quote(inner)}"
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
                out_b = stdout.read() or b""
                err_b = stderr.read() or b""
                code = stdout.channel.recv_exit_status()
                decoded_out = _decode_out(out_b)
                decoded_err = _decode_out(err_b)
                # sudo -S schreibt u. a. "[sudo] password for …:" auf stderr — nicht an echten Dateiinhalt hängen.
                if use_sudo and code == 0:
                    return decoded_out
                return decoded_out + decoded_err
            except Exception as e:
                try:
                    self.close()
                except Exception:
                    pass
                if set_status:
                    set_status(fail_msg, connected=False)
                return err_fmt.format(err=str(e))

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
        """Ohne SFTP: sudo python3 schreibt Datei (Base64). Für NAS ohne schreibbares SFTP-Ziel."""
        b64 = base64.b64encode(local_bytes).decode("ascii")
        try:
            mode_oct = int(str(chmod_mode).strip(), 8)
        except ValueError:
            mode_oct = 0o644
        rp = rp_final.strip()
        py_code = (
            f"import base64,os; p={rp!r}; data=base64.b64decode({b64!r}); "
            f"open(p,'wb').write(data); os.chmod(p,{mode_oct})"
        )
        cmd = f"sudo -S /usr/bin/python3 -c {shlex.quote(py_code)}"
        stdin, stdout, stderr = self._client.exec_command(cmd)
        stdin.write((password or "") + "\n")
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
        """SFTP-Staging (relativ / $HOME / /tmp) + sudo mv, oder Fallback ohne SFTP (Base64 + sudo python3)."""
        rp_final = remote_final_path.strip()
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
                try:
                    sftp = self._client.open_sftp()
                except Exception:
                    return self._write_remote_file_sudo_base64(
                        password, local_bytes, rp_final, chmod_mode
                    )
                try:
                    for cand in candidates:
                        try:
                            fh = sftp.file(cand, "wb")
                            fh.write(local_bytes)
                            fh.close()
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
                            continue
                finally:
                    try:
                        sftp.close()
                    except Exception:
                        pass

                if tmp_abs is None:
                    return self._write_remote_file_sudo_base64(
                        password, local_bytes, rp_final, chmod_mode
                    )

                inner = (
                    f"mv {shlex.quote(tmp_abs)} {shlex.quote(rp_final)} "
                    f"&& chmod {shlex.quote(str(chmod_mode))} {shlex.quote(rp_final)}"
                )
                full = f"sudo -S bash -lc {shlex.quote(inner)}"
                stdin, stdout, stderr = self._client.exec_command(full)
                stdin.write((password or "") + "\n")
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
