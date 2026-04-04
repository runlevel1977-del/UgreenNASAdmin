# -*- coding: utf-8 -*-
"""Analyse von Docker-Compose / docker run — Variablen, Volumes, Ports, -e für UI-Assistent."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DockerDeployVar:
    """Eine editierbare Größe aus dem Skript."""

    id: str
    kind: str  # placeholder | volume | port | env
    default: str
    # Ersetzung: bei placeholder der Name ohne ${}
    name: str = ""
    # Bei volume: Präfix vor Host-Pfad, Host-Pfad, Suffix ab erstem : (inkl. :) bis Zeilenende
    vol_prefix: str = ""
    vol_host: str = ""
    vol_tail: str = ""  # :/container[:ro]
    # Bei port: kompletter ursprünglicher Mapping-String innerhalb der Zeile
    port_full: str = ""
    port_container: str = ""
    # Bei env: KEY=
    env_key: str = ""


def _uniq_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _extract_placeholders(text: str) -> list[str]:
    a = re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", text)
    b = re.findall(r"(?<!\$)\$([A-Za-z_][A-Za-z0-9_]*)\b", text)
    return _uniq_preserve([*a, *b])


def _looks_like_path(s: str) -> bool:
    s = s.strip()
    return s.startswith("/") or s.startswith("./") or s.startswith("~/")


def _parse_volume_line(line: str, *, run_style: bool) -> tuple[str, str, str] | None:
    """
    Zerlegt list item oder -v Zeile in (prefix_vor_host, host, tail_ab_erstem_doppelpunkt).
    tail beginnt mit ':' und enthält Container-Pfad und optional :ro
    """
    raw = line.rstrip()
    if run_style:
        m = re.match(
            r"^(\s*-v\s+)([^\s]+)(:\S+.*?)(?:\s|$)",
            raw,
            re.IGNORECASE,
        )
        if not m:
            m = re.match(
                r"^(\s*--volume\s+)([^\s]+)(:\S+.*?)(?:\s|$)",
                raw,
                re.IGNORECASE,
            )
        if m:
            return m.group(1), m.group(2), m.group(3)
        return None
    # compose list: - /host:/c or - "/host:/c"
    m = re.match(r'^(\s*-\s+["\']?)([^:"\']+)(:\S+.*?)(?:\s*)$', raw)
    if m and _looks_like_path(m.group(2)):
        return m.group(1), m.group(2), m.group(3)
    m2 = re.match(r'^(\s*-\s+)([^\s]+)(:\S+.*?)(?:\s*)$', raw)
    if m2 and _looks_like_path(m2.group(2)):
        return m2.group(1), m2.group(2), m2.group(3)
    return None


def _iter_compose_volume_lines(text: str) -> list[tuple[int, int, str]]:
    """Findet YAML-Zeilen unter volumes: die wie Bind-Mounts aussehen."""
    lines = text.splitlines()
    in_vol = False
    vol_indent: int | None = None
    hits: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)
        if re.match(r"^volumes:\s*$", stripped):
            in_vol = True
            vol_indent = indent
            continue
        if in_vol and vol_indent is not None:
            if indent <= vol_indent and not stripped.startswith("-"):
                in_vol = False
                vol_indent = None
                continue
            if stripped.startswith("-"):
                parsed = _parse_volume_line(line, run_style=False)
                if parsed:
                    pfx, host, tail = parsed
                    if ":" in tail and _looks_like_path(host):
                        hits.append((i, len(line), line))
    return hits


def _compose_bind_sources(text: str) -> list[tuple[str, str]]:
    """type: bind + source: /path (einfaches Muster)."""
    out: list[tuple[str, str]] = []
    for m in re.finditer(
        r"type:\s*bind\s*\n\s*source:\s*(/\S+)\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    ):
        src = m.group(1).strip()
        out.append((src, m.group(0)))
    return out


def _docker_run_volume_lines(text: str) -> list[str]:
    lines: list[str] = []
    for m in re.finditer(r"-v\s+(\S+:\S+)", text, re.IGNORECASE):
        chunk = m.group(1)
        if ":" in chunk:
            host = chunk.split(":", 1)[0]
            if _looks_like_path(host):
                lines.append("-v " + chunk)
    for m in re.finditer(r"--volume\s+(\S+:\S+)", text, re.IGNORECASE):
        chunk = m.group(1)
        host = chunk.split(":", 1)[0]
        if _looks_like_path(host):
            lines.append("--volume " + chunk)
    return _uniq_preserve(lines)


def _extract_port_mappings(text: str, *, is_compose: bool) -> list[tuple[str, str]]:
    """
    Liefert (original_mapping_string, container_port) für Host-Port-Ersatz.
    original z.B. 8080:80 oder 127.0.0.1:8080:80
    """
    found: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(orig: str, cport: str) -> None:
        if orig not in seen:
            seen.add(orig)
            found.append((orig, cport))

    if is_compose:
        for m in re.finditer(
            r'-\s*["\']?((?:\d{1,3}\.){3}\d{1,3}:)?(\d+):(\d+)/?(?:tcp|udp)?["\']?',
            text,
            re.IGNORECASE,
        ):
            ip, h, c = m.group(1) or "", m.group(2), m.group(3)
            orig = f"{ip}{h}:{c}".replace("None", "") if ip else f"{h}:{c}"
            add(orig.strip(), c)
    # docker run -p
    for m in re.finditer(
        r"-p\s+((?:\d{1,3}\.){3}\d{1,3}:)?(\d+):(\d+)(?:/(tcp|udp))?",
        text,
        re.IGNORECASE,
    ):
        ip, h, c = m.group(1) or "", m.group(2), m.group(3)
        orig = f"{ip}{h}:{c}" if ip else f"{h}:{c}"
        add(orig, c)
    return found


def _extract_env_assignments(text: str) -> list[tuple[str, str]]:
    """-e KEY=VALUE oder --env KEY=VALUE; nur wenn VALUE leer oder Pfad oder auffällig."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in re.finditer(
        r"(?:-e|--env)\s+([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)",
        text,
        re.IGNORECASE,
    ):
        k, v = m.group(1), m.group(2)
        if k in seen:
            continue
        seen.add(k)
        if "${" in v or re.match(r"^\$[A-Za-z_]", v):
            continue
        if v == '""' or v == "''" or _looks_like_path(v):
            out.append((k, v))
    return out


