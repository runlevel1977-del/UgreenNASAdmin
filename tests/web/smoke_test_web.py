import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8088"


def get(path):
    req = urllib.request.Request(BASE + path, method="GET")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def main():
    checks = ["/", "/api/healthz", "/api/auth/bootstrap"]
    ok = True
    for c in checks:
        try:
            status, body = get(c)
            print(c, status)
            if status != 200:
                ok = False
            if c.endswith("bootstrap"):
                json.loads(body)
        except (urllib.error.URLError, json.JSONDecodeError) as e:
            ok = False
            print("ERROR", c, e)
    if not ok:
        raise SystemExit(1)
    print("Smoke test OK")


if __name__ == "__main__":
    main()
