"""Pull today's fixtures + odds from TheStatsAPI.

Reads STATS_API_KEY from model/.env and NEVER prints it. Stdlib only (urllib),
so it runs in the bare venv. First job is schema discovery: hit the endpoint and
dump the shape of one match so we map odds fields to model markets without
guessing. The edge + half-Kelly computation is layered on once the shape is known.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENV = REPO / "model" / ".env"


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_json(url: str, key: str) -> tuple[int, object]:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read().decode())


def main() -> None:
    env = load_env(ENV)
    key = env.get("STATS_API_KEY", "")
    base = env.get("STATS_API_BASE", "https://api.thestatsapi.com/api").rstrip("/")
    if not key:
        print("STATS_API_KEY is empty in model/.env — paste your key there (no quotes) and re-run.")
        sys.exit(1)

    today = date.today().isoformat()
    url = f"{base}/football/matches?date_from={today}&date_to={today}"
    try:
        status, data = get_json(url, key)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {e.reason} — {url}")
        print(e.read().decode()[:600])
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"request failed: {e}\nurl: {url}")
        sys.exit(1)

    print(f"HTTP {status} | {url}")
    matches = data.get("data") if isinstance(data, dict) else data
    if isinstance(data, dict):
        print("top-level keys:", list(data))
    print("today's match count:", len(matches) if isinstance(matches, list) else "?")
    if isinstance(matches, list) and matches:
        m0 = matches[0]
        print("\nfirst match keys:", list(m0) if isinstance(m0, dict) else type(m0))
        print(json.dumps(m0, indent=2)[:3000])


if __name__ == "__main__":
    main()
