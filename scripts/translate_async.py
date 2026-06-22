#!/usr/bin/env python3
"""Async batch translate — submit job, poll status, download ZIP artifact."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

API_KEY = os.environ["API_KEY"]
TARGET_LANG = os.environ["TARGET_LANG"]
API_BASE = os.environ["API_BASE"].rstrip("/")
ACCEPT_LANG = os.environ.get("ACCEPT_LANG", "en")
FAIL_ON_VALIDATION = os.environ.get("FAIL_ON_VALIDATION", "false").lower() == "true"
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "5"))
POLL_TIMEOUT_SECONDS = int(os.environ.get("POLL_TIMEOUT_SECONDS", "1800"))

FILES: list[str] = json.loads(os.environ.get("FILE_LIST_JSON", "[]"))


def request(method: str, path: str, body: dict | None = None, timeout: int = 120) -> tuple[int, dict | bytes]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept-Language": ACCEPT_LANG,
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if path.endswith("/download"):
            return resp.status, raw
        return resp.status, json.loads(raw.decode())


def write_outputs(files_written: int, validation_warnings: int) -> None:
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"files-count={len(FILES)}\n")
            f.write(f"files-written={files_written}\n")
            f.write(f"validation-warnings={validation_warnings}\n")


def main() -> None:
    if not FILES:
        print("::error::No files to translate", file=sys.stderr)
        sys.exit(1)

    payload_files = []
    path_by_name: dict[str, str] = {}
    for fp in FILES:
        p = Path(fp)
        payload_files.append({"name": p.name, "content": p.read_text(encoding="utf-8")})
        path_by_name[p.name] = str(p)

    try:
        status, data = request(
            "POST",
            "/v1/tools/json-translate/batch/async",
            {"target_lang": TARGET_LANG, "files": payload_files},
        )
    except urllib.error.HTTPError as e:
        print(f"::error::Routara async submit HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    if status not in (200, 202):
        print(f"::error::Unexpected submit status {status}: {data}", file=sys.stderr)
        sys.exit(1)

    job_id = data.get("job_id") or data.get("id")
    if not job_id:
        print(f"::error::No job_id in response: {data}", file=sys.stderr)
        sys.exit(1)

    print(f"Async job queued: {job_id}")
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    job: dict = {}
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            _, job = request("GET", f"/v1/tools/jobs/{job_id}")
        except urllib.error.HTTPError as e:
            print(f"::error::Poll failed HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
            sys.exit(1)
        st = job.get("status", "")
        done = job.get("progress_done", 0)
        total = job.get("file_count", len(FILES))
        print(f"Job {job_id}: {st} ({done}/{total})")
        if st == "completed":
            break
        if st == "failed":
            print(f"::error::Job failed: {job.get('error_text', 'unknown')}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"::error::Job timed out after {POLL_TIMEOUT_SECONDS}s", file=sys.stderr)
        sys.exit(1)

    validation_warnings = 0
    files_written = 0

    download_url = job.get("download_url")
    if download_url:
        try:
            _, blob = request("GET", download_url.replace(API_BASE, ""), timeout=300)
            if isinstance(blob, bytes):
                with zipfile.ZipFile(BytesIO(blob)) as zf:
                    for name in zf.namelist():
                        target = path_by_name.get(Path(name).name, name)
                        Path(target).write_bytes(zf.read(name))
                        files_written += 1
                        print(f"Wrote {target} (from zip)")
        except Exception as e:
            print(f"::warning::ZIP download failed, falling back to results JSON: {e}", file=sys.stderr)

    if files_written == 0:
        results = job.get("results") or []
        for row in results:
            name = row.get("name")
            if not name:
                continue
            if row.get("error"):
                print(f"::error::FAIL {name}: {row['error']}", file=sys.stderr)
                sys.exit(1)
            if not row.get("validation_passed", True):
                validation_warnings += 1
                if FAIL_ON_VALIDATION:
                    print(f"::error::Validation failed for {name}", file=sys.stderr)
                    sys.exit(1)
            target = path_by_name.get(name, name)
            Path(target).write_text(row.get("output") or "", encoding="utf-8")
            files_written += 1
            print(f"Wrote {target}")

    write_outputs(files_written, validation_warnings)
    print(f"Async job complete — {files_written}/{len(FILES)} files")


if __name__ == "__main__":
    main()
