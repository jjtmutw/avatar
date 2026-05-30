from __future__ import annotations

import sys
import time
from pathlib import Path

import requests


def download(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 16):
        existing = output.stat().st_size if output.exists() else 0
        headers = {"Range": f"bytes={existing}-"} if existing else {}
        try:
            with requests.get(url, headers=headers, stream=True, timeout=60) as response:
                if response.status_code == 416:
                    print(f"complete {output} ({existing} bytes)")
                    return
                if response.status_code not in (200, 206):
                    response.raise_for_status()
                mode = "ab" if response.status_code == 206 and existing else "wb"
                if mode == "wb":
                    existing = 0
                total = response.headers.get("content-length")
                print(f"attempt {attempt}: status={response.status_code} existing={existing} chunk={total}")
                written = existing
                with output.open(mode + "") as file:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            file.write(chunk)
                            written += len(chunk)
                            print(written, flush=True)
            return
        except Exception as exc:
            print(f"attempt {attempt} failed: {exc}")
            time.sleep(min(20, 2 * attempt))
    raise SystemExit(f"failed to download {url}")


if __name__ == "__main__":
    download(sys.argv[1], Path(sys.argv[2]))
