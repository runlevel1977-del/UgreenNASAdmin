from typing import Tuple

import nas_ssh
import paramiko

from app.services.config_store import get_settings

mgr = nas_ssh.SSHManager()


def run_cmd(cmd: str, use_sudo: bool = False) -> str:
    s = get_settings()
    return mgr.run(
        s.get("host", ""),
        s.get("user", ""),
        s.get("password", ""),
        cmd,
        ssh_port=int(s.get("port", 22)),
        ssh_use_key=bool(s.get("ssh_use_key", False)),
        ssh_key_path=s.get("ssh_key_path", ""),
        ssh_key_passphrase=s.get("ssh_key_passphrase", ""),
        use_sudo=use_sudo,
    )


def write_remote(path: str, text: str, use_sudo: bool = True) -> Tuple[bool, str]:
    s = get_settings()
    payload = (text + "\n").encode("utf-8")
    if use_sudo:
        return mgr.write_remote_file_sudo(
            s.get("host", ""),
            s.get("user", ""),
            s.get("password", ""),
            payload,
            path.strip(),
            chmod_mode="644",
            ssh_port=int(s.get("port", 22)),
            ssh_use_key=bool(s.get("ssh_use_key", False)),
            ssh_key_path=s.get("ssh_key_path", ""),
            ssh_key_passphrase=s.get("ssh_key_passphrase", ""),
        )
    return mgr.write_remote_file_user(
        s.get("host", ""),
        s.get("user", ""),
        s.get("password", ""),
        payload,
        path.strip(),
        ssh_port=int(s.get("port", 22)),
        ssh_use_key=bool(s.get("ssh_use_key", False)),
        ssh_key_path=s.get("ssh_key_path", ""),
        ssh_key_passphrase=s.get("ssh_key_passphrase", ""),
    )


def connect_client():
    s = get_settings()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = {
        "username": s.get("user", ""),
        "password": s.get("password", ""),
        "port": int(s.get("port", 22)),
        "timeout": 25,
        "banner_timeout": 40,
        "auth_timeout": 40,
        "look_for_keys": False,
        "allow_agent": False,
        "compress": False,
    }
    if s.get("ssh_use_key") and s.get("ssh_key_path"):
        kwargs["key_filename"] = s.get("ssh_key_path")
        if s.get("ssh_key_passphrase"):
            kwargs["passphrase"] = s.get("ssh_key_passphrase")
    ssh.connect(s.get("host", "").strip(), **kwargs)
    return ssh