def analyze_docker_text(content: str) -> tuple[list[DockerDeployVar], bool]:
    """
    Erkennt Compose (heuristisch) oder Run-CLI.
    Rückgabe: Variablenliste, is_compose
    """
    t = content.strip()
    if not t:
        return [], False
    is_compose = bool(
        re.search(r"(?m)^version:\s*[\"']?[0-9]", t)
        or re.search(r"(?m)^services:\s*$", t)
        or (t.startswith("services:") and "image:" in t)
    )
    vars_list: list[DockerDeployVar] = []
    used_ids: set[str] = set()

    def vid(base: str) -> str:
        b = re.sub(r"[^a-zA-Z0-9_]+", "_", base)[:40] or "x"
        s = b
        n = 0
        while s in used_ids:
            n += 1
            s = f"{b}_{n}"
        used_ids.add(s)
        return s

    for name in _extract_placeholders(t):
        vars_list.append(
            DockerDeployVar(
                id=vid(f"p_{name}"),
                kind="placeholder",
                default="",
                name=name,
            )
        )

    vol_idx = 0
    if is_compose:
        for i, _ln_len, line in _iter_compose_volume_lines(t):
            parsed = _parse_volume_line(line, run_style=False)
            if not parsed:
                continue
            pfx, host, tail = parsed
            vars_list.append(
                DockerDeployVar(
                    id=vid(f"vol_{vol_idx}"),
                    kind="volume",
                    default=host,
                    vol_prefix=pfx,
                    vol_host=host,
                    vol_tail=tail,
                    name=f"compose L{i+1}",
                )
            )
            vol_idx += 1
        seen_bind: set[str] = set()
        for src, _block in _compose_bind_sources(t):
            if src in seen_bind:
                continue
            seen_bind.add(src)
            vars_list.append(
                DockerDeployVar(
                    id=vid(f"vol_{vol_idx}"),
                    kind="volume",
                    default=src,
                    vol_prefix="__SOURCE_LINE__",
                    vol_host=src,
                    vol_tail="",
                    name="bind source",
                )
            )
            vol_idx += 1
    else:
        for part in _docker_run_volume_lines(t):
            parsed = _parse_volume_line(part, run_style=True)
            if not parsed:
                continue
            pfx, host, tail = parsed
            vars_list.append(
                DockerDeployVar(
                    id=vid(f"vol_{vol_idx}"),
                    kind="volume",
                    default=host,
                    vol_prefix=pfx,
                    vol_host=host,
                    vol_tail=tail,
                    name=f"run {vol_idx+1}",
                )
            )
            vol_idx += 1

    for orig, cport in _extract_port_mappings(t, is_compose=is_compose):
        hpart = orig.rsplit(":", 1)[0]
        if ":" in hpart and re.match(r"^\d{1,3}\.", hpart):
            host_default = hpart.rsplit(":", 1)[-1]
        else:
            host_default = hpart
        vars_list.append(
            DockerDeployVar(
                id=vid(f"port_{orig}"),
                kind="port",
                default=host_default,
                port_full=orig,
                port_container=cport,
                name=orig,
            )
        )

    for k, v in _extract_env_assignments(t):
        vars_list.append(
            DockerDeployVar(
                id=vid(f"env_{k}"),
                kind="env",
                default=v,
                env_key=k,
                name=k,
            )
        )

    return vars_list, is_compose


