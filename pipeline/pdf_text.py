"""
Helper for STEP 1 — read the press release PDFs.

Not a pipeline step of its own. fetch.py uses this to pull the sentences that
mention money out of each release, so transform.py can turn them into
numbers. We keep the sentence, not just the figure, so every dollar amount on
the site can be traced back to the words it came from.

PDFs are cached under data/raw/pdf/ (gitignored) and only downloaded once.
"""
import hashlib
import io
import re

import requests
from pypdf import PdfReader

from common import DATA

CACHE = DATA / "raw" / "pdf"

# Money written as digits ($243,000 / $2.5 million) or words ($3 Million).
MONEY = re.compile(
    r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(billion|million|thousand|k\b)?",
    re.I,
)

MAX_PAGES = 6          # press releases are short; this is generous
WINDOW = 130           # characters of context kept either side of a figure
MAX_MENTIONS = 8       # money mentions stored per release
SEP = " ¦ "            # separates mentions inside the stored field


def cache_path(url):
    name = hashlib.sha1(url.encode("utf-8")).hexdigest()[:20]
    return CACHE / f"{name}.pdf"


def download(url, session, timeout=90):
    """Return PDF bytes, from cache when we already have them."""
    path = cache_path(url)
    if path.exists() and path.stat().st_size > 0:
        return path.read_bytes()

    r = session.get(url, timeout=timeout)
    r.raise_for_status()

    ctype = r.headers.get("Content-Type", "")
    if "pdf" not in ctype.lower() and not r.content.startswith(b"%PDF"):
        raise ValueError(f"not a PDF (Content-Type: {ctype or 'none'})")

    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return r.content


def extract_text(blob):
    reader = PdfReader(io.BytesIO(blob))
    parts = []
    for page in reader.pages[:MAX_PAGES]:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    text = "\n".join(parts)
    # PDF extraction leaves ragged whitespace and hyphenated line breaks.
    text = text.replace("­", "").replace("-\n", "")
    return re.sub(r"\s+", " ", text).strip()


def money_mentions(text):
    """A tight window of words around each dollar figure in the release.

    Whole sentences are the wrong unit here. DOI releases routinely state a
    defendant's annual salary two clauses away from the amount they are
    accused of stealing, and PDF headers run together into 300-character
    pseudo-sentences. A narrow window around each figure keeps the words that
    actually govern it, so transform.py can tell a salary from a theft.
    """
    if not text:
        return ""
    out, seen = [], set()
    for m in MONEY.finditer(text):
        start = max(0, m.start() - WINDOW)
        end = min(len(text), m.end() + WINDOW)
        # Do not cut mid-word at either edge.
        chunk = text[start:end]
        if start > 0:
            chunk = chunk.partition(" ")[2]
        if end < len(text):
            chunk = chunk.rpartition(" ")[0]
        chunk = chunk.strip()
        if not chunk:
            continue
        key = re.sub(r"\W+", "", chunk.lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(chunk)
        if len(out) >= MAX_MENTIONS:
            break
    return SEP.join(out)


def release_money_context(url, session):
    """(money_context, text_chars, note) for one press release PDF."""
    try:
        blob = download(url, session)
    except Exception as e:
        return "", 0, f"download failed: {type(e).__name__}"

    try:
        text = extract_text(blob)
    except Exception as e:
        return "", 0, f"unreadable pdf: {type(e).__name__}"

    if not text:
        # Almost always a scanned image with no text layer.
        return "", 0, "no text layer"

    return money_mentions(text), len(text), ""
