#!/usr/bin/env python3
"""Data-only publish for the Home Tracker dashboard.

The scheduled run owns the DATA. Interactive sessions own the CHROME (the CSS,
the markup and the render JS). Copying the run's whole rebuilt HTML over
index.html silently reverts any styling a session pushed while the run was
working -- that is exactly what happened on 2026-07-30 (a0dc099 reverted the
black theme from ba94ee7, four minutes after it landed).

So: never publish the run's own file. Take the CURRENT origin/main index.html
as the base and swap in only its <script id="tracker-data"> block.

    python3 publish_data_only.py <fresh-clone-dir> <freshly-built-dashboard.html>

Exits non-zero, having written nothing, if either file lacks the data block.
Prints a CHROME-DRIFT notice (not an error) when the remote chrome differs from
the run's own template, which is the normal signal that a session restyled the
page mid-run.
"""
import io
import os
import re
import sys

TAG = re.compile(r'(?s)<script id="tracker-data" type="application/json">.*?</script>')


def read(p):
    return io.open(p, encoding="utf-8").read()


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: publish_data_only.py <clone-dir> <built-dashboard.html>")
    clone, built_path = sys.argv[1], sys.argv[2]
    base_path = os.path.join(clone, "index.html")

    built = read(built_path)
    base = read(base_path)

    mb = TAG.search(built)
    if not mb:
        sys.exit("ABORT: no tracker-data block in the freshly built dashboard -- publishing nothing")
    if not TAG.search(base):
        sys.exit("ABORT: no tracker-data block in origin/main index.html -- publishing nothing")

    payload = mb.group(0)
    # lambda, not a replacement string: the JSON is full of backslashes.
    out = TAG.sub(lambda _: payload, base, count=1)

    # Informational: did a session restyle the page while this run was working?
    chrome_base = TAG.sub(lambda _: "@@DATA@@", base)
    chrome_built = TAG.sub(lambda _: "@@DATA@@", built)
    if chrome_base != chrome_built:
        import difflib
        d = [l for l in difflib.unified_diff(
            chrome_built.splitlines(), chrome_base.splitlines(),
            "run-template", "origin/main", lineterm="", n=0)][:40]
        print("CHROME-DRIFT: origin/main's page differs from this run's template.")
        print("Keeping origin/main's version -- the session's edits win. First lines:")
        print("\n".join(d))
    else:
        print("chrome identical to origin/main")

    if out == base:
        print("NO-DATA-CHANGE: tracker-data is byte-identical to origin/main -- skip the commit")
        return 2

    io.open(base_path, "w", encoding="utf-8").write(out)
    print("wrote %s (%d bytes, data block %d bytes)" % (base_path, len(out), len(payload)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
