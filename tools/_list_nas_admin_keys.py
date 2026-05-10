import re
import pathlib

t = pathlib.Path(__file__).resolve().parent.parent.joinpath("ugreen_app", "i18n.py").read_text(encoding="utf-8")
m = re.search(r'"nas_admin\.title":.*?(?=\n        "sidebar\.subtitle")', t, re.S)
assert m, "EN nas_admin block not found"
keys = re.findall(r'^\s+"(nas_admin\.[^"]+)":\s', m.group(0), re.M)
print(len(keys))
for k in keys:
    print(k)
