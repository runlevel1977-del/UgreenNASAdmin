"""Vergleicht nas_admin Schlüssel zwischen EN-Block in i18n und Locale-Modul."""
import importlib
import re
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))


def en_keys() -> set[str]:
    t = (root / "ugreen_app" / "i18n.py").read_text(encoding="utf-8")
    m = re.search(
        r'"nas_admin\.title": "NAS management \(actions\)",.*?(?=\n        "nas2nas\.toolbar_ugreen")',
        t,
        re.S,
    )
    assert m
    # Erste Zeile beginnt direkt mit "nas_admin.title" (ohne führende Einrückung im Slice).
    return set(
        re.findall(r'(?:^|\n)\s*"(nas_admin\.[^"]+)":\s', m.group(0))
    )


def main(mod: str) -> int:
    keys_en = en_keys()
    m = importlib.import_module(mod)
    name = [x for x in dir(m) if x.startswith("NAS_ADMIN_")][0]
    d = getattr(m, name)
    miss = keys_en - set(d)
    extra = set(d) - keys_en
    if miss or extra:
        print(mod, "MISSING", sorted(miss))
        print(mod, "EXTRA", sorted(extra))
        return 1
    print(mod, "OK", len(d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
