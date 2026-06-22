#!/usr/bin/env python3
"""Sync batch translate — chunks requests to respect per-request file caps."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_KEY = os.environ["API_KEY"]
TARGET_LANG = os.environ["TARGET_LANG"]
API_BASE = os.environ["API_BASE"].rstrip("/")
ACCEPT_LANG = os.environ.get("ACCEPT_LANG", "en")
FAIL_ON_VALIDATION = os.environ.get("FAIL_ON_VALIDATION", "false").lower() == "true"
CHUNK = int(os.environ.get("MAX_FILES_PER_REQUEST", "5"))
FILES: list[str] = json.loads(os.environ.get("FILE_LIST_JSON", "[]"))


def api_post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept-Language": ACCEPT_LANG,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode())


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

    files_written = 0
    validation_warnings = 0
    path_by_name = {Path(fp).name: fp for fp in FILES}

    for i in range(0, len(FILES), CHUNK):
        chunk_paths = FILES[i : i + CHUNK]
        payload_files = []
        for fp in chunk_paths:
            p = Path(fp)
            payload_files.append({"name": p.name, "content": p.read_text(encoding="utf-8"), "path": str(p)})

        body = {
            "target_lang": TARGET_LANG,
            "files": [{"name": x["name"], "content": x["content"]} for x in payload_files],
        }
        try:
            data = api_post("/v1/tools/json-translate/batch", body)
        except urllib.error.HTTPError as e:
            print(f"::error::Routara API HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
            sys.exit(1)

        results = data.get("results") or []
        by_name = {r.get("name"): r for r in results}
        for item in payload_files:
            name = item["name"]
            out_path = Path(item["path"])
            row = by_name.get(name)
            if not row:
                print(f"::warning::No result for {name}", file=sys.stderr)
                continue
            if row.get("error"):
                print(f"::error::FAIL {name}: {row['error']}", file=sys.stderr)
                sys.exit(1)
            if not row.get("validation_passed", True):
                validation_warnings += 1
                print(
                    f"::warning::Validation warning for {name}: {row.get('validation_details', '')}",
                    file=sys.stderr,
                )
                if FAIL_ON_VALIDATION:
                    print(f"::error::Validation failed for {name}", file=sys.stderr)
                    sys.exit(1)
            out_path.write_text(row.get("output") or "", encoding="utf-8")
            files_written += 1
            print(f"Wrote {out_path}")

    write_outputs(files_written, validation_warnings)
    print(f"Done — {files_written}/{len(FILES)} files translated")


if __name__ == "__main__":
    main()
