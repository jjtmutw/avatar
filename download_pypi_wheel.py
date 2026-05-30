from __future__ import annotations

import sys
from pathlib import Path

import requests

from download_with_resume import download


def pick_wheel(package: str, version: str) -> tuple[str, str]:
    data = requests.get(f"https://pypi.org/pypi/{package}/{version}/json", timeout=60).json()
    wheels = [file for file in data["urls"] if file["packagetype"] == "bdist_wheel"]
    preferred = []
    for file in wheels:
        name = file["filename"]
        score = 0
        if "cp310" in name:
            score += 50
        if "win_amd64" in name:
            score += 40
        if "py3-none-any" in name or "py2.py3-none-any" in name:
            score += 35
        if "abi3" in name and "win_amd64" in name:
            score += 20
        if score:
            preferred.append((score, file))
    if not preferred:
        raise SystemExit(f"No usable wheel for {package} {version}")
    preferred.sort(key=lambda item: item[0], reverse=True)
    file = preferred[0][1]
    return file["url"], file["filename"]


if __name__ == "__main__":
    package, version, out_dir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    url, filename = pick_wheel(package, version)
    print(url)
    download(url, out_dir / filename)
