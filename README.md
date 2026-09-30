# GitHub Actions RSS Fetcher

This repository-ready setup reads RSS/Atom URLs from `list.txt`, fetches every feed, saves the exact raw HTTP response for each feed under `sample/`, and creates `sample/news.json` containing the parsed article `title`, `link`, and normalized UTC `time`.

The GitHub Actions workflow runs automatically at the start of every hour (`0 * * * *`) and can also be started manually from the **Actions** tab.

The workflow commits changed files in `sample/` back to the repository, so the results remain available after the runner finishes. It uses the repository's built-in `GITHUB_TOKEN` with `contents: write` permission.

No external Python packages are required; the script uses only Python's standard library.

## Output

Each feed gets a deterministic, unique filename such as:

```text
sample/001_example.com_1a2b3c4d.xml
```

`sample/news.json` has this shape:

```json
[
  {
    "title": "Example headline",
    "link": "https://example.com/article",
    "time": "2026-09-30T14:00:00Z"
  }
]
```

RSS `pubDate` and Atom `published`/`updated` timestamps are normalized to UTC ISO 8601 when possible.

## Local test

From the repository root:

```bash
python rss_fetch.py
```

To make feed failures return a non-zero exit code:

```bash
python rss_fetch.py --strict
```
