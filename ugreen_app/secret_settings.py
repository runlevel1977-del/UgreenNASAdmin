"""Local settings secrets in a native OS vault; JSON contains opaque references."""
import copy
import json
from pathlib import Path
import re
import threading
import uuid

from ugreen_app.private_json import write_private_json

SERVICE = "UgreenNASAdmin.Settings"
REFERENCE = "$ugreen_secret"
SECRET_FIELDS = frozenset({"password", "ssh_key_passphrase", "bot_token", "smtp_pass", "smtp_password"})
_lock = threading.RLock()
_failed_reads = set()


class SecretStorageError(RuntimeError):
    pass


def _backend():
    try:
        import keyring
        backend = keyring.get_keyring()
        # Do not silently use a plaintext/file fallback supplied by another plugin.
        if type(backend).__module__ not in {
            "keyring.backends.Windows", "keyring.backends.macOS",
            "keyring.backends.SecretService", "keyring.backends.kwallet", "keyring.backends.libsecret",
        }:
            raise ValueError("Unsupported vault")
        return backend
    except Exception:
        raise SecretStorageError("OS-Tresor nicht verfügbar. Geheimnisse und bisherige Einstellungen wurden nicht ersetzt.") from None


def _reference(node):
    if isinstance(node, dict) and REFERENCE in node:
        ref = node[REFERENCE]
        if set(node) != {REFERENCE} or not isinstance(ref, str) or not re.fullmatch(r"[0-9a-f]{32}", ref):
            raise SecretStorageError("Ungültiger Tresorverweis; Einstellungen bleiben unverändert.")
        return ref
    return None


def _get(ref):
    try:
        value = _backend().get_password(SERVICE, ref)
        if not isinstance(value, str) or not value:
            raise ValueError("Missing vault entry")
        return value
    except Exception:
        raise SecretStorageError("Gespeichertes Geheimnis im OS-Tresor nicht verfügbar. Einstellungen bleiben unverändert.") from None


def _resolve(node):
    ref = _reference(node)
    if ref:
        return _get(ref)
    if isinstance(node, dict):
        return {key: _resolve(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_resolve(value) for value in node]
    return node


def _contains_plaintext(node):
    if isinstance(node, dict):
        return any((key in SECRET_FIELDS and isinstance(value, str) and bool(value))
                   or _contains_plaintext(value) for key, value in node.items())
    return isinstance(node, list) and any(_contains_plaintext(value) for value in node)


def _read_raw(path):
    if Path(path).is_symlink():
        raise SecretStorageError("Konfiguration ist ein symbolischer Link; Zugriff abgebrochen.")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def _protect(node, previous, created):
    if isinstance(node, dict):
        if _reference(node):
            _get(node[REFERENCE])
            return copy.deepcopy(node)
        old = previous if isinstance(previous, dict) else {}
        result = {}
        for key, value in node.items():
            if key in SECRET_FIELDS and not isinstance(value, str) and not _reference(value):
                raise SecretStorageError("Ungültiges Geheimnisfeld; Einstellungen bleiben unverändert.")
            if key in SECRET_FIELDS and isinstance(value, str) and value:
                prior = old.get(key)
                ref = _reference(prior)
                if ref and _get(ref) == value:
                    result[key] = copy.deepcopy(prior)
                    continue
                ref = uuid.uuid4().hex
                try:
                    backend = _backend()
                    backend.set_password(SERVICE, ref, value)
                    created.append((backend, ref))
                    if backend.get_password(SERVICE, ref) != value:
                        raise ValueError("Vault readback failed")
                except Exception:
                    raise SecretStorageError("Geheimnis konnte nicht sicher im OS-Tresor gespeichert werden. Bisherige Datei bleibt erhalten.") from None
                result[key] = {REFERENCE: ref}
            else:
                result[key] = _protect(value, old.get(key), created)
        return result
    if isinstance(node, list):
        old = previous if isinstance(previous, list) else []
        return [_protect(value, old[i] if i < len(old) else None, created) for i, value in enumerate(node)]
    return node


def write_settings_json(path, value):
    # Check serializability before any vault or filesystem mutation.
    json.dumps(value)
    created = []
    with _lock:
        try:
            if str(Path(path).absolute()) in _failed_reads:
                raise SecretStorageError("Einstellungen zuerst erfolgreich neu laden; Speichern von Ersatzwerten ist gesperrt.")
            previous = _read_raw(path)
            # A loader may have fallen back to defaults. Never overwrite missing vault references.
            _resolve(previous)
            protected = _protect(value, previous, created)
            write_private_json(path, protected)
        except Exception:
            # Only fresh references are ours to discard. Existing vault entries are immutable.
            for backend, ref in created:
                try:
                    backend.delete_password(SERVICE, ref)
                except Exception:
                    pass
            raise


def read_settings_json(path):
    with _lock:
        identity = str(Path(path).absolute())
        try:
            raw = _read_raw(path)
            value = _resolve(raw)
            _failed_reads.discard(identity)
            if _contains_plaintext(raw):
                # Migration removes plaintext only after vault readback and atomic publication.
                write_settings_json(path, value)
            return value
        except Exception:
            _failed_reads.add(identity)
            raise


def migrate_settings_directory(directory):
    errors = []
    for name in ("app_settings.json", "telegram_notify.json", "qnap_smb_prefs.json",
                 "nas_watch_local.json", "nas_daily_report_local.json"):
        path = Path(directory) / name
        if path.exists():
            try:
                read_settings_json(path)
            except Exception:
                errors.append(name)
    return errors