def apply_docker_vars(content: str, variables: list[DockerDeployVar], values: dict[str, str]) -> str:
    """Wendet alle Ersetzungen auf den Text an (von hinten/vorsichtig pro Kind)."""
    out = content
    for v in variables:
        val = (values.get(v.id) if values.get(v.id) is not None else v.default) or ""
        if v.kind == "placeholder" and v.name:
            out = re.sub(r"\$\{" + re.escape(v.name) + r"\}", val, out)
            # $VAR aber nicht ${VAR} (sonst bricht ${NAME})
            out = re.sub(r"(?<!\$)\$(?!\{)" + re.escape(v.name) + r"\b", val, out)
        elif v.kind == "volume" and v.vol_prefix and v.vol_host is not None:
            if v.vol_prefix == "__SOURCE_LINE__":
                old = v.vol_host
                out = out.replace(f"source: {old}", f"source: {val}", 1)
                out = out.replace(f"source:{old}", f"source: {val}", 1)
            else:
                old_line = f"{v.vol_prefix}{v.vol_host}{v.vol_tail}"
                new_line = f"{v.vol_prefix}{val}{v.vol_tail}"
                if old_line in out:
                    out = out.replace(old_line, new_line, 1)
        elif v.kind == "port" and v.port_full and v.port_container:
            old = v.port_full
            parts = old.rsplit(":", 2)
            if len(parts) == 3 and re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", parts[0]):
                new_map = f"{parts[0]}:{val}:{parts[2]}"
            elif len(parts) == 2:
                new_map = f"{val}:{parts[1]}"
            elif len(parts) == 3:
                new_map = f"{parts[0]}:{val}:{parts[2]}"
            else:
                new_map = old
            if old in out:
                out = out.replace(old, new_map, 1)
        elif v.kind == "env" and v.env_key:
            old_pat = re.compile(
                r"((?:-e|--env)\s+" + re.escape(v.env_key) + r"=)([^\s]+)",
                re.IGNORECASE,
            )

            def _esub(m: re.Match[str]) -> str:
                return m.group(1) + val

            out, n = old_pat.subn(_esub, out, count=1)
    return out


def list_bind_host_paths(text: str) -> list[str]:
    """Alle Host-Pfade aus Bind-Mounts (nach Platzhalter-Ersetzung) — für mkdir auf dem NAS."""
    paths: list[str] = []
    for m in re.finditer(r'-\s+["\']?(/[^:"\']+):', text):
        p = m.group(1).strip()
        if p.startswith("/"):
            paths.append(p)
    for m in re.finditer(r"(?:^|\s)-v\s+(/[^\s:]+):", text, re.IGNORECASE):
        paths.append(m.group(1).strip())
    for m in re.finditer(r"(?:^|\s)--volume\s+(/[^\s:]+):", text, re.IGNORECASE):
        paths.append(m.group(1).strip())
    for m in re.finditer(r"^\s*source:\s*(/\S+)\s*$", text, re.MULTILINE):
        paths.append(m.group(1).strip())
    return _uniq_preserve([p for p in paths if p and not p.startswith("/var/lib/docker")])
