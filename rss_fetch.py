#!/usr/bin/env python3
"""Fetch RSS/Atom feeds listed in list.txt and write results to sample/."""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIST_FILE = ROOT / "list.txt"
SAMPLE_DIR = ROOT / "sample"
USER_AGENT = "github-rss-action/1.0 (+https://github.com/)"
TIMEOUT_SECONDS = 30


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def first_child_text(element: ET.Element, names: set[str]) -> str:
    for child in element:
        if local_name(child.tag) in names:
            text = clean_text(child.text)
            if text:
                return text
    return ""


def parse_datetime(value: str) -> str:
    value = value.strip()
    if not value:
        return ""

    # RFC 2822 / RSS pubDate.
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError):
        pass

    # ISO 8601 / Atom timestamps.
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return value


def find_link(entry: ET.Element) -> str:
    for child in entry:
        if local_name(child.tag) != "link":
            continue
        href = clean_text(child.attrib.get("href"))
        rel = child.attrib.get("rel", "alternate").lower()
        text = clean_text(child.text)
        if href and rel in {"alternate", ""}:
            return href
        if text:
            return text
    return ""


def parse_feed(data: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(data)
    entries: list[dict[str, str]] = []

    # RSS/Atom both use item/entry records. We identify by local name so common
    # namespaces such as Atom, DC and Content do not matter.
    for element in root.iter():
        if local_name(element.tag) not in {"item", "entry"}:
            continue

        title = first_child_text(element, {"title"})
        link = first_child_text(element, {"link"}) or find_link(element)
        published = first_child_text(
            element,
            {"pubdate", "published", "updated", "date", "issued", "modified"},
        )

        # Skip completely empty records, but keep records that lack one field.
        if title or link or published:
            entries.append(
                {
                    "title": title,
                    "link": link,
                    "time": parse_datetime(published),
                }
            )

    return entries


def safe_feed_name(url: str, index: int) -> str:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc or parsed.path.split("/", 1)[0]
    host = host.split("@")[-1].split(":")[0]
    host = re.sub(r"[^A-Za-z0-9._-]+", "_", host).strip("._-") or "feed"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"{index:03d}_{host}_{digest}.xml"


def read_urls() -> list[str]:
    if not LIST_FILE.exists():
        raise FileNotFoundError(f"Missing {LIST_FILE.name}")

    urls: list[str] = []
    for raw_line in LIST_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parsed = urllib.parse.urlparse(line)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            print(f"WARNING: skipping invalid URL: {line}", file=sys.stderr)
            continue
        urls.append(line)
    return urls


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            "Accept-Encoding": "identity",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any feed fails")
    args = parser.parse_args()

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    # Remove previous generated output so removed/failed feeds do not leave stale files.
    for path in SAMPLE_DIR.glob("*.xml"):
        path.unlink()
    news_json = SAMPLE_DIR / "news.json"
    if news_json.exists():
        news_json.unlink()

    urls = read_urls()
    all_news: list[dict[str, str]] = []
    failures = 0

    print(f"Found {len(urls)} feed URL(s) in {LIST_FILE.name}.")

    for index, url in enumerate(urls, start=1):
        filename = SAMPLE_DIR / safe_feed_name(url, index)
        print(f"[{index}/{len(urls)}] Fetching {url}")
        try:
            raw = fetch(url)
            filename.write_bytes(raw)
            print(f"  saved raw response: {filename.relative_to(ROOT)} ({len(raw)} bytes)")
            try:
                items = parse_feed(raw)
                all_news.extend(items)
                print(f"  parsed {len(items)} item(s)")
            except ET.ParseError as exc:
                failures += 1
                print(f"  WARNING: XML parse failed: {exc}", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            failures += 1
            print(f"  WARNING: fetch failed: {exc}", file=sys.stderr)
        except Exception as exc:  # Keep one broken feed from stopping the remaining feeds.
            failures += 1
            print(f"  WARNING: unexpected error: {exc}", file=sys.stderr)

    news_json.write_text(
        json.dumps(all_news, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(all_news)} news item(s) to {news_json.relative_to(ROOT)}.")

    if failures:
        print(f"Completed with {failures} feed failure(s).", file=sys.stderr)
        return 1 if args.strict else 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
