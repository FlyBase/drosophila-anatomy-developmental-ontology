#!/usr/bin/env python3
"""Check that foaf:depiction URLs in an OBO file resolve.

Writes a TSV report with one row per distinct URL. Failures (non-2xx
responses or network errors) are listed first, then the remaining URLs
in ascending alphabetical order. Exits 0 regardless of failures, but
prints a warning to stderr if any URL failed to resolve.
"""

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

DEPICTION_RE = re.compile(r'foaf:depiction\s+"([^"]+)"')
TIMEOUT = 20
WORKERS = 8
USER_AGENT = "fbbt-depiction-check/1.0 (+https://github.com/FlyBase/drosophila-anatomy-developmental-ontology)"


def extract_urls(path):
    urls = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = DEPICTION_RE.search(line)
            if m:
                urls.add(m.group(1))
    return urls


def check(url):
    try:
        r = requests.head(
            url, timeout=TIMEOUT, allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        if r.status_code >= 400 or r.status_code == 405:
            r = requests.get(
                url, timeout=TIMEOUT, allow_redirects=True, stream=True,
                headers={"User-Agent": USER_AGENT},
            )
            r.close()
        return url, r.status_code, r.status_code < 400, ""
    except requests.RequestException as e:
        return url, "", False, type(e).__name__ + ": " + str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="OBO file to scan")
    ap.add_argument("-o", "--output", required=True, help="report path")
    args = ap.parse_args()

    urls = sorted(extract_urls(args.input))
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(check, u): u for u in urls}
        for fut in as_completed(futures):
            results.append(fut.result())

    failures = sorted(r for r in results if not r[2])
    successes = sorted(r for r in results if r[2])

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("url\tstatus\tok\terror\n")
        for url, status, ok, err in failures + successes:
            f.write(f"{url}\t{status}\t{'OK' if ok else 'FAIL'}\t{err}\n")

    if failures:
        print(
            f"WARNING: {len(failures)} of {len(results)} foaf:depiction "
            f"URL(s) failed to resolve. See {args.output}.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
