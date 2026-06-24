# Routara JSON Translate 鈥?GitHub Action

[![GitHub release](https://img.shields.io/github/v/release/36412749-collab/json-translate-action)](https://github.com/36412749-collab/json-translate-action/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)

Translate JSON i18n locale files in CI/CD with **AST key-path validation** and **automatic repair** 鈥?not generic ChatGPT copy-paste.

![ChatGPT vs Routara JSON translation](assets/chatgpt-vs-routara.svg)

## Why not ChatGPT?

| | Generic ChatGPT | **Routara JSON Translate** |
|---|---|---|
| Key paths | Often renamed or dropped | **Validated** 鈥?every path must match |
| Output format | Wrapped in ` ```json ` fences | **Auto-stripped**, valid JSON only |
| Failed structure | Manual fix | **Auto-repair retry** (1 round) |
| CI integration | Copy-paste | **Native GitHub Action** |
| Large repos | HTTP timeout risk | **Async queue** + ZIP download |
| Cost to try | ChatGPT Plus | **Free tier** + **$1 promo credit** on signup |

**Get started:** [routara.ai/#auth](https://routara.ai/#auth) 鈥?sign up, create an API key (`sk-or-v1-...`), receive **$1 promo credit** to test routing and tools.

**Live tool:** [routara.ai/tools/json-translate](https://routara.ai/tools/json-translate)

---

## Quick start

```yaml
name: Translate locale JSON

on:
  workflow_dispatch:
  push:
    paths:
      - 'locales/**.json'

jobs:
  i18n:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Translate JSON with Routara
        uses: 36412749-collab/json-translate-action@v1
        with:
          api-key: ${{ secrets.ROUTARA_API_KEY }}
          target-lang: en
          glob: 'locales/**/*.json'

      - name: Commit translations
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: 'chore(i18n): update locale JSON via Routara'
```

> Marketplace publish: GitHub repo 鈫?**Actions** tab 鈫?**Publish to Marketplace** (one-time, requires maintainer login). See [Marketplace guide](https://github.com/36412749-collab/json-translate-action#quick-start).

---

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `api-key` | 鉁?| 鈥?| Routara API key (`sk-or-v1-...`) |
| `target-lang` | 鉁?| 鈥?| Target locale (`en`, `ja`, `zh-CN`, 鈥? |
| `glob` | | `**/*.json` | Bash globstar pattern |
| `api-base` | | `https://api.routara.ai` | API base URL |
| `locale` | | `en` | `Accept-Language` for API errors |
| `fail-on-validation` | | `false` | Fail step on validation warnings |
| `async-mode` | | `auto` | `auto` / `true` / `false` 鈥?async for large batches |
| `max-files-per-request` | | `5` | Sync chunk size (free tier cap) |
| `poll-seconds` | | `5` | Async job poll interval |
| `poll-timeout-seconds` | | `1800` | Max async wait (30 min) |

## Outputs

| Output | Description |
|--------|-------------|
| `files-count` | Files matched by glob |
| `files-written` | Files successfully translated |
| `validation-warnings` | Files with structure warnings |

---

## How it works

1. **Match** JSON files via glob.
2. **Sync mode** (鈮? files by default): chunked `POST /v1/tools/json-translate/batch`.
3. **Async mode** (>5 files or `async-mode: true`): `POST .../batch/async` 鈫?poll job 鈫?download ZIP.
4. **Validate** each output: JSON key paths must match source; failed runs trigger one repair retry.
5. **Write** translated files in place (same paths as matched).

---

## Async mode for large monorepos

```yaml
- uses: 36412749-collab/json-translate-action@v1
  with:
    api-key: ${{ secrets.ROUTARA_API_KEY }}
    target-lang: de
    glob: 'apps/**/locales/**/*.json'
    async-mode: true
    poll-timeout-seconds: '3600'
```

Async jobs run on Routara's Redis worker queue 鈥?no gateway timeout on 50+ file batches.

---

## Limits

| Tier | Sync batch | Async batch | Daily tool runs |
|------|------------|-------------|-----------------|
| Free (verified email) | 5 files/request | 20 files/job | 30/day per tool |
| VIP | 10 files/request | 100 files/job | Unlimited |

Verify your email at [routara.ai](https://routara.ai) to unlock the full free daily quota.

---

## Related

- [Markdown translate](https://routara.ai/tools/markdown-translate)
- [SRT subtitle translate](https://routara.ai/tools/srt-translate)
- [MCP for Cursor](https://github.com/36412749-collab/routara-mcp) 鈥?`npx -y routara-mcp`
- API docs 鈥?[routara.ai/#docs](https://routara.ai/#docs)

## License

MIT 鈥?Routara 漏 2026
